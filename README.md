# LLM Observability with OpenTelemetry + Azure Monitor

Containerized multi-agent LangGraph sample instrumented with OpenTelemetry exporting traces to Azure Monitor / Application Insights and leveraging a Log Analytics workspace for deeper analysis.

## Project Structure

```
├── src/
│   └── agent/
│       ├── app.py              # FastAPI service exposing /run and /health
│       ├── agents.py           # Planner / Worker / Reviewer agents
│       ├── graph.py            # LangGraph workflow assembly
│       ├── instrumentation.py  # OpenTelemetry + Azure Monitor exporter setup
│       └── __init__.py
├── test/test_graph.py          # Basic invocation test (root-level test directory)
├── pyproject.toml              # Modern project metadata & dependency management
├── infrastructure/             # Terraform IaC for Azure resources
│   ├── providers.tf
│   ├── variables.tf
│   ├── main.tf
│   └── outputs.tf
├── data/                       # Placeholder for future data assets
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Features

* Multi-agent workflow (planner → worker → reflection → reviewer) using LangGraph.
* OpenTelemetry tracing with custom spans per agent.
* Azure Monitor / Application Insights exporter via connection string.
* Containerized FastAPI service (Dockerfile + docker-compose).
* Terraform deployment for: Resource Group, Log Analytics Workspace, Application Insights, Container Apps Environment & Container App, Azure OpenAI (Cognitive) account.

## Prerequisites

* Python 3.11+
* Docker / Docker Compose
* Terraform >= 1.6.0
* Azure CLI authenticated (`az login`)

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # or: pip install -e .[dev]
pytest -q  # configured via pyproject to look in `test/`
cp .env.example .env  # then edit secrets before running
uvicorn src.agent.app:app --reload
```

Visit: http://localhost:8000/health then POST a task:

```bash
curl -X POST http://localhost:8000/run -H 'Content-Type: application/json' -d '{"task": "Outline observability advantages"}' | jq
```

### Enabling Real LLM Calls

Set one of the following environment variables before starting `uvicorn` or in `docker-compose.yml`:

* `OPENAI_API_KEY` with optional `OPENAI_BASE_URL`
* `GITHUB_MODELS_API_KEY` with `GITHUB_MODELS_BASE_URL=https://models.github.ai/inference/` (GitHub Models endpoint)

Otherwise the app returns stub responses.

### Telemetry Export

Provide `APPINSIGHTS_CONNECTION_STRING` (from Terraform output or existing resource) to enable Azure Monitor export. Without it spans stay local/no-op.

### .env & Terraform Variable Overrides
### Azure OpenAI Usage

Terraform now provisions an Azure OpenAI (Cognitive Services) account. Deployment creation may require enabling the preview feature or manual portal deployment if the `azurerm_cognitive_deployment` resource is not supported in your provider version. The app automatically prefers Azure OpenAI when `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_DEPLOYMENT` are set (injected by Terraform into the Container App). For local use:

```bash
export AZURE_OPENAI_ENDPOINT="https://<your-resource>.openai.azure.com"
export AZURE_OPENAI_API_KEY="<key>"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"
export AZURE_OPENAI_API_VERSION=2024-08-01-preview
uvicorn src.agent.app:app --reload
```

The code builds a deployment-specific base URL and appends `api-version` as a query parameter.

Copy `.env.example` to `.env` and fill in secrets. Terraform variable overrides can be set by editing `TF_VAR_*` entries or exporting them in your shell (e.g. `export TF_VAR_prefix=llmobs2`). The application reads runtime variables directly from `.env` (when using `docker compose`) or your shell environment.

## Docker

Build and run locally:

```bash
docker compose build
docker compose up -d
curl -X POST http://localhost:8000/run -H 'Content-Type: application/json' -d '{"task": "Demo docker run"}'
```

## Terraform Deployment

Navigate to `infrastructure/` and deploy resources.

```bash
cd infrastructure
terraform init
terraform validate
terraform plan -out tfplan
terraform apply -auto-approve tfplan
```

After apply, note outputs:

* `container_app_url` – public FQDN to call `/run`.
* `app_insights_connection_string` – feed into container app env var for telemetry export (already wired in `main.tf`).

### Update Container Image

Push your built image (e.g., to GHCR) and update `var.container_image` via `-var` or edit `variables.tf`.

### Observability Verification

1. Invoke endpoint several times.
2. In Azure Portal open Application Insights → Transactions / Traces to view spans (`planner.agent`, `worker.agent`, `reflection.agent`, `reviewer.agent`).
3. Use Log Analytics with query:

```kusto
traces
| where customDimensions.service_name == "langgraph-multi-agent"
| take 20
```

## Environment Variables Summary

| Variable | Purpose |
|----------|---------|
| `APPINSIGHTS_CONNECTION_STRING` | Enables Azure Monitor export |
| `SERVICE_NAME` | Service identity in telemetry |
| `SERVICE_VERSION` | Version tag for traces |
| `DEPLOYMENT_ENV` | Environment dimension (local/docker/azure) |
| `OPENAI_API_KEY` / `GITHUB_MODELS_API_KEY` | LLM provider auth |
| `MODEL_NAME` | Model identifier (default `openai/gpt-4o-mini`) |
| `AZURE_OPENAI_ENDPOINT` | Base endpoint for Azure OpenAI (Cognitive) |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name (model deployment in Azure) |
| `AZURE_OPENAI_API_VERSION` | API version query param appended |
| `AZURE_OPENAI_API_KEY` | Key for Azure OpenAI account |

## PyProject Usage

You can alternatively install using the modern PEP 621 metadata:

```bash
pip install -e .[dev]
```

This makes the `src/` layout importable and adds pytest as a dev dependency. The test discovery is configured in `pyproject.toml` to only scan the single `test/` directory.

## Next Steps / Enhancements

* Add metrics & logs exporters (extend `instrumentation.py`).
* Add semantic caching / RAG layer and trace retrieval latency.
* Integrate LangChain callbacks for token usage metrics.
* Add autoscaling policies (KEDA) for Container App.
* Add CI pipeline for building/pushing image & terraform apply.
* Security hardening: Managed Identity for Container App, key vault for secrets.

## License

See [LICENSE](LICENSE).

