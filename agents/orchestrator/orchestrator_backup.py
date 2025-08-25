"""
Central Orchestrator for Uplevel AI Multi-Agent System - FIXED VERSION

This orchestrator coordinates communication between Financial Intelligence and Sales & Marketing agents,
implements Agent2Agent Protocol, and manages persistent context through Redis state management.
"""

import asyncio
import os
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import re
from enum import Enum

# Core framework imports
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import httpx
import redis.asyncio as redis
import structlog
from contextlib import asynccontextmanager

# ML/AI for intent recognition
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

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

# ================================
# MODELS AND ENUMS
# ================================

class QueryType(str, Enum):
    """Types of queries the orchestrator can handle"""
    SINGLE_AGENT = "single_agent"
    MULTI_AGENT = "multi_agent"
    COLLABORATIVE = "collaborative"
    SEQUENTIAL = "sequential"

class AgentType(str, Enum):
    """Available agent types"""
    FINANCIAL = "financial_intelligence"
    SALES_MARKETING = "sales_marketing"
    ORCHESTRATOR = "orchestrator"

class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_COLLABORATION = "requires_collaboration"

class Agent2AgentMessage(BaseModel):
    """Standardized message format for Agent2Agent communication"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: AgentType = Field(..., description="Source agent")
    to_agent: AgentType = Field(..., description="Destination agent")
    message_type: str = Field(..., description="Type of message (query, response, request_help, etc.)")
    content: Dict[str, Any] = Field(..., description="Message content")
    context: Dict[str, Any] = Field(default_factory=dict, description="Shared context")
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    requires_response: bool = Field(default=True, description="Whether this message requires a response")
    correlation_id: Optional[str] = Field(None, description="ID linking related messages")

class OrchestratorQuery(BaseModel):
    """Main query model for orchestrator requests"""
    query: str = Field(..., description="User's query")
    session_id: Optional[str] = Field(None, description="Session ID for context persistence")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    user_id: Optional[str] = Field(None, description="User identifier")
    
    @field_validator('session_id')
    @classmethod
    def set_session_id(cls, v):
        return v or str(uuid.uuid4())

class OrchestratorResponse(BaseModel):
    """Response model from orchestrator"""
    answer: str = Field(..., description="Primary response")
    query_type: QueryType = Field(..., description="Type of query processed")
    agents_involved: List[AgentType] = Field(..., description="Agents that contributed")
    session_id: str = Field(..., description="Session ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="Supporting data")
    analysis: Dict[str, Any] = Field(default_factory=dict, description="Analysis results")
    recommendations: List[str] = Field(default_factory=list, description="Action recommendations")
    workflow_id: Optional[str] = Field(None, description="Multi-step workflow ID")
    next_actions: List[str] = Field(default_factory=list, description="Suggested next steps")

class WorkflowStep(BaseModel):
    """Individual step in a multi-agent workflow"""
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent: AgentType = Field(..., description="Agent responsible for this step")
    task: str = Field(..., description="Task description")
    dependencies: List[str] = Field(default_factory=list, description="Step IDs this depends on")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    result: Optional[Dict[str, Any]] = Field(None, description="Step result")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)

class Workflow(BaseModel):
    """Multi-agent workflow definition"""
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str = Field(..., description="Original user query")
    steps: List[WorkflowStep] = Field(..., description="Workflow steps")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    session_id: str = Field(..., description="Session ID")

# ================================
# INTENT RECOGNITION SYSTEM
# ================================

class IntentRecognitionEngine:
    """ML-based intent recognition for query classification"""
    
    def __init__(self):
        # Enhanced intent patterns with more comprehensive keywords
        self.intent_patterns = {
            # Single agent intents
            QueryType.SINGLE_AGENT: {
                AgentType.FINANCIAL: [
                    "generate p&l statement", "profit and loss report", "financial statement analysis",
                    "revenue analysis report", "expense breakdown analysis", "cost analysis detailed",
                    "financial forecast planning", "budget variance report", "cash flow statement",
                    "profitability analysis", "financial performance metrics", "income statement",
                    "balance sheet review", "financial ratios", "expense management", "revenue tracking",
                    "profit margin analysis", "financial dashboard", "accounting reports", "tax analysis"
                ],
                AgentType.SALES_MARKETING: [
                    "lead generation campaign", "marketing campaign strategy", "sales pipeline analysis",
                    "email marketing automation", "linkedin prospecting tools", "campaign analytics dashboard",
                    "conversion rate optimization", "lead scoring system", "sales performance tracking",
                    "marketing roi calculation", "customer acquisition cost", "pipeline management",
                    "sales forecasting", "marketing metrics", "customer segmentation", "campaign management",
                    "social media marketing", "content marketing", "sales automation", "crm management"
                ]
            },
            # Multi-agent collaborative intents
            QueryType.MULTI_AGENT: [
                "analyze financial performance and create marketing strategy",
                "revenue analysis with sales recommendations",
                "cost analysis combined with marketing optimization",
                "profit analysis and sales strategy development",
                "financial review and marketing plan",
                "budget analysis with sales forecasting",
                "expense review and sales optimization",
                "comprehensive business performance analysis"
            ],
            # Sequential workflow intents
            QueryType.SEQUENTIAL: [
                "first generate financial report then create sales strategy",
                "show p&l statement then recommend marketing actions",
                "analyze expenses first then optimize sales process",
                "create financial forecast then develop marketing plan",
                "review profitability then suggest sales improvements"
            ]
        }
        
        # Initialize TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),  # Reduced n-gram range for better matching
            stop_words='english',
            lowercase=True,
            max_features=500,  # Reduced features for better performance
            min_df=1  # Include all terms
        )
        
        # Build intent corpus
        self._build_intent_corpus()
    
    def _build_intent_corpus(self):
        """Build corpus for intent recognition"""
        corpus = []
        self.intent_labels = []
        
        # Add single agent patterns
        for agent_type in [AgentType.FINANCIAL, AgentType.SALES_MARKETING]:
            patterns = self.intent_patterns[QueryType.SINGLE_AGENT][agent_type]
            for pattern in patterns:
                corpus.append(pattern)
                self.intent_labels.append((QueryType.SINGLE_AGENT, agent_type))
        
        # Add multi-agent patterns
        for pattern in self.intent_patterns[QueryType.MULTI_AGENT]:
            corpus.append(pattern)
            self.intent_labels.append((QueryType.MULTI_AGENT, None))
        
        # Add sequential patterns
        for pattern in self.intent_patterns[QueryType.SEQUENTIAL]:
            corpus.append(pattern)
            self.intent_labels.append((QueryType.SEQUENTIAL, None))
        
        # Fit vectorizer
        if corpus:  # Ensure corpus is not empty
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        else:
            # Fallback with basic patterns
            corpus = ["financial analysis", "sales marketing", "multi agent workflow"]
            self.intent_labels = [(QueryType.SINGLE_AGENT, AgentType.FINANCIAL)] * len(corpus)
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        
        logger.info("Intent recognition engine initialized", 
                   corpus_size=len(corpus), 
                   feature_count=self.tfidf_matrix.shape[1])
    
    def classify_intent(self, query: str) -> tuple:
        """
        Classify query intent and determine agent assignment
        
        Returns:
            tuple: (query_type, primary_agent, confidence_score)
        """
        try:
            query_lower = query.lower()
            
            # Apply heuristic rules first for better accuracy
            
            # Check for explicit sequential indicators
            sequential_indicators = ["first", "then", "after that", "next", "followed by"]
            if any(indicator in query_lower for indicator in sequential_indicators):
                # Determine primary agent for sequential workflow
                financial_keywords = ["p&l", "profit", "loss", "revenue", "expense", "financial", "cost", "budget"]
                sales_keywords = ["sales", "marketing", "leads", "campaign", "pipeline", "conversion"]
                
                financial_pos = min([query_lower.find(kw) for kw in financial_keywords if kw in query_lower], default=float('inf'))
                sales_pos = min([query_lower.find(kw) for kw in sales_keywords if kw in query_lower], default=float('inf'))
                
                primary_agent = AgentType.FINANCIAL if financial_pos < sales_pos else AgentType.SALES_MARKETING
                return QueryType.SEQUENTIAL, primary_agent, 0.9
            
            # Check for multi-agent indicators
            multi_agent_keywords = ["and", "along with", "combined with", "plus", "also", "both", "analyze and", "with"]
            financial_keywords = ["p&l", "profit", "loss", "revenue", "expense", "financial", "cost", "budget"]
            sales_keywords = ["sales", "marketing", "leads", "campaign", "pipeline", "conversion", "lead"]
            
            has_multi_keywords = any(keyword in query_lower for keyword in multi_agent_keywords)
            has_financial = any(keyword in query_lower for keyword in financial_keywords)
            has_sales = any(keyword in query_lower for keyword in sales_keywords)
            
            if has_multi_keywords and has_financial and has_sales:
                return QueryType.COLLABORATIVE, None, 0.85
            
            # Single agent classification
            if has_financial and not has_sales:
                return QueryType.SINGLE_AGENT, AgentType.FINANCIAL, 0.8
            elif has_sales and not has_financial:
                return QueryType.SINGLE_AGENT, AgentType.SALES_MARKETING, 0.8
            
            # Fallback to TF-IDF similarity if heuristics don't work
            if hasattr(self, 'tfidf_matrix') and self.tfidf_matrix.shape[0] > 0:
                query_vector = self.vectorizer.transform([query_lower])
                similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
                
                if similarities.max() > 0:
                    best_match_idx = np.argmax(similarities)
                    best_similarity = similarities[best_match_idx]
                    query_type, primary_agent = self.intent_labels[best_match_idx]
                    
                    return query_type, primary_agent, float(best_similarity)
            
            # Final fallback - default to financial agent
            return QueryType.SINGLE_AGENT, AgentType.FINANCIAL, 0.5
            
        except Exception as e:
            logger.error("Intent classification failed", error=str(e))
            return QueryType.SINGLE_AGENT, AgentType.FINANCIAL, 0.5

# ================================
# REDIS STATE MANAGEMENT
# ================================

class RedisStateManager:
    """Redis-based state management for persistent context"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.project_id = "uplevel-phase2-1756155822"  # Using existing project ID
        self._fallback_storage = {}
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Redis connection established", redis_url=self.redis_url)
        except Exception as e:
            logger.error("Redis connection failed", error=str(e))
            # Use in-memory fallback
            self.redis_client = None
            logger.warning("Using in-memory storage fallback")
    
    async def store_session_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """Store session context with expiration"""
        try:
            key = f"session:{session_id}:context"
            if self.redis_client:
                await self.redis_client.setex(
                    key, 
                    int(timedelta(hours=24).total_seconds()), 
                    json.dumps(context, default=str)
                )
                return True
            else:
                # Fallback storage
                self._fallback_storage[key] = context
                return True
        except Exception as e:
            logger.error("Failed to store session context", error=str(e))
            return False
    
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Retrieve session context"""
        try:
            key = f"session:{session_id}:context"
            if self.redis_client:
                data = await self.redis_client.get(key)
                return json.loads(data) if data else {}
            else:
                return self._fallback_storage.get(key, {})
        except Exception as e:
            logger.error("Failed to retrieve session context", error=str(e))
            return {}
    
    async def store_workflow(self, workflow: Workflow) -> bool:
        """Store workflow state"""
        try:
            key = f"workflow:{workflow.workflow_id}"
            if self.redis_client:
                await self.redis_client.setex(
                    key,
                    int(timedelta(hours=48).total_seconds()),
                    workflow.model_dump_json()
                )
                return True
            else:
                self._fallback_storage[key] = workflow.model_dump()
                return True
        except Exception as e:
            logger.error("Failed to store workflow", error=str(e))
            return False
    
    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Retrieve workflow state"""
        try:
            key = f"workflow:{workflow_id}"
            if self.redis_client:
                data = await self.redis_client.get(key)
                return Workflow.model_validate_json(data) if data else None
            else:
                data = self._fallback_storage.get(key)
                return Workflow.model_validate(data) if data else None
        except Exception as e:
            logger.error("Failed to retrieve workflow", error=str(e))
            return None
    
    async def store_agent_response(self, session_id: str, agent: AgentType, response: Dict[str, Any]) -> bool:
        """Store agent response for context sharing"""
        try:
            key = f"session:{session_id}:agent_responses:{agent.value}"
            if self.redis_client:
                await self.redis_client.setex(
                    key,
                    int(timedelta(hours=24).total_seconds()),
                    json.dumps(response, default=str)
                )
                return True
            else:
                self._fallback_storage[key] = response
                return True
        except Exception as e:
            logger.error("Failed to store agent response", error=str(e))
            return False
    
    async def get_agent_response(self, session_id: str, agent: AgentType) -> Dict[str, Any]:
        """Retrieve agent response for context sharing"""
        try:
            key = f"session:{session_id}:agent_responses:{agent.value}"
            if self.redis_client:
                data = await self.redis_client.get(key)
                return json.loads(data) if data else {}
            else:
                return self._fallback_storage.get(key, {})
        except Exception as e:
            logger.error("Failed to retrieve agent response", error=str(e))
            return {}

# ================================
# AGENT COMMUNICATION SERVICE
# ================================

class AgentCommunicationService:
    """Service for communicating with individual agents"""
    
    def __init__(self):
        self.agent_endpoints = {
            AgentType.FINANCIAL: "https://uplevel-financial-agent-834012950450.us-central1.run.app",
            AgentType.SALES_MARKETING: "http://localhost:8003"
        }
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def send_to_agent(self, agent: AgentType, message: Agent2AgentMessage) -> Dict[str, Any]:
        """Send message to specific agent"""
        try:
            endpoint = self.agent_endpoints.get(agent)
            if not endpoint:
                raise HTTPException(status_code=404, detail=f"Agent {agent} not found")
            
            # Construct agent-specific request
            if agent == AgentType.FINANCIAL:
                request_data = {
                    "query": message.content.get("query", ""),
                    "period": message.content.get("period", "current_month"),
                    "context": message.context
                }
                url = f"{endpoint}/query"
            elif agent == AgentType.SALES_MARKETING:
                request_data = {
                    "query": message.content.get("query", ""),
                    "context": message.context,
                    "agent_type": message.content.get("agent_type", "general")
                }
                url = f"{endpoint}/query"
            
            logger.info("Sending request to agent", agent=agent.value, url=url)
            
            response = await self.http_client.post(
                url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("Agent request failed", 
                           agent=agent.value, 
                           status_code=response.status_code,
                           response_text=response.text)
                return {
                    "error": f"Agent {agent} returned status {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            logger.error("Agent communication failed", agent=agent.value, error=str(e))
            return {
                "error": f"Failed to communicate with {agent}",
                "details": str(e)
            }
    
    async def send_collaborative_request(self, query: str, agent: AgentType, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send a collaborative request that includes context from other agents"""
        message = Agent2AgentMessage(
            from_agent=AgentType.ORCHESTRATOR,
            to_agent=agent,
            message_type="collaborative_query",
            content={"query": query},
            context=context
        )
        return await self.send_to_agent(agent, message)

# ================================
# MAIN ORCHESTRATOR CLASS
# ================================

class CentralOrchestrator:
    """Central orchestrator for multi-agent coordination"""
    
    def __init__(self):
        self.intent_engine = IntentRecognitionEngine()
        self.state_manager = RedisStateManager()
        self.agent_comm = AgentCommunicationService()
        
        logger.info("Central Orchestrator initialized")
    
    async def initialize(self):
        """Initialize orchestrator services"""
        await self.state_manager.initialize()
        logger.info("Orchestrator services initialized")
    
    async def process_query(self, query: OrchestratorQuery) -> OrchestratorResponse:
        """Main query processing endpoint"""
        try:
            logger.info("Processing orchestrator query", 
                       query=query.query, 
                       session_id=query.session_id)
            
            # Load session context
            session_context = await self.state_manager.get_session_context(query.session_id)
            combined_context = {**session_context, **query.context}
            
            # Classify intent
            query_type, primary_agent, confidence = self.intent_engine.classify_intent(query.query)
            
            logger.info("Query classified", 
                       query_type=query_type, 
                       primary_agent=primary_agent, 
                       confidence=confidence)
            
            # Route based on query type
            if query_type == QueryType.SINGLE_AGENT:
                response = await self._handle_single_agent_query(
                    query, primary_agent, combined_context
                )
            elif query_type == QueryType.COLLABORATIVE:
                response = await self._handle_collaborative_query(
                    query, combined_context
                )
            elif query_type == QueryType.SEQUENTIAL:
                response = await self._handle_sequential_query(
                    query, primary_agent, combined_context
                )
            else:
                response = await self._handle_multi_agent_query(
                    query, combined_context
                )
            
            # Update session context
            updated_context = {
                **combined_context,
                "last_query": query.query,
                "last_response": response.model_dump(),
                "last_updated": datetime.utcnow().isoformat()
            }
            await self.state_manager.store_session_context(query.session_id, updated_context)
            
            return response
            
        except Exception as e:
            logger.error("Query processing failed", error=str(e))
            return OrchestratorResponse(
                answer=f"I encountered an error processing your request: {str(e)}",
                query_type=QueryType.SINGLE_AGENT,
                agents_involved=[AgentType.ORCHESTRATOR],
                session_id=query.session_id,
                analysis={"error": str(e)},
                recommendations=["Please try again", "Contact support if the issue persists"]
            )
    
    async def _handle_single_agent_query(
        self, 
        query: OrchestratorQuery, 
        agent: AgentType, 
        context: Dict[str, Any]
    ) -> OrchestratorResponse:
        """Handle queries that require only one agent"""
        
        message = Agent2AgentMessage(
            from_agent=AgentType.ORCHESTRATOR,
            to_agent=agent,
            message_type="single_query",
            content={"query": query.query},
            context=context
        )
        
        response = await self.agent_comm.send_to_agent(agent, message)
        
        # Store agent response for future context
        await self.state_manager.store_agent_response(query.session_id, agent, response)
        
        if "error" in response:
            answer = f"I encountered an issue with the {agent.value} agent: {response['error']}"
            recommendations = ["Please try again", "Check agent connectivity"]
        else:
            answer = response.get("answer", "No response received from agent")
            recommendations = response.get("recommendations", [])
        
        return OrchestratorResponse(
            answer=answer,
            query_type=QueryType.SINGLE_AGENT,
            agents_involved=[agent],
            session_id=query.session_id,
            data=response.get("data", {}),
            analysis=response.get("analysis", {}),
            recommendations=recommendations,
            next_actions=response.get("next_actions", [])
        )
    
    async def _handle_collaborative_query(
        self, 
        query: OrchestratorQuery, 
        context: Dict[str, Any]
    ) -> OrchestratorResponse:
        """Handle queries that require multiple agents working together"""
        
        agents = [AgentType.FINANCIAL, AgentType.SALES_MARKETING]
        responses = {}
        
        # Send query to all relevant agents concurrently
        tasks = []
        for agent in agents:
            task = self.agent_comm.send_collaborative_request(query.query, agent, context)
            tasks.append((agent, task))
        
        # Wait for all responses
        for agent, task in tasks:
            response = await task
            responses[agent] = response
            # Store each agent response for context sharing
            await self.state_manager.store_agent_response(query.session_id, agent, response)
        
        # Synthesize responses
        synthesized_response = await self._synthesize_multi_agent_responses(
            query.query, responses, context
        )
        
        return OrchestratorResponse(
            answer=synthesized_response["answer"],
            query_type=QueryType.COLLABORATIVE,
            agents_involved=agents,
            session_id=query.session_id,
            data=synthesized_response["data"],
            analysis=synthesized_response["analysis"],
            recommendations=synthesized_response["recommendations"],
            next_actions=synthesized_response["next_actions"]
        )
    
    async def _handle_sequential_query(
        self, 
        query: OrchestratorQuery, 
        primary_agent: AgentType, 
        context: Dict[str, Any]
    ) -> OrchestratorResponse:
        """Handle queries that require sequential agent execution"""
        
        # Create workflow
        workflow = await self._create_sequential_workflow(query.query, primary_agent, context)
        await self.state_manager.store_workflow(workflow)
        
        # Execute workflow steps
        final_response = await self._execute_workflow(workflow)
        
        return OrchestratorResponse(
            answer=final_response["answer"],
            query_type=QueryType.SEQUENTIAL,
            agents_involved=final_response["agents_involved"],
            session_id=query.session_id,
            data=final_response["data"],
            analysis=final_response["analysis"],
            recommendations=final_response["recommendations"],
            workflow_id=workflow.workflow_id,
            next_actions=final_response["next_actions"]
        )
    
    async def _handle_multi_agent_query(
        self, 
        query: OrchestratorQuery, 
        context: Dict[str, Any]
    ) -> OrchestratorResponse:
        """Handle general multi-agent queries"""
        return await self._handle_collaborative_query(query, context)
    
    async def _synthesize_multi_agent_responses(
        self, 
        original_query: str, 
        responses: Dict[AgentType, Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize responses from multiple agents into coherent answer"""
        
        # Extract key information from each response
        financial_response = responses.get(AgentType.FINANCIAL, {})
        sales_response = responses.get(AgentType.SALES_MARKETING, {})
        
        # Build comprehensive answer
        answer_parts = []
        
        if financial_response.get("answer"):
            answer_parts.append(f"**Financial Analysis:**\n{financial_response['answer']}")
        
        if sales_response.get("answer"):
            answer_parts.append(f"**Sales & Marketing Insights:**\n{sales_response['answer']}")
        
        # Cross-reference insights
        if financial_response.get("data") and sales_response.get("data"):
            cross_insights = self._generate_cross_insights(financial_response, sales_response)
            if cross_insights:
                answer_parts.append(cross_insights)
        
        combined_answer = "\n\n".join(answer_parts) if answer_parts else "No responses received from agents."
        
        # Combine data and analysis
        combined_data = {}
        combined_analysis = {}
        combined_recommendations = []
        combined_next_actions = []
        
        for response in [financial_response, sales_response]:
            if response.get("data"):
                combined_data.update(response["data"])
            if response.get("analysis"):
                combined_analysis.update(response["analysis"])
            if response.get("recommendations"):
                combined_recommendations.extend(response["recommendations"])
            if response.get("next_actions"):
                combined_next_actions.extend(response["next_actions"])
        
        return {
            "answer": combined_answer,
            "data": combined_data,
            "analysis": combined_analysis,
            "recommendations": combined_recommendations,
            "next_actions": combined_next_actions
        }
    
    def _generate_cross_insights(
        self, 
        financial_response: Dict[str, Any], 
        sales_response: Dict[str, Any]
    ) -> str:
        """Generate insights by correlating financial and sales data"""
        
        insights = ["**Cross-Functional Insights:**"]
        
        # Analyze profit margins vs sales performance
        financial_data = financial_response.get("data", {})
        sales_data = sales_response.get("data", {})
        
        if "profit_margin" in financial_data and "conversion_rate" in sales_data:
            profit_margin = financial_data.get("profit_margin", 0)
            conversion_rate = sales_data.get("conversion_rate", 0)
            
            if profit_margin < 20 and conversion_rate > 15:
                insights.append("• High sales conversion but low profit margins suggest pricing optimization opportunities")
            elif profit_margin > 30 and conversion_rate < 10:
                insights.append("• Strong margins but low conversion suggest potential for increased sales investment")
        
        # Analyze revenue trends vs marketing performance
        if "total_revenue" in financial_data and "total_campaigns" in sales_data:
            insights.append("• Marketing campaign effectiveness directly correlates with revenue performance")
        
        return "\n".join(insights) if len(insights) > 1 else ""
    
    async def _create_sequential_workflow(
        self, 
        query: str, 
        primary_agent: AgentType, 
        context: Dict[str, Any]
    ) -> Workflow:
        """Create sequential workflow for multi-step processes"""
        
        # Parse query for workflow steps
        steps = []
        
        if "first" in query.lower() and "then" in query.lower():
            query_parts = query.lower().split("then")
            
            # First step
            first_task = query_parts[0].replace("first", "").strip()
            step1 = WorkflowStep(
                agent=primary_agent,
                task=first_task,
                dependencies=[]
            )
            steps.append(step1)
            
            # Subsequent steps
            secondary_agent = AgentType.SALES_MARKETING if primary_agent == AgentType.FINANCIAL else AgentType.FINANCIAL
            for i, part in enumerate(query_parts[1:], 1):
                steps.append(WorkflowStep(
                    agent=secondary_agent,
                    task=part.strip(),
                    dependencies=[steps[0].step_id] if i == 1 else [steps[-2].step_id]
                ))
        else:
            # Default sequential workflow
            step1 = WorkflowStep(
                agent=primary_agent,
                task=query,
                dependencies=[]
            )
            steps.append(step1)
            
            step2 = WorkflowStep(
                agent=AgentType.SALES_MARKETING if primary_agent == AgentType.FINANCIAL else AgentType.FINANCIAL,
                task=f"Based on the previous analysis, provide recommendations for {query}",
                dependencies=[step1.step_id]
            )
            steps.append(step2)
        
        return Workflow(
            query=query,
            steps=steps,
            session_id=context.get("session_id", str(uuid.uuid4()))
        )
    
    async def _execute_workflow(self, workflow: Workflow) -> Dict[str, Any]:
        """Execute workflow steps sequentially"""
        
        agents_involved = []
        all_responses = {}
        
        for step in workflow.steps:
            # Check dependencies
            dependencies_met = all(
                any(s.step_id == dep_id and s.status == TaskStatus.COMPLETED for s in workflow.steps)
                for dep_id in step.dependencies
            )
            
            if not dependencies_met and step.dependencies:
                step.status = TaskStatus.FAILED
                step.error = "Dependencies not met"
                continue
            
            # Execute step
            step.status = TaskStatus.IN_PROGRESS
            step.started_at = datetime.utcnow()
            
            # Build context from previous steps
            step_context = {}
            for prev_step in workflow.steps:
                if prev_step.status == TaskStatus.COMPLETED and prev_step.result:
                    step_context[f"previous_{prev_step.agent.value}"] = prev_step.result
            
            # Send to agent
            message = Agent2AgentMessage(
                from_agent=AgentType.ORCHESTRATOR,
                to_agent=step.agent,
                message_type="workflow_step",
                content={"query": step.task},
                context=step_context
            )
            
            response = await self.agent_comm.send_to_agent(step.agent, message)
            
            if "error" not in response:
                step.status = TaskStatus.COMPLETED
                step.result = response
                step.completed_at = datetime.utcnow()
                all_responses[step.agent] = response
                
                if step.agent not in agents_involved:
                    agents_involved.append(step.agent)
            else:
                step.status = TaskStatus.FAILED
                step.error = response["error"]
        
        # Update workflow
        workflow.status = TaskStatus.COMPLETED if all(
            s.status == TaskStatus.COMPLETED for s in workflow.steps
        ) else TaskStatus.FAILED
        workflow.updated_at = datetime.utcnow()
        
        await self.state_manager.store_workflow(workflow)
        
        # Synthesize final response
        if all_responses:
            synthesized = await self._synthesize_multi_agent_responses(
                workflow.query, all_responses, {}
            )
            synthesized["agents_involved"] = agents_involved
            return synthesized
        else:
            return {
                "answer": "Workflow execution failed",
                "data": {},
                "analysis": {"workflow_status": workflow.status.value},
                "recommendations": ["Review workflow configuration", "Check agent connectivity"],
                "next_actions": ["Retry workflow", "Debug failed steps"],
                "agents_involved": agents_involved
            }

# ================================
# FASTAPI APPLICATION
# ================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await orchestrator.initialize()
    logger.info("Orchestrator application started")
    yield
    # Shutdown
    logger.info("Orchestrator application shutdown")

app = FastAPI(
    title="Uplevel AI Central Orchestrator",
    description="Multi-agent coordination and workflow orchestration service",
    version="1.0.0",
    lifespan=lifespan
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
security = HTTPBearer(auto_error=False)

# Initialize orchestrator
orchestrator = CentralOrchestrator()

# ================================
# API ENDPOINTS
# ================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "central_orchestrator",
        "version": "1.0.0"
    }

@app.post("/query", response_model=OrchestratorResponse)
async def process_query(query: OrchestratorQuery):
    """Main query processing endpoint"""
    return await orchestrator.process_query(query)

@app.get("/session/{session_id}/context")
async def get_session_context(session_id: str):
    """Get session context"""
    context = await orchestrator.state_manager.get_session_context(session_id)
    return {"session_id": session_id, "context": context}

@app.get("/workflow/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get workflow status"""
    workflow = await orchestrator.state_manager.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow.model_dump()

@app.get("/agents/status")
async def get_agent_status():
    """Get status of all connected agents"""
    status = {}
    
    for agent_type in [AgentType.FINANCIAL, AgentType.SALES_MARKETING]:
        try:
            # Send health check to each agent
            response = await orchestrator.agent_comm.http_client.get(
                f"{orchestrator.agent_comm.agent_endpoints[agent_type]}/health",
                timeout=5.0
            )
            status[agent_type.value] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds(),
                "endpoint": orchestrator.agent_comm.agent_endpoints[agent_type]
            }
        except Exception as e:
            status[agent_type.value] = {
                "status": "unreachable",
                "error": str(e),
                "endpoint": orchestrator.agent_comm.agent_endpoints.get(agent_type, "unknown")
            }
    
    return {"agents": status, "orchestrator_status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
