import os
import sys
from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV_VARS = {
    'DB_HOST': 'Database host',
    'DB_PORT': 'Database port',
    'DB_USER': 'Database user',
    'DB_PASSWORD': 'Database password',
    'DB_NAME': 'Database name',
    'JWT_SECRET_KEY': 'JWT secret key',
    'REDIS_URL': 'Redis connection URL'
}

OPTIONAL_ENV_VARS = {
    'DB_POOL_MIN': ('Minimum database pool connections', '5'),
    'DB_POOL_MAX': ('Maximum database pool connections', '20'),
    'FLASK_ENV': ('Flask environment', 'production'),
    'FLASK_DEBUG': ('Flask debug mode', 'False'),
    'RATE_LIMIT_PER_MINUTE': ('API rate limit per minute', '60'),
    'SESSION_TIMEOUT_HOURS': ('Session timeout in hours', '24'),
    'MAX_UPLOAD_SIZE_MB': ('Maximum upload size in MB', '50')
}

def validate_environment():
    missing_vars = []
    warnings = []
    
    for var, description in REQUIRED_ENV_VARS.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"  - {var}: {description}")
        elif var == 'JWT_SECRET_KEY' and (value == 'your-secret-key' or 'change' in value.lower()):
            warnings.append(f"  - {var}: Using default/weak secret key. CHANGE FOR PRODUCTION!")
    
    if missing_vars:
        print("\n❌ CRITICAL: Missing required environment variables:")
        print("\n".join(missing_vars))
        print("\nPlease set these variables in your .env file.")
        sys.exit(1)
    
    for var, (description, default) in OPTIONAL_ENV_VARS.items():
        if not os.getenv(var):
            os.environ[var] = default
    
    if warnings:
        print("\n⚠️  WARNING: Security concerns detected:")
        print("\n".join(warnings))
    
    try:
        int(os.getenv('DB_PORT'))
    except ValueError:
        print("\n❌ CRITICAL: DB_PORT must be a valid integer")
        sys.exit(1)
    
    try:
        int(os.getenv('DB_POOL_MIN'))
        int(os.getenv('DB_POOL_MAX'))
    except ValueError:
        print("\n❌ CRITICAL: DB_POOL_MIN and DB_POOL_MAX must be valid integers")
        sys.exit(1)
    
    if int(os.getenv('DB_POOL_MIN')) > int(os.getenv('DB_POOL_MAX')):
        print("\n❌ CRITICAL: DB_POOL_MIN cannot be greater than DB_POOL_MAX")
        sys.exit(1)
    
    print("✓ Environment validation passed")
    return True

if __name__ == '__main__':
    validate_environment()
