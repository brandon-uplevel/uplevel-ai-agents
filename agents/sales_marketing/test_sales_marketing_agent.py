"""
Test suite for Sales & Marketing Intelligence Agent

Tests all service integrations, database operations, and agent functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

# FastAPI testing
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import our agent and models
from sales_marketing_agent import (
    app, agent, SalesQuery, SalesResponse, LeadCreate, CampaignCreate,
    ContractRequest, PaymentRequest, Lead, Campaign, Contract, Payment,
    Base, SessionLocal
)
from config import config

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test tables
Base.metadata.create_all(bind=engine)

# Test client
client = TestClient(app)

class TestSalesMarketingAgent:
    """Test the main agent functionality"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        # Create test database session
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        
        # Create test data
        self.test_lead = Lead(
            email="test@example.com",
            first_name="John",
            last_name="Doe", 
            company="Test Corp",
            title="CEO",
            phone="555-1234",
            source="linkedin",
            status="new",
            score=75.0
        )
        self.db.add(self.test_lead)
        self.db.commit()
        self.db.refresh(self.test_lead)
    
    def teardown_method(self):
        """Clean up after each test"""
        self.db.close()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    
    @pytest.mark.asyncio
    async def test_process_lead_query(self):
        """Test lead management query processing"""
        query = SalesQuery(
            query="Show me my lead statistics",
            agent_type="lead_management"
        )
        
        response = await agent.process_query(query)
        
        assert isinstance(response, SalesResponse)
        assert "Lead Management Summary" in response.answer
        assert "total_leads" in response.analysis
        assert len(response.recommendations) > 0
        assert len(response.next_actions) > 0
    
    @pytest.mark.asyncio
    async def test_process_campaign_query(self):
        """Test campaign management query processing"""
        # Add test campaign
        test_campaign = Campaign(
            name="Test Campaign",
            type="email",
            subject_line="Test Subject",
            message_template="Hello {{first_name}}",
            status="active",
            sent_count=100,
            opened_count=25
        )
        self.db.add(test_campaign)
        self.db.commit()
        
        query = SalesQuery(
            query="Show me campaign performance",
            agent_type="campaign_management"
        )
        
        response = await agent.process_query(query)
        
        assert isinstance(response, SalesResponse)
        assert "Marketing Campaign Overview" in response.answer
        assert "total_campaigns" in response.analysis
        assert response.analysis["total_campaigns"] >= 1
    
    @pytest.mark.asyncio
    async def test_process_contract_query(self):
        """Test contract management query processing"""
        # Add test contract
        test_contract = Contract(
            lead_id=self.test_lead.id,
            docusign_envelope_id="test_envelope_123",
            contract_type="service_agreement",
            status="signed",
            amount=5000.00
        )
        self.db.add(test_contract)
        self.db.commit()
        
        query = SalesQuery(
            query="Show me contract status",
            agent_type="contract_management"
        )
        
        response = await agent.process_query(query)
        
        assert isinstance(response, SalesResponse)
        assert "Contract Management Summary" in response.answer
        assert "total_contracts" in response.analysis
        assert response.analysis["total_contracts"] >= 1
    
    @pytest.mark.asyncio 
    async def test_process_payment_query(self):
        """Test payment processing query processing"""
        # Add test payment
        test_payment = Payment(
            lead_id=self.test_lead.id,
            stripe_payment_id="test_payment_123",
            amount=5000.00,
            status="succeeded"
        )
        self.db.add(test_payment)
        self.db.commit()
        
        query = SalesQuery(
            query="Show me payment statistics",
            agent_type="payment_processing"
        )
        
        response = await agent.process_query(query)
        
        assert isinstance(response, SalesResponse)
        assert "Payment Processing Summary" in response.answer
        assert "total_payments" in response.analysis
        assert response.analysis["total_revenue"] >= 5000.00
    
    @pytest.mark.asyncio
    async def test_process_analytics_query(self):
        """Test analytics and reporting query processing"""
        query = SalesQuery(
            query="Show me full analytics dashboard",
            agent_type="analytics"
        )
        
        response = await agent.process_query(query)
        
        assert isinstance(response, SalesResponse)
        assert "Analytics Dashboard" in response.answer
        assert "overview" in response.analysis
        assert "funnel" in response.analysis
        assert "revenue" in response.analysis
    
    @pytest.mark.asyncio
    async def test_process_general_query(self):
        """Test general query processing"""
        query = SalesQuery(
            query="What can you help me with?",
            agent_type="general"
        )
        
        response = await agent.process_query(query)
        
        assert isinstance(response, SalesResponse)
        assert "Sales & Marketing Intelligence Agent" in response.answer
        assert "capabilities" in response.analysis
        assert len(response.recommendations) > 0

class TestLinkedInService:
    """Test LinkedIn integration"""
    
    def setup_method(self):
        self.linkedin_service = agent.linkedin
    
    @patch('linkedin_api.Linkedin')
    def test_authenticate_user(self, mock_linkedin):
        """Test LinkedIn user authentication"""
        mock_linkedin.return_value = MagicMock()
        
        # Test successful authentication
        result = asyncio.run(self.linkedin_service.authenticate_user("test_user", "test_pass"))
        assert result is True
        
        # Test failed authentication
        mock_linkedin.side_effect = Exception("Authentication failed")
        result = asyncio.run(self.linkedin_service.authenticate_user("bad_user", "bad_pass"))
        assert result is False
    
    @patch('linkedin_api.Linkedin')
    @pytest.mark.asyncio
    async def test_search_prospects(self, mock_linkedin):
        """Test LinkedIn prospect searching"""
        # Mock LinkedIn API response
        mock_api = MagicMock()
        mock_api.search_people.return_value = [
            {
                'firstName': 'Jane',
                'lastName': 'Smith',
                'occupation': 'CEO',
                'companyName': 'Tech Corp',
                'locationName': 'San Francisco',
                'publicIdentifier': 'janesmith',
                'distance': 'DISTANCE_1'
            }
        ]
        
        self.linkedin_service.api = mock_api
        
        prospects = await self.linkedin_service.search_prospects(['CEO'], 'San Francisco')
        
        assert len(prospects) > 0
        assert prospects[0]['name'] == 'Jane Smith'
        assert prospects[0]['title'] == 'CEO'
        assert prospects[0]['score'] > 0
    
    def test_calculate_lead_score(self):
        """Test lead scoring algorithm"""
        # Test high-value prospect (CEO, first connection)
        person = {
            'occupation': 'CEO',
            'companyName': 'Big Corp',
            'distance': 'DISTANCE_1'
        }
        score = self.linkedin_service._calculate_lead_score(person)
        assert score >= 65  # 30 (CEO) + 25 (first connection) + 10 (base)
        
        # Test medium-value prospect
        person = {
            'occupation': 'Manager',
            'companyName': 'Small Corp', 
            'distance': 'DISTANCE_2'
        }
        score = self.linkedin_service._calculate_lead_score(person)
        assert score >= 45  # 20 (manager) + 15 (second connection) + 10 (base)

class TestSendGridService:
    """Test SendGrid email marketing integration"""
    
    def setup_method(self):
        self.sendgrid_service = agent.sendgrid
    
    @patch('sendgrid.SendGridAPIClient')
    @pytest.mark.asyncio
    async def test_send_email(self, mock_sendgrid):
        """Test individual email sending"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sendgrid.return_value.send.return_value = mock_response
        
        result = await self.sendgrid_service.send_email(
            to_email="test@example.com",
            subject="Test Subject",
            content="<h1>Test Content</h1>"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_bulk_campaign(self):
        """Test bulk email campaign sending"""
        # Create test campaign and leads
        campaign = Campaign(
            name="Test Campaign",
            subject_line="Test Subject", 
            message_template="Hello {{first_name}} from {{company}}"
        )
        
        leads = [
            Lead(
                email="test1@example.com",
                first_name="John",
                last_name="Doe",
                company="Test Corp"
            ),
            Lead(
                email="test2@example.com", 
                first_name="Jane",
                last_name="Smith",
                company="Another Corp"
            )
        ]
        
        with patch.object(self.sendgrid_service, 'send_email', return_value=True):
            results = await self.sendgrid_service.send_bulk_campaign(campaign, leads)
            
            assert results["sent"] == 2
            assert results["failed"] == 0
    
    def test_personalize_content(self):
        """Test email content personalization"""
        template = "Hello {{first_name}} {{last_name}} from {{company}}"
        lead = Lead(
            first_name="John",
            last_name="Doe", 
            company="Test Corp"
        )
        
        personalized = self.sendgrid_service._personalize_content(template, lead)
        
        assert personalized == "Hello John Doe from Test Corp"

class TestDocuSignService:
    """Test DocuSign e-signature integration"""
    
    def setup_method(self):
        self.docusign_service = agent.docusign
    
    @patch('docusign_esign.ApiClient')
    @pytest.mark.asyncio
    async def test_authenticate(self, mock_api_client):
        """Test DocuSign authentication"""
        # Mock successful authentication
        mock_client = MagicMock()
        mock_accounts_api = MagicMock()
        mock_account_info = MagicMock()
        mock_account_info.accounts = [MagicMock(account_id="test_account_123")]
        
        mock_accounts_api.list_accounts.return_value = mock_account_info
        mock_client.accounts_api.return_value = mock_accounts_api
        
        with patch.object(self.docusign_service, 'api_client', mock_client):
            result = await self.docusign_service.authenticate("test_user", "test_token")
            assert result is True
            assert self.docusign_service.account_id == "test_account_123"
    
    def test_generate_contract_pdf(self):
        """Test contract PDF generation"""
        contract_request = ContractRequest(
            lead_id=1,
            contract_type="service_agreement",
            amount=5000.00
        )
        
        lead = Lead(
            first_name="John",
            last_name="Doe",
            company="Test Corp"
        )
        
        pdf_base64 = self.docusign_service._generate_contract_pdf(contract_request, lead)
        
        assert pdf_base64 is not None
        assert len(pdf_base64) > 0

class TestStripeService:
    """Test Stripe payment processing integration"""
    
    def setup_method(self):
        self.stripe_service = agent.stripe
    
    @patch('stripe.Customer.create')
    @pytest.mark.asyncio
    async def test_create_customer(self, mock_create):
        """Test Stripe customer creation"""
        # Mock Stripe customer creation
        mock_customer = MagicMock()
        mock_customer.id = "cus_test123"
        mock_create.return_value = mock_customer
        
        lead = Lead(
            email="test@example.com",
            first_name="John", 
            last_name="Doe",
            company="Test Corp"
        )
        
        customer_id = await self.stripe_service.create_customer(lead)
        
        assert customer_id == "cus_test123"
        mock_create.assert_called_once()
    
    @patch('stripe.PaymentIntent.create')
    @patch('stripe.Customer.create')
    @pytest.mark.asyncio
    async def test_process_payment(self, mock_customer, mock_payment):
        """Test payment processing"""
        # Mock Stripe responses
        mock_customer.return_value = MagicMock(id="cus_test123")
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = "pi_test123"
        mock_payment_intent.status = "succeeded"
        mock_payment_intent.amount = 500000  # $5000 in cents
        mock_payment_intent.currency = "usd"
        mock_payment.return_value = mock_payment_intent
        
        payment_request = PaymentRequest(
            lead_id=1,
            amount=5000.00,
            payment_method_id="pm_test123"
        )
        
        lead = Lead(
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        result = await self.stripe_service.process_payment(payment_request, lead)
        
        assert result["payment_id"] == "pi_test123"
        assert result["status"] == "succeeded"
        assert result["amount"] == 5000.00
        assert result["currency"] == "USD"

class TestAPIEndpoints:
    """Test FastAPI endpoints"""
    
    def setup_method(self):
        """Set up test database for API tests"""
        Base.metadata.create_all(bind=engine)
    
    def teardown_method(self):
        """Clean up test database"""
        Base.metadata.drop_all(bind=engine)
    
    def test_health_check(self):
        """Test root health check endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "Sales & Marketing Intelligence Agent" in data["service"]
    
    def test_query_endpoint(self):
        """Test query processing endpoint"""
        query_data = {
            "query": "Show me lead statistics",
            "agent_type": "lead_management"
        }
        
        response = client.post("/query", json=query_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "answer" in data
        assert "analysis" in data
        assert "recommendations" in data
    
    def test_create_lead_endpoint(self):
        """Test lead creation endpoint"""
        lead_data = {
            "email": "newlead@example.com",
            "first_name": "Alice",
            "last_name": "Johnson",
            "company": "New Corp",
            "title": "CTO",
            "source": "website"
        }
        
        response = client.post("/leads", json=lead_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "lead_id" in data
    
    def test_create_campaign_endpoint(self):
        """Test campaign creation endpoint"""
        campaign_data = {
            "name": "Test Campaign",
            "type": "email",
            "subject_line": "Test Subject",
            "message_template": "Hello {{first_name}}"
        }
        
        response = client.post("/campaigns", json=campaign_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "campaign_id" in data
    
    def test_create_contract_endpoint(self):
        """Test contract creation endpoint"""
        # First create a lead
        lead_data = {
            "email": "contract@example.com",
            "first_name": "Bob",
            "last_name": "Wilson",
            "company": "Contract Corp"
        }
        lead_response = client.post("/leads", json=lead_data)
        lead_id = lead_response.json()["lead_id"]
        
        # Then create contract
        contract_data = {
            "lead_id": lead_id,
            "contract_type": "service_agreement",
            "amount": 7500.00
        }
        
        response = client.post("/contracts", json=contract_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "contract_id" in data
        assert "envelope_id" in data
    
    def test_process_payment_endpoint(self):
        """Test payment processing endpoint"""
        # First create a lead
        lead_data = {
            "email": "payment@example.com", 
            "first_name": "Carol",
            "last_name": "Davis",
            "company": "Payment Corp"
        }
        lead_response = client.post("/leads", json=lead_data)
        lead_id = lead_response.json()["lead_id"]
        
        # Then process payment
        payment_data = {
            "lead_id": lead_id,
            "amount": 2500.00,
            "payment_method_id": "pm_test123"
        }
        
        response = client.post("/payments", json=payment_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "payment_id" in data
        assert "stripe_payment_id" in data

class TestDatabaseModels:
    """Test database models and relationships"""
    
    def setup_method(self):
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
    
    def teardown_method(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)
    
    def test_lead_model(self):
        """Test Lead model creation and queries"""
        lead = Lead(
            email="model@example.com",
            first_name="Model",
            last_name="Test",
            company="Model Corp",
            score=85.5,
            custom_fields={"industry": "tech", "size": "medium"}
        )
        
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        
        assert lead.id is not None
        assert lead.email == "model@example.com"
        assert lead.score == 85.5
        assert lead.custom_fields["industry"] == "tech"
        assert lead.created_at is not None
    
    def test_campaign_model(self):
        """Test Campaign model creation and queries"""
        campaign = Campaign(
            name="Test Model Campaign",
            type="email",
            status="active",
            subject_line="Model Test",
            message_template="Hello {{first_name}}",
            sent_count=150,
            opened_count=45
        )
        
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        
        assert campaign.id is not None
        assert campaign.name == "Test Model Campaign"
        assert campaign.sent_count == 150
        assert campaign.opened_count == 45
    
    def test_contract_model(self):
        """Test Contract model creation and queries"""
        # Create lead first
        lead = Lead(email="contract@example.com", first_name="Contract", last_name="Test")
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        
        # Create contract
        contract = Contract(
            lead_id=lead.id,
            docusign_envelope_id="env_test123",
            contract_type="service_agreement",
            status="signed",
            amount=10000.00,
            currency="USD"
        )
        
        self.db.add(contract)
        self.db.commit()
        self.db.refresh(contract)
        
        assert contract.id is not None
        assert contract.lead_id == lead.id
        assert contract.amount == 10000.00
        assert contract.status == "signed"
    
    def test_payment_model(self):
        """Test Payment model creation and queries"""
        # Create lead first
        lead = Lead(email="payment@example.com", first_name="Payment", last_name="Test")
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        
        # Create payment
        payment = Payment(
            lead_id=lead.id,
            stripe_payment_id="pi_test123",
            amount=5000.00,
            currency="USD",
            status="succeeded",
            metadata={"source": "website", "campaign": "spring2024"}
        )
        
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        
        assert payment.id is not None
        assert payment.lead_id == lead.id
        assert payment.amount == 5000.00
        assert payment.status == "succeeded"
        assert payment.payment_metadata["source"] == "website"

class TestIntegrationScenarios:
    """Test complete integration scenarios"""
    
    def setup_method(self):
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
    
    def teardown_method(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)
    
    def test_complete_sales_funnel(self):
        """Test complete sales funnel from lead to payment"""
        # 1. Create lead
        lead_data = {
            "email": "funnel@example.com",
            "first_name": "Funnel",
            "last_name": "Test",
            "company": "Funnel Corp",
            "title": "CEO",
            "source": "linkedin"
        }
        
        lead_response = client.post("/leads", json=lead_data)
        assert lead_response.status_code == 200
        lead_id = lead_response.json()["lead_id"]
        
        # 2. Create marketing campaign
        campaign_data = {
            "name": "Funnel Test Campaign",
            "type": "email",
            "subject_line": "Special Offer for {{company}}",
            "message_template": "Hello {{first_name}}, we have a special offer for {{company}}!"
        }
        
        campaign_response = client.post("/campaigns", json=campaign_data)
        assert campaign_response.status_code == 200
        
        # 3. Send contract
        contract_data = {
            "lead_id": lead_id,
            "contract_type": "service_agreement", 
            "amount": 15000.00
        }
        
        contract_response = client.post("/contracts", json=contract_data)
        assert contract_response.status_code == 200
        
        # 4. Process payment
        payment_data = {
            "lead_id": lead_id,
            "amount": 15000.00,
            "payment_method_id": "pm_funnel_test"
        }
        
        payment_response = client.post("/payments", json=payment_data)
        assert payment_response.status_code == 200
        
        # 5. Query analytics to verify funnel
        query_data = {
            "query": "Show me analytics dashboard",
            "agent_type": "analytics"
        }
        
        analytics_response = client.post("/query", json=query_data)
        assert analytics_response.status_code == 200
        
        analytics_data = analytics_response.json()
        assert analytics_data["analysis"]["overview"]["total_leads"] >= 1
        assert analytics_data["analysis"]["revenue"]["total"] >= 15000.00

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
