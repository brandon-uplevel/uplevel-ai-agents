#!/usr/bin/env python3
"""
Startup script for Central Orchestrator
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from config import config

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('orchestrator.log')
        ]
    )

def validate_environment():
    """Validate environment and configuration"""
    print("🔍 Validating environment...")
    
    validation = config.validate_config()
    
    if validation["valid"]:
        print("✅ Configuration is valid")
        print(f"   - Redis URL: {validation['config']['redis_url']}")
        print(f"   - Financial Agent: {validation['config']['financial_agent']}")
        print(f"   - Sales Agent: {validation['config']['sales_agent']}")
        print(f"   - Orchestrator Port: {validation['config']['orchestrator_port']}")
        return True
    else:
        print("❌ Configuration issues found:")
        for issue in validation["issues"]:
            print(f"   - {issue}")
        return False

async def test_agent_connectivity():
    """Test connectivity to agent services"""
    print("🔗 Testing agent connectivity...")
    
    import httpx
    
    agents = config.get_agent_endpoints()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for agent_name, endpoint in agents.items():
            try:
                response = await client.get(f"{endpoint}/health")
                if response.status_code == 200:
                    print(f"   ✅ {agent_name}: Connected ({endpoint})")
                else:
                    print(f"   ⚠️  {agent_name}: Responded with status {response.status_code}")
            except Exception as e:
                print(f"   ❌ {agent_name}: Connection failed - {str(e)}")

def start_orchestrator():
    """Start the orchestrator service"""
    import uvicorn
    from orchestrator import app
    
    print(f"🚀 Starting Central Orchestrator on port {config.ORCHESTRATOR_PORT}...")
    print(f"   - Project ID: {config.PROJECT_ID}")
    print(f"   - Session timeout: {config.SESSION_TIMEOUT_HOURS} hours")
    print(f"   - Workflow timeout: {config.WORKFLOW_TIMEOUT_HOURS} hours")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.ORCHESTRATOR_PORT,
        log_level=config.LOG_LEVEL.lower(),
        reload=False,
        access_log=True
    )

async def main():
    """Main startup function"""
    print("🎯 Uplevel AI Central Orchestrator")
    print("=" * 50)
    
    # Setup logging
    setup_logging()
    
    # Validate environment
    if not validate_environment():
        print("❌ Environment validation failed. Please fix configuration issues.")
        sys.exit(1)
    
    # Test agent connectivity
    await test_agent_connectivity()
    
    print("\n🎉 All checks passed! Starting orchestrator...\n")
    
    # Start the orchestrator
    start_orchestrator()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Orchestrator stopped by user")
    except Exception as e:
        print(f"💥 Orchestrator startup failed: {str(e)}")
        sys.exit(1)
