"""OpenTelemetry + Azure Monitor instrumentation helpers.

Sets up tracing, metrics, and logs export to Azure Monitor (App Insights + Log Analytics).
Requires environment variable APPINSIGHTS_CONNECTION_STRING.
"""
from __future__ import annotations
import os
from functools import wraps
from typing import Callable, Any, Dict

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

_tracer_initialized = False

def _init_tracer() -> None:
    global _tracer_initialized
    if _tracer_initialized:
        return
    connection_string = os.getenv("APPINSIGHTS_CONNECTION_STRING")
    if not connection_string:
        # No Azure Monitor exporter active; use default noop provider.
        _tracer_initialized = True
        return
    resource = Resource.create({
        "service.name": os.getenv("SERVICE_NAME", "langgraph-multi-agent"),
        "service.version": os.getenv("SERVICE_VERSION", "0.1.0"),
        "deployment.environment": os.getenv("DEPLOYMENT_ENV", "local"),
    })
    provider = TracerProvider(resource=resource)
    exporter = AzureMonitorTraceExporter.from_connection_string(connection_string)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    _tracer_initialized = True

def get_tracer():
    _init_tracer()
    return trace.get_tracer(__name__)

def traced_span(name: str, attributes: Dict[str, Any] | None = None):
    attributes = attributes or {}
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(name) as span:
                for k, v in attributes.items():
                    span.set_attribute(k, v)
                try:
                    result = func(*args, **kwargs)
                    # Add simple state size metric on exit if dict
                    if isinstance(result, dict):
                        span.set_attribute("state.keys", len(result.keys()))
                except Exception as e:  # noqa: BLE001
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                    raise
                return result
        return wrapper
    return decorator
