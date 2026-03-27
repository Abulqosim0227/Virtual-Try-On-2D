import structlog
from redis import Redis, RedisError

from vto.config import settings

logger = structlog.get_logger()


class ResultCache:
    def __init__(self) -> None:
        self._client: Redis | None = None

    def connect(self) -> None:
        try:
            self._client = Redis.from_url(settings.redis_url, decode_responses=False)
            self._client.ping()
            logger.info("redis_connected", url=settings.redis_url)
        except RedisError:
            logger.warning("redis_unavailable", url=settings.redis_url)
            self._client = None

    def get(self, cache_key: str) -> bytes | None:
        if not self._client:
            return None
        try:
            return self._client.get(f"vto:result:{cache_key}")
        except RedisError:
            logger.warning("redis_get_failed", key=cache_key)
            return None

    def set(self, cache_key: str, image_bytes: bytes) -> None:
        if not self._client:
            return
        try:
            ttl_seconds = settings.result_ttl_hours * 3600
            self._client.setex(f"vto:result:{cache_key}", ttl_seconds, image_bytes)
            logger.info("cache_set", key=cache_key, ttl_hours=settings.result_ttl_hours)
        except RedisError:
            logger.warning("redis_set_failed", key=cache_key)

    def exists(self, cache_key: str) -> bool:
        if not self._client:
            return False
        try:
            return self._client.exists(f"vto:result:{cache_key}") > 0
        except RedisError:
            return False

    @property
    def connected(self) -> bool:
        return self._client is not None
