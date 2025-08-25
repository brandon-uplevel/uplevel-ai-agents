"""
Test suite for HubSpot MCP Integration
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any

from hubspot_mcp import HubSpotMCPServer, HubSpotDeal, RevenueReport
from config import HubSpotConfig

class TestHubSpotMCPServer:
    """Test HubSpot MCP Server functionality"""
    
    @pytest.fixture
    def mock_hubspot_api(self):
        """Mock HubSpot API client"""
        mock_client = Mock()
        mock_deals_api = Mock()
        mock_search_api = Mock()
        
        mock_client.crm.deals = mock_deals_api
        mock_deals_api.search_api = mock_search_api
        
        return mock_client
    
    @pytest.fixture
    def sample_deal_data(self):
        """Sample HubSpot deal data"""
        return {
            "hs_object_id": "12345",
            "dealname": "Test Deal",
            "amount": "50000",
            "closedate": "2024-01-15",
            "dealstage": "closedwon",
            "pipeline": "default",
            "hubspot_owner_id": "owner123",
            "createdate": "2024-01-01"
        }
    
    @pytest.fixture
    def mcp_server(self, mock_hubspot_api):
        """Create MCP server with mocked HubSpot API"""
        with patch.dict('os.environ', {'HUBSPOT_ACCESS_TOKEN': 'test-token'}):
            server = HubSpotMCPServer()
            server.api_client = mock_hubspot_api
            return server
    
    def test_server_initialization(self):
        """Test server initializes correctly"""
        with patch.dict('os.environ', {'HUBSPOT_ACCESS_TOKEN': 'test-token'}):
            server = HubSpotMCPServer()
            assert server.access_token == 'test-token'
            assert server.server.name == 'hubspot-mcp'
    
    def test_server_initialization_no_token(self):
        """Test server raises error without access token"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="HubSpot access token not provided"):
                HubSpotMCPServer()
    
    def test_process_deal_properties(self, mcp_server, sample_deal_data):
        """Test deal properties processing"""
        result = mcp_server._process_deal_properties(sample_deal_data)
        
        assert result["deal_id"] == "12345"
        assert result["deal_name"] == "Test Deal"
        assert result["amount"] == 50000.0
        assert result["deal_stage"] == "closedwon"
    
    def test_process_deal_properties_invalid_amount(self, mcp_server):
        """Test deal properties processing with invalid amount"""
        invalid_data = {
            "hs_object_id": "12345",
            "dealname": "Test Deal",
            "amount": "invalid",
            "dealstage": "closedwon"
        }
        
        result = mcp_server._process_deal_properties(invalid_data)
        assert result["amount"] == 0.0
    
    def test_parse_date_range_current_month(self, mcp_server):
        """Test date range parsing for current month"""
        start_date, end_date = mcp_server._parse_date_range("current_month")
        
        now = datetime.now()
        assert start_date.day == 1
        assert start_date.month == now.month
        assert start_date.year == now.year
        assert end_date.month == now.month
        assert end_date.year == now.year
    
    def test_parse_date_range_last_month(self, mcp_server):
        """Test date range parsing for last month"""
        start_date, end_date = mcp_server._parse_date_range("last_month")
        
        now = datetime.now()
        expected_month = now.month - 1 if now.month > 1 else 12
        expected_year = now.year if now.month > 1 else now.year - 1
        
        assert start_date.day == 1
        assert start_date.month == expected_month
        assert start_date.year == expected_year
        assert end_date.month == expected_month
        assert end_date.year == expected_year
    
    def test_get_stage_probability(self, mcp_server):
        """Test stage probability calculation"""
        assert mcp_server._get_stage_probability("closedwon") == 1.0
        assert mcp_server._get_stage_probability("closedlost") == 0.0
        assert mcp_server._get_stage_probability("contractsent") == 0.8
        assert mcp_server._get_stage_probability("unknown_stage") == 0.3
    
    @pytest.mark.asyncio
    async def test_fetch_deals_success(self, mcp_server, sample_deal_data):
        """Test successful deal fetching"""
        # Mock API response
        mock_result = Mock()
        mock_result.properties = sample_deal_data
        
        mock_response = Mock()
        mock_response.results = [mock_result]
        mock_response.paging = None
        
        mcp_server.api_client.crm.deals.search_api.do_search.return_value = mock_response
        
        deals = await mcp_server._fetch_deals_by_criteria(deal_stage="closedwon")
        
        assert len(deals) == 1
        assert deals[0].deal_name == "Test Deal"
        assert deals[0].amount == 50000.0
    
    @pytest.mark.asyncio
    async def test_fetch_deals_api_exception(self, mcp_server):
        """Test deal fetching with API exception"""
        from hubspot.crm.deals import ApiException
        
        mcp_server.api_client.crm.deals.search_api.do_search.side_effect = ApiException("API Error")
        
        deals = await mcp_server._fetch_deals_by_criteria(deal_stage="closedwon")
        
        assert len(deals) == 0
    
class TestHubSpotIntegration:
    """Integration tests for HubSpot API"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_hubspot_connection(self):
        """Test connection to real HubSpot API (requires valid token)"""
        
        # Skip if no real token available
        token = HubSpotConfig().get_access_token()
        if not token or token == 'test-token':
            pytest.skip("No valid HubSpot access token for integration test")
        
        server = HubSpotMCPServer(token)
        
        # Test basic API connectivity
        try:
            # This will make a real API call
            deals = await server._fetch_deals_by_criteria(
                deal_stage="closedwon",
                start_date=datetime.now() - timedelta(days=90)
            )
            
            # Should return a list (even if empty)
            assert isinstance(deals, list)
            
            # If deals exist, validate structure
            if deals:
                assert isinstance(deals[0], HubSpotDeal)
                assert hasattr(deals[0], 'deal_id')
                assert hasattr(deals[0], 'amount')
                
        except Exception as e:
            pytest.fail(f"Real HubSpot API integration failed: {e}")

class TestRevenueCalculations:
    """Test revenue calculation logic"""
    
    def test_revenue_report_creation(self):
        """Test revenue report model creation"""
        deals = [
            HubSpotDeal(
                deal_id="1",
                deal_name="Deal 1",
                amount=10000,
                deal_stage="closedwon",
                created_date="2024-01-01"
            ),
            HubSpotDeal(
                deal_id="2", 
                deal_name="Deal 2",
                amount=20000,
                deal_stage="closedwon",
                created_date="2024-01-02"
            )
        ]
        
        report = RevenueReport(
            period="current_month",
            total_revenue=30000,
            deal_count=2,
            average_deal_size=15000,
            pipeline_value=50000,
            closed_deals=deals
        )
        
        assert report.total_revenue == 30000
        assert report.deal_count == 2
        assert report.average_deal_size == 15000
        assert len(report.closed_deals) == 2

def run_tests():
    """Run all tests"""
    import subprocess
    
    # Run unit tests
    result = subprocess.run([
        "python", "-m", "pytest", 
        "test_hubspot_mcp.py", 
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
    # Install pytest if not available
    try:
        import pytest
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "pytest", "pytest-asyncio"])
    
    run_tests()
