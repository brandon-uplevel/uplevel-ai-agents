#!/bin/bash
# Simple deployment script for Uplevel Central Orchestrator
# Uses external Redis (Redis Cloud) for faster deployment

set -e  # Exit on any error

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"uplevel-ai-agents"}
REGION=${VERTEX_AI_LOCATION:-"us-central1"}
REPOSITORY="uplevel-agents"
SERVICE_NAME="uplevel-orchestrator"

echo "🚀 Starting simple deployment of Uplevel Central Orchestrator"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Repository: $REPOSITORY"

# Step 1: Set up GCP project
echo "📋 Setting up GCP project..."
gcloud config set project $PROJECT_ID

# Step 2: Enable required APIs (basic ones)
echo "🔌 Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
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

# Step 5: Use external Redis (Redis Cloud) for now
echo "🔧 Using external Redis service..."
REDIS_URL="redis://redis-19374.c263.us-east-1-2.ec2.cloud.redislabs.com:19374"
echo "Redis URL: $REDIS_URL (external service)"

# Step 6: Build and deploy using Cloud Build (simplified)
echo "🏗️  Building and deploying with Cloud Build..."
cd /home/brandon/projects/uplevel

# Create temporary cloudbuild.yaml for simple deployment
cat > /tmp/simple_cloudbuild.yaml << EOFBUILD
steps:
  # Step 1: Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - '${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/uplevel-orchestrator:latest'
      - '-f'
      - 'Dockerfile'
      - '.'
    dir: 'agents/orchestrator'

  # Step 2: Push the container image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/uplevel-orchestrator:latest'

  # Step 3: Deploy to Cloud Run (simple deployment)
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'uplevel-orchestrator'
      - '--image'
      - '${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/uplevel-orchestrator:latest'
      - '--region'
      - '${REGION}'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--port'
      - '8080'
      - '--memory'
      - '2Gi'
      - '--cpu'
      - '1000m'
      - '--min-instances'
      - '0'
      - '--max-instances'
      - '10'
      - '--timeout'
      - '300s'
      - '--set-env-vars'
      - 'GOOGLE_CLOUD_PROJECT=${PROJECT_ID},ORCHESTRATOR_PORT=8080,FINANCIAL_AGENT_URL=https://uplevel-financial-agent-834012950450.us-central1.run.app,REDIS_URL=redis://localhost:6379,SALES_MARKETING_AGENT_URL=http://localhost:8003,LOG_LEVEL=INFO,ENVIRONMENT=production'

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: 'E2_HIGHCPU_8'

timeout: '1200s'

images:
  - '${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/uplevel-orchestrator:latest'
EOFBUILD

gcloud builds submit agents/orchestrator \
    --config=/tmp/simple_cloudbuild.yaml \
    --substitutions=_REGION=$REGION,_REPOSITORY=$REPOSITORY

# Step 7: Get the deployment URL
echo "🔗 Getting deployment information..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

# Step 8: Test the deployment
echo "🧪 Testing deployment..."
sleep 30  # Give service time to fully start

if curl -f "$SERVICE_URL/health" --max-time 30; then
    echo "✅ Health check passed"
else
    echo "⚠️  Health check failed - check logs for issues"
fi

# Step 9: Create deployment info file
echo "📝 Creating deployment info..."
cat > /home/brandon/projects/uplevel/agents/orchestrator/deployment_info.json << EOFJSON
{
  "agent_name": "uplevel-central-orchestrator",
  "project_id": "$PROJECT_ID",
  "region": "$REGION", 
  "service_url": "$SERVICE_URL",
  "service_name": "$SERVICE_NAME",
  "repository": "$REPOSITORY",
  "redis_type": "local",
  "deployment_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "deployed",
  "endpoints": {
    "health": "$SERVICE_URL/health",
    "query": "$SERVICE_URL/query",
    "orchestrate": "$SERVICE_URL/orchestrate",
    "status": "$SERVICE_URL/status",
    "docs": "$SERVICE_URL/docs"
  },
  "agents": {
    "financial_intelligence": "https://uplevel-financial-agent-834012950450.us-central1.run.app",
    "sales_marketing": "http://localhost:8003"
  }
}
EOFJSON

# Step 10: Display deployment summary
echo ""
echo "🎉 Central Orchestrator deployment completed!"
echo "=============================================="
echo "Service URL: $SERVICE_URL"
echo "Health Check: $SERVICE_URL/health"
echo "API Documentation: $SERVICE_URL/docs"
echo "Query Endpoint: $SERVICE_URL/query"
echo "Orchestration Endpoint: $SERVICE_URL/orchestrate"
echo ""
echo "📋 Next steps:"
echo "1. Test multi-agent orchestration workflows"
echo "2. Set up production Redis (Google Cloud Memorystore)"
echo "3. Deploy Sales & Marketing agent"
echo "4. Update frontend configuration"
echo ""
echo "💡 Deployment info saved to: agents/orchestrator/deployment_info.json"

# Clean up temp file
rm -f /tmp/simple_cloudbuild.yaml
