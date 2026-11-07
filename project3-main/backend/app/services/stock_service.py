import asyncio
import time
from dataclasses import dataclass

from app.models.financial import FinancialData
from app.providers.base import StockDataProvider


@dataclass
class CacheEntry:
    expires_at: float
    value: FinancialData


class StockService:
    """Small process-local TTL cache. Entries are not shared across workers or restarts."""

    def __init__(self, provider: StockDataProvider, ttl_seconds: int = 300):
        self.provider = provider
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get_stock(self, symbol: str) -> FinancialData:
        key = symbol.upper()
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached and cached.expires_at > now:
            return cached.value.model_copy(deep=True)
        async with self._lock:
            cached = self._cache.get(key)
            if cached and cached.expires_at > time.monotonic():
                return cached.value.model_copy(deep=True)
            value = await self.provider.get_stock(key)
            if self.ttl_seconds:
                self._cache[key] = CacheEntry(time.monotonic() + self.ttl_seconds, value.model_copy(deep=True))
            return value

    async def close(self) -> None:
        await self.provider.close()

