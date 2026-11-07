from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.financial import FinancialData


class Thresholds(BaseModel):
    return_on_equity_min: float = Field(.15, ge=-10, le=10)
    return_on_assets_min: float = Field(.05, ge=-10, le=10)
    profit_margin_min: float = Field(.10, ge=-10, le=10)
    operating_margin_min: float = Field(.15, ge=-10, le=10)
    price_earnings_min_exclusive: float = Field(0, ge=-1000, le=1000)
    price_earnings_max: float = Field(25, gt=0, le=10000)
    debt_to_equity_max: float = Field(1, ge=0, le=1000)
    current_ratio_min: float = Field(1.5, ge=0, le=1000)
    quarterly_revenue_growth_min_exclusive: float = Field(0, ge=-10, le=10)
    operating_cash_flow_min_exclusive: float = Field(0, ge=-1e18, le=1e18)
    levered_free_cash_flow_min_exclusive: float = Field(0, ge=-1e18, le=1e18)

    @model_validator(mode="after")
    def validate_pe_range(self) -> "Thresholds":
        if self.price_earnings_max <= self.price_earnings_min_exclusive:
            raise ValueError("P/E maximum must exceed the exclusive minimum")
        return self


class CategoryWeights(BaseModel):
    profitability: float = Field(30, gt=0, le=100)
    valuation: float = Field(20, gt=0, le=100)
    financial_stability: float = Field(20, gt=0, le=100)
    growth: float = Field(15, gt=0, le=100)
    cash_flow: float = Field(15, gt=0, le=100)

    @model_validator(mode="after")
    def totals_one_hundred(self) -> "CategoryWeights":
        if abs(sum(self.model_dump().values()) - 100) > .001:
            raise ValueError("Category weights must total 100")
        return self


class ScreeningRuleset(BaseModel):
    thresholds: Thresholds = Field(default_factory=Thresholds)
    category_weights: CategoryWeights = Field(default_factory=CategoryWeights)
    minimum_data_coverage: float = Field(60, ge=0, le=100)


class MetricResult(BaseModel):
    key: str
    category: str
    metric_name: str
    actual_value: float | None
    unit: str
    threshold: str
    status: Literal["PASS", "FAIL", "N/A"]
    weight: float
    earned_points: float
    explanation: str
    measures: str
    investor_relevance: str
    limitations: str


class ScreeningResult(BaseModel):
    score: float | None
    classification: str
    data_coverage: float
    passing_checks: int
    failing_checks: int
    unavailable_checks: int
    metrics: list[MetricResult]
    strengths: list[str]
    concerns: list[str]
    overall_assessment: str
    applicability_warnings: list[str]
    ruleset: ScreeningRuleset


class StockScreenResponse(BaseModel):
    company: FinancialData
    screening: ScreeningResult

