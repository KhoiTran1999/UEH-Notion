"""Redis connection singleton and cache TTL constants."""
import redis
from src.config.settings import Config

_client = None


def get_redis() -> redis.Redis | None:
    """Return a shared Redis client instance, creating it lazily."""
    global _client
    if _client is None and Config.REDIS_URL:
        _client = redis.from_url(
            Config.REDIS_URL,
            socket_connect_timeout=5,
            decode_responses=True,
        )
    return _client


# Cache TTL constants (seconds)
CACHE_PAGE_TITLE_TTL = 30 * 24 * 3600      # 30 days
CACHE_CANDIDATES_TTL = 24 * 3600            # 24 hours
CACHE_QUIZ_TTL = 14 * 24 * 3600             # 14 days
LOCK_QUIZ_TTL = 120                          # 2 minutes