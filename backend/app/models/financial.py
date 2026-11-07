from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FinancialData(BaseModel):
    """Provider-neutral financial snapshot. Missing values remain None, never zero."""

    model_config = ConfigDict(extra="ignore")
    symbol: str
    long_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    exchange: str | None = None
    currency: str | None = None
    price: float | None = None
    market_cap: float | None = None
    price_earnings_ratio: float | None = None
    earnings_per_share: float | None = None
    book_value_per_share: float | None = None
    revenue_per_share: float | None = None
    profit_margin: float | None = None
    operating_margin: float | None = None
    return_on_equity: float | None = None
    return_on_assets: float | None = None
    debt_to_equity_ratio: float | None = None
    current_ratio: float | None = None
    cash: float | None = None
    debt: float | None = None
    quarterly_revenue_growth: float | None = None
    quarterly_earnings_growth: float | None = None
    operating_cash_flow: float | None = None
    levered_free_cash_flow: float | None = None
    revenue: float | None = None
    shares_outstanding: float | None = None
    last_fiscal_quarter_end: datetime | None = None
    last_fiscal_year_end: datetime | None = None
    source: str
    is_mock: bool = False
    data_as_of: datetime | None = None
    negative_equity: bool | None = None
    raw_values: dict[str, Any] | None = None

