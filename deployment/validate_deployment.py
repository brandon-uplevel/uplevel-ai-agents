#!/usr/bin/env python3
"""
Deployment validation script for Uplevel Financial Intelligence Agent
Tests the deployed agent endpoints and functionality
"""

import asyncio
import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeploymentValidator:
    """Validates deployed agent functionality"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def validate_health_endpoint(self) -> bool:
        """Test health endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ Health check passed: {data['status']}")
            
            # Validate response structure
            required_fields = ['status', 'agent', 'version', 'components']
            for field in required_fields:
                if field not in data:
                    logger.error(f"❌ Missing field in health response: {field}")
                    return False
            
            return data['status'] == 'healthy'
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False
    
    async def validate_query_endpoint(self) -> bool:
        """Test query endpoint with sample query"""
        try:
            test_query = {
                "query": "What can you help me with?",
                "user_id": "test_user",
                "session_id": "test_session"
            }
            
            response = await self.client.post(
                f"{self.base_url}/query",
                json=test_query,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ Query endpoint responded: {data['status']}")
            
            # Validate response structure
            required_fields = ['response', 'agent', 'version', 'status']
            for field in required_fields:
                if field not in data:
                    logger.error(f"❌ Missing field in query response: {field}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Query endpoint test failed: {e}")
            return False
    
    async def validate_pl_endpoint(self) -> bool:
        """Test P&L statement endpoint"""
        try:
            response = await self.client.post(
                f"{self.base_url}/pl-statement",
                params={
                    "period": "current_month",
                    "user_id": "test_user"
                }
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ P&L endpoint responded: {data['status']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ P&L endpoint test failed: {e}")
            return False
    
    async def validate_docs_endpoint(self) -> bool:
        """Test API documentation endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/docs")
            response.raise_for_status()
            
            # Check if it returns HTML (swagger docs)
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                logger.info("✅ API documentation accessible")
                return True
            else:
                logger.warning("⚠️  API docs returned unexpected content type")
                return False
                
        except Exception as e:
            logger.error(f"❌ API docs test failed: {e}")
            return False
    
    async def run_full_validation(self) -> Dict[str, bool]:
        """Run complete validation suite"""
        logger.info(f"🧪 Starting validation for: {self.base_url}")
        
        results = {
            "health_check": await self.validate_health_endpoint(),
            "query_endpoint": await self.validate_query_endpoint(),
            "pl_endpoint": await self.validate_pl_endpoint(),
            "docs_endpoint": await self.validate_docs_endpoint()
        }
        
        # Summary
        passed = sum(results.values())
        total = len(results)
        
        logger.info(f"\n📊 Validation Results: {passed}/{total} tests passed")
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {test_name}: {status}")
        
        if passed == total:
            logger.info("🎉 All validation tests passed!")
        else:
            logger.error("💥 Some validation tests failed")
        
        await self.client.aclose()
        return results

async def main():
    """Main validation function"""
    # Load deployment info
    try:
        with open("deployment/deployment_info.json", "r") as f:
            deployment_info = json.load(f)
        
        service_url = deployment_info.get("service_url")
        if not service_url:
            logger.error("❌ No service URL found in deployment info")
            sys.exit(1)
        
        logger.info(f"🎯 Validating deployment at: {service_url}")
        
        # Run validation
        validator = DeploymentValidator(service_url)
        results = await validator.run_full_validation()
        
        # Exit with appropriate code
        if all(results.values()):
            sys.exit(0)
        else:
            sys.exit(1)
            
    except FileNotFoundError:
        logger.error("❌ Deployment info file not found. Run deployment first.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
