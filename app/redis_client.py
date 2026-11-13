import os
import redis
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

class RedisClient:
    def __init__(self):
        try:
            logger.debug(f"Attempting to connect to Redis at {REDIS_URL}")
            self.client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            self.client.ping()
            self.enabled = True
            logger.info("Successfully connected to Redis. Caching is ENABLED.")
        except Exception as e:
            logger.warning(f"Redis connection failed. Application will run in graceful fallback mode without cache. Reason: {e}.")
            self.enabled = False

    def get(self, key: str):
        if not self.enabled:
            return None
        try:
            value = self.client.get(key)
            if value:
                logger.debug(f"Redis GET successful. Key found: '{key}'")
            return value
        except Exception as e:
            logger.error(f"Redis GET operation failed for key '{key}': {e}")
            return None

    def setex(self, key: str, time: int, value: str):
        if not self.enabled:
            return
        try:
            self.client.setex(key, time, value)
            logger.info(f"Successfully cached item in Redis with TTL {time}s. Key: '{key}'")
        except Exception as e:
            logger.error(f"Redis SETEX operation failed for key '{key}': {e}")

    def clear_cache(self):
        if not self.enabled:
            logger.warning("Attempted to clear cache, but Redis is disabled.")
            return False
        try:
            # flushdb clears all keys in the current database
            self.client.flushdb()
            logger.info("Redis cache completely cleared.")
            return True
        except Exception as e:
            logger.error(f"Failed to clear Redis cache: {e}")
            return False
        
redis_client = RedisClient()