"""
Configuration management for QuickBooks MCP Integration
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from google.cloud import secretmanager

class QuickBooksConfig(BaseSettings):
    """QuickBooks configuration with secret management"""
    
    # QuickBooks OAuth Configuration
    client_id: Optional[str] = Field(None, env="QB_CLIENT_ID")
    client_secret: Optional[str] = Field(None, env="QB_CLIENT_SECRET")
    access_token: Optional[str] = Field(None, env="QB_ACCESS_TOKEN")
    refresh_token: Optional[str] = Field(None, env="QB_REFRESH_TOKEN")
    company_id: Optional[str] = Field(None, env="QB_COMPANY_ID")
    
    # Environment Configuration
    environment: str = Field("sandbox", env="QB_ENVIRONMENT")  # sandbox or production
    redirect_uri: str = Field("http://localhost:8000/callback", env="QB_REDIRECT_URI")
    
    # Google Cloud Configuration
    project_id: str = Field("uplevel-ai-agents", env="GOOGLE_CLOUD_PROJECT")
    secret_manager_enabled: bool = Field(True, env="USE_SECRET_MANAGER")
    
    # MCP Server Configuration
    server_host: str = Field("localhost", env="QB_MCP_HOST")
    server_port: int = Field(8002, env="QB_MCP_PORT")
    
    # API Configuration
    api_minor_version: int = Field(70, env="QB_API_MINOR_VERSION")
    
    # Cache Configuration
    cache_ttl_seconds: int = Field(600, env="QB_CACHE_TTL")  # 10 minutes
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def get_client_credentials(self) -> tuple[str, str]:
        """Get QuickBooks client ID and secret from environment or Secret Manager"""
        
        client_id = self.client_id
        client_secret = self.client_secret
        
        if self.secret_manager_enabled:
            try:
                client_id = client_id or self._get_secret("quickbooks-client-id")
                client_secret = client_secret or self._get_secret("quickbooks-client-secret")
            except Exception as e:
                if not (client_id and client_secret):
                    raise ValueError(f"Failed to retrieve QuickBooks credentials from Secret Manager: {e}")
        
        if not (client_id and client_secret):
            raise ValueError("QuickBooks client credentials not configured")
        
        return client_id, client_secret
    
    def get_tokens(self) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Get QuickBooks access token, refresh token, and company ID"""
        
        access_token = self.access_token
        refresh_token = self.refresh_token
        company_id = self.company_id
        
        if self.secret_manager_enabled:
            try:
                access_token = access_token or self._get_secret("quickbooks-access-token")
                refresh_token = refresh_token or self._get_secret("quickbooks-refresh-token")
                company_id = company_id or self._get_secret("quickbooks-company-id")
            except Exception:
                # Tokens may not exist yet if OAuth hasn't been completed
                pass
        
        return access_token, refresh_token, company_id
    
    def save_tokens(self, access_token: str, refresh_token: str, company_id: str):
        """Save QuickBooks tokens to Secret Manager"""
        
        if self.secret_manager_enabled:
            try:
                self._create_or_update_secret("quickbooks-access-token", access_token)
                self._create_or_update_secret("quickbooks-refresh-token", refresh_token)
                self._create_or_update_secret("quickbooks-company-id", company_id)
                logger.info("QuickBooks tokens saved to Secret Manager")
            except Exception as e:
                logger.error(f"Failed to save tokens to Secret Manager: {e}")
                # Fallback to environment variables
                os.environ["QB_ACCESS_TOKEN"] = access_token
                os.environ["QB_REFRESH_TOKEN"] = refresh_token
                os.environ["QB_COMPANY_ID"] = company_id
    
    def _get_secret(self, secret_id: str) -> str:
        """Retrieve secret from Google Secret Manager"""
        
        client = secretmanager.SecretManagerServiceClient()
        secret_name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
        
        response = client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8")
    
    def _create_or_update_secret(self, secret_id: str, secret_value: str):
        """Create or update secret in Google Secret Manager"""
        
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{self.project_id}"
        secret_name = f"{parent}/secrets/{secret_id}"
        
        try:
            # Try to create secret
            secret = client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
            logger.info(f"Created secret: {secret.name}")
        except Exception:
            # Secret already exists, that's okay
            pass
        
        # Add secret version
        client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": secret_value.encode("UTF-8")},
            }
        )

# Global configuration instance
config = QuickBooksConfig()

# Import logging after config
import logging
logger = logging.getLogger(__name__)
