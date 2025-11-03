output "resource_group_name" { value = azurerm_resource_group.rg.name }
output "container_app_url" { value = azurerm_container_app.app.latest_revision_fqdn }
output "app_insights_connection_string" { value = azurerm_application_insights.appinsights.connection_string sensitive = true }
output "log_analytics_workspace_id" { value = azurerm_log_analytics_workspace.law.id }
output "azure_openai_endpoint" { value = azurerm_cognitive_account.aoai.endpoint }
output "azure_openai_key" { value = azurerm_cognitive_account.aoai.primary_access_key sensitive = true }
