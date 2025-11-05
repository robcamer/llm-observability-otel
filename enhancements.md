# Enhancements

### Suggested Next Enhancements

Next Optional Enhancements
- Add a lint target (Ruff check with fail-on-error).
- Export metrics (MeterProvider) alongside traces.
- Assert specific span attributes (e.g., state.keys) in API test.
- Consider snapshot testing span names/order.
- Let me know if you want metrics/logs next or CI wiring; everything you requested in this round is complete and validated.
- Introduce coverage reporting (pip install coverage or add to dev extras).
- Add more agent behavior tests (error paths, telemetry assertions).
- Cconsolidate dependency management 
- Eexpand tests next. 

- If you want richer attributes (e.g., request body size, custom status codes), we can add a middleware to enrich spans. Just say the word.
- Add metrics/log exporters (AzureMonitorLogExporter / metrics pipeline).
- Token usage + latency instrumentation via LangChain callbacks.
- Managed Identity + Key Vault for secretless config in Terraform.
- CI pipeline (image build + terraform plan/apply).
- Add autoscaling rules (HTTP concurrency / CPU) for Container App.
- Expand tests (error path, missing env vars, stub vs real LLM).

Let me know if you’d like a PR opened, more agents added (e.g., validation/reflection), or deeper telemetry (metrics & spans correlation). Ready for next steps when you are.

