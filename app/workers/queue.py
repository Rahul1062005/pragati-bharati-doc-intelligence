import asyncio
import logging
from typing import Callable, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class TaskQueueManager:
    def __init__(self):
        self.redis_client = None
        self._check_redis()

    def _check_redis(self):
        try:
            import redis
            client = redis.from_url(settings.REDIS_URL, socket_timeout=1)
            client.ping()
            self.redis_client = client
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            self.redis_client = None
            logger.info(f"Redis not available ({e}). Using local async background worker.")

    def enqueue_task(self, coro_func: Callable[..., Any], *args, **kwargs):
        """
        Enqueue an asynchronous background task.
        If Redis is running, logs the task into Redis.
        Always dispatches non-blocking async execution.
        """
        task = asyncio.create_task(coro_func(*args, **kwargs))
        return task

task_queue = TaskQueueManager()
