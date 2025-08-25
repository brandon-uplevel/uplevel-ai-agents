"""
Configuration for Central Orchestrator
Enhanced for production deployment on Google Cloud Run
"""

import os
from typing import Dict, Any
import logging

class OrchestratorConfig:
    """Configuration class for orchestrator settings"""
    
    # Redis Configuration
    # Support both local Redis and Google Cloud Memorystore
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Agent Endpoints
    FINANCIAL_AGENT_URL = os.getenv(
        "FINANCIAL_AGENT_URL", 
        "https://uplevel-financial-agent-834012950450.us-central1.run.app"
    )
    
    # Sales agent - will be updated when deployed
    SALES_MARKETING_AGENT_URL = os.getenv(
        "SALES_MARKETING_AGENT_URL", 
        "http://localhost:8003"
    )
    
    # Orchestrator Settings
    # Use PORT environment variable for Cloud Run compatibility
    ORCHESTRATOR_PORT = int(os.getenv("PORT", os.getenv("ORCHESTRATOR_PORT", "8000")))
    
    # Project Configuration
    PROJECT_ID = "uplevel-phase2-1756155822"
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "uplevel-ai-agents")
    
    # Session Management
    SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    WORKFLOW_TIMEOUT_HOURS = int(os.getenv("WORKFLOW_TIMEOUT_HOURS", "48"))
    
    # Intent Recognition Settings
    INTENT_CONFIDENCE_THRESHOLD = float(os.getenv("INTENT_CONFIDENCE_THRESHOLD", "0.6"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Security
    API_KEY = os.getenv("ORCHESTRATOR_API_KEY")
    REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"
    
    # Production Settings
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # Health Check Configuration
    HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "10"))
    
    # Agent Communication Settings
    AGENT_REQUEST_TIMEOUT = int(os.getenv("AGENT_REQUEST_TIMEOUT", "30"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    
    @classmethod
    def get_agent_endpoints(cls) -> Dict[str, str]:
        """Get all agent endpoints"""
        return {
            "financial_intelligence": cls.FINANCIAL_AGENT_URL,
            "sales_marketing": cls.SALES_MARKETING_AGENT_URL
        }
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment"""
        return cls.ENVIRONMENT.lower() == "production" or cls.GOOGLE_CLOUD_PROJECT is not None
    
    @classmethod
    def get_redis_config(cls) -> Dict[str, Any]:
        """Get Redis configuration with connection pooling settings"""
        config = {
            "url": cls.REDIS_URL,
            "decode_responses": True,
            "socket_keepalive": True,
            "socket_keepalive_options": {},
            "health_check_interval": 30,
        }
        
        # Production-specific Redis settings
        if cls.is_production():
            config.update({
                "max_connections": 20,
                "retry_on_timeout": True,
                "socket_connect_timeout": 10,
                "socket_timeout": 10,
            })
        else:
            config.update({
                "max_connections": 10,
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
            })
        
        return config
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate configuration and return status"""
        issues = []
        warnings = []
        
        # Check required endpoints
        if not cls.FINANCIAL_AGENT_URL:
            issues.append("FINANCIAL_AGENT_URL not configured")
        
        if not cls.SALES_MARKETING_AGENT_URL:
            warnings.append("SALES_MARKETING_AGENT_URL not configured (using default)")
        
        # Check Redis URL
        if not cls.REDIS_URL:
            issues.append("REDIS_URL not configured")
        
        # Check production settings
        if cls.is_production():
            if not cls.GOOGLE_CLOUD_PROJECT:
                warnings.append("GOOGLE_CLOUD_PROJECT not set in production")
            
            if cls.LOG_LEVEL.upper() == "DEBUG":
                warnings.append("DEBUG logging enabled in production")
        
        # Port validation
        if not (1 <= cls.ORCHESTRATOR_PORT <= 65535):
            issues.append(f"Invalid port number: {cls.ORCHESTRATOR_PORT}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "config": {
                "redis_url": cls.REDIS_URL,
                "financial_agent": cls.FINANCIAL_AGENT_URL,
                "sales_agent": cls.SALES_MARKETING_AGENT_URL,
                "orchestrator_port": cls.ORCHESTRATOR_PORT,
                "project_id": cls.PROJECT_ID,
                "google_cloud_project": cls.GOOGLE_CLOUD_PROJECT,
                "environment": cls.ENVIRONMENT,
                "is_production": cls.is_production()
            }
        }
    
    @classmethod
    def log_configuration(cls, logger: logging.Logger = None):
        """Log current configuration (safe for production)"""
        if not logger:
            logger = logging.getLogger(__name__)
        
        logger.info("🔧 Orchestrator Configuration:")
        logger.info(f"   - Environment: {cls.ENVIRONMENT}")
        logger.info(f"   - Port: {cls.ORCHESTRATOR_PORT}")
        logger.info(f"   - Project ID: {cls.PROJECT_ID}")
        logger.info(f"   - Google Cloud Project: {cls.GOOGLE_CLOUD_PROJECT}")
        logger.info(f"   - Log Level: {cls.LOG_LEVEL}")
        logger.info(f"   - Session Timeout: {cls.SESSION_TIMEOUT_HOURS}h")
        logger.info(f"   - Workflow Timeout: {cls.WORKFLOW_TIMEOUT_HOURS}h")
        logger.info(f"   - Financial Agent: {cls.FINANCIAL_AGENT_URL}")
        
        # Only log Redis host/port in production for security
        if cls.is_production():
            try:
                import redis.utils
                redis_info = redis.utils.from_url(cls.REDIS_URL)
                logger.info(f"   - Redis: {redis_info.connection_kwargs.get('host', 'unknown')}:***")
            except:
                logger.info("   - Redis: configured")
        else:
            logger.info(f"   - Redis URL: {cls.REDIS_URL}")
        
        # Mask API key if set
        if cls.API_KEY:
            logger.info(f"   - API Key: {'*' * len(cls.API_KEY[:4])}...")
        else:
            logger.info("   - API Key: not set")

# Create instance for easy import
config = OrchestratorConfig()
