import os
from redis import Redis
from rq import Worker, Queue, Connection

# Connect to Redis
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(redis_conn):
        q = Queue()
        worker = Worker([q])
        worker.work()
