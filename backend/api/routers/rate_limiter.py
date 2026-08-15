import os
import time
from fastapi import HTTPException
from redis import Redis

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(redis_url)

class RateLimitExceeded(HTTPException):
    def __init__(self, detail="Too many requests"):
        super().__init__(status_code=429, detail=detail)

def check_rate_limit(action: str, agent_id: str, session_id: str, max_requests: int = 10, window_seconds: int = 60):
    """
    A simple fixed-window rate limiter using Redis.
    """
    current_time = int(time.time())
    window = current_time // window_seconds
    key = f"rate:{action}:{agent_id}:{session_id}:{window}"
    
    # Increment the counter for this window
    current_count = redis_conn.incr(key)
    
    # Set expiration on the first request in this window
    if current_count == 1:
        redis_conn.expire(key, window_seconds * 2)
        
    if current_count > max_requests:
        raise RateLimitExceeded(detail=f"Rate limit exceeded for {action}.")
