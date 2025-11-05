# End-to-End Telemetry Guide

This document describes the comprehensive OpenTelemetry instrumentation in this LLM observability demo:

- See [Enhanced Telemetry](./Enhanced_Telemetry.md) for additional implementation details.
- See [Telemetry Tutorial](telemetry-tutorial-app-insights.md) for steps to review telemetry in App Insights.

NOTE: Queries require modification for Log Analytics, which places AppInsights telemetry into different tables.

## Telemetry Architecture

### Instrumentation Layers

The application uses multiple layers of OpenTelemetry instrumentation to provide complete end-to-end observability:

#### 1. Auto-Instrumentation (Zero-code)
- **FastAPI** - Automatically traces all HTTP requests
- **HTTPX** - Traces all HTTP client calls (used by OpenAI SDK)
- **Requests** - Traces HTTP calls from any requests-based libraries

#### 2. Custom Agent Spans
Each agent in the workflow creates a custom span:
- `planner.agent` - Initial planning phase
- `worker.agent` - Execution phase
- `reflection.agent` - Quality validation
- `reviewer.agent` - Final review

#### 3. Workflow Orchestration Span
- `workflow.execution` - Parent span for entire multi-agent flow
- Links all agent executions under single operation

#### 4. LLM Call Instrumentation
Each LLM call creates a detailed span with rich attributes:
- `llm.completion.planner`
- `llm.completion.worker`
- `llm.completion.reflection`
- `llm.completion.reviewer`

## Captured Metrics

### LLM Call Attributes

Every LLM API call captures:

| Attribute | Description | Example |
|-----------|-------------|---------|
| `llm.system` | Provider type | `azure_openai`, `openai` |
| `llm.model` | Model identifier | `gpt-4o-mini` |
| `llm.request.max_tokens` | Token limit requested | `256` |
| `llm.request.prompt_length` | Input character count | `150` |
| `llm.usage.prompt_tokens` | Actual prompt tokens | `45` |
| `llm.usage.completion_tokens` | Response tokens | `128` |
| `llm.usage.total_tokens` | Total tokens consumed | `173` |
| `llm.response.length` | Response character count | `512` |
| `llm.response.finish_reason` | Why completion stopped | `stop`, `length` |
| `llm.response.model` | Actual model used | `gpt-4o-mini-2024-07-18` |
| `llm.azure.endpoint` | Azure OpenAI endpoint | `https://xxx.openai.azure.com/` |
| `llm.azure.api_version` | API version | `2024-08-01-preview` |

### Agent Attributes

Each agent span captures:

| Attribute | Description |
|-----------|-------------|
| `state.keys` | Number of state keys |
| `state.content_size` | Total character count in state |
| `duration_ms` | Execution time in milliseconds |

### Workflow Attributes

The workflow span captures:

| Attribute | Description |
|-----------|-------------|
| `workflow.task` | User's input task |
| `workflow.task_length` | Task character count |
| `workflow.completed` | Success flag |
| `workflow.plan_length` | Generated plan size |
| `workflow.work_length` | Work output size |
| `workflow.review_length` | Review output size |

## Span Hierarchy

Complete trace for a single request:

```
POST /run                                    [FastAPI auto-instrumentation]
├── attributes: http.method, http.url, http.status_code
└── workflow.execution                       [Custom span]
    ├── attributes: workflow.task, workflow.completed
    ├── planner.agent                        [Custom span]
    │   ├── attributes: state.keys, duration_ms
    │   └── llm.completion.planner           [Custom span with LLM metrics]
    │       ├── attributes: llm.model, llm.usage.*, duration
    │       └── POST /openai/deployments/... [HTTPX auto-instrumentation]
    ├── worker.agent
    │   └── llm.completion.worker
    │       └── POST /openai/deployments/...
    ├── reflection.agent
    │   └── llm.completion.reflection
    │       └── POST /openai/deployments/...
    └── reviewer.agent
        └── llm.completion.reviewer
            └── POST /openai/deployments/...
```

## KQL Queries for Analysis

### Token Usage by Agent

```kusto
dependencies
| where timestamp > ago(24h)
| where cloud_RoleName == "langgraph-multi-agent"
| where name startswith "llm.completion"
| extend 
    agent = tostring(split(name, ".")[2]),
    prompt_tokens = toint(customDimensions["llm.usage.prompt_tokens"]),
    completion_tokens = toint(customDimensions["llm.usage.completion_tokens"]),
    total_tokens = toint(customDimensions["llm.usage.total_tokens"])
| summarize 
    total_calls = count(),
    avg_prompt_tokens = avg(prompt_tokens),
    avg_completion_tokens = avg(completion_tokens),
    total_tokens_consumed = sum(total_tokens),
    avg_duration_ms = avg(duration)
by agent
| order by total_tokens_consumed desc
```

### LLM Performance Percentiles

```kusto
dependencies
| where timestamp > ago(1h)
| where cloud_RoleName == "langgraph-multi-agent"
| where name startswith "llm.completion"
| extend agent = tostring(split(name, ".")[2])
| summarize 
    p50 = percentile(duration, 50),
    p95 = percentile(duration, 95),
    p99 = percentile(duration, 99),
    avg_duration = avg(duration)
by agent
| order by p95 desc
```

### Cost Estimation (tokens to dollars)

```kusto
// Example: GPT-4o-mini pricing
// Input: $0.150 per 1M tokens
// Output: $0.600 per 1M tokens
dependencies
| where timestamp > ago(24h)
| where cloud_RoleName == "langgraph-multi-agent"
| where name startswith "llm.completion"
| extend 
    prompt_tokens = toint(customDimensions["llm.usage.prompt_tokens"]),
    completion_tokens = toint(customDimensions["llm.usage.completion_tokens"])
| summarize 
    total_prompt_tokens = sum(prompt_tokens),
    total_completion_tokens = sum(completion_tokens),
    total_calls = count()
| extend 
    input_cost = total_prompt_tokens * 0.150 / 1000000.0,
    output_cost = total_completion_tokens * 0.600 / 1000000.0,
    total_cost = input_cost + output_cost
| project total_calls, total_prompt_tokens, total_completion_tokens, 
          input_cost, output_cost, total_cost
```

### Error Rate by Agent

```kusto
dependencies
| where timestamp > ago(1h)
| where cloud_RoleName == "langgraph-multi-agent"
| where name startswith "llm.completion"
| extend 
    agent = tostring(split(name, ".")[2]),
    is_success = resultCode == "0" or success == true
| summarize 
    total = count(),
    successes = countif(is_success),
    failures = countif(not(is_success)),
    success_rate = countif(is_success) * 100.0 / count()
by agent
| order by success_rate asc
```

### End-to-End Request Latency Breakdown

```kusto
let OperationIds = requests
    | where timestamp > ago(1h)
    | where cloud_RoleName == "langgraph-multi-agent"
    | project operation_Id;
union traces, dependencies, requests
| where operation_Id in (OperationIds)
| project timestamp, itemType, name, duration, operation_Id
| order by operation_Id, timestamp
```

## Viewing in Application Insights

### Transaction Search
1. Navigate to **Application Insights → Transaction search**
2. Filter by time range
3. Look for `POST /run` requests
4. Click any request to see the complete span hierarchy
5. Expand each span to view attributes (token usage, durations, etc.)

### Application Map
1. Navigate to **Application Insights → Application Map**
2. View service dependencies and call patterns
3. See failure rates and average durations
4. Identify bottlenecks in the agent workflow

### Performance Blade
1. Navigate to **Application Insights → Performance**
2. View operation times for each agent
3. Analyze dependencies (LLM calls)
4. Drill into specific operations for detailed traces

### Live Metrics
1. Navigate to **Application Insights → Live Metrics**
2. Run a request: `curl -X POST http://localhost:8000/run -H 'Content-Type: application/json' -d '{"task": "Test"}'`
3. Watch real-time telemetry flow
4. See request rate, duration, dependencies as they happen

## Local Testing with In-Memory Exporter

For testing without Azure connection:

```bash
export OTEL_INMEMORY_EXPORTER=1
pytest -v test/test_api.py
```

This captures spans in memory for validation without requiring Application Insights.

## Troubleshooting

### No telemetry appearing in Azure

1. Check `APPINSIGHTS_CONNECTION_STRING` is set correctly
2. Verify spans are being created locally first (use in-memory exporter)
3. Check firewall allows outbound HTTPS to `*.applicationinsights.azure.com`
4. Telemetry batching may delay up to 60 seconds - wait and refresh

### Missing LLM metrics

1. Ensure `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` are set
2. Check `AZURE_OPENAI_DEPLOYMENT` matches your deployment name
3. Verify the OpenAI SDK version is >= 1.54.0
4. LLM attributes only appear when real API calls succeed

### Incomplete span hierarchy

1. Ensure all instrumentation packages are installed:
   - `opentelemetry-instrumentation-fastapi`
   - `opentelemetry-instrumentation-httpx`
   - `opentelemetry-instrumentation-requests`
2. Check that `get_tracer()` is called before creating spans
3. Verify spans are created within an active context

## Best Practices

1. **Always use correlation IDs**: The `operation_Id` links all spans in a request
2. **Set semantic attributes**: Use standard OpenTelemetry semantic conventions
3. **Capture errors**: Use `span.record_exception()` and set error status
4. **Add business metrics**: Include domain-specific attributes (task type, user info)
5. **Monitor token usage**: Track costs and optimize prompts based on metrics
6. **Set up alerts**: Create Azure Monitor alerts for high latency or error rates
7. **Use sampling for scale**: Configure sampling in production to manage costs

## Next Steps

- Add metrics exporters for real-time dashboards
- Implement distributed tracing across microservices
- Add logging exporter for structured logs
- Create custom Azure Monitor workbooks for LLM analytics
- Set up alerting rules for token usage thresholds
- Implement trace sampling strategies for high-volume scenarios
