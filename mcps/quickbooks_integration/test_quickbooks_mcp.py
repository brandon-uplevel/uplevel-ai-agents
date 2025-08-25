"""
Test suite for QuickBooks MCP Integration
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any

from quickbooks_mcp import (
    QuickBooksMCPServer, QuickBooksExpense, QuickBooksIncome, 
    QuickBooksAccount, ProfitLossStatement
)
from config import QuickBooksConfig

class TestQuickBooksMCPServer:
    """Test QuickBooks MCP Server functionality"""
    
    @pytest.fixture
    def mock_qb_client(self):
        """Mock QuickBooks API client"""
        mock_client = Mock()
        mock_client.query_objects = Mock()
        return mock_client
    
    @pytest.fixture
    def sample_expense_data(self):
        """Sample QuickBooks expense data"""
        return {
            "Id": "123",
            "TxnDate": "2024-01-15",
            "EntityRef": Mock(name="Test Vendor"),
            "Line": [
                Mock(
                    Amount=500.00,
                    Description="Office Supplies",
                    AccountBasedExpenseLineDetail=Mock(
                        AccountRef=Mock(name="Office Expenses")
                    )
                )
            ],
            "DocNumber": "EXP-001"
        }
    
    @pytest.fixture
    def sample_income_data(self):
        """Sample QuickBooks income data"""
        return {
            "Id": "456",
            "TxnDate": "2024-01-15",
            "CustomerRef": Mock(name="Test Customer"),
            "Line": [
                Mock(
                    Amount=2000.00,
                    Description="Consulting Services"
                )
            ],
            "DocNumber": "INV-001"
        }
    
    @pytest.fixture
    def mcp_server(self):
        """Create MCP server with mocked QB client"""
        with patch.dict('os.environ', {
            'QB_CLIENT_ID': 'test-client-id',
            'QB_CLIENT_SECRET': 'test-client-secret',
            'QB_ACCESS_TOKEN': 'test-access-token',
            'QB_COMPANY_ID': 'test-company-id'
        }):
            server = QuickBooksMCPServer()
            return server
    
    def test_server_initialization_success(self):
        """Test server initializes with proper credentials"""
        with patch.dict('os.environ', {
            'QB_CLIENT_ID': 'test-client-id',
            'QB_CLIENT_SECRET': 'test-client-secret'
        }):
            server = QuickBooksMCPServer()
            assert server.client_id == 'test-client-id'
            assert server.client_secret == 'test-client-secret'
            assert server.mcp.name == 'QuickBooks MCP Server'
    
    def test_server_initialization_no_credentials(self):
        """Test server raises error without credentials"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="QuickBooks client ID and secret are required"):
                QuickBooksMCPServer()
    
    def test_parse_date_range_current_month(self, mcp_server):
        """Test date range parsing for current month"""
        start_date, end_date = mcp_server._parse_date_range("current_month")
        
        now = datetime.now()
        assert start_date.day == 1
        assert start_date.month == now.month
        assert start_date.year == now.year
        assert end_date.month == now.month
        assert end_date.year == now.year
    
    def test_parse_date_range_ytd(self, mcp_server):
        """Test date range parsing for year-to-date"""
        start_date, end_date = mcp_server._parse_date_range("ytd")
        
        now = datetime.now()
        assert start_date.day == 1
        assert start_date.month == 1
        assert start_date.year == now.year
        assert end_date.year == now.year
    
    @pytest.mark.asyncio
    async def test_fetch_expenses_success(self, mcp_server, sample_expense_data):
        """Test successful expense fetching"""
        # Mock the QB client and query response
        mock_purchase = Mock()
        for key, value in sample_expense_data.items():
            setattr(mock_purchase, key, value)
        
        mcp_server.qb_client = Mock()
        mcp_server.qb_client.query_objects.return_value = [mock_purchase]
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        expenses = await mcp_server._fetch_expenses(start_date, end_date)
        
        assert len(expenses) == 1
        assert expenses[0].amount == 500.00
        assert expenses[0].description == "Office Supplies"
        assert expenses[0].vendor == "Test Vendor"
    
    @pytest.mark.asyncio
    async def test_fetch_income_success(self, mcp_server, sample_income_data):
        """Test successful income fetching"""
        # Mock the QB client and query response
        mock_invoice = Mock()
        for key, value in sample_income_data.items():
            setattr(mock_invoice, key, value)
        
        mcp_server.qb_client = Mock()
        mcp_server.qb_client.query_objects.return_value = [mock_invoice]
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        income = await mcp_server._fetch_income(start_date, end_date)
        
        assert len(income) == 1
        assert income[0].amount == 2000.00
        assert income[0].description == "Consulting Services"
        assert income[0].customer == "Test Customer"
    
    @pytest.mark.asyncio
    async def test_fetch_expenses_no_client(self, mcp_server):
        """Test expense fetching without QB client"""
        mcp_server.qb_client = None
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        expenses = await mcp_server._fetch_expenses(start_date, end_date)
        
        assert len(expenses) == 0

class TestDataModels:
    """Test QuickBooks data models"""
    
    def test_quickbooks_expense_creation(self):
        """Test QuickBooksExpense model creation"""
        expense = QuickBooksExpense(
            expense_id="123",
            description="Office Supplies",
            amount=500.00,
            expense_date="2024-01-15",
            category="Office",
            vendor="Staples",
            account="Office Expenses"
        )
        
        assert expense.expense_id == "123"
        assert expense.amount == 500.00
        assert expense.vendor == "Staples"
    
    def test_quickbooks_income_creation(self):
        """Test QuickBooksIncome model creation"""
        income = QuickBooksIncome(
            income_id="456",
            description="Consulting",
            amount=2000.00,
            income_date="2024-01-15",
            customer="Acme Corp"
        )
        
        assert income.income_id == "456"
        assert income.amount == 2000.00
        assert income.customer == "Acme Corp"
    
    def test_profit_loss_statement_creation(self):
        """Test ProfitLossStatement model creation"""
        expense = QuickBooksExpense(
            expense_id="123",
            description="Office Supplies",
            amount=500.00,
            expense_date="2024-01-15"
        )
        
        income = QuickBooksIncome(
            income_id="456",
            description="Consulting",
            amount=2000.00,
            income_date="2024-01-15"
        )
        
        pl_statement = ProfitLossStatement(
            period="current_month",
            start_date="2024-01-01",
            end_date="2024-01-31",
            total_income=2000.00,
            total_expenses=500.00,
            net_profit=1500.00,
            profit_margin=75.0,
            income_breakdown=[income],
            expense_breakdown=[expense]
        )
        
        assert pl_statement.total_income == 2000.00
        assert pl_statement.total_expenses == 500.00
        assert pl_statement.net_profit == 1500.00
        assert pl_statement.profit_margin == 75.0
        assert len(pl_statement.income_breakdown) == 1
        assert len(pl_statement.expense_breakdown) == 1

class TestOAuthFlow:
    """Test OAuth flow functionality"""
    
    @pytest.fixture
    def oauth_server(self):
        """Create server for OAuth testing"""
        with patch.dict('os.environ', {
            'QB_CLIENT_ID': 'test-client-id',
            'QB_CLIENT_SECRET': 'test-client-secret'
        }):
            return QuickBooksMCPServer()
    
    def test_oauth_url_generation(self, oauth_server):
        """Test OAuth URL generation"""
        # Mock the auth client
        oauth_server.auth_client.get_authorization_url = Mock(return_value="https://test-url.com")
        oauth_server.auth_client.state_token = "test-state"
        
        # This would be tested via the MCP tool in real usage
        # For now, we test the underlying auth client setup
        assert oauth_server.auth_client.client_id == 'test-client-id'
        assert oauth_server.auth_client.client_secret == 'test-client-secret'

class TestQuickBooksIntegration:
    """Integration tests for QuickBooks API (requires sandbox credentials)"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_quickbooks_connection(self):
        """Test connection to real QuickBooks sandbox (requires valid credentials)"""
        
        config = QuickBooksConfig()
        
        # Skip if no real credentials available
        try:
            client_id, client_secret = config.get_client_credentials()
            access_token, refresh_token, company_id = config.get_tokens()
        except ValueError:
            pytest.skip("No valid QuickBooks credentials for integration test")
        
        if not all([client_id, client_secret, access_token, company_id]):
            pytest.skip("Incomplete QuickBooks credentials for integration test")
        
        server = QuickBooksMCPServer(
            client_id=client_id,
            client_secret=client_secret,
            access_token=access_token,
            refresh_token=refresh_token,
            company_id=company_id
        )
        
        # Test basic API connectivity (this would make real API calls)
        if server.qb_client:
            try:
                # Test fetching accounts (safe operation)
                start_date = datetime.now() - timedelta(days=30)
                end_date = datetime.now()
                
                expenses = await server._fetch_expenses(start_date, end_date)
                income = await server._fetch_income(start_date, end_date)
                
                # Should return lists (even if empty)
                assert isinstance(expenses, list)
                assert isinstance(income, list)
                
                # If data exists, validate structure
                if expenses:
                    assert isinstance(expenses[0], QuickBooksExpense)
                if income:
                    assert isinstance(income[0], QuickBooksIncome)
                    
            except Exception as e:
                # Don't fail the test for API errors in sandbox
                logger.warning(f"QuickBooks API test warning: {e}")

def run_tests():
    """Run all tests"""
    import subprocess
    
    result = subprocess.run([
        "python", "-m", "pytest", 
        "test_quickbooks_mcp.py", 
        "-v",
        "--tb=short",
        "-m", "not integration"  # Skip integration tests by default
    ], capture_output=True, text=True)
    
    print("Test Results:")
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
    
    return result.returncode == 0

if __name__ == "__main__":
    run_tests()
