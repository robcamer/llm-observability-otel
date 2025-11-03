variable "prefix" { type = string default = "llmobs" }
variable "location" { type = string default = "eastus" }
variable "container_image" { type = string default = "ghcr.io/your-org/llm-observability-otel:latest" }
variable "resource_group_name" { type = string default = "" description = "If empty will create one using prefix" }
variable "azure_openai_sku_name" { type = string default = "S0" }
variable "azure_openai_deployment_model" { type = string default = "gpt-4o-mini" description = "Base model name used for deployment (Azure catalog)" }
variable "azure_openai_deployment_name" { type = string default = "gpt-4o-mini" description = "Deployment name referenced by the app" }
