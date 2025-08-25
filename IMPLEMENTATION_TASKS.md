# Uplevel AI Agent Implementation Tasks

## Quick Start Commands

```bash
# 1. Set up Google Cloud project
gcloud projects create uplevel-ai-agents
gcloud config set project uplevel-ai-agents
gcloud services enable aiplatform.googleapis.com run.googleapis.com firestore.googleapis.com

# 2. Initialize ADK project
pip install google-adk
adk init financial-intelligence-agent
cd financial-intelligence-agent

# 3. Install dependencies
pip install google-cloud-aiplatform mcp-hubspot mcp-quickbooks fastapi uvicorn
```

## Task Breakdown for Claude Code

### TASK 1: Project Foundation Setup
**Priority**: Critical  
**Estimated Time**: 4-6 hours

#### Subtasks:
1. **Google Cloud Project Setup**
   - Create new GCP project: `uplevel-ai-agents`
   - Enable required APIs: Vertex AI, Cloud Run, Firestore, BigQuery
   - Create service account with appropriate permissions
   - Generate and download service account key

2. **Development Environment**
   - Install Google ADK Python: `pip install google-adk`
   - Set up virtual environment with Python 3.9+
   - Configure authentication: `export GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json`

3. **Repository Structure**
   ```
   uplevel-ai-agents/
   ├── agents/
   │   ├── financial_intelligence/
   │   ├── sales_marketing/
   │   └── operations/
   ├── mcps/
   │   ├── hubspot_integration/
   │   └── quickbooks_integration/
   ├── portal/
   │   ├── frontend/
   │   └── backend/
   ├── deployment/
   └── tests/
   ```

**Acceptance Criteria**:
- [ ] GCP project created and APIs enabled
- [ ] ADK installed and authenticated
- [ ] Repository structure established
- [ ] Can run `adk --version` successfully

---

### TASK 2: HubSpot MCP Integration
**Priority**: Critical  
**Estimated Time**: 8-12 hours

#### Implementation Details:
```python
# File: mcps/hubspot_integration/hubspot_mcp.py
import asyncio
import os
from typing import List, Dict, Any
from hubspot import HubSpot
from hubspot.crm.deals import ApiException

class HubSpotMCP:
    def __init__(self, access_token: str):
        self.api_client = HubSpot(access_token=access_token)
        
    async def get_closed_deals(self, date_range: str) -> List[Dict]:
        """Fetch closed deals for P&L calculation"""
        try:
            deals_api = self.api_client.crm.deals
            # Implementation for date filtering and deal retrieval
            deals = deals_api.basic_api.get_page(
                properties=['dealname', 'amount', 'closedate', 'dealstage']
            )
            return [deal.properties for deal in deals.results]
        except ApiException as e:
            print(f"HubSpot API error: {e}")
            return []
    
    async def get_revenue_by_period(self, period: str) -> float:
        """Calculate total revenue for specific period"""
        deals = await self.get_closed_deals(period)
        return sum(float(deal.get('amount', 0)) for deal in deals)
```

#### Subtasks:
1. **HubSpot API Setup**
   - Create HubSpot private app in developer account
   - Configure OAuth scopes: `crm.objects.deals.read`, `crm.objects.contacts.read`
   - Generate access token and store securely

2. **MCP Server Implementation**
   - Create HubSpot MCP server following MCP protocol
   - Implement deal retrieval methods
   - Add contact and company data access
   - Handle rate limiting and error responses

3. **Data Models**
   - Create Pydantic models for HubSpot data structures
   - Implement data validation and transformation
   - Add caching layer for frequent queries

**Acceptance Criteria**:
- [ ] Can authenticate with HubSpot API
- [ ] Successfully retrieve deal data
- [ ] MCP server responds to protocol requests
- [ ] Data models validate HubSpot responses
- [ ] Rate limiting implemented

---

### TASK 3: QuickBooks MCP Integration  
**Priority**: Critical  
**Estimated Time**: 10-14 hours

#### Implementation Details:
```python
# File: mcps/quickbooks_integration/quickbooks_mcp.py
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
import requests

class QuickBooksMCP:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_client = AuthClient(
            client_id=client_id,
            client_secret=client_secret,
            environment='sandbox',  # Change to 'production' for live
            redirect_uri='http://localhost:8000/callback'
        )
    
    async def get_expenses(self, date_range: str) -> List[Dict]:
        """Fetch expenses for P&L calculation"""
        base_url = f"{self.base_url}/v3/company/{self.company_id}"
        
        query = f"SELECT * FROM Purchase WHERE TxnDate BETWEEN '{start_date}' AND '{end_date}'"
        response = requests.get(
            f"{base_url}/query",
            params={'query': query},
            headers={'Authorization': f'Bearer {self.access_token}'}
        )
        return response.json()
    
    async def get_profit_loss(self, period: str) -> Dict:
        """Generate P&L statement from QuickBooks data"""
        # Implementation for P&L report generation
        pass
```

#### Subtasks:
1. **QuickBooks API Setup**
   - Register QuickBooks developer account
   - Create sandbox app for testing
   - Implement OAuth 2.0 flow for authorization
   - Handle token refresh automatically

2. **Financial Data Access**
   - Implement expense tracking queries
   - Add revenue/income data retrieval
   - Create chart of accounts mapping
   - Build P&L statement generation logic

3. **Security & Compliance**
   - Encrypt stored tokens and credentials
   - Implement secure token storage in Google Secret Manager
   - Add audit logging for financial data access
   - Ensure PCI DSS compliance for financial data

**Acceptance Criteria**:
- [ ] OAuth flow completed with QuickBooks
- [ ] Can retrieve expense and income data
- [ ] P&L statement generates correctly
- [ ] Secure credential storage implemented
- [ ] Audit logging functional

---

### TASK 4: Financial Intelligence Agent Core
**Priority**: Critical  
**Estimated Time**: 12-16 hours

#### Implementation Details:
```python
# File: agents/financial_intelligence/agent.py
from adk import Agent
from adk.core import State, Memory
import asyncio
from datetime import datetime, timedelta

class FinancialIntelligenceAgent(Agent):
    def __init__(self):
        super().__init__(name="financial_intelligence")
        self.hubspot = HubSpotMCP(os.getenv("HUBSPOT_TOKEN"))
        self.quickbooks = QuickBooksMCP(
            client_id=os.getenv("QB_CLIENT_ID"),
            client_secret=os.getenv("QB_CLIENT_SECRET")
        )
        self.memory = Memory()
        
    async def handle_query(self, query: str, context: Dict) -> str:
        """Main query handler for financial questions"""
        
        # Classify query intent
        intent = await self.classify_intent(query)
        
        if intent == "generate_pl":
            return await self.generate_pl_statement(context.get('period', 'current_month'))
        elif intent == "forecast":
            return await self.generate_forecast(context.get('months', 3))
        elif intent == "cost_analysis":
            return await self.analyze_costs(context.get('category'))
        else:
            return "I can help with P&L statements, forecasting, and cost analysis. What would you like to know?"
    
    async def generate_pl_statement(self, period: str) -> str:
        """Generate comprehensive P&L statement"""
        try:
            # Parallel data fetching
            revenue_task = asyncio.create_task(self.hubspot.get_revenue_by_period(period))
            expenses_task = asyncio.create_task(self.quickbooks.get_expenses(period))
            
            revenue = await revenue_task
            expenses = await expenses_task
            
            net_profit = revenue - sum(exp['amount'] for exp in expenses)
            margin = (net_profit / revenue * 100) if revenue > 0 else 0
            
            # Store in memory for future reference
            self.memory.store(f"pl_{period}", {
                "revenue": revenue,
                "expenses": expenses,
                "net_profit": net_profit,
                "margin": margin,
                "generated_at": datetime.now().isoformat()
            })
            
            return self.format_pl_response(revenue, expenses, net_profit, margin)
            
        except Exception as e:
            return f"Error generating P&L statement: {str(e)}"
```

#### Subtasks:
1. **Agent Architecture**
   - Implement base ADK Agent class
   - Add conversation state management
   - Create intent classification system
   - Implement context-aware responses

2. **Financial Analysis Logic**
   - Build P&L statement generation
   - Implement forecasting algorithms
   - Create cost analysis and trend detection
   - Add budget variance reporting

3. **Memory & Learning**
   - Implement conversation memory
   - Add knowledge retention between sessions
   - Create user preference learning
   - Build query history analysis

**Acceptance Criteria**:
- [ ] Agent responds to financial queries correctly
- [ ] P&L statements generate with real data
- [ ] Conversation context maintained
- [ ] Memory system stores relevant information
- [ ] Error handling covers edge cases

---

### TASK 5: Vertex AI Deployment
**Priority**: High  
**Estimated Time**: 6-8 hours

#### Implementation Details:
```python
# File: deployment/deploy_agent.py
from vertexai import agent_engines
import os

def deploy_financial_agent():
    """Deploy agent to Vertex AI Agent Engine"""
    
    # Agent configuration
    config = {
        "display_name": "Uplevel Financial Intelligence Agent",
        "location": "us-central1",
        "description": "AI agent for financial analysis and P&L generation"
    }
    
    # Create agent application
    app = create_financial_agent_app()
    
    # Deploy to managed Agent Engine
    remote_agent = agent_engines.create(
        app,
        requirements=[
            "google-cloud-aiplatform>=1.47.0",
            "fastapi>=0.104.0",
            "pydantic>=2.0.0",
            "hubspot-api-client>=8.0.0",
            "intuitlib>=1.0.0"
        ],
        **config
    )
    
    print(f"Agent deployed successfully: {remote_agent.resource_name}")
    return remote_agent

if __name__ == "__main__":
    agent = deploy_financial_agent()
```

#### Subtasks:
1. **Deployment Configuration**
   - Configure Vertex AI Agent Engine settings
   - Set up environment variables and secrets
   - Define resource requirements and scaling
   - Configure networking and security

2. **Testing & Validation**
   - Deploy to staging environment first
   - Run integration tests against live APIs
   - Validate response accuracy and performance
   - Load test with concurrent requests

3. **Monitoring Setup**
   - Configure Cloud Monitoring dashboards
   - Set up alerting for errors and performance
   - Add custom metrics for business KPIs
   - Implement health checks and uptime monitoring

**Acceptance Criteria**:
- [ ] Agent successfully deploys to Vertex AI
- [ ] All integrations work in cloud environment
- [ ] Monitoring dashboards show healthy metrics
- [ ] Can handle 100+ concurrent requests
- [ ] Response times under 10 seconds

---

### TASK 6: Frontend Portal Development
**Priority**: Medium  
**Estimated Time**: 16-20 hours

#### Implementation Overview:
- **Framework**: Next.js 14 with TypeScript
- **Styling**: Tailwind CSS + shadcn/ui components
- **Authentication**: Google OAuth via NextAuth.js
- **State Management**: Zustand for client state
- **Real-time**: WebSockets for live chat

#### Key Features:
1. **Chat Interface**: Real-time conversation with agent
2. **Session Management**: Persistent conversation history
3. **Agent Selection**: Switch between different agents
4. **Dashboard**: Financial metrics and insights visualization
5. **Settings**: User preferences and API configurations

**Acceptance Criteria**:
- [ ] Responsive design works on desktop/mobile
- [ ] Real-time chat functionality
- [ ] Session persistence across browser sessions
- [ ] Authentication integrated with Google
- [ ] Dashboard shows live financial data

---

## Testing Strategy

### Unit Tests
```python
# File: tests/test_financial_agent.py
import pytest
from agents.financial_intelligence.agent import FinancialIntelligenceAgent

@pytest.fixture
def agent():
    return FinancialIntelligenceAgent()

@pytest.mark.asyncio
async def test_pl_statement_generation(agent, mock_hubspot_data, mock_quickbooks_data):
    result = await agent.generate_pl_statement("2024-01")
    assert "Revenue:" in result
    assert "Expenses:" in result
    assert "Net Profit:" in result
```

### Integration Tests
- Test HubSpot API integration with sandbox data
- Validate QuickBooks OAuth flow and data retrieval
- End-to-end agent conversation testing
- Performance testing with concurrent users

### Deployment Testing
- Staging environment validation
- Production deployment smoke tests
- Rollback procedure verification
- Security penetration testing

## Monitoring & Observability

### Metrics to Track
- **Performance**: Response times, throughput, error rates
- **Business**: P&L accuracy, user engagement, cost savings
- **Technical**: API latency, memory usage, CPU utilization
- **Security**: Failed authentication attempts, API rate limits

### Alerting Rules
- Agent response time > 30 seconds
- Error rate > 5%
- API failures > 10 in 5 minutes
- Memory usage > 80%

## Security Considerations

### Data Protection
- Encrypt all API credentials using Google Secret Manager
- Implement row-level security for multi-tenant data
- Use HTTPS for all communications
- Add API rate limiting and DDoS protection

### Access Control
- Implement role-based access control (RBAC)
- Use Google IAM for service-to-service authentication
- Add audit logging for all financial data access
- Implement session timeout and refresh policies

## Success Metrics

### Phase 1 KPIs
- **Accuracy**: P&L statements match manual calculations (>95%)
- **Performance**: Average response time <10 seconds
- **Reliability**: 99.9% uptime during business hours
- **Adoption**: 80% of financial queries answered by agent

### Business Impact Goals
- **Cost Reduction**: Save 20+ hours/week of manual reporting
- **Accuracy Improvement**: Reduce financial reporting errors by 90%
- **Speed**: Generate P&L statements 10x faster than manual process
- **Scalability**: Handle 10x more financial queries without additional staff