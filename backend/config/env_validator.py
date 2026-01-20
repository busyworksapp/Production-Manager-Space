import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env for local development
env_file = Path(__file__).parent.parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)

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
        elif (var == 'JWT_SECRET_KEY' and
              (value == 'your-secret-key' or
               'change' in value.lower())):
            warnings.append(
                f"  - {var}: Using default/weak secret key. "
                "CHANGE FOR PRODUCTION!"
            )

    if missing_vars:
        print("\n⚠️  WARNING: Missing environment variables:")
        print("\n".join(missing_vars))
        print("\nFor Railway: Set these in Railway Dashboard > Variables")
        print("For Local: Add to .env file")
        print("\nAttempting to start anyway...")

    for var, (description, default) in OPTIONAL_ENV_VARS.items():
        if not os.getenv(var):
            os.environ[var] = default

    if warnings:
        print("\n⚠️  WARNING: Security concerns detected:")
        print("\n".join(warnings))

    try:
        port = os.getenv('DB_PORT')
        if port:
            int(port)
    except ValueError:
        print("\n❌ CRITICAL: DB_PORT must be a valid integer")
        sys.exit(1)

    try:
        pool_min = os.getenv('DB_POOL_MIN')
        pool_max = os.getenv('DB_POOL_MAX')
        if pool_min:
            int(pool_min)
        if pool_max:
            int(pool_max)
    except ValueError:
        print(
            "\n❌ CRITICAL: DB_POOL_MIN and DB_POOL_MAX must be "
            "valid integers"
        )
        sys.exit(1)

    if pool_min and pool_max:
        if int(pool_min) > int(pool_max):
            print(
                "\n❌ CRITICAL: DB_POOL_MIN cannot be greater than "
                "DB_POOL_MAX"
            )
            sys.exit(1)

    print("✓ Environment validation passed")
    return True

if __name__ == '__main__':
    validate_environment()

