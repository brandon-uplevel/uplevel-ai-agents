#!/usr/bin/env python3
"""
Simple FastAPI Application for Uplevel Financial Intelligence Agent
Simplified version without ADK dependencies for initial deployment
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Import our agent components
try:
    from agents.financial_intelligence.financial_agent import FinancialIntelligenceAgent
    from mcps.hubspot_integration.hubspot_mcp import HubSpotMCPServer  
    from mcps.quickbooks_integration.quickbooks_mcp import QuickBooksMCPServer
    agent_available = True
except ImportError as e:
    logging.warning(f"Agent components not available: {e}")
    agent_available = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Uplevel Financial Intelligence Agent",
    description="AI agent for financial analysis, P&L generation, and business intelligence",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent: Optional[FinancialIntelligenceAgent] = None

# Request/Response models
class AgentRequest(BaseModel):
    """Agent request model"""
    query: str
    user_id: Optional[str] = "anonymous"
    session_id: Optional[str] = None
    period: Optional[str] = "current_month"
    format: Optional[str] = "detailed"

class AgentResponse(BaseModel):
    """Agent response model"""
    response: str
    agent: str
    version: str
    timestamp: str
    session_id: Optional[str]
    status: str
    error: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    agent: str
    version: str
    timestamp: str
    components: Optional[Dict[str, str]] = None
    error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup"""
    global agent
    try:
        logger.info("🚀 Starting Uplevel Financial Intelligence Agent...")
        
        if agent_available:
            agent = FinancialIntelligenceAgent()
            await agent.initialize()
            logger.info("✅ Agent initialized successfully")
        else:
            logger.warning("⚠️  Agent components not available, running in demo mode")
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize agent: {e}")
        # Don't fail startup, run in demo mode
        agent = None

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down Uplevel Financial Intelligence Agent")

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "service": "Uplevel Financial Intelligence Agent",
        "version": "1.0.0",
        "status": "running",
        "mode": "full" if agent_available else "demo",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        status = "healthy"
        components = {}
        
        if agent_available and agent:
            components = {
                "financial_agent": "active",
                "hubspot_mcp": "available",
                "quickbooks_mcp": "available"
            }
        else:
            status = "demo"
            components = {"demo_mode": "active"}
        
        return HealthResponse(
            status=status,
            agent="uplevel-financial-intelligence",
            version="1.0.0",
            timestamp=datetime.utcnow().isoformat(),
            components=components
        )
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            agent="uplevel-financial-intelligence",
            version="1.0.0",
            timestamp=datetime.utcnow().isoformat(),
            error=str(e)
        )

@app.post("/query", response_model=AgentResponse)
async def process_query(request: AgentRequest):
    """Process agent query"""
    try:
        session_id = request.session_id or f"session_{datetime.utcnow().timestamp()}"
        
        if agent_available and agent:
            # Build context for agent
            context = {
                "user_id": request.user_id,
                "session_id": session_id,
                "timestamp": datetime.utcnow(),
                "period": request.period,
                "format": request.format
            }
            
            # Process query with financial agent
            response_text = await agent.handle_query(request.query, context)
        else:
            # Demo mode response
            response_text = f"""
🏦 **Uplevel Financial Intelligence Agent - Demo Mode**

I'm currently running in demo mode. Here's what I can help you with once fully configured:

**Financial Analysis:**
• Generate comprehensive P&L statements from HubSpot & QuickBooks
• Create multi-month financial forecasts  
• Analyze cost trends and expense categories
• Compare revenue performance across time periods

**Your Query:** {request.query}

**Demo Response:** I would analyze your request using real-time data from:
- HubSpot (deals, revenue, sales pipeline)
- QuickBooks (expenses, accounts, financial records)

To enable full functionality, please configure:
1. HubSpot API credentials
2. QuickBooks OAuth tokens
3. Google Cloud Secret Manager access
            """.strip()
        
        return AgentResponse(
            response=response_text,
            agent="uplevel-financial-intelligence",
            version="1.0.0",
            timestamp=datetime.utcnow().isoformat(),
            session_id=session_id,
            status="success"
        )
    
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return AgentResponse(
            response="I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists.",
            agent="uplevel-financial-intelligence",
            version="1.0.0",
            timestamp=datetime.utcnow().isoformat(),
            session_id=request.session_id,
            status="error",
            error=str(e)
        )

@app.post("/pl-statement")
async def generate_pl_statement(
    period: str = "current_month",
    user_id: str = "anonymous",
    session_id: Optional[str] = None
):
    """Generate P&L statement endpoint"""
    request = AgentRequest(
        query=f"Generate a comprehensive P&L statement for {period}",
        user_id=user_id,
        session_id=session_id,
        period=period,
        format="detailed"
    )
    
    return await process_query(request)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else "An unexpected error occurred"
        }
    )

# For local development and Cloud Run
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "simple_app:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
