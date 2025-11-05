"""OpenTelemetry + Azure Monitor instrumentation helpers.

Sets up tracing, metrics, and logs export to Azure Monitor (App Insights + Log Analytics).
Requires environment variable APPINSIGHTS_CONNECTION_STRING.
Provides comprehensive LLM call tracing with token usage and latency metrics.
"""

from __future__ import annotations
import os
import time
from functools import wraps
from typing import Callable, Any, Dict

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

_tracer_initialized = False
_in_memory_spans = []


class _InMemoryExporter(SpanExporter):
    """Simple in-memory exporter for testing spans without monkeypatching.

    Enabled when environment variable OTEL_INMEMORY_EXPORTER is truthy ("1", "true", etc.).
    """

    def export(self, spans):  # type: ignore[override]
        _in_memory_spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self):  # type: ignore[override]
        return


def get_in_memory_spans():  # pragma: no cover - accessor trivial
    return list(_in_memory_spans)


def reset_in_memory_spans():  # pragma: no cover - test helper
    _in_memory_spans.clear()


def _init_tracer() -> None:
    global _tracer_initialized
    if _tracer_initialized:
        return
    connection_string = os.getenv("APPINSIGHTS_CONNECTION_STRING")
    enable_in_memory = os.getenv("OTEL_INMEMORY_EXPORTER", "").lower() in {"1", "true", "yes"}
    resource = Resource.create(
        {
            "service.name": os.getenv("SERVICE_NAME", "langgraph-multi-agent"),
            "service.version": os.getenv("SERVICE_VERSION", "0.1.0"),
            "deployment.environment": os.getenv("DEPLOYMENT_ENV", "local"),
        }
    )
    provider = TracerProvider(resource=resource)

    if connection_string:
        exporter = AzureMonitorTraceExporter.from_connection_string(connection_string)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    if enable_in_memory:
        provider.add_span_processor(SimpleSpanProcessor(_InMemoryExporter()))

    if connection_string or enable_in_memory:
        trace.set_tracer_provider(provider)
    
    # Auto-instrument HTTP clients for outbound LLM API calls
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        HTTPXClientInstrumentor().instrument()
        RequestsInstrumentor().instrument()
    except Exception:  # pragma: no cover
        pass  # Continue if instrumentation libraries not available
    
    _tracer_initialized = True


def get_tracer():
    _init_tracer()
    return trace.get_tracer(__name__)


def traced_span(name: str, attributes: Dict[str, Any] | None = None):
    """Decorator to create a traced span with custom attributes.
    
    Args:
        name: Span name (e.g., 'planner.agent', 'llm.call')
        attributes: Optional dict of attributes to add to span
    """
    attributes = attributes or {}

    def decorator(func: Callable[..., Any]):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(name) as span:
                # Set initial attributes
                for k, v in attributes.items():
                    span.set_attribute(k, v)
                
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    # Add simple state size metric on exit if dict
                    if isinstance(result, dict):
                        span.set_attribute("state.keys", len(result.keys()))
                        # Add state content size estimate
                        total_size = sum(len(str(v)) for v in result.values())
                        span.set_attribute("state.content_size", total_size)
                    
                    # Add duration metric
                    duration_ms = (time.time() - start_time) * 1000
                    span.set_attribute("duration_ms", round(duration_ms, 2))
                    span.set_status(trace.Status(trace.StatusCode.OK))
                except Exception as e:  # noqa: BLE001
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
                return result

        return wrapper

    return decorator


def trace_llm_call(model: str, prompt: str, max_tokens: int = 256):
    """Context manager for tracing LLM calls with detailed metrics.
    
    Usage:
        tracer = get_tracer()
        with tracer.start_as_current_span('llm.call') as span:
            trace_llm_call_attributes(span, model, prompt, max_tokens)
            # ... make LLM call ...
            trace_llm_response(span, response)
    """
    tracer = get_tracer()
    span = tracer.start_as_current_span(
        "llm.call",
        attributes={
            "llm.model": model,
            "llm.request.max_tokens": max_tokens,
            "llm.request.prompt_length": len(prompt),
            "llm.system": "azure_openai" if "azure" in model.lower() else "openai",
        }
    )
    return span


def add_llm_response_attributes(span: trace.Span, response: Any) -> None:
    """Add LLM response attributes to an existing span.
    
    Args:
        span: Active OpenTelemetry span
        response: OpenAI completion response object
    """
    try:
        if hasattr(response, "usage"):
            # Token usage metrics
            if response.usage:
                span.set_attribute("llm.usage.prompt_tokens", response.usage.prompt_tokens)
                span.set_attribute("llm.usage.completion_tokens", response.usage.completion_tokens)
                span.set_attribute("llm.usage.total_tokens", response.usage.total_tokens)
        
        if hasattr(response, "choices") and response.choices:
            choice = response.choices[0]
            if hasattr(choice, "message"):
                content = choice.message.content or ""
                span.set_attribute("llm.response.length", len(content))
                span.set_attribute("llm.response.finish_reason", choice.finish_reason or "unknown")
        
        if hasattr(response, "model"):
            span.set_attribute("llm.response.model", response.model)
    except Exception:  # pragma: no cover
        pass  # Don't fail if response structure is unexpected
