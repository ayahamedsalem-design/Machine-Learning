import os
import redis
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

class RedisClient:
    def __init__(self):
        try:
            self.client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            self.client.ping()
            self.enabled = True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Running without cache.")
            self.enabled = False

    def get(self, key: str):
        if not self.enabled:
            return None
        try:
            return self.client.get(key)
        except Exception as e:
            logger.warning(f"Redis GET failed: {e}")
            return None

    def setex(self, key: str, time: int, value: str):
        if not self.enabled:
            return
        try:
            self.client.setex(key, time, value)
        except Exception as e:
            logger.warning(f"Redis SETEX failed: {e}")

redis_client = RedisClient()