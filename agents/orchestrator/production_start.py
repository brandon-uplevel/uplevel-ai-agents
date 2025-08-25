#!/usr/bin/env python3
"""
Production startup script for Central Orchestrator - Cloud Run optimized
"""

import os
import sys
import asyncio
import logging
import uvicorn
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from config import config

def setup_production_logging():
    """Setup production logging for Cloud Run"""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)  # Cloud Run logs to stdout
        ]
    )
    
    # Set specific loggers to reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

def validate_production_environment():
    """Validate production environment"""
    logger = logging.getLogger(__name__)
    
    logger.info("🔍 Validating production environment...")
    
    validation = config.validate_config()
    
    if validation["valid"]:
        logger.info("✅ Configuration is valid")
        logger.info(f"   - Redis URL: {validation['config']['redis_url']}")
        logger.info(f"   - Financial Agent: {validation['config']['financial_agent']}")
        logger.info(f"   - Sales Agent: {validation['config']['sales_agent']}")
        logger.info(f"   - Orchestrator Port: {validation['config']['orchestrator_port']}")
        return True
    else:
        logger.error("❌ Configuration issues found:")
        for issue in validation["issues"]:
            logger.error(f"   - {issue}")
        return False

def start_production_orchestrator():
    """Start the orchestrator in production mode"""
    logger = logging.getLogger(__name__)
    
    # Use PORT environment variable if set by Cloud Run
    port = int(os.getenv("PORT", config.ORCHESTRATOR_PORT))
    
    logger.info(f"🚀 Starting Central Orchestrator in production mode")
    logger.info(f"   - Port: {port}")
    logger.info(f"   - Project ID: {config.PROJECT_ID}")
    logger.info(f"   - Session timeout: {config.SESSION_TIMEOUT_HOURS} hours")
    logger.info(f"   - Workflow timeout: {config.WORKFLOW_TIMEOUT_HOURS} hours")
    
    from orchestrator import app
    
    # Production uvicorn configuration
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level=config.LOG_LEVEL.lower(),
        reload=False,  # No reload in production
        access_log=True,
        workers=1,  # Single worker for now, can scale later
        timeout_keep_alive=30,
        timeout_graceful_shutdown=30
    )

def main():
    """Main production startup function"""
    print("🎯 Uplevel AI Central Orchestrator - Production Mode")
    print("=" * 60)
    
    # Setup logging
    setup_production_logging()
    logger = logging.getLogger(__name__)
    
    # Validate environment
    if not validate_production_environment():
        logger.error("❌ Environment validation failed. Check configuration.")
        sys.exit(1)
    
    logger.info("🎉 All checks passed! Starting production orchestrator...")
    
    # Start the orchestrator
    start_production_orchestrator()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Orchestrator stopped")
    except Exception as e:
        print(f"💥 Orchestrator startup failed: {str(e)}")
        logging.exception("Startup failure:")
        sys.exit(1)
