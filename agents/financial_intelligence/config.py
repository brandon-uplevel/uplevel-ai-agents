"""
Configuration for Financial Intelligence Agent
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class AgentConfig(BaseSettings):
    """Financial Intelligence Agent configuration"""
    
    # Agent Configuration
    agent_name: str = Field("financial_intelligence_agent", env="AGENT_NAME")
    agent_version: str = Field("1.0.0", env="AGENT_VERSION")
    
    # MCP Server URLs
    hubspot_mcp_url: str = Field("http://localhost:8001", env="HUBSPOT_MCP_URL")
    quickbooks_mcp_url: str = Field("http://localhost:8002", env="QUICKBOOKS_MCP_URL")
    
    # Google Cloud Configuration
    project_id: str = Field("uplevel-ai-agents", env="GOOGLE_CLOUD_PROJECT")
    region: str = Field("us-central1", env="GOOGLE_CLOUD_REGION")
    
    # Vertex AI Configuration
    vertex_ai_endpoint: Optional[str] = Field(None, env="VERTEX_AI_ENDPOINT")
    
    # Memory and Session Configuration
    memory_enabled: bool = Field(True, env="AGENT_MEMORY_ENABLED")
    session_timeout: int = Field(3600, env="AGENT_SESSION_TIMEOUT")  # 1 hour
    
    # Performance Configuration
    max_concurrent_requests: int = Field(10, env="AGENT_MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(30, env="AGENT_REQUEST_TIMEOUT")  # seconds
    
    # Logging Configuration
    log_level: str = Field("INFO", env="AGENT_LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global configuration instance
config = AgentConfig()
