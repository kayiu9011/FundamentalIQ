from dataclasses import dataclass

from app.schemas.screening import ScreeningRuleset


@dataclass(frozen=True)
class Criterion:
    key: str
    category: str
    name: str
    unit: str
    comparator: str
    threshold_key: str
    measures: str
    relevance: str
    limitations: str


CRITERIA = (
    Criterion("return_on_equity", "profitability", "Return on Equity", "percent", "gte", "return_on_equity_min",
        "Profit earned relative to accounting shareholders’ equity.", "Shows how effectively equity capital supports earnings.", "Can be inflated by leverage, buybacks, or a small equity base."),
    Criterion("return_on_assets", "profitability", "Return on Assets", "percent", "gte", "return_on_assets_min",
        "Profit earned relative to the asset base.", "Offers a broad view of asset efficiency.", "Asset intensity and accounting conventions vary substantially by industry."),
    Criterion("profit_margin", "profitability", "Net Profit Margin", "percent", "gte", "profit_margin_min",
        "Net income as a share of revenue.", "Indicates how much revenue remains after all reported expenses.", "One-off items and industry economics can distort comparisons."),
    Criterion("operating_margin", "profitability", "Operating Margin", "percent", "gte", "operating_margin_min",
        "Operating income as a share of revenue.", "Highlights profitability from core operations before financing and taxes.", "Definitions and typical levels differ across industries."),
    Criterion("price_earnings_ratio", "valuation", "Price / Earnings Ratio", "ratio", "pe_range", "price_earnings_max",
        "Market price relative to trailing earnings per share.", "Provides one limited view of how the market prices current earnings.", "P/E alone cannot establish undervaluation and is not meaningful with negative earnings."),
    Criterion("debt_to_equity_ratio", "financial_stability", "Debt to Equity", "ratio", "lte", "debt_to_equity_max",
        "Debt relative to accounting shareholders’ equity.", "Helps assess balance-sheet leverage and financing risk.", "Negative equity makes the ratio non-comparable; financial firms use leverage differently."),
    Criterion("current_ratio", "financial_stability", "Current Ratio", "ratio", "gte", "current_ratio_min",
        "Current assets relative to current liabilities.", "Indicates short-term balance-sheet liquidity.", "A high ratio is not always efficient, and it is structurally unsuitable for many financial firms."),
    Criterion("quarterly_revenue_growth", "growth", "Quarterly Revenue Growth", "percent", "gt", "quarterly_revenue_growth_min_exclusive",
        "Provider-reported quarterly revenue growth.", "Positive growth can indicate expanding recent sales activity.", "A single quarterly rate may be volatile, seasonal, or acquisition-driven."),
    Criterion("operating_cash_flow", "cash_flow", "Operating Cash Flow", "currency", "gt", "operating_cash_flow_min_exclusive",
        "Cash generated or used by operating activities.", "Positive operating cash flow supports internal funding capacity.", "Working-capital timing can materially affect a single period."),
    Criterion("levered_free_cash_flow", "cash_flow", "Levered Free Cash Flow", "currency", "gt", "levered_free_cash_flow_min_exclusive",
        "Cash flow remaining after operating needs, capital spending, and debt-related obligations.", "Positive levered free cash flow can support flexibility after financing obligations.", "Provider methodology may differ; it is not unlevered free cash flow."),
)


def default_ruleset(minimum_coverage: float = 60) -> ScreeningRuleset:
    return ScreeningRuleset(minimum_data_coverage=minimum_coverage)


def criteria_catalog(ruleset: ScreeningRuleset) -> dict[str, object]:
    return {
        "ruleset": ruleset.model_dump(),
        "criteria": [{"key": c.key, "category": c.category, "name": c.name, "unit": c.unit,
            "measures": c.measures, "investor_relevance": c.relevance, "limitations": c.limitations}
            for c in CRITERIA],
        "applicability_notes": [
            "Thresholds are simplified heuristics and may not suit every sector, industry, business model, or stage of development.",
            "Financial institutions may require specialized liquidity and leverage measures.",
            "Results are educational screening classifications, not forecasts or buy/sell recommendations."
        ],
    }
