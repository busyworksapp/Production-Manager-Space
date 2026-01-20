#!/usr/bin/env python
"""
Production startup script for Railway
Handles environment setup and app initialization
"""
import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check required environment variables
required_vars = [
    'DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME',
    'JWT_SECRET_KEY'
]

logger.info("🚀 Starting Production Manager Space application...")
logger.info("Checking environment variables...")

missing_vars = []
for var in required_vars:
    if not os.getenv(var):
        missing_vars.append(var)
        logger.error(f"❌ Missing: {var}")
    else:
        if 'PASSWORD' in var or 'TOKEN' in var or 'SECRET' in var:
            logger.info(f"✓ {var}: [SET]")
        else:
            logger.info(f"✓ {var}: {os.getenv(var)}")

if missing_vars:
    logger.error(f"\n❌ CRITICAL: Missing environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

logger.info("\n✓ All environment variables configured")

# Import and run the app
try:
    logger.info("Importing Flask application...")
    from app import app
    logger.info("✓ Flask application imported successfully")
    
    logger.info("Application ready - gunicorn will start worker processes")
    
except Exception as e:
    logger.error(f"❌ Failed to import application: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == '__main__':
    logger.info("Starting application server...")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
