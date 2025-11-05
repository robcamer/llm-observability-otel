# LLM Observability with OpenTelemetry + Azure Monitor

Containerized multi-agent LangGraph sample instrumented with OpenTelemetry exporting traces to Azure Monitor / Application Insights and leveraging a Log Analytics workspace for deeper analysis.

**Key Capabilities:**
- 🔍 **End-to-end tracing** from HTTP request through agent execution to LLM API calls
- 📊 **Token usage metrics** captured for every LLM call (prompt tokens, completion tokens, total cost)
- ⚡ **Performance monitoring** with latency tracking at HTTP, workflow, agent, and LLM layers
- 🎯 **Custom span attributes** for business metrics (task type, state size, response quality)
- 🔗 **Automatic correlation** of all spans in a request via operation_Id
- 📈 **Rich KQL queries** for cost analysis, performance optimization, and error tracking

See **[Telemetry.md](docs/Telemetry.md)** for instrumentation details and KQL query examples.

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

* **Multi-agent workflow** (planner → worker → reflection → reviewer) using LangGraph.
* **Comprehensive OpenTelemetry tracing** with custom spans per agent and LLM call.
* **Detailed LLM observability**: Token usage, latency, prompt/response metrics for every LLM call.
* **End-to-end tracing**: HTTP request → agent execution → LLM calls → response with full span hierarchy.
* **Auto-instrumentation**: FastAPI, HTTPX, and Requests automatically traced.
* **Azure Monitor / Application Insights** exporter via connection string.
* **Optional in-memory span exporter** for deterministic telemetry tests (`OTEL_INMEMORY_EXPORTER`).
* **Async API + agent workflow tests** with coverage & Ruff lint/format (`make fmt`, `make coverage`).
* **Containerized FastAPI service** (Dockerfile + docker-compose).
* **Terraform deployment** for: Resource Group, Log Analytics Workspace, Application Insights, Container Apps Environment & Container App, mandatory Azure OpenAI (Cognitive) account with model deployment.

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

#### OpenTelemetry Instrumentation Details

The application provides comprehensive end-to-end observability with multiple instrumentation layers:

**1. HTTP Layer (Auto-instrumented)**
- FastAPI requests automatically create parent spans
- HTTPX and Requests libraries trace outbound HTTP calls to LLM APIs
- Each HTTP request gets a unique `operation_Id` for correlation

**2. Workflow Layer (Custom spans)**
- `workflow.execution` - Parent span for entire agent workflow
- Captures task metadata, result lengths, and completion status
- Links all agent and LLM spans under a single operation

**3. Agent Layer (Custom spans)**
- `planner.agent` - Planning phase with task breakdown
- `worker.agent` - Execution phase
- `reflection.agent` - Quality validation phase
- `reviewer.agent` - Final review and summary
- Each agent span includes state keys, content size, and duration

**4. LLM Call Layer (Detailed tracing)**
- `llm.completion.planner` - LLM calls from planner agent
- `llm.completion.worker` - LLM calls from worker agent
- `llm.completion.reflection` - LLM calls from reflection agent
- `llm.completion.reviewer` - LLM calls from reviewer agent

**LLM Span Attributes Captured:**
- `llm.system` - Provider (azure_openai, openai)
- `llm.model` - Model name (gpt-4o-mini, etc.)
- `llm.request.max_tokens` - Token limit
- `llm.request.prompt_length` - Character count
- `llm.usage.prompt_tokens` - Actual prompt tokens used
- `llm.usage.completion_tokens` - Tokens in response
- `llm.usage.total_tokens` - Total token consumption
- `llm.response.length` - Response character count
- `llm.response.finish_reason` - Completion status (stop, length, etc.)
- `llm.azure.endpoint` - Azure OpenAI endpoint (when applicable)
- `llm.azure.api_version` - API version used

**Span Hierarchy Example:**
```
HTTP POST /run (FastAPI auto-instrumentation)
└── workflow.execution
    ├── planner.agent
    │   └── llm.completion.planner (with token metrics)
    │       └── HTTP POST to Azure OpenAI API (httpx auto-instrumentation)
    ├── worker.agent
    │   └── llm.completion.worker (with token metrics)
    │       └── HTTP POST to Azure OpenAI API
    ├── reflection.agent
    │   └── llm.completion.reflection (with token metrics)
    │       └── HTTP POST to Azure OpenAI API
    └── reviewer.agent
        └── llm.completion.reviewer (with token metrics)
            └── HTTP POST to Azure OpenAI API
```

This architecture ensures complete visibility from HTTP request to individual LLM token usage.

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
./setup-tf-backend.sh

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

After running requests locally or from the deployed Container App, view telemetry in Azure Application Insights.

#### Viewing Telemetry in Azure Portal

**1. Open Application Insights**

Navigate to your Application Insights resource:
- **Azure Portal** → **Resource Groups** → **llmobs-rg** → **llmobs-ai** (Application Insights)

Or open directly from command line:
```bash
az portal open --resource-group llmobs-rg --resource-name llmobs-ai --resource-type Microsoft.Insights/components
```

**2. Explore Your Telemetry Data**

Once in Application Insights, use these views:

**Transaction Search** (fastest way to see traces)
- Left menu: **Investigate → Transaction search**
- View all traces, dependencies, and requests
- Filter by time range (last 30 minutes, 1 hour, etc.)
- Look for your requests with custom spans: `planner.agent`, `worker.agent`, `reflection.agent`, `reviewer.agent`

**Logs** (for detailed KQL queries)
- Left menu: **Monitoring → Logs**

**View end-to-end request traces:**
  ```kusto
  traces
  | where timestamp > ago(1h)
  | where cloud_RoleName == "langgraph-multi-agent"
  | project timestamp, message, severityLevel, customDimensions
  | order by timestamp desc
  | take 50
  ```

**View LLM call metrics with token usage:**
  ```kusto
  dependencies
  | where timestamp > ago(1h)
  | where cloud_RoleName == "langgraph-multi-agent"
  | where name startswith "llm.completion"
  | extend 
      model = tostring(customDimensions["llm.model"]),
      prompt_tokens = toint(customDimensions["llm.usage.prompt_tokens"]),
      completion_tokens = toint(customDimensions["llm.usage.completion_tokens"]),
      total_tokens = toint(customDimensions["llm.usage.total_tokens"]),
      response_length = toint(customDimensions["llm.response.length"])
  | project timestamp, name, model, duration, prompt_tokens, completion_tokens, total_tokens, response_length
  | order by timestamp desc
  ```

**Analyze token usage by agent:**
  ```kusto
  dependencies
  | where timestamp > ago(24h)
  | where cloud_RoleName == "langgraph-multi-agent"
  | where name startswith "llm.completion"
  | extend 
      agent = tostring(split(name, ".")[2]),
      total_tokens = toint(customDimensions["llm.usage.total_tokens"])
  | summarize 
      total_calls = count(),
      avg_tokens = avg(total_tokens),
      total_tokens = sum(total_tokens),
      avg_duration_ms = avg(duration)
  by agent
  | order by total_tokens desc
  ```

**View complete workflow execution with all spans:**
  ```kusto
  union traces, dependencies, requests
  | where timestamp > ago(1h)
  | where cloud_RoleName == "langgraph-multi-agent"
  | project timestamp, itemType, name, operation_Id, duration, customDimensions
  | order by timestamp desc, operation_Id
  ```

**Track LLM performance and errors:**
  ```kusto
  dependencies
  | where timestamp > ago(1h)
  | where cloud_RoleName == "langgraph-multi-agent"
  | where name startswith "llm.completion"
  | extend 
      agent = tostring(split(name, ".")[2]),
      model = tostring(customDimensions["llm.model"]),
      success = resultCode == "0" or success == true
  | summarize 
      total_calls = count(),
      success_rate = countif(success) * 100.0 / count(),
      avg_duration_ms = avg(duration),
      p95_duration_ms = percentile(duration, 95)
  by agent, model
  | order by total_calls desc
  ```

**Full HTTP request flow:**
  ```kusto
  requests
  | where timestamp > ago(1h)
  | where cloud_RoleName == "langgraph-multi-agent"
  | project timestamp, name, url, duration, resultCode, operation_Id
  | order by timestamp desc
  ```

**Performance**
- Left menu: **Investigate → Performance**
- See operation times and dependencies
- View the call tree for each request

**Live Metrics**
- Left menu: **Investigate → Live Metrics**
- Run a new request and watch real-time telemetry flow in
- Useful for debugging and monitoring active sessions

**3. Test Telemetry Flow**

Run a test request:
```bash
curl -X POST http://localhost:8000/run -H 'Content-Type: application/json' -d '{"task": "Check telemetry visibility"}'
```

Telemetry appears in Application Insights within 1-2 minutes. Refresh Transaction Search or Logs to see your traces.

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

