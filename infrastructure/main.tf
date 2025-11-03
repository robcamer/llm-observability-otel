locals {
  rg_name = coalesce(var.resource_group_name, "${var.prefix}-rg")
}

resource "azurerm_resource_group" "rg" {
  name     = local.rg_name
  location = var.location
}

resource "azurerm_log_analytics_workspace" "law" {
  name                = "${var.prefix}-law"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "appinsights" {
  name                = "${var.prefix}-ai"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.law.id
}

resource "azurerm_container_app_environment" "cae" {
  name                       = "${var.prefix}-env"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
}

# Azure OpenAI (Cognitive Services) Account
resource "azurerm_cognitive_account" "aoai" {
  name                = "${var.prefix}-aoai"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "OpenAI"
  sku_name            = var.azure_openai_sku_name
  custom_subdomain_name = "${var.prefix}-aoai-${replace(var.location, " ", "")}" 
  tags = { application = "llm-observability" }
}

# (Optional) Deployment resource: some provider versions expose azurerm_cognitive_deployment for models.
# Guard with 'count' if the resource type is available; fallback is manual deployment.
# Uncomment if your provider version supports it.
# resource "azurerm_cognitive_deployment" "aoai_model" {
#   name                 = var.azure_openai_deployment_name
#   cognitive_account_id = azurerm_cognitive_account.aoai.id
#   model_format         = "OpenAI"
#   model_name           = var.azure_openai_deployment_model
#   scale_settings { scale_type = "Standard" }
# }

resource "azurerm_container_app" "app" {
  name                         = "${var.prefix}-app"
  container_app_environment_id = azurerm_container_app_environment.cae.id
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = var.location

  revision_mode = "Single"

  template {
    container {
      name   = "langgraph"
      image  = var.container_image
      cpu    = 0.5
      memory = "1Gi"
      # Secrets referencing App Insights + Azure OpenAI key
      env {
        name  = "SERVICE_NAME"
        value = "langgraph-multi-agent"
      }
      env {
        name  = "SERVICE_VERSION"
        value = "0.1.0"
      }
      env {
        name  = "APPINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.appinsights.connection_string
      }
      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = azurerm_cognitive_account.aoai.endpoint
      }
      env {
        name  = "AZURE_OPENAI_DEPLOYMENT"
        value = var.azure_openai_deployment_name
      }
      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = "2024-08-01-preview"
      }
      # Inject primary key as secret
      env {
        name  = "AZURE_OPENAI_API_KEY"
        value = azurerm_cognitive_account.aoai.primary_access_key
      }
    }
    scale {
      min_replicas = 1
      max_replicas = 2
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
  }

  tags = {
    application = "llm-observability"
  }
}
