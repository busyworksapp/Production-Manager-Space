import redis
import os
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.from_url(
    os.getenv('REDIS_URL'),
    decode_responses=True
)

def get_redis():
    return redis_client
