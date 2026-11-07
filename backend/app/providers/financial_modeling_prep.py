import asyncio
import math
from datetime import datetime
from typing import Any

import httpx

from app.models.financial import FinancialData
from app.providers.base import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    StockDataProvider,
    StockNotFoundError,
)


def _number(value: Any) -> float | None:
    """Parse FMP numeric values while preserving missing data as None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and value.strip().lower() in {"", "none", "null", "-"}:
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    records = [item for item in payload if isinstance(item, dict)]
    return sorted(records, key=lambda item: str(item.get("date", "")), reverse=True)


def _sum_records(records: list[dict[str, Any]], field: str, count: int = 4) -> float | None:
    values = [_number(record.get(field)) for record in records[:count]]
    if len(values) < count or any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def _prior_year_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None
    latest_date = _date(records[0].get("date"))
    if latest_date is None:
        return records[4] if len(records) > 4 else None
    for record in records[1:]:
        record_date = _date(record.get("date"))
        if record_date and 330 <= (latest_date - record_date).days <= 400:
            return record
    return None


def _growth(records: list[dict[str, Any]], field: str) -> float | None:
    if not records:
        return None
    current = _number(records[0].get(field))
    prior_record = _prior_year_record(records)
    prior = _number(prior_record.get(field)) if prior_record else None
    if current is None or prior is None or prior <= 0:
        return None
    return (current / prior) - 1


def _divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _first(payload: Any) -> dict[str, Any]:
    records = _records(payload)
    return records[0] if records else {}


def normalize_financial_modeling_prep(
    symbol: str,
    income_payload: Any,
    balance_payload: Any,
    cash_flow_payload: Any,
    quote_payload: Any,
    profile_payload: Any,
) -> FinancialData:
    """Combine FMP quarterly statements, quote, and profile into FinancialData.

    Trailing values use the latest four complete quarters. Ratios are calculated
    only when all required inputs are present and meaningful.
    """
    income = _records(income_payload)
    balance = _records(balance_payload)
    cash_flow = _records(cash_flow_payload)
    quote = _first(quote_payload)
    profile = _first(profile_payload)
    if not income and not balance and not cash_flow:
        raise StockNotFoundError(f"No Financial Modeling Prep fundamental data found for '{symbol.upper()}'")

    latest_balance = balance[0] if balance else {}
    prior_balance = _prior_year_record(balance)
    equity = _number(latest_balance.get("totalStockholdersEquity"))
    if equity is None:
        equity = _number(latest_balance.get("totalEquity"))
    assets = _number(latest_balance.get("totalAssets"))
    prior_equity = _number(prior_balance.get("totalStockholdersEquity")) if prior_balance else None
    if prior_equity is None and prior_balance:
        prior_equity = _number(prior_balance.get("totalEquity"))
    prior_assets = _number(prior_balance.get("totalAssets")) if prior_balance else None
    average_equity = (equity + prior_equity) / 2 if equity is not None and prior_equity is not None else equity
    average_assets = (assets + prior_assets) / 2 if assets is not None and prior_assets is not None else assets

    revenue = _sum_records(income, "revenue")
    net_income = _sum_records(income, "netIncome")
    operating_income = _sum_records(income, "operatingIncome")
    operating_cash_flow = _sum_records(cash_flow, "netCashProvidedByOperatingActivities")
    free_cash_flow = _sum_records(cash_flow, "freeCashFlow")
    shares = _number(income[0].get("weightedAverageShsOut")) if income else None
    debt = _number(latest_balance.get("totalDebt"))
    if debt is None:
        short_term_debt = _number(latest_balance.get("shortTermDebt"))
        long_term_debt = _number(latest_balance.get("longTermDebt"))
        if short_term_debt is not None or long_term_debt is not None:
            debt = (short_term_debt or 0) + (long_term_debt or 0)
    cash = _number(latest_balance.get("cashAndCashEquivalents"))
    if cash is None:
        cash = _number(latest_balance.get("cashAndShortTermInvestments"))
    current_assets = _number(latest_balance.get("totalCurrentAssets"))
    current_liabilities = _number(latest_balance.get("totalCurrentLiabilities"))
    price = _number(quote.get("price")) or _number(profile.get("price"))
    market_cap = _number(quote.get("marketCap")) or _number(profile.get("marketCap"))

    eps = _divide(net_income, shares)
    pe_ratio = _divide(price, eps)
    latest_quarter = _date((income[0] if income else latest_balance).get("date"))
    fiscal_year_records = [
        record for record in income
        if str(record.get("period", "")).upper() in {"FY", "Q4"}
    ]
    latest_year = _date(fiscal_year_records[0].get("date")) if fiscal_year_records else None
    values: dict[str, Any] = {
        "symbol": symbol.upper(),
        "long_name": profile.get("companyName") or quote.get("name") or None,
        "sector": profile.get("sector") or None,
        "industry": profile.get("industry") or None,
        "exchange": profile.get("exchange") or quote.get("exchange") or None,
        "currency": profile.get("currency") or (income[0].get("reportedCurrency") if income else None),
        "price": price,
        "market_cap": market_cap,
        "price_earnings_ratio": pe_ratio,
        "earnings_per_share": eps,
        "book_value_per_share": _divide(equity, shares),
        "revenue_per_share": _divide(revenue, shares),
        "profit_margin": _divide(net_income, revenue),
        "operating_margin": _divide(operating_income, revenue),
        "return_on_equity": _divide(net_income, average_equity),
        "return_on_assets": _divide(net_income, average_assets),
        "debt_to_equity_ratio": _divide(debt, equity),
        "current_ratio": _divide(current_assets, current_liabilities),
        "cash": cash,
        "debt": debt,
        "quarterly_revenue_growth": _growth(income, "revenue"),
        "quarterly_earnings_growth": _growth(income, "netIncome"),
        "operating_cash_flow": operating_cash_flow,
        "levered_free_cash_flow": free_cash_flow,
        "revenue": revenue,
        "shares_outstanding": shares,
        "last_fiscal_quarter_end": latest_quarter,
        "last_fiscal_year_end": latest_year,
        "source": "Financial Modeling Prep fundamental statements",
        "is_mock": False,
        "data_as_of": latest_quarter,
        "negative_equity": equity < 0 if equity is not None else None,
        "raw_values": {
            "income_fiscal_date": income[0].get("date") if income else None,
            "balance_fiscal_date": latest_balance.get("date"),
            "cash_flow_fiscal_date": cash_flow[0].get("date") if cash_flow else None,
        },
    }
    try:
        return FinancialData.model_validate(values)
    except Exception as exc:
        raise ProviderResponseError("Financial Modeling Prep returned malformed financial data") from exc


class FinancialModelingPrepStockDataProvider(StockDataProvider):
    def __init__(self, api_key: str, base_url: str, client: httpx.AsyncClient | None = None):
        if not api_key.strip():
            raise ProviderConfigurationError("Financial Modeling Prep mode requires FMP_API_KEY")
        self._api_key = api_key
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(20, connect=5),
        )

    async def _request(self, endpoint: str, symbol: str, limit: int | None = None) -> Any:
        params: dict[str, Any] = {"symbol": symbol, "apikey": self._api_key}
        if limit is not None:
            params.update({"period": "quarter", "limit": limit})
        try:
            response = await self._client.get(f"/{endpoint}", params=params)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Financial Modeling Prep request timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderError("Could not connect to Financial Modeling Prep") from exc
        if response.status_code in (401, 403):
            raise ProviderAuthenticationError("Financial Modeling Prep rejected the configured API key")
        if response.status_code == 429:
            raise ProviderRateLimitError("Financial Modeling Prep rate limit reached; try again later")
        if response.status_code >= 500:
            raise ProviderError("Financial Modeling Prep is temporarily unavailable")
        if response.status_code >= 400:
            raise ProviderResponseError("Financial Modeling Prep could not process this stock lookup")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderResponseError("Financial Modeling Prep returned invalid JSON") from exc
        if not isinstance(payload, (list, dict)):
            raise ProviderResponseError("Financial Modeling Prep returned an unexpected response shape")
        if isinstance(payload, dict):
            message = " ".join(str(payload.get(key, "")) for key in ("Error Message", "error", "message"))
            lowered = message.lower()
            if "api key" in lowered or "apikey" in lowered or "unauthorized" in lowered:
                raise ProviderAuthenticationError("Financial Modeling Prep rejected the configured API key")
            if "rate limit" in lowered or "limit reach" in lowered or "too many" in lowered:
                raise ProviderRateLimitError("Financial Modeling Prep rate limit reached; try again later")
            if message.strip():
                raise ProviderResponseError("Financial Modeling Prep could not provide the requested dataset")
            raise ProviderResponseError("Financial Modeling Prep returned an unexpected response shape")
        return payload

    async def get_stock(self, symbol: str) -> FinancialData:
        requests = (
            self._request("income-statement", symbol, limit=5),
            self._request("balance-sheet-statement", symbol, limit=5),
            self._request("cash-flow-statement", symbol, limit=4),
            self._request("quote", symbol),
            self._request("profile", symbol),
        )
        payloads = await asyncio.gather(*requests)
        return normalize_financial_modeling_prep(symbol, *payloads)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
