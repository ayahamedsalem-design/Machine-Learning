import redis

# Initialize Redis client connecting to localhost on port 6379
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True  # Automatically decodes bytes to strings for easier handling
)