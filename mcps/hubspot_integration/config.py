"""
Configuration management for HubSpot MCP Integration
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from google.cloud import secretmanager

class HubSpotConfig(BaseSettings):
    """HubSpot configuration with secret management"""
    
    # HubSpot API Configuration
    access_token: Optional[str] = Field(None, env="HUBSPOT_ACCESS_TOKEN")
    app_id: Optional[str] = Field(None, env="HUBSPOT_APP_ID")
    client_id: Optional[str] = Field(None, env="HUBSPOT_CLIENT_ID")
    client_secret: Optional[str] = Field(None, env="HUBSPOT_CLIENT_SECRET")
    
    # Google Cloud Configuration
    project_id: str = Field("uplevel-ai-agents", env="GOOGLE_CLOUD_PROJECT")
    secret_manager_enabled: bool = Field(True, env="USE_SECRET_MANAGER")
    
    # MCP Server Configuration
    server_host: str = Field("localhost", env="HUBSPOT_MCP_HOST")
    server_port: int = Field(8001, env="HUBSPOT_MCP_PORT")
    
    # Rate Limiting Configuration
    max_requests_per_second: int = Field(10, env="HUBSPOT_MAX_RPS")
    max_concurrent_requests: int = Field(5, env="HUBSPOT_MAX_CONCURRENT")
    
    # Cache Configuration
    cache_ttl_seconds: int = Field(300, env="HUBSPOT_CACHE_TTL")  # 5 minutes
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def get_access_token(self) -> str:
        """Get HubSpot access token from environment or Secret Manager"""
        
        if self.access_token:
            return self.access_token
        
        if self.secret_manager_enabled:
            try:
                return self._get_secret("hubspot-access-token")
            except Exception as e:
                raise ValueError(f"Failed to retrieve HubSpot access token from Secret Manager: {e}")
        
        raise ValueError("HubSpot access token not configured")
    
    def _get_secret(self, secret_id: str) -> str:
        """Retrieve secret from Google Secret Manager"""
        
        client = secretmanager.SecretManagerServiceClient()
        secret_name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
        
        response = client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8")

# Global configuration instance
config = HubSpotConfig()
