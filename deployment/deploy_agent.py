#!/usr/bin/env python3
"""
Vertex AI Deployment Script for Financial Intelligence Agent
Uses Google ADK to deploy to Vertex AI Agent Engine
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.cloud import aiplatform
from google.adk import Agent
from google.adk.core import State, Context

# Import our agent components
from agents.financial_intelligence.financial_agent import FinancialIntelligenceAgent
from mcps.hubspot_integration.hubspot_mcp import HubSpotMCPServer  
from mcps.quickbooks_integration.quickbooks_mcp import QuickBooksMCPServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UplevelFinancialAgent(Agent):
    """
    ADK-compatible wrapper for the Financial Intelligence Agent
    Deployed to Vertex AI Agent Engine for production use
    """
    
    def __init__(self):
        super().__init__(name="uplevel-financial-intelligence")
        
        # Initialize core agent
        self.financial_agent = FinancialIntelligenceAgent()
        
        # Initialize MCP servers
        self.hubspot_mcp = None
        self.quickbooks_mcp = None
        
        # Agent metadata
        self.description = "AI agent for financial analysis, P&L generation, and business intelligence"
        self.version = "1.0.0"
        
        logger.info("Uplevel Financial Intelligence Agent initialized")
    
    async def initialize(self) -> None:
        """Initialize agent and MCP connections"""
        try:
            # Initialize MCP servers with proper error handling
            try:
                self.hubspot_mcp = HubSpotMCPServer()
                logger.info("HubSpot MCP initialized successfully")
            except Exception as e:
                logger.warning(f"HubSpot MCP initialization failed: {e}")
            
            try:
                self.quickbooks_mcp = QuickBooksMCPServer()
                logger.info("QuickBooks MCP initialized successfully")
            except Exception as e:
                logger.warning(f"QuickBooks MCP initialization failed: {e}")
            
            # Initialize financial agent
            await self.financial_agent.initialize()
            logger.info("Financial Intelligence Agent core initialized")
            
        except Exception as e:
            logger.error(f"Agent initialization failed: {e}")
            raise
    
    async def handle_request(self, request: Dict[str, Any], context: Context) -> Dict[str, Any]:
        """
        Handle incoming requests from Vertex AI Agent Engine
        
        Args:
            request: Request data from user
            context: Agent execution context
            
        Returns:
            Response dictionary
        """
        try:
            # Extract query from request
            query = request.get("query", request.get("message", ""))
            user_id = request.get("user_id", "anonymous")
            session_id = request.get("session_id", context.session_id)
            
            logger.info(f"Processing request from user {user_id}: {query[:100]}...")
            
            # Build context for agent
            agent_context = {
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": context.timestamp,
                "period": request.get("period", "current_month"),
                "format": request.get("format", "detailed")
            }
            
            # Process query with financial agent
            response_text = await self.financial_agent.handle_query(query, agent_context)
            
            # Return structured response
            return {
                "response": response_text,
                "agent": "uplevel-financial-intelligence",
                "version": self.version,
                "timestamp": context.timestamp.isoformat(),
                "session_id": session_id,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {
                "response": f"I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists.",
                "agent": "uplevel-financial-intelligence",
                "version": self.version,
                "timestamp": context.timestamp.isoformat() if hasattr(context, 'timestamp') else None,
                "status": "error",
                "error": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint for monitoring"""
        try:
            # Check MCP server status
            hubspot_status = "connected" if self.hubspot_mcp else "disconnected"
            quickbooks_status = "connected" if self.quickbooks_mcp else "disconnected"
            
            return {
                "status": "healthy",
                "agent": "uplevel-financial-intelligence",
                "version": self.version,
                "components": {
                    "financial_agent": "active",
                    "hubspot_mcp": hubspot_status,
                    "quickbooks_mcp": quickbooks_status
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

async def deploy_to_vertex_ai():
    """Deploy agent to Vertex AI Agent Engine"""
    
    try:
        # Configuration
        PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "uplevel-ai-agents")
        LOCATION = os.getenv("VERTEX_AI_LOCATION", "us-central1")
        AGENT_NAME = "uplevel-financial-intelligence"
        
        logger.info(f"Deploying to Vertex AI - Project: {PROJECT_ID}, Location: {LOCATION}")
        
        # Initialize Vertex AI
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
        
        # Create agent instance
        agent = UplevelFinancialAgent()
        await agent.initialize()
        
        # Deploy using ADK
        logger.info("Creating Vertex AI Agent Engine deployment...")
        
        # Agent configuration for Vertex AI
        agent_config = {
            "display_name": "Uplevel Financial Intelligence Agent",
            "description": "AI agent for financial analysis, P&L generation, and business intelligence",
            "agent_settings": {
                "max_session_duration": "3600s",  # 1 hour sessions
                "conversation_timeout": "300s",   # 5 minute timeout
                "enable_logging": True,
                "enable_monitoring": True
            },
            "resource_requirements": {
                "memory": "2Gi",
                "cpu": "1000m",
                "max_replicas": 10,
                "min_replicas": 1
            }
        }
        
        # Deploy to Vertex AI Agent Engine
        from google.adk.deployment import VertexAgentEngine
        
        deployment = VertexAgentEngine.deploy(
            agent=agent,
            config=agent_config,
            project_id=PROJECT_ID,
            location=LOCATION
        )
        
        logger.info(f"✅ Agent deployed successfully!")
        logger.info(f"Agent Endpoint: {deployment.endpoint_url}")
        logger.info(f"Agent Resource Name: {deployment.resource_name}")
        
        # Save deployment info
        deployment_info = {
            "agent_name": AGENT_NAME,
            "project_id": PROJECT_ID,
            "location": LOCATION,
            "endpoint_url": deployment.endpoint_url,
            "resource_name": deployment.resource_name,
            "deployment_time": deployment.deployment_time.isoformat(),
            "status": "deployed"
        }
        
        # Write deployment info to file
        import json
        with open("deployment/deployment_info.json", "w") as f:
            json.dump(deployment_info, f, indent=2)
        
        logger.info("Deployment information saved to deployment/deployment_info.json")
        
        return deployment
        
    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        raise

async def main():
    """Main deployment function"""
    try:
        deployment = await deploy_to_vertex_ai()
        logger.info("🎉 Financial Intelligence Agent deployment completed successfully!")
        return deployment
    except Exception as e:
        logger.error(f"💥 Deployment failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
