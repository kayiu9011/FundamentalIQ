from app.models.financial import FinancialData
from app.schemas.screening import MetricResult, ScreeningResult, ScreeningRuleset
from app.screening.criteria import CRITERIA


FINANCIAL_TERMS = ("financial", "bank", "insurance", "capital markets", "credit")


def _is_financial(data: FinancialData) -> bool:
    context = f"{data.sector or ''} {data.industry or ''}".lower()
    return any(term in context for term in FINANCIAL_TERMS)


def _threshold_text(key: str, comparator: str, value: float, rules: ScreeningRuleset) -> str:
    if key == "price_earnings_ratio":
        return f"> {rules.thresholds.price_earnings_min_exclusive:g} and ≤ {value:g}×"
    shown = value * 100 if key in {"return_on_equity", "return_on_assets", "profit_margin", "operating_margin", "quarterly_revenue_growth"} else value
    suffix = "%" if key in {"return_on_equity", "return_on_assets", "profit_margin", "operating_margin", "quarterly_revenue_growth"} else ""
    symbol = {"gte": "≥", "lte": "≤", "gt": ">"}[comparator]
    return f"{symbol} {shown:g}{suffix}"


def screen_financials(data: FinancialData, rules: ScreeningRuleset) -> ScreeningResult:
    """Score only available weighted checks; unavailable weight is excluded from score."""
    category_counts = {cat: sum(c.category == cat for c in CRITERIA) for cat in rules.category_weights.model_dump()}
    results: list[MetricResult] = []
    financial = _is_financial(data)
    warnings: list[str] = []
    if financial:
        warnings.append("Financial-sector accounting differs from ordinary operating companies; current ratio and debt-to-equity are excluded from this general-purpose screen.")
    for criterion in CRITERIA:
        weight = getattr(rules.category_weights, criterion.category) / category_counts[criterion.category]
        actual = getattr(data, criterion.key)
        threshold = getattr(rules.thresholds, criterion.threshold_key)
        status = "N/A"
        special = None
        if financial and criterion.key in {"debt_to_equity_ratio", "current_ratio"}:
            special = "This check is structurally inappropriate for many financial institutions and is excluded."
        elif criterion.key == "debt_to_equity_ratio" and data.negative_equity:
            special = "Debt-to-equity is not meaningfully comparable because the available context indicates negative equity."
        elif actual is None:
            special = "The provider did not supply this metric, so it is excluded from scoring."
        elif criterion.comparator == "pe_range":
            if actual <= rules.thresholds.price_earnings_min_exclusive:
                status, special = "FAIL", "Earnings are zero or negative, so the P/E is not treated as a cheap valuation signal."
            else:
                status = "PASS" if actual <= threshold else "FAIL"
        else:
            passed = {"gte": actual >= threshold, "lte": actual <= threshold, "gt": actual > threshold}[criterion.comparator]
            status = "PASS" if passed else "FAIL"
        if special:
            explanation = special
        elif status == "PASS":
            explanation = f"{criterion.name} meets the selected threshold. This is favorable within this simplified screen."
        else:
            explanation = f"{criterion.name} does not meet the selected threshold and warrants further investigation."
        if criterion.key == "return_on_equity" and status == "PASS" and data.debt_to_equity_ratio is not None and data.debt_to_equity_ratio > rules.thresholds.debt_to_equity_max:
            explanation += " High leverage may be contributing to the reported ROE."
        results.append(MetricResult(key=criterion.key, category=criterion.category, metric_name=criterion.name,
            actual_value=actual, unit=criterion.unit, threshold=_threshold_text(criterion.key, criterion.comparator, threshold, rules),
            status=status, weight=round(weight, 4), earned_points=round(weight if status == "PASS" else 0, 4),
            explanation=explanation, measures=criterion.measures, investor_relevance=criterion.relevance, limitations=criterion.limitations))
    available = sum(r.weight for r in results if r.status != "N/A")
    earned = sum(r.earned_points for r in results)
    coverage = round(available, 1)
    score = round(earned / available * 100, 1) if available else None
    passes = sum(r.status == "PASS" for r in results)
    failures = sum(r.status == "FAIL" for r in results)
    unavailable = sum(r.status == "N/A" for r in results)
    if coverage < rules.minimum_data_coverage or score is None:
        classification = "Insufficient Data"
        assessment = f"Only {coverage:.1f}% of weighted criteria are available, below the {rules.minimum_data_coverage:g}% minimum for a classification."
    elif score >= 80:
        classification = "Strong initial fundamentals"
        assessment = "Most available weighted checks pass this initial screen. Review company filings and context before drawing conclusions."
    elif score >= 60:
        classification = "Generally favorable, with areas to examine"
        assessment = "A majority of available weighted checks pass, with specific areas that merit closer review."
    elif score >= 40:
        classification = "Mixed fundamentals"
        assessment = "The available checks show a mixed profile; both favorable indicators and concerns require context."
    else:
        classification = "Multiple financial concerns"
        assessment = "Several available checks fall outside the selected thresholds and warrant deeper investigation."
    strengths = [r.explanation for r in results if r.status == "PASS"][:5]
    concerns = [r.explanation for r in results if r.status == "FAIL"][:5]
    if unavailable:
        concerns.append(f"{unavailable} check(s) lack usable or applicable data and were excluded from scoring.")
    return ScreeningResult(score=score, classification=classification, data_coverage=coverage,
        passing_checks=passes, failing_checks=failures, unavailable_checks=unavailable, metrics=results,
        strengths=strengths, concerns=concerns, overall_assessment=assessment,
        applicability_warnings=warnings, ruleset=rules)
