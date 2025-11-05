"""FastAPI entrypoint exposing multi-agent LangGraph workflow.
Run locally:
  uvicorn src.agent.app:app --reload
"""

from fastapi import FastAPI
from pydantic import BaseModel
from .graph import build_graph
from .instrumentation import get_tracer

# Initialize tracer FIRST before creating the app
# This ensures OpenTelemetry is ready for FastAPI instrumentation
_tracer = get_tracer()

app = FastAPI(title="LangGraph Multi-Agent Demo", version="0.1.0")

# Auto-instrument FastAPI to generate request spans in addition to custom agent spans.
# Safe to call multiple times; instrumentation library guards against duplicate patches.
try:  # noqa: SIM105
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore

    FastAPIInstrumentor.instrument_app(app)
except Exception as e:  # pragma: no cover
    print(f"Warning: FastAPI instrumentation failed: {e}")
    pass

_graph = build_graph()


class RunRequest(BaseModel):
    task: str


@app.post("/run")
def run_graph(req: RunRequest):
    """Execute the multi-agent workflow with full OpenTelemetry tracing.
    
    This endpoint creates a parent span 'workflow.execution' that contains
    all agent spans and LLM calls, providing end-to-end observability.
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("workflow.execution") as span:
        # Add request attributes to the workflow span
        span.set_attribute("workflow.task", req.task)
        span.set_attribute("workflow.task_length", len(req.task))
        
        state = {"task": req.task}
        result = _graph.invoke(state)
        
        # Add result metrics
        span.set_attribute("workflow.completed", True)
        if result.get("plan"):
            span.set_attribute("workflow.plan_length", len(result["plan"]))
        if result.get("work"):
            span.set_attribute("workflow.work_length", len(result["work"]))
        if result.get("review"):
            span.set_attribute("workflow.review_length", len(result["review"]))
        
        return {
            "task": req.task,
            "plan": result.get("plan"),
            "work": result.get("work"),
            "review": result.get("review"),
        }


@app.get("/health")
def health():
    return {"status": "ok"}
