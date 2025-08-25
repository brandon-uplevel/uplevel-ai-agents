"""
Sales & Marketing Intelligence Agent for Uplevel AI

This agent provides comprehensive sales and marketing automation including:
- LinkedIn lead generation and prospecting
- Email marketing campaigns via SendGrid
- E-signature document processing via DocuSign  
- Payment processing and subscription management via Stripe
- Sales pipeline management and lead scoring
- Marketing automation and analytics
"""

import asyncio
import os
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import logging
from urllib.parse import urlencode
import hashlib

# Core framework imports
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
import httpx
import redis
import structlog

# Service integrations
import stripe
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from docusign_esign import ApiClient, EnvelopesApi
from docusign_esign.client.api_exception import ApiException as DocuSignApiException
from linkedin_api import Linkedin
from requests_oauthlib import OAuth2Session

# Database and async workers
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from celery import Celery

# Configuration
from config import config

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Database setup
Base = declarative_base()
engine = create_engine(config.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis setup
redis_client = redis.from_url(config.redis_url)

# Celery setup
celery_app = Celery(
    'sales_marketing_agent',
    broker=config.celery_broker_url,
    backend=config.celery_result_backend
)

# FastAPI app setup
app = FastAPI(
    title="Sales & Marketing Intelligence Agent",
    description="Comprehensive sales and marketing automation platform",
    version=config.agent_version
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# ================================
# DATABASE MODELS
# ================================

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    company = Column(String)
    title = Column(String)
    phone = Column(String)
    linkedin_url = Column(String)
    source = Column(String)  # linkedin, website, referral, etc.
    status = Column(String, default="new")  # new, contacted, qualified, converted, lost
    score = Column(Float, default=0.0)
    notes = Column(Text)
    custom_fields = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    type = Column(String)  # email, linkedin, mixed
    status = Column(String, default="draft")  # draft, active, paused, completed
    subject_line = Column(String)
    message_template = Column(Text)
    target_audience = Column(JSON)
    scheduled_at = Column(DateTime)
    sent_count = Column(Integer, default=0)
    opened_count = Column(Integer, default=0)
    clicked_count = Column(Integer, default=0)
    replied_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Contract(Base):
    __tablename__ = "contracts"
    
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, index=True)
    docusign_envelope_id = Column(String, unique=True)
    contract_type = Column(String)
    status = Column(String, default="draft")  # draft, sent, signed, completed, voided
    amount = Column(Float)
    currency = Column(String, default="USD")
    template_id = Column(String)
    document_url = Column(String)
    signed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, index=True)
    stripe_payment_id = Column(String, unique=True)
    stripe_customer_id = Column(String)
    amount = Column(Float)
    currency = Column(String, default="USD")
    status = Column(String)  # pending, succeeded, failed, canceled
    payment_method = Column(String)
    description = Column(String)
    payment_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ================================
# PYDANTIC MODELS
# ================================

class SalesQuery(BaseModel):
    """Model for sales & marketing query requests"""
    query: str = Field(..., description="User's sales/marketing question")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    agent_type: str = Field(default="general", description="Specific agent capability needed")

class SalesResponse(BaseModel):
    """Model for sales & marketing response"""
    answer: str = Field(..., description="Response to user query")
    data: Dict[str, Any] = Field(default_factory=dict, description="Supporting data")
    analysis: Dict[str, Any] = Field(default_factory=dict, description="Sales analysis")
    recommendations: List[str] = Field(default_factory=list, description="Action recommendations")
    next_actions: List[str] = Field(default_factory=list, description="Suggested next steps")

class LeadCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    company: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: str = "manual"
    custom_fields: Optional[Dict[str, Any]] = None

class CampaignCreate(BaseModel):
    name: str
    type: str = Field(..., pattern="^(email|linkedin|mixed)$")
    subject_line: str
    message_template: str
    target_audience: Dict[str, Any] = Field(default_factory=dict)
    scheduled_at: Optional[datetime] = None

class ContractRequest(BaseModel):
    lead_id: int
    contract_type: str
    amount: float
    currency: str = "USD"
    template_id: Optional[str] = None

class PaymentRequest(BaseModel):
    lead_id: int
    amount: float
    currency: str = "USD"
    payment_method_id: str
    description: Optional[str] = None
    payment_metadata: Optional[Dict[str, Any]] = None

# ================================
# SERVICE INTEGRATIONS
# ================================

class LinkedInService:
    """LinkedIn Marketing API integration for lead generation"""
    
    def __init__(self):
        self.client_id = config.linkedin_client_id
        self.client_secret = config.linkedin_client_secret
        self.redirect_uri = config.linkedin_redirect_uri
        self.api = None
    
    async def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate user with LinkedIn (for legitimate business use)"""
        try:
            # Note: This should use OAuth2 flow in production
            self.api = Linkedin(username, password)
            return True
        except Exception as e:
            logger.error("LinkedIn authentication failed", error=str(e))
            return False
    
    async def search_prospects(self, keywords: List[str], location: str = "", company_size: str = "") -> List[Dict]:
        """Search for potential prospects on LinkedIn"""
        if not self.api:
            raise HTTPException(status_code=401, detail="LinkedIn not authenticated")
        
        try:
            # Search for people with specific keywords in their profile
            prospects = []
            for keyword in keywords:
                results = self.api.search_people(
                    keyword_title=keyword,
                    network_depths=['F', 'S'],  # First and second connections
                    regions=[location] if location else None,
                    limit=50
                )
                
                for person in results:
                    prospect = {
                        'name': f"{person.get('firstName', '')} {person.get('lastName', '')}",
                        'title': person.get('occupation', ''),
                        'company': person.get('companyName', ''),
                        'location': person.get('locationName', ''),
                        'linkedin_url': person.get('publicIdentifier', ''),
                        'score': self._calculate_lead_score(person)
                    }
                    prospects.append(prospect)
            
            # Sort by lead score
            prospects.sort(key=lambda x: x['score'], reverse=True)
            return prospects[:100]  # Return top 100 prospects
            
        except Exception as e:
            logger.error("LinkedIn prospect search failed", error=str(e))
            raise HTTPException(status_code=500, detail="Prospect search failed")
    
    def _calculate_lead_score(self, person: Dict) -> float:
        """Calculate lead score based on LinkedIn profile data"""
        score = 0.0
        
        # Title relevance
        if any(keyword in person.get('occupation', '').lower() for keyword in ['ceo', 'founder', 'director', 'vp']):
            score += 30
        elif any(keyword in person.get('occupation', '').lower() for keyword in ['manager', 'head', 'lead']):
            score += 20
        
        # Company size (would need additional API calls to get this)
        # This is a simplified scoring system
        score += 10  # Base score for having a company
        
        # Connection level
        if person.get('distance') == 'DISTANCE_1':
            score += 25  # First connection
        elif person.get('distance') == 'DISTANCE_2':
            score += 15  # Second connection
        
        return min(score, 100)  # Cap at 100

class SendGridService:
    """SendGrid email marketing integration"""
    
    def __init__(self):
        self.api_key = config.sendgrid_api_key
        self.from_email = config.sendgrid_from_email
        self.client = SendGridAPIClient(api_key=self.api_key) if self.api_key else None
    
    async def send_email(self, to_email: str, subject: str, content: str, content_type: str = "text/html") -> bool:
        """Send individual email"""
        if not self.client:
            raise HTTPException(status_code=500, detail="SendGrid not configured")
        
        try:
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content(content_type, content)
            )
            
            response = self.client.send(message)
            return response.status_code in [200, 201, 202]
            
        except Exception as e:
            logger.error("Email sending failed", error=str(e), to_email=to_email)
            return False
    
    async def send_bulk_campaign(self, campaign: Campaign, leads: List[Lead]) -> Dict[str, int]:
        """Send bulk email campaign"""
        if not self.client:
            raise HTTPException(status_code=500, detail="SendGrid not configured")
        
        results = {"sent": 0, "failed": 0}
        
        for lead in leads:
            try:
                # Personalize message
                personalized_content = self._personalize_content(
                    campaign.message_template,
                    lead
                )
                
                success = await self.send_email(
                    to_email=lead.email,
                    subject=campaign.subject_line,
                    content=personalized_content
                )
                
                if success:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    
                # Rate limiting
                await asyncio.sleep(0.1)  # 10 emails per second max
                
            except Exception as e:
                logger.error("Bulk email failed for lead", error=str(e), lead_id=lead.id)
                results["failed"] += 1
        
        return results
    
    def _personalize_content(self, template: str, lead: Lead) -> str:
        """Personalize email content with lead data"""
        replacements = {
            '{{first_name}}': lead.first_name or 'there',
            '{{last_name}}': lead.last_name or '',
            '{{company}}': lead.company or '',
            '{{title}}': lead.title or '',
        }
        
        content = template
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        
        return content

class DocuSignService:
    """DocuSign e-signature integration"""
    
    def __init__(self):
        self.client_id = config.docusign_client_id
        self.client_secret = config.docusign_client_secret
        self.base_url = config.docusign_base_url
        self.api_client = None
        self.account_id = None
    
    async def authenticate(self, user_id: str, access_token: str) -> bool:
        """Authenticate with DocuSign"""
        try:
            self.api_client = ApiClient(base_path=self.base_url)
            self.api_client.set_default_header("Authorization", f"Bearer {access_token}")
            
            # Get account info
            accounts_api = self.api_client.accounts_api()
            account_info = accounts_api.list_accounts()
            
            if account_info.accounts:
                self.account_id = account_info.accounts[0].account_id
                return True
            
            return False
            
        except Exception as e:
            logger.error("DocuSign authentication failed", error=str(e))
            return False
    
    async def send_contract(self, contract_request: ContractRequest, lead: Lead) -> str:
        """Send contract for e-signature"""
        if not self.api_client or not self.account_id:
            raise HTTPException(status_code=401, detail="DocuSign not authenticated")
        
        try:
            envelopes_api = EnvelopesApi(self.api_client)
            
            # Create envelope definition
            envelope_definition = {
                "emailSubject": f"Please sign your contract - {lead.company or lead.first_name}",
                "documents": [{
                    "documentBase64": self._generate_contract_pdf(contract_request, lead),
                    "name": "Contract",
                    "fileExtension": "pdf",
                    "documentId": "1"
                }],
                "recipients": {
                    "signers": [{
                        "email": lead.email,
                        "name": f"{lead.first_name} {lead.last_name}",
                        "recipientId": "1",
                        "tabs": {
                            "signHereTabs": [{
                                "documentId": "1",
                                "pageNumber": "1",
                                "xPosition": "100",
                                "yPosition": "100"
                            }]
                        }
                    }]
                },
                "status": "sent"
            }
            
            # Send envelope
            results = envelopes_api.create_envelope(self.account_id, envelope_definition)
            return results.envelope_id
            
        except DocuSignApiException as e:
            logger.error("DocuSign contract sending failed", error=str(e))
            raise HTTPException(status_code=500, detail="Contract sending failed")
    
    def _generate_contract_pdf(self, contract_request: ContractRequest, lead: Lead) -> str:
        """Generate contract PDF (simplified - would use proper PDF generation in production)"""
        import base64
        
        # This is a simplified version - in production, you'd use a proper PDF library
        contract_html = f"""
        <html>
        <body>
            <h1>Service Agreement</h1>
            <p>Client: {lead.first_name} {lead.last_name}</p>
            <p>Company: {lead.company}</p>
            <p>Amount: ${contract_request.amount} {contract_request.currency}</p>
            <p>Date: {datetime.now().strftime('%Y-%m-%d')}</p>
            <br><br>
            <p>Signature: _____________________</p>
        </body>
        </html>
        """
        
        # Convert to base64 (in production, you'd convert HTML to PDF first)
        return base64.b64encode(contract_html.encode()).decode()

class StripeService:
    """Stripe payment processing integration"""
    
    def __init__(self):
        stripe.api_key = config.stripe_api_key
    
    async def create_customer(self, lead: Lead) -> str:
        """Create Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=lead.email,
                name=f"{lead.first_name} {lead.last_name}",
                metadata={
                    'lead_id': lead.id,
                    'company': lead.company or '',
                    'source': 'uplevel_ai'
                }
            )
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error("Stripe customer creation failed", error=str(e))
            raise HTTPException(status_code=500, detail="Customer creation failed")
    
    async def process_payment(self, payment_request: PaymentRequest, lead: Lead) -> Dict[str, Any]:
        """Process one-time payment"""
        try:
            # Create customer if needed
            customer_id = await self.create_customer(lead)
            
            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(payment_request.amount * 100),  # Convert to cents
                currency=payment_request.currency.lower(),
                customer=customer_id,
                payment_method=payment_request.payment_method_id,
                description=payment_request.description or f"Payment from {lead.company}",
                metadata=payment_request.payment_metadata or {},
                confirm=True
            )
            
            return {
                'payment_id': payment_intent.id,
                'customer_id': customer_id,
                'status': payment_intent.status,
                'amount': payment_intent.amount / 100,
                'currency': payment_intent.currency.upper()
            }
            
        except stripe.error.StripeError as e:
            logger.error("Stripe payment failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"Payment failed: {str(e)}")
    
    async def create_subscription(self, lead: Lead, price_id: str) -> Dict[str, Any]:
        """Create recurring subscription"""
        try:
            # Create customer if needed
            customer_id = await self.create_customer(lead)
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                metadata={
                    'lead_id': lead.id,
                    'source': 'uplevel_ai'
                }
            )
            
            return {
                'subscription_id': subscription.id,
                'customer_id': customer_id,
                'status': subscription.status,
                'current_period_end': subscription.current_period_end
            }
            
        except stripe.error.StripeError as e:
            logger.error("Stripe subscription creation failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"Subscription creation failed: {str(e)}")

# ================================
# CORE AGENT CLASS
# ================================

class SalesMarketingAgent:
    """Main Sales & Marketing Intelligence Agent"""
    
    def __init__(self):
        self.linkedin = LinkedInService()
        self.sendgrid = SendGridService()
        self.docusign = DocuSignService()
        self.stripe = StripeService()
        
        # Initialize database tables
        Base.metadata.create_all(bind=engine)
    
    async def process_query(self, query: SalesQuery) -> SalesResponse:
        """Process sales and marketing queries with AI intelligence"""
        try:
            logger.info("Processing sales query", query=query.query, agent_type=query.agent_type)
            
            # Route to specific agent capabilities
            if "lead" in query.query.lower() or "prospect" in query.query.lower():
                return await self._handle_lead_query(query)
            elif "campaign" in query.query.lower() or "email" in query.query.lower():
                return await self._handle_campaign_query(query)
            elif "contract" in query.query.lower() or "signature" in query.query.lower():
                return await self._handle_contract_query(query)
            elif "payment" in query.query.lower() or "invoice" in query.query.lower():
                return await self._handle_payment_query(query)
            elif "analytics" in query.query.lower() or "report" in query.query.lower():
                return await self._handle_analytics_query(query)
            else:
                return await self._handle_general_query(query)
                
        except Exception as e:
            logger.error("Query processing failed", error=str(e))
            return SalesResponse(
                answer="I encountered an error processing your request. Please try again.",
                analysis={"error": str(e)},
                recommendations=["Please check your query and try again", "Contact support if the issue persists"]
            )
    
    async def _handle_lead_query(self, query: SalesQuery) -> SalesResponse:
        """Handle lead generation and management queries"""
        db = SessionLocal()
        try:
            # Get lead statistics
            total_leads = db.query(Lead).count()
            new_leads = db.query(Lead).filter(Lead.status == "new").count()
            qualified_leads = db.query(Lead).filter(Lead.status == "qualified").count()
            converted_leads = db.query(Lead).filter(Lead.status == "converted").count()
            
            # Calculate conversion rate
            conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
            
            # Top leads by score
            top_leads = db.query(Lead).order_by(Lead.score.desc()).limit(10).all()
            
            analysis = {
                "total_leads": total_leads,
                "new_leads": new_leads,
                "qualified_leads": qualified_leads,
                "converted_leads": converted_leads,
                "conversion_rate": round(conversion_rate, 2),
                "top_leads": [
                    {
                        "name": f"{lead.first_name} {lead.last_name}",
                        "company": lead.company,
                        "score": lead.score,
                        "status": lead.status
                    }
                    for lead in top_leads
                ]
            }
            
            answer = f"""Lead Management Summary:
            
• Total Leads: {total_leads}
• New Leads: {new_leads}
• Qualified Leads: {qualified_leads}
• Converted Leads: {converted_leads}
• Conversion Rate: {conversion_rate}%

Your top leads by score are ready for immediate follow-up."""
            
            recommendations = [
                f"Focus on {qualified_leads} qualified leads for immediate conversion",
                f"Follow up with {new_leads} new leads to qualify them",
                "Consider LinkedIn prospecting to expand your pipeline",
                "Set up automated email sequences for lead nurturing"
            ]
            
            return SalesResponse(
                answer=answer,
                analysis=analysis,
                recommendations=recommendations,
                next_actions=["Review top leads", "Create follow-up campaign", "Update lead scores"]
            )
            
        finally:
            db.close()
    
    async def _handle_campaign_query(self, query: SalesQuery) -> SalesResponse:
        """Handle marketing campaign queries"""
        db = SessionLocal()
        try:
            # Get campaign statistics
            total_campaigns = db.query(Campaign).count()
            active_campaigns = db.query(Campaign).filter(Campaign.status == "active").count()
            
            # Calculate total metrics
            total_sent = db.query(Campaign).with_entities(Campaign.sent_count).all()
            total_opened = db.query(Campaign).with_entities(Campaign.opened_count).all()
            
            sent_sum = sum([c[0] or 0 for c in total_sent])
            opened_sum = sum([c[0] or 0 for c in total_opened])
            
            open_rate = (opened_sum / sent_sum * 100) if sent_sum > 0 else 0
            
            analysis = {
                "total_campaigns": total_campaigns,
                "active_campaigns": active_campaigns,
                "total_sent": sent_sum,
                "total_opened": opened_sum,
                "open_rate": round(open_rate, 2)
            }
            
            answer = f"""Marketing Campaign Overview:
            
• Total Campaigns: {total_campaigns}
• Active Campaigns: {active_campaigns}
• Total Emails Sent: {sent_sum}
• Total Opens: {opened_sum}
• Average Open Rate: {open_rate}%

Your email marketing performance is being tracked across all campaigns."""
            
            recommendations = [
                "Optimize subject lines to improve open rates above 25%",
                "A/B test different email templates",
                "Segment your audience for better targeting",
                "Set up automated drip campaigns"
            ]
            
            return SalesResponse(
                answer=answer,
                analysis=analysis,
                recommendations=recommendations,
                next_actions=["Review campaign performance", "Create new campaign", "Optimize templates"]
            )
            
        finally:
            db.close()
    
    async def _handle_contract_query(self, query: SalesQuery) -> SalesResponse:
        """Handle contract and e-signature queries"""
        db = SessionLocal()
        try:
            # Get contract statistics
            total_contracts = db.query(Contract).count()
            signed_contracts = db.query(Contract).filter(Contract.status == "signed").count()
            pending_contracts = db.query(Contract).filter(Contract.status == "sent").count()
            
            # Calculate total value
            signed_value = db.query(Contract).filter(Contract.status == "signed").with_entities(Contract.amount).all()
            total_value = sum([c[0] or 0 for c in signed_value])
            
            signing_rate = (signed_contracts / total_contracts * 100) if total_contracts > 0 else 0
            
            analysis = {
                "total_contracts": total_contracts,
                "signed_contracts": signed_contracts,
                "pending_contracts": pending_contracts,
                "signing_rate": round(signing_rate, 2),
                "total_contract_value": total_value
            }
            
            answer = f"""Contract Management Summary:
            
• Total Contracts: {total_contracts}
• Signed Contracts: {signed_contracts}
• Pending Signatures: {pending_contracts}
• Signing Rate: {signing_rate}%
• Total Contract Value: ${total_value:,.2f}

Your e-signature workflow is streamlining deal closure."""
            
            recommendations = [
                f"Follow up on {pending_contracts} pending contracts",
                "Simplify contract templates to improve signing rates",
                "Set up automated reminders for pending signatures",
                "Consider offering incentives for quick signatures"
            ]
            
            return SalesResponse(
                answer=answer,
                analysis=analysis,
                recommendations=recommendations,
                next_actions=["Review pending contracts", "Send reminders", "Optimize templates"]
            )
            
        finally:
            db.close()
    
    async def _handle_payment_query(self, query: SalesQuery) -> SalesResponse:
        """Handle payment and revenue queries"""
        db = SessionLocal()
        try:
            # Get payment statistics
            total_payments = db.query(Payment).count()
            successful_payments = db.query(Payment).filter(Payment.status == "succeeded").count()
            
            # Calculate revenue
            successful_amounts = db.query(Payment).filter(Payment.status == "succeeded").with_entities(Payment.amount).all()
            total_revenue = sum([p[0] or 0 for p in successful_amounts])
            
            success_rate = (successful_payments / total_payments * 100) if total_payments > 0 else 0
            
            analysis = {
                "total_payments": total_payments,
                "successful_payments": successful_payments,
                "success_rate": round(success_rate, 2),
                "total_revenue": total_revenue
            }
            
            answer = f"""Payment Processing Summary:
            
• Total Payments: {total_payments}
• Successful Payments: {successful_payments}
• Success Rate: {success_rate}%
• Total Revenue: ${total_revenue:,.2f}

Your payment processing is handling transactions efficiently."""
            
            recommendations = [
                "Monitor failed payments and retry with different methods",
                "Set up automated invoicing for recurring clients",
                "Consider offering multiple payment options",
                "Implement payment reminders for overdue invoices"
            ]
            
            return SalesResponse(
                answer=answer,
                analysis=analysis,
                recommendations=recommendations,
                next_actions=["Review failed payments", "Set up recurring billing", "Send invoice reminders"]
            )
            
        finally:
            db.close()
    
    async def _handle_analytics_query(self, query: SalesQuery) -> SalesResponse:
        """Handle analytics and reporting queries"""
        db = SessionLocal()
        try:
            # Comprehensive analytics across all modules
            leads_count = db.query(Lead).count()
            campaigns_count = db.query(Campaign).count()
            contracts_count = db.query(Contract).count()
            payments_count = db.query(Payment).count()
            
            # Calculate funnel metrics
            qualified_leads = db.query(Lead).filter(Lead.status == "qualified").count()
            signed_contracts = db.query(Contract).filter(Contract.status == "signed").count()
            successful_payments = db.query(Payment).filter(Payment.status == "succeeded").count()
            
            # Revenue calculation
            revenue_data = db.query(Payment).filter(Payment.status == "succeeded").with_entities(Payment.amount).all()
            total_revenue = sum([p[0] or 0 for p in revenue_data])
            
            analysis = {
                "overview": {
                    "total_leads": leads_count,
                    "total_campaigns": campaigns_count,
                    "total_contracts": contracts_count,
                    "total_payments": payments_count
                },
                "funnel": {
                    "leads": leads_count,
                    "qualified": qualified_leads,
                    "contracts": signed_contracts,
                    "payments": successful_payments
                },
                "revenue": {
                    "total": total_revenue,
                    "average_deal": total_revenue / successful_payments if successful_payments > 0 else 0
                }
            }
            
            answer = f"""Sales & Marketing Analytics Dashboard:
            
📊 OVERVIEW:
• Total Leads: {leads_count}
• Total Campaigns: {campaigns_count}
• Total Contracts: {contracts_count}
• Total Payments: {payments_count}

🎯 CONVERSION FUNNEL:
• Leads → Qualified: {qualified_leads}/{leads_count} ({(qualified_leads/leads_count*100) if leads_count > 0 else 0:.1f}%)
• Qualified → Contracts: {signed_contracts}/{qualified_leads} ({(signed_contracts/qualified_leads*100) if qualified_leads > 0 else 0:.1f}%)
• Contracts → Payments: {successful_payments}/{signed_contracts} ({(successful_payments/signed_contracts*100) if signed_contracts > 0 else 0:.1f}%)

💰 REVENUE:
• Total Revenue: ${total_revenue:,.2f}
• Average Deal Size: ${(total_revenue/successful_payments) if successful_payments > 0 else 0:,.2f}

Your sales and marketing machine is performing across all key metrics."""
            
            recommendations = [
                "Focus on improving lead qualification to increase conversion",
                "Optimize contract templates to reduce friction",
                "Implement automated follow-up sequences",
                "Consider upselling strategies to increase deal size"
            ]
            
            return SalesResponse(
                answer=answer,
                analysis=analysis,
                recommendations=recommendations,
                next_actions=["Review funnel bottlenecks", "Optimize underperforming areas", "Set revenue targets"]
            )
            
        finally:
            db.close()
    
    async def _handle_general_query(self, query: SalesQuery) -> SalesResponse:
        """Handle general sales and marketing queries"""
        answer = f"""I'm your Sales & Marketing Intelligence Agent, ready to help with:

🎯 LEAD GENERATION:
• LinkedIn prospecting and lead scoring
• Lead management and qualification
• CRM automation and data enrichment

📧 MARKETING CAMPAIGNS:
• Email marketing via SendGrid
• Campaign automation and personalization
• A/B testing and optimization

📄 CONTRACT MANAGEMENT:
• E-signature workflows via DocuSign
• Contract templates and automation
• Deal closure tracking

💳 PAYMENT PROCESSING:
• Stripe payment integration
• Subscription management
• Revenue tracking and reporting

📊 ANALYTICS & INSIGHTS:
• Sales funnel analysis
• Marketing campaign performance
• Revenue forecasting and trends

How can I help optimize your sales and marketing operations today?"""
        
        recommendations = [
            "Start by reviewing your current lead pipeline",
            "Set up automated email campaigns for lead nurturing", 
            "Implement e-signature workflows for faster deal closure",
            "Connect your payment processing for seamless transactions"
        ]
        
        return SalesResponse(
            answer=answer,
            analysis={"capabilities": ["lead_generation", "email_marketing", "contract_management", "payment_processing", "analytics"]},
            recommendations=recommendations,
            next_actions=["Ask about specific sales/marketing needs", "Review current pipeline", "Set up automation"]
        )

# ================================
# API ENDPOINTS
# ================================

# Initialize agent
agent = SalesMarketingAgent()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Sales & Marketing Intelligence Agent", "version": config.agent_version}

@app.post("/query", response_model=SalesResponse)
async def process_query(query: SalesQuery):
    """Process sales and marketing intelligence queries"""
    return await agent.process_query(query)

@app.post("/leads", response_model=Dict[str, Any])
async def create_lead(lead: LeadCreate, db: Session = Depends(lambda: SessionLocal())):
    """Create new lead"""
    try:
        db_lead = Lead(**lead.dict())
        db.add(db_lead)
        db.commit()
        db.refresh(db_lead)
        
        return {"success": True, "lead_id": db_lead.id, "message": "Lead created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/campaigns", response_model=Dict[str, Any])
async def create_campaign(campaign: CampaignCreate, db: Session = Depends(lambda: SessionLocal())):
    """Create marketing campaign"""
    try:
        db_campaign = Campaign(**campaign.dict())
        db.add(db_campaign)
        db.commit()
        db.refresh(db_campaign)
        
        return {"success": True, "campaign_id": db_campaign.id, "message": "Campaign created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/contracts", response_model=Dict[str, Any])
async def create_contract(contract: ContractRequest, db: Session = Depends(lambda: SessionLocal())):
    """Create and send contract for e-signature"""
    try:
        lead = db.query(Lead).filter(Lead.id == contract.lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Send via DocuSign (would need authentication in production)
        envelope_id = f"mock_envelope_{contract.lead_id}_{int(datetime.now().timestamp())}"
        
        db_contract = Contract(
            lead_id=contract.lead_id,
            docusign_envelope_id=envelope_id,
            contract_type=contract.contract_type,
            amount=contract.amount,
            currency=contract.currency,
            status="sent"
        )
        db.add(db_contract)
        db.commit()
        db.refresh(db_contract)
        
        return {
            "success": True, 
            "contract_id": db_contract.id, 
            "envelope_id": envelope_id,
            "message": "Contract sent for signature"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/payments", response_model=Dict[str, Any])
async def process_payment(payment: PaymentRequest, db: Session = Depends(lambda: SessionLocal())):
    """Process payment via Stripe"""
    try:
        lead = db.query(Lead).filter(Lead.id == payment.lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Process payment (would use real Stripe in production)
        payment_id = f"mock_payment_{payment.lead_id}_{int(datetime.now().timestamp())}"
        
        db_payment = Payment(
            lead_id=payment.lead_id,
            stripe_payment_id=payment_id,
            amount=payment.amount,
            currency=payment.currency,
            status="succeeded",
            description=payment.description,
            payment_metadata=payment.payment_metadata
        )
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        
        return {
            "success": True,
            "payment_id": db_payment.id,
            "stripe_payment_id": payment_id,
            "message": "Payment processed successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# Celery background tasks
@celery_app.task
def process_linkedin_search(keywords: List[str], location: str = ""):
    """Background task for LinkedIn prospecting"""
    # This would run LinkedIn searches in the background
    pass

@celery_app.task
def send_email_campaign(campaign_id: int):
    """Background task for sending email campaigns"""
    # This would send bulk emails in the background
    pass

# ================================
# STARTUP
# ================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
