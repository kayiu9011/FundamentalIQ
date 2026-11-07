import pytest
from pydantic import ValidationError

from app.models.financial import FinancialData
from app.schemas.screening import CategoryWeights, ScreeningRuleset, Thresholds
from app.screening.engine import screen_financials


def stock(**overrides):
    values = dict(symbol="TEST", source="test", return_on_equity=.2, return_on_assets=.08,
        profit_margin=.15, operating_margin=.2, price_earnings_ratio=18, debt_to_equity_ratio=.5,
        current_ratio=2, quarterly_revenue_growth=.1, operating_cash_flow=100, levered_free_cash_flow=50)
    values.update(overrides)
    return FinancialData(**values)


def test_all_checks_passing_and_score():
    result = screen_financials(stock(), ScreeningRuleset())
    assert result.score == 100
    assert result.data_coverage == 100
    assert result.passing_checks == 10
    assert result.classification == "Strong initial fundamentals"


def test_all_checks_failing():
    result = screen_financials(stock(return_on_equity=-.2, return_on_assets=-.1, profit_margin=-.2,
        operating_margin=-.1, price_earnings_ratio=40, debt_to_equity_ratio=3, current_ratio=.4,
        quarterly_revenue_growth=-.2, operating_cash_flow=-1, levered_free_cash_flow=-1), ScreeningRuleset())
    assert result.score == 0
    assert result.failing_checks == 10
    assert result.classification == "Multiple financial concerns"


def test_mixed_score_is_weighted_correctly():
    result = screen_financials(stock(return_on_equity=.1, price_earnings_ratio=30, current_ratio=1), ScreeningRuleset())
    # Failed weights: ROE 7.5, P/E 20, current ratio 10.
    assert result.score == 62.5
    assert result.passing_checks == 7


def test_missing_metrics_excluded_and_insufficient_coverage():
    sparse = stock(return_on_equity=None, return_on_assets=None, profit_margin=None, operating_margin=None,
        price_earnings_ratio=None, debt_to_equity_ratio=None, quarterly_revenue_growth=None,
        levered_free_cash_flow=None)
    result = screen_financials(sparse, ScreeningRuleset())
    assert result.unavailable_checks == 8
    assert result.data_coverage == 17.5
    assert result.classification == "Insufficient Data"


@pytest.mark.parametrize("pe", [0, -12])
def test_zero_or_negative_pe_fails_not_cheap(pe):
    metric = next(m for m in screen_financials(stock(price_earnings_ratio=pe), ScreeningRuleset()).metrics if m.key == "price_earnings_ratio")
    assert metric.status == "FAIL"
    assert "not treated as a cheap" in metric.explanation


def test_negative_equity_makes_debt_equity_unavailable():
    metric = next(m for m in screen_financials(stock(debt_to_equity_ratio=-2, negative_equity=True), ScreeningRuleset()).metrics if m.key == "debt_to_equity_ratio")
    assert metric.status == "N/A"
    assert "negative equity" in metric.explanation


def test_financial_sector_excludes_structural_checks():
    result = screen_financials(stock(sector="Financial Services", industry="Banks—Regional"), ScreeningRuleset())
    statuses = {m.key: m.status for m in result.metrics}
    assert statuses["debt_to_equity_ratio"] == statuses["current_ratio"] == "N/A"
    assert result.applicability_warnings


def test_custom_threshold_changes_result():
    rules = ScreeningRuleset(thresholds=Thresholds(return_on_equity_min=.25))
    result = screen_financials(stock(return_on_equity=.2), rules)
    assert next(m for m in result.metrics if m.key == "return_on_equity").status == "FAIL"


def test_weights_must_total_one_hundred():
    with pytest.raises(ValidationError):
        CategoryWeights(profitability=25)


def test_high_roe_and_leverage_caution():
    metric = next(m for m in screen_financials(stock(return_on_equity=.3, debt_to_equity_ratio=2), ScreeningRuleset()).metrics if m.key == "return_on_equity")
    assert "leverage" in metric.explanation.lower()

