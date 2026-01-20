#!/usr/bin/env python
"""
WSGI entry point for gunicorn
Used by: gunicorn wsgi:app
"""
import os
import sys

# For local development, load .env file
try:
    from pathlib import Path
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
except Exception:
    pass

# Import Flask app - gunicorn will call this
from app import app

if __name__ == '__main__':
    # This won't be called by gunicorn in production,
    # but allows direct python wsgi.py execution for testing
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

