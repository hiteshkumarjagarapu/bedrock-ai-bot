import hashlib
import json
import logging

import redis.asyncio as redis

from config import Settings

logger = logging.getLogger(__name__)
TTL_SECONDS = 3600


class ResponseCache:
    """Redis cache-aside. Failures degrade gracefully to cache misses."""

    def __init__(self, settings: Settings) -> None:
        self.client = redis.from_url(settings.redis_url, decode_responses=True)

    @staticmethod
    def make_key(user_id: int, query: str, doc_ids: list[int] | None) -> str:
        raw = json.dumps([user_id, query.strip().lower(), sorted(doc_ids or [])])
        return "chat:" + hashlib.sha256(raw.encode()).hexdigest()

    async def get(self, key: str) -> dict | None:
        try:
            value = await self.client.get(key)
            return json.loads(value) if value else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis get failed: %s", exc)
            return None

    async def set(self, key: str, value: dict) -> None:
        try:
            await self.client.set(key, json.dumps(value), ex=TTL_SECONDS)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis set failed: %s", exc)

    async def close(self) -> None:
        await self.client.aclose()
