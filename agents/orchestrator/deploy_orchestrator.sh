#!/bin/bash
# Deployment script for Uplevel Central Orchestrator
# Sets up GCP resources and deploys to Cloud Run

set -e  # Exit on any error

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"uplevel-ai-agents"}
REGION=${VERTEX_AI_LOCATION:-"us-central1"}
REPOSITORY="uplevel-agents"
SERVICE_NAME="uplevel-orchestrator"

echo "🚀 Starting deployment of Uplevel Central Orchestrator"
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
    redis.googleapis.com \
    vpcaccess.googleapis.com \
    artifactregistry.googleapis.com \
    memorystore.googleapis.com

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

# Step 5: Set up Redis instance (Google Cloud Memorystore)
echo "🔧 Setting up Redis instance..."
REDIS_INSTANCE="uplevel-orchestrator-redis"

if ! gcloud redis instances describe $REDIS_INSTANCE --region=$REGION >/dev/null 2>&1; then
    echo "Creating new Redis instance..."
    gcloud redis instances create $REDIS_INSTANCE \
        --size=1 \
        --region=$REGION \
        --redis-version=redis_7_0 \
        --tier=basic \
        --display-name="Uplevel Orchestrator Redis" \
        --labels=purpose=orchestrator,project=uplevel
    
    echo "✅ Redis instance created"
    
    # Wait for Redis instance to be ready
    echo "⏳ Waiting for Redis instance to be ready..."
    gcloud redis instances wait-for-ready $REDIS_INSTANCE --region=$REGION --timeout=600
else
    echo "✅ Redis instance already exists"
fi

# Get Redis connection info
REDIS_HOST=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="value(host)")
REDIS_PORT=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="value(port)")
REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}"

echo "Redis URL: $REDIS_URL"

# Step 6: Set up VPC Connector (if needed for Redis access)
echo "🔗 Setting up VPC Connector for Redis access..."
CONNECTOR_NAME="uplevel-orchestrator-connector"

if ! gcloud compute networks vpc-access connectors describe $CONNECTOR_NAME --region=$REGION >/dev/null 2>&1; then
    echo "Creating VPC connector..."
    gcloud compute networks vpc-access connectors create $CONNECTOR_NAME \
        --region=$REGION \
        --subnet=default \
        --subnet-project=$PROJECT_ID \
        --min-instances=2 \
        --max-instances=3 \
        --machine-type=e2-micro
    echo "✅ VPC connector created"
else
    echo "✅ VPC connector already exists"
fi

# Step 7: Build and deploy using Cloud Build
echo "🏗️  Building and deploying with Cloud Build..."
cd /home/brandon/projects/uplevel

gcloud builds submit agents/orchestrator \
    --config=agents/orchestrator/cloudbuild.yaml \
    --substitutions=_REGION=$REGION,_REPOSITORY=$REPOSITORY,_REDIS_URL=$REDIS_URL,_SALES_AGENT_URL="http://localhost:8003"

# Step 8: Update Cloud Run service with VPC connector
echo "🔗 Configuring VPC connector for Cloud Run service..."
gcloud run services update $SERVICE_NAME \
    --region=$REGION \
    --vpc-connector=$CONNECTOR_NAME \
    --vpc-egress=private-ranges-only

# Step 9: Get the deployment URL
echo "🔗 Getting deployment information..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

# Step 10: Test the deployment
echo "🧪 Testing deployment..."
sleep 30  # Give service time to fully start

if curl -f "$SERVICE_URL/health" --max-time 30; then
    echo "✅ Health check passed"
else
    echo "⚠️  Health check failed - check logs for issues"
    echo "Logs: gcloud run services logs read $SERVICE_NAME --region=$REGION"
fi

# Step 11: Create deployment info file
echo "📝 Creating deployment info..."
cat > /home/brandon/projects/uplevel/agents/orchestrator/deployment_info.json << EOL
{
  "agent_name": "uplevel-central-orchestrator",
  "project_id": "$PROJECT_ID",
  "region": "$REGION", 
  "service_url": "$SERVICE_URL",
  "service_name": "$SERVICE_NAME",
  "repository": "$REPOSITORY",
  "redis_instance": "$REDIS_INSTANCE",
  "redis_url": "$REDIS_URL",
  "vpc_connector": "$CONNECTOR_NAME",
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
EOL

# Step 12: Display deployment summary
echo ""
echo "🎉 Central Orchestrator deployment completed successfully!"
echo "========================================================"
echo "Service URL: $SERVICE_URL"
echo "Health Check: $SERVICE_URL/health"
echo "API Documentation: $SERVICE_URL/docs"
echo "Query Endpoint: $SERVICE_URL/query"
echo "Orchestration Endpoint: $SERVICE_URL/orchestrate"
echo "Status Endpoint: $SERVICE_URL/status"
echo ""
echo "🔧 Infrastructure:"
echo "Redis Instance: $REDIS_INSTANCE ($REDIS_URL)"
echo "VPC Connector: $CONNECTOR_NAME"
echo ""
echo "🔗 Connected Agents:"
echo "- Financial Intelligence: https://uplevel-financial-agent-834012950450.us-central1.run.app"
echo "- Sales & Marketing: TBD (currently localhost:8003)"
echo ""
echo "📋 Next steps:"
echo "1. Deploy Sales & Marketing agent and update configuration"
echo "2. Test multi-agent orchestration workflows"
echo "3. Set up monitoring and alerting in Google Cloud Console"
echo "4. Update frontend configuration to use production orchestrator URL"
echo ""
echo "💡 Deployment info saved to: agents/orchestrator/deployment_info.json"
echo "📊 Monitor logs: gcloud run services logs read $SERVICE_NAME --region=$REGION --follow"
