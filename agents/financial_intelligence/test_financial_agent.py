"""
Test suite for Financial Intelligence Agent
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any

from financial_agent import (
    FinancialIntelligenceAgent, FinancialQuery, FinancialResponse, 
    ComprehensivePL
)
from config import AgentConfig

class TestFinancialIntelligenceAgent:
    """Test Financial Intelligence Agent functionality"""
    
    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP client for MCP communication"""
        mock_client = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def sample_hubspot_response(self):
        """Sample HubSpot MCP response"""
        return {
            "success": True,
            "data": {
                "total_revenue": 50000,
                "deal_count": 5,
                "average_deal_size": 10000,
                "pipeline_value": 75000
            }
        }
    
    @pytest.fixture
    def sample_quickbooks_response(self):
        """Sample QuickBooks MCP response"""
        return {
            "success": True,
            "data": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "total_expenses": 30000,
                "expense_count": 15
            }
        }
    
    @pytest.fixture
    def agent(self, mock_http_client):
        """Create agent with mocked HTTP client"""
        agent = FinancialIntelligenceAgent()
        agent.http_client = mock_http_client
        return agent
    
    def test_agent_initialization(self):
        """Test agent initializes correctly"""
        agent = FinancialIntelligenceAgent()
        assert agent.name == "financial_intelligence_agent"
        assert agent.hubspot_mcp_url == "http://localhost:8001"
        assert agent.quickbooks_mcp_url == "http://localhost:8002"
        assert agent.memory is not None
    
    def test_classify_intent_pl(self, agent):
        """Test P&L intent classification"""
        queries = [
            "Generate a P&L statement",
            "Show me profit and loss",
            "What's our pl for this month?"
        ]
        
        for query in queries:
            intent = agent._classify_intent(query)
            assert intent == "generate_pl"
    
    def test_classify_intent_forecast(self, agent):
        """Test forecast intent classification"""
        queries = [
            "What's our forecast for next quarter?",
            "Predict our future performance",
            "Show me revenue projections"
        ]
        
        for query in queries:
            intent = agent._classify_intent(query)
            assert intent == "forecast"
    
    def test_classify_intent_cost_analysis(self, agent):
        """Test cost analysis intent classification"""
        queries = [
            "Analyze our costs",
            "What are our expenses?",
            "Show me spending breakdown"
        ]
        
        for query in queries:
            intent = agent._classify_intent(query)
            assert intent == "cost_analysis"
    
    def test_classify_intent_general(self, agent):
        """Test general intent classification"""
        queries = [
            "Hello",
            "What can you do?",
            "Help me"
        ]
        
        for query in queries:
            intent = agent._classify_intent(query)
            assert intent == "general"
    
    @pytest.mark.asyncio
    async def test_generate_comprehensive_pl_success(
        self, 
        agent, 
        sample_hubspot_response, 
        sample_quickbooks_response
    ):
        """Test successful P&L generation"""
        
        # Mock HTTP responses
        async def mock_post(url, json):
            if "hubspot" in url:
                response = Mock()
                response.json.return_value = sample_hubspot_response
                response.raise_for_status.return_value = None
                return response
            else:  # quickbooks
                response = Mock()
                response.json.return_value = sample_quickbooks_response
                response.raise_for_status.return_value = None
                return response
        
        agent.http_client.post = mock_post
        
        pl = await agent._generate_comprehensive_pl("current_month")
        
        assert isinstance(pl, ComprehensivePL)
        assert pl.total_revenue == 50000
        assert pl.total_expenses == 30000
        assert pl.net_profit == 20000
        assert pl.profit_margin == 40.0
    
    @pytest.mark.asyncio
    async def test_generate_comprehensive_pl_api_failure(self, agent):
        """Test P&L generation with API failure"""
        
        # Mock failed HTTP response
        async def mock_post_failure(url, json):
            response = Mock()
            response.json.return_value = {"success": False, "error": "API Error"}
            response.raise_for_status.return_value = None
            return response
        
        agent.http_client.post = mock_post_failure
        
        with pytest.raises(Exception, match="Failed to get revenue data"):
            await agent._generate_comprehensive_pl("current_month")
    
    @pytest.mark.asyncio
    async def test_handle_pl_request(
        self, 
        agent, 
        sample_hubspot_response, 
        sample_quickbooks_response
    ):
        """Test P&L request handling"""
        
        # Mock successful P&L generation
        async def mock_generate_pl(period):
            return ComprehensivePL(
                period=period,
                start_date="2024-01-01",
                end_date="2024-01-31",
                total_revenue=50000,
                revenue_deals=5,
                average_deal_size=10000,
                pipeline_value=75000,
                total_expenses=30000,
                expense_count=15,
                net_profit=20000,
                profit_margin=40.0,
                break_even_point=30000,
                projected_revenue=62500,
                projected_expenses=31500,
                projected_profit=31000,
                generated_at=datetime.now().isoformat()
            )
        
        agent._generate_comprehensive_pl = mock_generate_pl
        
        query = FinancialQuery(query="Generate P&L statement", period="current_month")
        response = await agent._handle_pl_request(query)
        
        assert isinstance(response, FinancialResponse)
        assert "Profit & Loss Statement" in response.answer
        assert response.data["total_revenue"] == 50000
        assert len(response.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_handle_general_query(self, agent):
        """Test general query handling"""
        
        query = FinancialQuery(query="What can you help me with?")
        response = await agent._handle_general_financial_query(query)
        
        assert isinstance(response, FinancialResponse)
        assert "financial analysis" in response.answer.lower()
        assert "p&l statements" in response.answer.lower()
    
    @pytest.mark.asyncio
    async def test_handle_query_with_exception(self, agent):
        """Test query handling with exception"""
        
        # Mock method to raise exception
        async def mock_handle_pl_request(query):
            raise Exception("Test error")
        
        agent._handle_pl_request = mock_handle_pl_request
        
        query = FinancialQuery(query="Generate P&L statement")
        response = await agent.handle_query(query)
        
        assert isinstance(response, FinancialResponse)
        assert "error processing your financial query" in response.answer
        assert "Test error" in response.answer
    
    def test_format_pl_response(self, agent):
        """Test P&L response formatting"""
        
        pl = ComprehensivePL(
            period="current_month",
            start_date="2024-01-01",
            end_date="2024-01-31",
            total_revenue=50000,
            revenue_deals=5,
            average_deal_size=10000,
            pipeline_value=75000,
            total_expenses=30000,
            expense_count=15,
            net_profit=20000,
            profit_margin=40.0,
            break_even_point=30000,
            projected_revenue=62500,
            projected_expenses=31500,
            projected_profit=31000,
            generated_at=datetime.now().isoformat()
        )
        
        response = agent._format_pl_response(pl)
        
        assert "Profit & Loss Statement" in response
        assert "$50,000.00" in response
        assert "$20,000.00" in response
        assert "40.0%" in response
    
    def test_analyze_pl_performance(self, agent):
        """Test P&L performance analysis"""
        
        pl = ComprehensivePL(
            period="current_month",
            start_date="2024-01-01",
            end_date="2024-01-31",
            total_revenue=50000,
            revenue_deals=5,
            average_deal_size=10000,
            pipeline_value=75000,
            total_expenses=30000,
            expense_count=15,
            net_profit=20000,
            profit_margin=40.0,
            break_even_point=30000,
            projected_revenue=62500,
            projected_expenses=31500,
            projected_profit=31000,
            generated_at=datetime.now().isoformat()
        )
        
        analysis = agent._analyze_pl_performance(pl)
        
        assert analysis["profitability"] == "profitable"
        assert analysis["margin_health"] == "excellent"
        assert analysis["revenue_per_deal"] == 10000
        assert analysis["expense_ratio"] == 0.6
    
    def test_generate_pl_recommendations_profitable(self, agent):
        """Test recommendations for profitable business"""
        
        pl = ComprehensivePL(
            period="current_month",
            start_date="2024-01-01",
            end_date="2024-01-31",
            total_revenue=50000,
            revenue_deals=5,
            average_deal_size=10000,
            pipeline_value=75000,
            total_expenses=30000,
            expense_count=15,
            net_profit=20000,
            profit_margin=40.0,
            break_even_point=30000,
            projected_revenue=62500,
            projected_expenses=31500,
            projected_profit=31000,
            generated_at=datetime.now().isoformat()
        )
        
        recommendations = agent._generate_pl_recommendations(pl)
        
        assert len(recommendations) > 0
        assert any("pipeline" in rec.lower() for rec in recommendations)
        assert any("monthly" in rec.lower() for rec in recommendations)
    
    def test_generate_pl_recommendations_loss_making(self, agent):
        """Test recommendations for loss-making business"""
        
        pl = ComprehensivePL(
            period="current_month",
            start_date="2024-01-01",
            end_date="2024-01-31",
            total_revenue=20000,
            revenue_deals=2,
            average_deal_size=10000,
            pipeline_value=30000,
            total_expenses=30000,
            expense_count=20,
            net_profit=-10000,
            profit_margin=-50.0,
            break_even_point=30000,
            projected_revenue=25000,
            projected_expenses=31500,
            projected_profit=-6500,
            generated_at=datetime.now().isoformat()
        )
        
        recommendations = agent._generate_pl_recommendations(pl)
        
        assert any("profitability" in rec.lower() for rec in recommendations)
        assert any("pricing" in rec.lower() for rec in recommendations)

class TestFinancialModels:
    """Test Financial data models"""
    
    def test_financial_query_creation(self):
        """Test FinancialQuery model creation"""
        
        query = FinancialQuery(
            query="Generate P&L",
            period="current_month",
            context={"user_id": "123"}
        )
        
        assert query.query == "Generate P&L"
        assert query.period == "current_month"
        assert query.context["user_id"] == "123"
    
    def test_financial_response_creation(self):
        """Test FinancialResponse model creation"""
        
        response = FinancialResponse(
            answer="Your P&L statement is ready",
            data={"revenue": 50000},
            analysis={"profitability": "good"},
            recommendations=["Review expenses"]
        )
        
        assert response.answer == "Your P&L statement is ready"
        assert response.data["revenue"] == 50000
        assert response.analysis["profitability"] == "good"
        assert len(response.recommendations) == 1
    
    def test_comprehensive_pl_creation(self):
        """Test ComprehensivePL model creation"""
        
        pl = ComprehensivePL(
            period="current_month",
            start_date="2024-01-01",
            end_date="2024-01-31",
            total_revenue=50000,
            revenue_deals=5,
            average_deal_size=10000,
            total_expenses=30000,
            expense_count=15,
            net_profit=20000,
            profit_margin=40.0,
            break_even_point=30000,
            generated_at=datetime.now().isoformat()
        )
        
        assert pl.total_revenue == 50000
        assert pl.net_profit == 20000
        assert pl.profit_margin == 40.0

def run_tests():
    """Run all tests"""
    import subprocess
    
    result = subprocess.run([
        "python", "-m", "pytest", 
        "test_financial_agent.py", 
        "-v",
        "--tb=short"
    ], capture_output=True, text=True)
    
    print("Test Results:")
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
    
    return result.returncode == 0

if __name__ == "__main__":
    run_tests()
