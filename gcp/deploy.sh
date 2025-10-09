#!/bin/bash

# Google Cloud Run Deployment Script
# Usage: ./deploy.sh [PROJECT_ID] [REGION]

set -e

# Configuration
PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
SERVICE_NAME="rag-medical-assistant"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Deploying RAG Medical Assistant to Google Cloud Run"
echo "📋 Project: $PROJECT_ID"
echo "🌍 Region: $REGION"
echo "🏷️  Image: $IMAGE_NAME"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Set the project
echo "🔧 Setting up Google Cloud project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔌 Enabling required Google Cloud APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    sql-component.googleapis.com \
    redis.googleapis.com \
    secretmanager.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com \
    storage-component.googleapis.com \
    vpcaccess.googleapis.com

# Build and push the Docker image
echo "🏗️  Building Docker image..."
gcloud builds submit --tag $IMAGE_NAME --file Dockerfile.gcp .

# Update the Cloud Run YAML with actual project ID
echo "📝 Updating Cloud Run configuration..."
sed -i.bak "s/PROJECT_ID/$PROJECT_ID/g" gcp/cloud-run.yaml
sed -i.bak "s/REGION/$REGION/g" gcp/cloud-run.yaml

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run services replace gcp/cloud-run.yaml --region=$REGION

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

echo "✅ Deployment completed successfully!"
echo "🌐 Service URL: $SERVICE_URL"
echo "📊 Monitor at: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME"

# Optional: Set up custom domain
read -p "🌍 Do you want to set up a custom domain? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter your domain name: " DOMAIN_NAME
    gcloud run domain-mappings create --service=$SERVICE_NAME --domain=$DOMAIN_NAME --region=$REGION
    echo "🔗 Custom domain mapping created for $DOMAIN_NAME"
    echo "📋 Please update your DNS records to point to ghs.googlehosted.com"
fi

echo "🎉 RAG Medical Assistant is now live at: $SERVICE_URL"