from copy import deepcopy
from datetime import UTC, datetime

from app.models.financial import FinancialData
from app.providers.base import StockDataProvider, StockNotFoundError


def _company(symbol: str, name: str, **values: object) -> dict[str, object]:
    base: dict[str, object] = {
        "symbol": symbol, "long_name": f"{name} — Illustrative Sample", "exchange": "SAMPLE",
        "currency": "USD", "source": "FundamentalIQ illustrative fixture", "is_mock": True,
        "data_as_of": datetime(2026, 9, 30, tzinfo=UTC), "last_fiscal_quarter_end": "2026-09-30T00:00:00Z",
        "last_fiscal_year_end": "2025-12-31T00:00:00Z", "raw_values": None,
    }
    base.update(values)
    return base


MOCK_COMPANIES: dict[str, dict[str, object]] = {
    "NOVA": _company("NOVA", "Nova Precision Systems", sector="Industrials", industry="Specialty Machinery",
        price=84.25, market_cap=8_420_000_000, price_earnings_ratio=18.4, earnings_per_share=4.58,
        book_value_per_share=23.1, revenue_per_share=41.2, profit_margin=.164, operating_margin=.202,
        return_on_equity=.218, return_on_assets=.091, debt_to_equity_ratio=.44, current_ratio=2.15,
        cash=1_120_000_000, debt=780_000_000, quarterly_revenue_growth=.112,
        quarterly_earnings_growth=.146, operating_cash_flow=1_040_000_000, levered_free_cash_flow=720_000_000,
        revenue=4_120_000_000, shares_outstanding=100_000_000),
    "SKYH": _company("SKYH", "Skyharbor Cloud Labs", sector="Technology", industry="Software—Infrastructure",
        price=146.80, market_cap=29_360_000_000, price_earnings_ratio=61.2, earnings_per_share=2.4,
        book_value_per_share=12.5, revenue_per_share=18.9, profit_margin=.122, operating_margin=.171,
        return_on_equity=.184, return_on_assets=.066, debt_to_equity_ratio=.35, current_ratio=2.8,
        cash=3_200_000_000, debt=1_100_000_000, quarterly_revenue_growth=.38,
        quarterly_earnings_growth=.44, operating_cash_flow=2_050_000_000, levered_free_cash_flow=1_460_000_000,
        revenue=3_780_000_000, shares_outstanding=200_000_000),
    "IRON": _company("IRON", "Ironridge Logistics Group", sector="Industrials", industry="Integrated Freight & Logistics",
        price=31.10, market_cap=3_110_000_000, price_earnings_ratio=14.9, earnings_per_share=2.09,
        book_value_per_share=8.2, revenue_per_share=52.0, profit_margin=.074, operating_margin=.119,
        return_on_equity=.164, return_on_assets=.031, debt_to_equity_ratio=2.75, current_ratio=.88,
        cash=210_000_000, debt=3_400_000_000, quarterly_revenue_growth=.021,
        quarterly_earnings_growth=-.12, operating_cash_flow=510_000_000, levered_free_cash_flow=-80_000_000,
        revenue=5_200_000_000, shares_outstanding=100_000_000),
    "BURN": _company("BURN", "Ember Therapeutics", sector="Healthcare", industry="Biotechnology",
        price=9.40, market_cap=940_000_000, price_earnings_ratio=-4.2, earnings_per_share=-2.24,
        book_value_per_share=3.8, revenue_per_share=.9, profit_margin=-1.42, operating_margin=-1.65,
        return_on_equity=-.73, return_on_assets=-.39, debt_to_equity_ratio=.62, current_ratio=1.9,
        cash=380_000_000, debt=120_000_000, quarterly_revenue_growth=-.18,
        quarterly_earnings_growth=None, operating_cash_flow=-220_000_000, levered_free_cash_flow=-245_000_000,
        revenue=90_000_000, shares_outstanding=100_000_000),
    "PART": _company("PART", "Partial Data Works", sector="Communication Services", industry="Advertising Agencies",
        price=22.00, market_cap=1_100_000_000, price_earnings_ratio=None, earnings_per_share=None,
        profit_margin=.11, operating_margin=None, return_on_equity=None, return_on_assets=None,
        debt_to_equity_ratio=None, current_ratio=1.6, quarterly_revenue_growth=None,
        operating_cash_flow=90_000_000, levered_free_cash_flow=None, revenue=620_000_000),
    "FINX": _company("FINX", "Finex Community Bancorp", sector="Financial Services", industry="Banks—Regional",
        price=47.20, market_cap=4_720_000_000, price_earnings_ratio=11.8, earnings_per_share=4.0,
        book_value_per_share=36.2, revenue_per_share=14.8, profit_margin=.258, operating_margin=.31,
        return_on_equity=.132, return_on_assets=.014, debt_to_equity_ratio=1.8, current_ratio=None,
        cash=6_800_000_000, debt=9_300_000_000, quarterly_revenue_growth=.061,
        quarterly_earnings_growth=.043, operating_cash_flow=670_000_000, levered_free_cash_flow=520_000_000,
        revenue=1_480_000_000, shares_outstanding=100_000_000),
}


class MockStockDataProvider(StockDataProvider):
    async def get_stock(self, symbol: str) -> FinancialData:
        data = MOCK_COMPANIES.get(symbol.upper())
        if not data:
            raise StockNotFoundError(f"No illustrative fixture exists for '{symbol.upper()}'")
        return FinancialData.model_validate(deepcopy(data))

