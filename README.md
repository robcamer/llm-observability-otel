# LLM Observability with OpenTelemetry + Azure Monitor

Containerized multi-agent LangGraph sample instrumented with OpenTelemetry exporting traces to Azure Monitor / Application Insights and leveraging a Log Analytics workspace for deeper analysis.

## Project Structure

```
├── src/
│   └── agent/
│       ├── app.py              # FastAPI service exposing /run and /health
│       ├── agents.py           # Planner / Worker / Reflection / Reviewer agents
│       ├── graph.py            # LangGraph workflow assembly
│       ├── instrumentation.py  # OpenTelemetry + Azure Monitor exporter setup
│       └── __init__.py
├── test/test_graph.py          # Basic workflow invocation test
├── test/test_api.py            # FastAPI /run endpoint async test & span assertions
├── test/test_telemetry.py      # Direct span decorator & error handling tests
├── Makefile                    # Common dev tasks (install/test/coverage/fmt/run)
├── pyproject.toml              # Modern project metadata & dependency management
├── infrastructure/             # Terraform IaC for Azure resources
│   ├── providers.tf
│   ├── variables.tf
│   ├── main.tf
│   └── outputs.tf
├── data/                       # Placeholder for future data assets
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Features

* Multi-agent workflow (planner → worker → reflection → reviewer) using LangGraph.
* OpenTelemetry tracing with custom spans per agent.
* Azure Monitor / Application Insights exporter via connection string.
* Optional in-memory span exporter for deterministic telemetry tests (`OTEL_INMEMORY_EXPORTER`).
* Async API + agent workflow tests with coverage & Ruff lint/format (`make fmt`, `make coverage`).
* Containerized FastAPI service (Dockerfile + docker-compose).
* Terraform deployment for: Resource Group, Log Analytics Workspace, Application Insights, Container Apps Environment & Container App, mandatory Azure OpenAI (Cognitive) account.

## Prerequisites

* Python 3.10+
* Docker / Docker Compose
* Terraform >= 1.6.0
* Azure CLI authenticated (`az login`)

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]   # single source of truth: pyproject.toml
pytest -q               # discovers tests in `test/`
cp .env.example .env    # then edit secrets before running
uvicorn src.agent.app:app --reload
```

Visit: http://localhost:8000/health then POST a task:

```bash
curl -X POST http://localhost:8000/run -H 'Content-Type: application/json' -d '{"task": "Outline observability advantages"}' | jq
```

### VS Code Debugging

The repo includes a pre-configured debug configuration (`.vscode/launch.json`):

1. **Set up environment**: Copy `.env.example` to `.env` and populate with Azure OpenAI credentials from Terraform outputs
2. **Set breakpoints**: Click in the gutter next to line numbers in Python files
3. **Start debugging**: Press `F5` or select "Python Debugger: FastAPI" from Run and Debug panel
4. **Test the endpoint**:
   ```bash
   curl -X POST http://localhost:8000/run -H 'Content-Type: application/json' -d '{"task": "Test local debug"}''
   ```

Environment variables are automatically loaded from `.env`.

### Enabling Real LLM Calls

Set one of the following environment variables before starting `uvicorn` or in `docker-compose.yml`:

* `OPENAI_API_KEY` with optional `OPENAI_BASE_URL`
* `GITHUB_MODELS_API_KEY` with `GITHUB_MODELS_BASE_URL=https://models.github.ai/inference/` (GitHub Models endpoint)

Otherwise the app returns stub responses.

### Telemetry Export

Provide `APPINSIGHTS_CONNECTION_STRING` (from Terraform output or existing resource) to enable Azure Monitor export. Without it spans stay local/no-op.

### .env & Terraform Variable Overrides
### Azure OpenAI Usage (Mandatory)

Terraform provisions a mandatory Azure OpenAI (Cognitive Services) account. The application always uses the Azure endpoint and deployment injected into the Container App environment. If the `azurerm_cognitive_deployment` resource is unavailable in your provider version, ensure the model deployment already exists (Portal or CLI). For local development set these manually:

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

### Local State (Default)

Terraform uses local state by default (`terraform.tfstate` - gitignored):

```bash
cd infrastructure
terraform init
terraform validate
terraform plan -out tfplan
terraform apply -auto-approve tfplan
```

### Remote State (Recommended for Teams)

For collaboration or CI/CD, configure Azure Storage backend:

```bash
# Option 1: Auto-create storage backend
./setup-backend.sh

# Option 2: Use existing storage
cp backend.hcl.example backend.hcl
# Edit backend.hcl with your storage details
terraform init -backend-config=backend.hcl -reconfigure
```

The backend configuration provides:
- State locking (prevents concurrent modifications)
- Shared access for team members
- State versioning and backup
- Encryption at rest

After apply, note outputs:

* `container_app_url` – public FQDN to call `/run`.
* `app_insights_connection_string` – telemetry ingestion (wired in `main.tf`).
* `azure_openai_endpoint` – Azure OpenAI endpoint base URL.
* `azure_openai_key` – Primary Azure OpenAI key (sensitive).

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
| `OTEL_INMEMORY_EXPORTER` | When `1`/`true`, adds in-memory span exporter for tests |

## Terraform Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `prefix` | `llmobs` | Name prefix for all resources |
| `location` | `eastus` | Azure region |
| `container_image` | `ghcr.io/your-org/llm-observability-otel:latest` | Deployed container image |
| `resource_group_name` | (empty) | Existing RG name (if blank one is created) |
| `azure_openai_sku_name` | `S0` | Azure OpenAI SKU tier |
| `azure_openai_deployment_name` | `gpt-4o-mini` | Model deployment name referenced by the app |
| `azure_openai_api_version` | `2024-08-01-preview` | API version used in requests |

Override via `-var` flags or `TF_VAR_<name>` environment variables (e.g. `export TF_VAR_prefix=llmobsx`).

## Makefile Workflow

Common developer tasks are scripted in the `Makefile`:

| Target | Action |
|--------|--------|
| `make install` | Install production deps from pyproject (PEP 621) |
| `make freeze` | Generate pinned snapshot `requirements.lock.txt` |
| `make dev` | Editable install with dev extras (`pytest`, coverage, ruff`) |
| `make test` | Run test suite (quiet configured in pyproject) |
| `make coverage` | Run tests with coverage report (term-missing) |
| `make run` | Start FastAPI app with reload (`uvicorn src.agent.app:app --reload`) |
| `make fmt` | Ruff lint (non-failing) then auto-format code |
| `make clean` | Remove caches and coverage artifacts |

Example:

```bash
make dev
make fmt   # optional style tidy
make test
make coverage
```

## Telemetry Testing & In-Memory Exporter

Set `OTEL_INMEMORY_EXPORTER=1` to capture spans in memory for assertions (no Azure dependency):

```bash
export OTEL_INMEMORY_EXPORTER=1
pytest -k test_api
```

Tests (`test/test_api.py`, `test/test_telemetry.py`) validate:
* Agent span names (`planner.agent`, `worker.agent`, `reflection.agent`, `reviewer.agent`)
* Error span status & exception event recording
* End-to-end request through `/run` with all state keys present

Coverage report:

```bash
make coverage
```

Formatting & lint:

```bash
make fmt
```

## PyProject Usage

You install everything from a single source (pyproject). For production/non-dev use:

```bash
pip install .
```

To emit a pinned requirements snapshot (for environments that still expect a file):

```bash
make freeze   # writes requirements.lock.txt
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

