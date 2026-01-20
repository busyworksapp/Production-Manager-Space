import redis
import os
from dotenv import load_dotenv
from backend.utils.logger import app_logger

load_dotenv()

_redis_client = None


def _get_redis_client():
    """Get or create the Redis client lazily"""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            try:
                _redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True
                )
                app_logger.info("Redis client initialized successfully")
            except Exception as e:
                app_logger.error(f"Failed to initialize Redis client: {e}")
                # Return None - Redis is optional for some operations
                _redis_client = None
        else:
            app_logger.warning("REDIS_URL not configured - Redis operations will fail")
            _redis_client = None
    return _redis_client


# Create a lazy-loading wrapper that returns None if not configured
class LazyRedisClient:
    """Lazy wrapper for Redis client that gracefully handles missing configuration"""
    
    def __getattr__(self, name):
        client = _get_redis_client()
        if client is None:
            raise RuntimeError(
                "Redis client not available. Set REDIS_URL environment variable."
            )
        return getattr(client, name)
    
    def ping(self):
        """Check if Redis is available"""
        client = _get_redis_client()
        if client is None:
            return False
        try:
            return client.ping()
        except Exception:
            return False


redis_client = LazyRedisClient()


def get_redis():
    """Get the Redis client"""
    return _get_redis_client()
