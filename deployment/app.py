#!/usr/bin/env python3
"""
FastAPI Application for Uplevel Financial Intelligence Agent
ADK-compatible wrapper for Vertex AI Agent Engine deployment
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

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Import deployment agent
from deploy_agent import UplevelFinancialAgent

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
agent: Optional[UplevelFinancialAgent] = None

# Request/Response models
class AgentRequest(BaseModel):
    """Agent request model"""
    query: str
    user_id: Optional[str] = "anonymous"
    session_id: Optional[str] = None
    period: Optional[str] = "current_month"
    format: Optional[str] = "detailed"
    context: Optional[Dict[str, Any]] = {}

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
    components: Dict[str, str]
    timestamp: str
    error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup"""
    global agent
    try:
        logger.info("🚀 Starting Uplevel Financial Intelligence Agent...")
        agent = UplevelFinancialAgent()
        await agent.initialize()
        logger.info("✅ Agent initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize agent: {e}")
        raise

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
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        if agent is None:
            raise HTTPException(status_code=503, detail="Agent not initialized")
        
        health_info = await agent.health_check()
        health_info["timestamp"] = datetime.utcnow().isoformat()
        
        return HealthResponse(**health_info)
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            agent="uplevel-financial-intelligence",
            version="1.0.0",
            components={},
            timestamp=datetime.utcnow().isoformat(),
            error=str(e)
        )

@app.post("/query", response_model=AgentResponse)
async def process_query(request: AgentRequest, background_tasks: BackgroundTasks):
    """Process agent query"""
    try:
        if agent is None:
            raise HTTPException(status_code=503, detail="Agent not initialized")
        
        # Create context object
        from google.adk.core import Context
        context = Context(
            session_id=request.session_id or f"session_{datetime.utcnow().timestamp()}",
            timestamp=datetime.utcnow(),
            user_id=request.user_id
        )
        
        # Prepare request data
        request_data = {
            "query": request.query,
            "user_id": request.user_id,
            "session_id": context.session_id,
            "period": request.period,
            "format": request.format,
            **request.context
        }
        
        # Process request
        response_data = await agent.handle_request(request_data, context)
        
        return AgentResponse(**response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return AgentResponse(
            response="I apologize, but I encountered an error processing your request. Please try again.",
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
    
    return await process_query(request, BackgroundTasks())

@app.post("/forecast")
async def generate_forecast(
    months: int = 3,
    user_id: str = "anonymous",
    session_id: Optional[str] = None
):
    """Generate financial forecast endpoint"""
    request = AgentRequest(
        query=f"Generate a {months}-month financial forecast",
        user_id=user_id,
        session_id=session_id,
        context={"months": months},
        format="detailed"
    )
    
    return await process_query(request, BackgroundTasks())

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

# For local development
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
