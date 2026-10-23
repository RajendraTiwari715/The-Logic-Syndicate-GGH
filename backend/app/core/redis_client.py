import redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.client = None

    def connect(self):
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")

    def get_client(self):
        if not self.client:
            self.connect()
        return self.client

redis_client = RedisClient()
