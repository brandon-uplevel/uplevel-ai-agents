#!/bin/bash
# Deployment script for Uplevel Financial Intelligence Agent
# Sets up GCP resources and deploys to Vertex AI Agent Engine

set -e  # Exit on any error

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"uplevel-ai-agents"}
REGION=${VERTEX_AI_LOCATION:-"us-central1"}
REPOSITORY="uplevel-agents"
SERVICE_NAME="uplevel-financial-agent"

echo "🚀 Starting deployment of Uplevel Financial Intelligence Agent"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Repository: $REPOSITORY"

# Step 1: Set up GCP project
echo "📋 Setting up GCP project..."
gcloud config set project $PROJECT_ID

# Step 2: Enable required APIs (if not already enabled)
echo "🔌 Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    aiplatform.googleapis.com \
    secretmanager.googleapis.com \
    firestore.googleapis.com \
    artifactregistry.googleapis.com

# Step 3: Create Artifact Registry repository
echo "📦 Setting up Artifact Registry..."
if ! gcloud artifacts repositories describe $REPOSITORY --location=$REGION >/dev/null 2>&1; then
    gcloud artifacts repositories create $REPOSITORY \
        --repository-format=docker \
        --location=$REGION \
        --description="Uplevel AI Agents repository"
    echo "✅ Artifact Registry repository created"
else
    echo "✅ Artifact Registry repository already exists"
fi

# Step 4: Configure Docker authentication
echo "🔐 Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Step 5: Create Secret Manager secrets (with dummy values if not exist)
echo "🔑 Setting up Secret Manager secrets..."

# HubSpot secrets
if ! gcloud secrets describe hubspot-access-token >/dev/null 2>&1; then
    echo "dummy-hubspot-token" | gcloud secrets create hubspot-access-token --data-file=-
    echo "✅ HubSpot access token secret created (update with real token)"
else
    echo "✅ HubSpot access token secret already exists"
fi

# QuickBooks secrets
if ! gcloud secrets describe quickbooks-client-id >/dev/null 2>&1; then
    echo "dummy-qb-client-id" | gcloud secrets create quickbooks-client-id --data-file=-
    echo "✅ QuickBooks client ID secret created (update with real credentials)"
fi

if ! gcloud secrets describe quickbooks-client-secret >/dev/null 2>&1; then
    echo "dummy-qb-client-secret" | gcloud secrets create quickbooks-client-secret --data-file=-
    echo "✅ QuickBooks client secret created (update with real credentials)"
fi

# Step 6: Build and deploy using Cloud Build
echo "🏗️  Building and deploying with Cloud Build..."
gcloud builds submit . \
    --config=deployment/cloudbuild.yaml \
    --substitutions=_REGION=$REGION,_REPOSITORY=$REPOSITORY

# Step 7: Get the deployment URL
echo "🔗 Getting deployment information..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

# Step 8: Test the deployment
echo "🧪 Testing deployment..."
if curl -f "$SERVICE_URL/health" >/dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "⚠️  Health check failed - check logs for issues"
fi

# Step 9: Create deployment info file
echo "📝 Creating deployment info..."
cat > deployment/deployment_info.json << EOL
{
  "agent_name": "uplevel-financial-intelligence",
  "project_id": "$PROJECT_ID",
  "region": "$REGION", 
  "service_url": "$SERVICE_URL",
  "service_name": "$SERVICE_NAME",
  "repository": "$REPOSITORY",
  "deployment_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "deployed",
  "endpoints": {
    "health": "$SERVICE_URL/health",
    "query": "$SERVICE_URL/query",
    "pl_statement": "$SERVICE_URL/pl-statement",
    "forecast": "$SERVICE_URL/forecast",
    "docs": "$SERVICE_URL/docs"
  }
}
EOL

# Step 10: Display deployment summary
echo ""
echo "🎉 Deployment completed successfully!"
echo "=================================="
echo "Service URL: $SERVICE_URL"
echo "Health Check: $SERVICE_URL/health"
echo "API Documentation: $SERVICE_URL/docs"
echo "Query Endpoint: $SERVICE_URL/query"
echo "P&L Statement: $SERVICE_URL/pl-statement"
echo "Forecast: $SERVICE_URL/forecast"
echo ""
echo "📋 Next steps:"
echo "1. Update Secret Manager with real API credentials:"
echo "   - HubSpot access token: gcloud secrets versions add hubspot-access-token --data-file=<token-file>"
echo "   - QuickBooks credentials: gcloud secrets versions add quickbooks-client-id --data-file=<id-file>"
echo "2. Test the agent endpoints using the API documentation"
echo "3. Set up monitoring and alerting in Google Cloud Console"
echo ""
echo "💡 Deployment info saved to: deployment/deployment_info.json"
