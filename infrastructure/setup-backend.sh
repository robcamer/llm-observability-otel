#!/bin/bash
# setup-backend.sh - Creates Azure Storage backend for Terraform state

set -e

RESOURCE_GROUP="${TF_STATE_RG:-tfstate-rg}"
STORAGE_ACCOUNT="${TF_STATE_SA:-tfstate$(openssl rand -hex 4)}"
CONTAINER_NAME="${TF_STATE_CONTAINER:-tfstate}"
LOCATION="${TF_STATE_LOCATION:-eastus}"

echo "Creating Terraform state backend..."
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Storage Account: $STORAGE_ACCOUNT"
echo "  Container: $CONTAINER_NAME"
echo ""

# Create resource group
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

# Create storage account
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --encryption-services blob \
  --allow-blob-public-access false \
  --output none

# Create blob container
az storage container create \
  --name "$CONTAINER_NAME" \
  --account-name "$STORAGE_ACCOUNT" \
  --auth-mode login \
  --output none

echo ""
echo "✓ Backend created successfully!"
echo ""
echo "Update infrastructure/backend.tf with:"
echo "  resource_group_name  = \"$RESOURCE_GROUP\""
echo "  storage_account_name = \"$STORAGE_ACCOUNT\""
echo "  container_name       = \"$CONTAINER_NAME\""
echo "  key                  = \"llmobs.terraform.tfstate\""
echo ""
echo "Then run: cd infrastructure && terraform init -reconfigure"
