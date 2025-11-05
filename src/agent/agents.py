from typing import Dict, Any
import os
from .instrumentation import traced_span, get_tracer, add_llm_response_attributes

# Simple placeholder LLM call; replace with real model (GitHub Models / Azure OpenAI)
# If OPENAI_API_KEY or GITHUB_MODELS_API_KEY not set, returns stub output.


def _call_llm(prompt: str, operation: str = "llm.completion") -> str:
    """Make an LLM call with comprehensive OpenTelemetry tracing.
    
    Args:
        prompt: The prompt to send to the LLM
        operation: Operation name for the span (e.g., 'llm.completion.planner')
    
    Returns:
        The LLM response text
    """
    # Prefer Azure OpenAI if endpoint is present
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    api_key = azure_key or os.getenv("OPENAI_API_KEY") or os.getenv("GITHUB_MODELS_API_KEY")
    if not api_key:
        return f"[stub-response] {prompt[:80]}..."
    
    tracer = get_tracer()
    
    try:
        if azure_endpoint and azure_deployment:
            # Use AzureOpenAI client for Azure endpoints
            from openai import AzureOpenAI  # type: ignore

            with tracer.start_as_current_span(operation) as span:
                # Set LLM-specific attributes
                span.set_attribute("llm.system", "azure_openai")
                span.set_attribute("llm.model", azure_deployment)
                span.set_attribute("llm.request.max_tokens", 256)
                span.set_attribute("llm.request.prompt_length", len(prompt))
                span.set_attribute("llm.azure.endpoint", azure_endpoint)
                span.set_attribute("llm.azure.api_version", azure_api_version)
                
                client = AzureOpenAI(
                    api_key=azure_key,
                    azure_endpoint=azure_endpoint,
                    api_version=azure_api_version,
                )
                
                completion = client.chat.completions.create(
                    model=azure_deployment,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=256,
                )
                
                # Add response metrics to span
                add_llm_response_attributes(span, completion)
                
                result = completion.choices[0].message.content or ""
                span.set_attribute("llm.response.length", len(result))
                return result
        else:
            # Use standard OpenAI client for OpenAI or GitHub Models
            from openai import OpenAI  # type: ignore

            base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("GITHUB_MODELS_BASE_URL")
            model_name = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")
            
            with tracer.start_as_current_span(operation) as span:
                span.set_attribute("llm.system", "openai")
                span.set_attribute("llm.model", model_name)
                span.set_attribute("llm.request.max_tokens", 256)
                span.set_attribute("llm.request.prompt_length", len(prompt))
                if base_url:
                    span.set_attribute("llm.base_url", base_url)
                
                client = (
                    OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
                )
                
                completion = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=256,
                )
                
                # Add response metrics to span
                add_llm_response_attributes(span, completion)
                
                result = completion.choices[0].message.content or ""
                span.set_attribute("llm.response.length", len(result))
                return result
    except Exception as e:  # noqa: BLE001
        return f"[llm-error-fallback] {e}"


@traced_span("planner.agent")
def planner_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    task = state.get("task", "")
    plan = _call_llm(f"Create a concise 2-step plan for: {task}", "llm.completion.planner")
    state["plan"] = plan
    return state


@traced_span("worker.agent")
def worker_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    plan = state.get("plan", "")
    work = _call_llm(f"Execute the following plan and produce a result. Plan: {plan}", "llm.completion.worker")
    state["work"] = work
    return state


@traced_span("reflection.agent")
def reflection_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Lightweight validation / reflection stage.

    Heuristics (stub when no real LLM key):
      - Check length of work output
      - Provide a short critique and improvement suggestion
    Could be extended to trigger a corrective iteration.
    """
    work = state.get("work", "")
    length = len(work)
    critique_prompt = (
        "Act as a senior reviewer. Provide a terse validation summary and one improvement suggestion. "
        f"The current work output (len={length}) is: {work}"
    )
    reflection = _call_llm(critique_prompt, "llm.completion.reflection")
    state["reflection"] = reflection
    return state


@traced_span("reviewer.agent")
def reviewer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    work = state.get("work", "")
    reflection = state.get("reflection", "")
    review = _call_llm(
        "Review the following work taking into account prior reflection. Provide FINAL summary only. "
        f"Work: {work}\nReflection: {reflection}",
        "llm.completion.reviewer"
    )
    state["review"] = review
    return state


__all__ = ["planner_agent", "worker_agent", "reflection_agent", "reviewer_agent"]
