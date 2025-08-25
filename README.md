# Uplevel AI Agent System

A comprehensive multi-agent AI system for business automation integrating financial intelligence, sales & marketing automation, and orchestrated agent communication.

## 🏗️ System Architecture

- **Orchestrator Agent**: Central coordination and agent management
- **Financial Intelligence Agent**: QuickBooks integration and financial data analysis  
- **Sales & Marketing Agent**: HubSpot CRM integration and marketing automation
- **Frontend Portal**: Next.js web interface for agent interaction
- **MCP Servers**: Model Context Protocol integrations for external services

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Redis (for orchestrator state management)
- Git

### 1. Clone Repository
```bash
git clone https://github.com/brandon-uplevel/uplevel-ai-agents.git
cd uplevel-ai-agents
```

### 2. Environment Configuration
Copy and configure environment files for each component:

```bash
# Main configuration
cp .env.example .env

# Agent configurations
cp agents/orchestrator/.env.example agents/orchestrator/.env
cp agents/financial_intelligence/.env.example agents/financial_intelligence/.env
cp agents/sales_marketing/.env.example agents/sales_marketing/.env

# MCP server configurations
cp mcps/hubspot_integration/.env.example mcps/hubspot_integration/.env
cp mcps/quickbooks_integration/.env.example mcps/quickbooks_integration/.env

# Frontend configuration
cp portal/frontend/.env.local.example portal/frontend/.env.local
```

### 3. Required API Keys

#### HubSpot Integration
1. Create HubSpot App at [HubSpot Developer Portal](https://developers.hubspot.com/)
2. Get Client ID, Client Secret, and Access Token
3. Configure redirect URI: `http://localhost:8000/auth/hubspot/callback`

#### QuickBooks Integration  
1. Create QuickBooks App at [Intuit Developer](https://developer.intuit.com/)
2. Get Client ID and Client Secret
3. Configure redirect URI: `http://localhost:8000/auth/quickbooks/callback`

#### Google Cloud (Optional)
1. Create service account at [Google Cloud Console](https://console.cloud.google.com/)
2. Download service account JSON key
3. Set `GOOGLE_APPLICATION_CREDENTIALS` path

### 4. Install Dependencies

#### Backend Agents
```bash
# Orchestrator
cd agents/orchestrator
python -m venv orchestrator-env
source orchestrator-env/bin/activate  # Windows: orchestrator-env\Scripts\activate
pip install -r requirements.txt

# Financial Intelligence
cd ../financial_intelligence
pip install -r requirements.txt

# Sales & Marketing  
cd ../sales_marketing
pip install -r requirements.txt

# MCP Servers
cd ../../mcps/hubspot_integration
pip install -r requirements.txt

cd ../quickbooks_integration
pip install -r requirements.txt
```

#### Frontend Portal
```bash
cd portal/frontend
npm install
```

### 5. Start System

#### Start Redis (Required for orchestrator)
```bash
redis-server
```

#### Start Backend Services
```bash
# Terminal 1: Orchestrator Agent
cd agents/orchestrator
source orchestrator-env/bin/activate
python orchestrator.py

# Terminal 2: Financial Intelligence Agent
cd agents/financial_intelligence
python financial_agent.py

# Terminal 3: Sales & Marketing Agent
cd agents/sales_marketing
python sales_marketing_agent.py

# Terminal 4: HubSpot MCP Server
cd mcps/hubspot_integration
python hubspot_mcp.py

# Terminal 5: QuickBooks MCP Server
cd mcps/quickbooks_integration
python quickbooks_mcp.py
```

#### Start Frontend Portal
```bash
# Terminal 6: Frontend
cd portal/frontend
npm run dev
```

### 6. Access System
- Frontend Portal: http://localhost:3000
- Orchestrator API: http://localhost:8001
- Financial Agent API: http://localhost:8002
- Sales/Marketing Agent API: http://localhost:8003

## 📁 Project Structure

```
uplevel-ai-agents/
├── agents/                          # AI Agent implementations
│   ├── orchestrator/               # Central orchestration agent
│   ├── financial_intelligence/     # QuickBooks financial agent
│   └── sales_marketing/            # HubSpot sales & marketing agent
├── mcps/                           # Model Context Protocol servers
│   ├── hubspot_integration/        # HubSpot MCP server
│   └── quickbooks_integration/     # QuickBooks MCP server
├── portal/                         # Web interface
│   └── frontend/                   # Next.js frontend application
├── deployment/                     # Cloud deployment configurations
└── docs/                          # Documentation
```

## 🔧 Configuration

### Agent Communication
Agents communicate via HTTP APIs and Redis for state management. The orchestrator coordinates multi-agent workflows.

### Database Configuration
- Financial Agent: SQLite by default (`financial_data.db`)
- Sales Agent: SQLite by default (`sales_marketing.db`) 
- For production: Configure PostgreSQL/MySQL in environment files

### Authentication
- Frontend uses NextAuth.js
- Agents use API key authentication
- External services use OAuth2 (HubSpot, QuickBooks)

## 🚢 Deployment

### Google Cloud Platform
```bash
# Deploy orchestrator
cd deployment
./deploy_agent.py orchestrator

# Deploy other agents
./deploy_agent.py financial
./deploy_agent.py sales_marketing
```

### Docker Containers
Each agent includes a Dockerfile for containerized deployment.

## 🧪 Testing

```bash
# Run agent tests
cd agents/orchestrator
python -m pytest test_orchestrator.py

cd ../financial_intelligence  
python -m pytest test_financial_agent.py

cd ../sales_marketing
python -m pytest test_sales_marketing_agent.py

# Run MCP tests
cd ../../mcps/hubspot_integration
python -m pytest test_hubspot_mcp.py

cd ../quickbooks_integration
python -m pytest test_quickbooks_mcp.py
```

## 📖 Documentation

- [System Documentation](SYSTEM_DOCUMENTATION.md) - Complete technical overview
- [Agent2Agent Communication](AGENT2AGENT_DEMO.md) - Inter-agent communication examples
- [Implementation Tasks](IMPLEMENTATION_TASKS.md) - Development roadmap
- [Deployment Status](DEPLOYMENT_STATUS.md) - Current deployment state

## 🔒 Security Notes

- Never commit actual API keys or secrets
- Use environment files for configuration
- Rotate API keys regularly
- Enable OAuth2 for production external service integrations
- Use HTTPS in production deployments

## 📞 Support

For questions or issues:
1. Check existing documentation
2. Review environment configuration
3. Verify API key setup
4. Check agent logs for errors

## 🎯 System Capabilities

### Financial Intelligence
- QuickBooks integration for accounting data
- Financial report generation
- Transaction analysis
- Budget tracking and forecasting

### Sales & Marketing
- HubSpot CRM integration
- Lead management and scoring
- Email marketing automation
- Sales pipeline analytics

### Multi-Agent Orchestration
- Coordinated workflows across agents
- State management via Redis
- Event-driven communication
- Scalable agent deployment

Built for enterprise-grade business automation and intelligence.
