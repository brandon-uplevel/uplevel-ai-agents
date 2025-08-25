"""
Configuration for Sales & Marketing Intelligence Agent
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class SalesMarketingConfig(BaseSettings):
    """Sales & Marketing Intelligence Agent configuration"""
    
    # Agent Configuration
    agent_name: str = Field("sales_marketing_agent", env="AGENT_NAME")
    agent_version: str = Field("1.0.0", env="AGENT_VERSION")
    
    # Service Integration URLs and Keys
    linkedin_client_id: Optional[str] = Field(None, env="LINKEDIN_CLIENT_ID")
    linkedin_client_secret: Optional[str] = Field(None, env="LINKEDIN_CLIENT_SECRET")
    linkedin_redirect_uri: str = Field("http://localhost:8000/auth/linkedin/callback", env="LINKEDIN_REDIRECT_URI")
    
    sendgrid_api_key: Optional[str] = Field(None, env="SENDGRID_API_KEY")
    sendgrid_from_email: str = Field("noreply@uplevel.ai", env="SENDGRID_FROM_EMAIL")
    
    docusign_client_id: Optional[str] = Field(None, env="DOCUSIGN_CLIENT_ID")
    docusign_client_secret: Optional[str] = Field(None, env="DOCUSIGN_CLIENT_SECRET")
    docusign_redirect_uri: str = Field("http://localhost:8000/auth/docusign/callback", env="DOCUSIGN_REDIRECT_URI")
    docusign_base_url: str = Field("https://demo.docusign.net", env="DOCUSIGN_BASE_URL")  # demo environment
    
    stripe_api_key: Optional[str] = Field(None, env="STRIPE_API_KEY")
    stripe_webhook_secret: Optional[str] = Field(None, env="STRIPE_WEBHOOK_SECRET")
    
    # Database Configuration
    database_url: str = Field("sqlite:///./sales_marketing.db", env="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    
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
    
    # Celery Configuration
    celery_broker_url: str = Field("redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field("redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    
    # Security Configuration
    secret_key: str = Field("your-secret-key-change-in-production", env="SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Compliance and Rate Limiting
    linkedin_rate_limit_per_hour: int = Field(100, env="LINKEDIN_RATE_LIMIT_PER_HOUR")
    sendgrid_rate_limit_per_hour: int = Field(10000, env="SENDGRID_RATE_LIMIT_PER_HOUR")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="AGENT_LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global configuration instance
config = SalesMarketingConfig()
