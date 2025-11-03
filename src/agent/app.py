"""FastAPI entrypoint exposing multi-agent LangGraph workflow.
Run locally:
  uvicorn src.agent.app:app --reload
"""

from fastapi import FastAPI
from pydantic import BaseModel
from .graph import build_graph

app = FastAPI(title="LangGraph Multi-Agent Demo", version="0.1.0")

# Auto-instrument FastAPI to generate request spans in addition to custom agent spans.
# Safe to call multiple times; instrumentation library guards against duplicate patches.
try:  # noqa: SIM105
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore

    FastAPIInstrumentor.instrument_app(app)
except Exception:  # pragma: no cover - if instrumentation not available or errors, continue
    pass

_graph = build_graph()


class RunRequest(BaseModel):
    task: str


@app.post("/run")
def run_graph(req: RunRequest):
    state = {"task": req.task}
    result = _graph.invoke(state)
    return {
        "task": req.task,
        "plan": result.get("plan"),
        "work": result.get("work"),
        "review": result.get("review"),
    }


@app.get("/health")
def health():
    return {"status": "ok"}
