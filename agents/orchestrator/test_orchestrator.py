"""
Test suite for Central Orchestrator
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from orchestrator import (
    CentralOrchestrator, 
    OrchestratorQuery, 
    QueryType, 
    AgentType,
    IntentRecognitionEngine,
    RedisStateManager,
    app
)

# Test client
client = TestClient(app)

class TestIntentRecognitionEngine:
    """Test intent recognition system"""
    
    def test_intent_engine_initialization(self):
        """Test intent recognition engine initializes correctly"""
        engine = IntentRecognitionEngine()
        assert engine.vectorizer is not None
        assert len(engine.intent_labels) > 0
        assert engine.tfidf_matrix is not None
    
    def test_single_agent_financial_classification(self):
        """Test classification of financial queries"""
        engine = IntentRecognitionEngine()
        
        queries = [
            "Generate a P&L statement for this month",
            "Show me our revenue analysis",
            "What are our expenses this quarter?",
            "Create a financial forecast"
        ]
        
        for query in queries:
            query_type, agent, confidence = engine.classify_intent(query)
            assert query_type in [QueryType.SINGLE_AGENT, QueryType.COLLABORATIVE]
            if query_type == QueryType.SINGLE_AGENT:
                assert agent == AgentType.FINANCIAL
            assert confidence > 0.0
    
    def test_single_agent_sales_classification(self):
        """Test classification of sales/marketing queries"""
        engine = IntentRecognitionEngine()
        
        queries = [
            "Show me our lead generation performance",
            "Create a marketing campaign",
            "Analyze our sales pipeline",
            "What's our conversion rate?"
        ]
        
        for query in queries:
            query_type, agent, confidence = engine.classify_intent(query)
            assert query_type in [QueryType.SINGLE_AGENT, QueryType.COLLABORATIVE]
            if query_type == QueryType.SINGLE_AGENT:
                assert agent == AgentType.SALES_MARKETING
    
    def test_multi_agent_classification(self):
        """Test classification of multi-agent queries"""
        engine = IntentRecognitionEngine()
        
        queries = [
            "Show me our financial performance and create a sales strategy",
            "Analyze our P&L and recommend marketing improvements",
            "Review costs and optimize our sales process"
        ]
        
        for query in queries:
            query_type, agent, confidence = engine.classify_intent(query)
            assert query_type in [QueryType.COLLABORATIVE, QueryType.MULTI_AGENT]
    
    def test_sequential_classification(self):
        """Test classification of sequential queries"""
        engine = IntentRecognitionEngine()
        
        queries = [
            "First generate a P&L statement then create a sales strategy",
            "Show financial performance then recommend marketing actions"
        ]
        
        for query in queries:
            query_type, agent, confidence = engine.classify_intent(query)
            assert query_type == QueryType.SEQUENTIAL

class TestRedisStateManager:
    """Test Redis state management"""
    
    @pytest.fixture
    def state_manager(self):
        """Create state manager for testing"""
        manager = RedisStateManager()
        return manager
    
    @pytest.mark.asyncio
    async def test_redis_initialization(self, state_manager):
        """Test Redis connection initialization"""
        await state_manager.initialize()
        # Should work with fallback if Redis not available
        assert hasattr(state_manager, '_fallback_storage') or state_manager.redis_client is not None
    
    @pytest.mark.asyncio
    async def test_session_context_storage(self, state_manager):
        """Test session context storage and retrieval"""
        await state_manager.initialize()
        
        session_id = "test_session_123"
        context = {
            "user_id": "user_123",
            "last_query": "test query",
            "preferences": {"theme": "dark"}
        }
        
        # Store context
        success = await state_manager.store_session_context(session_id, context)
        assert success
        
        # Retrieve context
        retrieved_context = await state_manager.get_session_context(session_id)
        assert retrieved_context == context

class TestOrchestratorAPI:
    """Test orchestrator API endpoints"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_query_endpoint_structure(self):
        """Test query endpoint accepts proper structure"""
        query_data = {
            "query": "Generate a P&L statement",
            "session_id": "test_session",
            "context": {"period": "current_month"}
        }
        
        # This will fail without agents running, but should validate structure
        response = client.post("/query", json=query_data)
        # Should return 200 but with error about agent connectivity
        data = response.json()
        assert "answer" in data
        assert "query_type" in data
        assert "agents_involved" in data
        assert "session_id" in data

class TestCentralOrchestrator:
    """Test central orchestrator functionality"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator for testing"""
        return CentralOrchestrator()
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes correctly"""
        await orchestrator.initialize()
        assert orchestrator.intent_engine is not None
        assert orchestrator.state_manager is not None
        assert orchestrator.agent_comm is not None
    
    @pytest.mark.asyncio
    async def test_single_agent_query_structure(self, orchestrator):
        """Test single agent query processing structure"""
        await orchestrator.initialize()
        
        query = OrchestratorQuery(
            query="Generate a P&L statement for this month",
            session_id="test_session"
        )
        
        # Mock agent communication
        with patch.object(orchestrator.agent_comm, 'send_to_agent', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {
                "answer": "Mock P&L statement",
                "data": {"revenue": 100000},
                "analysis": {"profit_margin": 25},
                "recommendations": ["Reduce costs"]
            }
            
            response = await orchestrator.process_query(query)
            
            assert response.query_type == QueryType.SINGLE_AGENT
            assert AgentType.FINANCIAL in response.agents_involved
            assert response.session_id == "test_session"
            assert "Mock P&L statement" in response.answer
    
    @pytest.mark.asyncio
    async def test_collaborative_query_structure(self, orchestrator):
        """Test collaborative query processing structure"""
        await orchestrator.initialize()
        
        query = OrchestratorQuery(
            query="Show me financial performance and create a sales strategy",
            session_id="test_session"
        )
        
        # Mock agent communication
        with patch.object(orchestrator.agent_comm, 'send_collaborative_request', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = [
                # Financial agent response
                {
                    "answer": "Financial analysis complete",
                    "data": {"revenue": 100000, "profit_margin": 25},
                    "recommendations": ["Optimize costs"]
                },
                # Sales agent response  
                {
                    "answer": "Sales strategy recommendations",
                    "data": {"lead_count": 500, "conversion_rate": 10},
                    "recommendations": ["Increase lead generation"]
                }
            ]
            
            response = await orchestrator.process_query(query)
            
            assert response.query_type == QueryType.COLLABORATIVE
            assert AgentType.FINANCIAL in response.agents_involved
            assert AgentType.SALES_MARKETING in response.agents_involved
            assert "Financial Analysis" in response.answer
            assert "Sales & Marketing" in response.answer

class TestAgentCommunication:
    """Test agent communication functionality"""
    
    @pytest.mark.asyncio
    async def test_agent_endpoint_configuration(self):
        """Test agent endpoints are configured correctly"""
        from orchestrator import AgentCommunicationService
        
        comm_service = AgentCommunicationService()
        
        assert AgentType.FINANCIAL in comm_service.agent_endpoints
        assert AgentType.SALES_MARKETING in comm_service.agent_endpoints
        
        # Check endpoints are valid URLs
        for agent, endpoint in comm_service.agent_endpoints.items():
            assert endpoint.startswith(('http://', 'https://'))

# Integration tests (require running agents)
class TestIntegration:
    """Integration tests - require actual agent services"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_orchestrator_workflow(self):
        """Test complete orchestrator workflow with real agents"""
        # This test requires actual agents to be running
        # Skip if not in integration test mode
        pytest.skip("Integration test - requires running agent services")
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/query", json={
                "query": "Generate a P&L statement for this month",
                "session_id": "integration_test"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["query_type"] == "single_agent"
            assert "financial_intelligence" in [agent for agent in data["agents_involved"]]

# Performance tests
class TestPerformance:
    """Performance tests for orchestrator"""
    
    @pytest.mark.asyncio
    async def test_concurrent_query_processing(self):
        """Test orchestrator handles concurrent requests"""
        orchestrator = CentralOrchestrator()
        await orchestrator.initialize()
        
        queries = [
            OrchestratorQuery(query="Generate P&L", session_id=f"session_{i}")
            for i in range(10)
        ]
        
        # Mock agent responses
        with patch.object(orchestrator.agent_comm, 'send_to_agent', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {
                "answer": "Mock response",
                "data": {},
                "recommendations": []
            }
            
            # Process queries concurrently
            tasks = [orchestrator.process_query(query) for query in queries]
            responses = await asyncio.gather(*tasks)
            
            # All should complete successfully
            assert len(responses) == 10
            for response in responses:
                assert response.answer is not None
                assert response.session_id.startswith("session_")

if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
