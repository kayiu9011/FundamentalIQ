from abc import ABC, abstractmethod

from app.models.financial import FinancialData


class ProviderError(Exception):
    status_code = 503
    code = "provider_error"

    def __init__(self, message: str = "Financial data provider is temporarily unavailable"):
        super().__init__(message)


class ProviderConfigurationError(ProviderError):
    status_code, code = 503, "provider_not_configured"


class StockNotFoundError(ProviderError):
    status_code, code = 404, "stock_not_found"


class ProviderAuthenticationError(ProviderError):
    status_code, code = 502, "provider_authentication_failed"


class ProviderRateLimitError(ProviderError):
    status_code, code = 429, "provider_rate_limited"


class ProviderTimeoutError(ProviderError):
    status_code, code = 504, "provider_timeout"


class ProviderResponseError(ProviderError):
    status_code, code = 502, "provider_invalid_response"


class StockDataProvider(ABC):
    @abstractmethod
    async def get_stock(self, symbol: str) -> FinancialData:
        raise NotImplementedError

    async def close(self) -> None:
        return None
