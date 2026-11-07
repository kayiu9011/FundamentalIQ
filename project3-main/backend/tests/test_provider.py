import httpx
import pytest

from app.providers.base import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    StockNotFoundError,
)
from app.providers.financial_modeling_prep import (
    FinancialModelingPrepStockDataProvider,
    normalize_financial_modeling_prep,
)


def income_payload():
    return [
        {"date": "2025-03-31", "period": "Q1", "reportedCurrency": "USD", "revenue": 100,
         "netIncome": 20, "operatingIncome": 25, "weightedAverageShsOut": 10},
        {"date": "2024-12-31", "period": "Q4", "revenue": 90, "netIncome": 18,
         "operatingIncome": 22, "weightedAverageShsOut": 10},
        {"date": "2024-09-30", "period": "Q3", "revenue": 80, "netIncome": 16,
         "operatingIncome": 20, "weightedAverageShsOut": 10},
        {"date": "2024-06-30", "period": "Q2", "revenue": 70, "netIncome": 14,
         "operatingIncome": 18, "weightedAverageShsOut": 10},
        {"date": "2024-03-31", "period": "Q1", "revenue": 50, "netIncome": 10,
         "operatingIncome": 12, "weightedAverageShsOut": 10},
    ]


def balance_payload():
    return [
        {"date": "2025-03-31", "period": "Q1", "totalStockholdersEquity": 100,
         "totalAssets": 400, "totalDebt": 50, "totalCurrentAssets": 200,
         "totalCurrentLiabilities": 100, "cashAndCashEquivalents": 40},
        {"date": "2024-12-31", "period": "Q4", "totalStockholdersEquity": 95, "totalAssets": 390},
        {"date": "2024-09-30", "period": "Q3", "totalStockholdersEquity": 90, "totalAssets": 380},
        {"date": "2024-06-30", "period": "Q2", "totalStockholdersEquity": 85, "totalAssets": 370},
        {"date": "2024-03-31", "period": "Q1", "totalStockholdersEquity": 80, "totalAssets": 360},
    ]


def cash_payload():
    return [
        {"date": "2025-03-31", "netCashProvidedByOperatingActivities": 30, "freeCashFlow": 24},
        {"date": "2024-12-31", "netCashProvidedByOperatingActivities": 25, "freeCashFlow": 20},
        {"date": "2024-09-30", "netCashProvidedByOperatingActivities": 25, "freeCashFlow": 19},
        {"date": "2024-06-30", "netCashProvidedByOperatingActivities": 20, "freeCashFlow": 17},
    ]


def quote_payload():
    return [{"symbol": "ABC", "name": "ABC Corp", "price": 34, "marketCap": 340}]


def profile_payload():
    return [{"symbol": "ABC", "companyName": "ABC Corporation", "sector": "Technology",
             "industry": "Software", "exchange": "NASDAQ", "currency": "USD"}]


def normalize(balance=None, quote=None):
    return normalize_financial_modeling_prep(
        "ABC", income_payload(), balance if balance is not None else balance_payload(),
        cash_payload(), quote if quote is not None else quote_payload(), profile_payload(),
    )


def test_normalizes_and_calculates_statement_metrics():
    result = normalize()
    assert result.symbol == "ABC"
    assert result.long_name == "ABC Corporation"
    assert result.sector == "Technology"
    assert result.price == 34
    assert result.revenue == 340
    assert result.earnings_per_share == pytest.approx(6.8)
    assert result.price_earnings_ratio == pytest.approx(5)
    assert result.debt_to_equity_ratio == pytest.approx(.5)
    assert result.current_ratio == pytest.approx(2)
    assert result.quarterly_revenue_growth == pytest.approx(1)
    assert result.operating_cash_flow == 100
    assert result.levered_free_cash_flow == 80
    assert result.last_fiscal_year_end.isoformat() == "2024-12-31T00:00:00"
    assert result.raw_values["income_fiscal_date"] == "2025-03-31"


def test_missing_values_remain_none():
    balance = balance_payload()
    balance[0]["totalCurrentAssets"] = None
    result = normalize(balance=balance, quote=[])
    assert result.price is None
    assert result.current_ratio is None


def test_negative_equity_is_identified():
    balance = balance_payload()
    balance[0]["totalStockholdersEquity"] = -20
    assert normalize(balance=balance).negative_equity is True


def test_empty_statements_are_not_found():
    with pytest.raises(StockNotFoundError):
        normalize_financial_modeling_prep("ABC", [], [], [], [], [])


def provider_for(handler):
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://example.test/stable")
    return FinancialModelingPrepStockDataProvider("secret", "https://example.test/stable", client), client


@pytest.mark.asyncio
async def test_valid_provider_requests_required_endpoints_without_leaking_key():
    responses = {
        "/stable/income-statement": income_payload(),
        "/stable/balance-sheet-statement": balance_payload(),
        "/stable/cash-flow-statement": cash_payload(),
        "/stable/quote": quote_payload(),
        "/stable/profile": profile_payload(),
    }
    seen = []

    def handler(request):
        assert request.url.params["apikey"] == "secret"
        assert request.url.params["symbol"] == "ABC"
        seen.append(request.url.path)
        return httpx.Response(200, json=responses[request.url.path])

    provider, client = provider_for(handler)
    result = await provider.get_stock("ABC")
    assert result.symbol == "ABC"
    assert set(seen) == set(responses)
    assert "secret" not in str(result.raw_values)
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(("status", "error"), [
    (401, ProviderAuthenticationError),
    (403, ProviderAuthenticationError),
    (429, ProviderRateLimitError),
])
async def test_provider_http_status_errors(status, error):
    provider, client = provider_for(lambda _: httpx.Response(status, json={}))
    with pytest.raises(error):
        await provider.get_stock("ABC")
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_embedded_rate_limit_error():
    provider, client = provider_for(lambda _: httpx.Response(200, json={"Error Message": "Rate limit reached"}))
    with pytest.raises(ProviderRateLimitError):
        await provider.get_stock("ABC")
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_embedded_invalid_key_error():
    provider, client = provider_for(lambda _: httpx.Response(200, json={"Error Message": "Invalid API key"}))
    with pytest.raises(ProviderAuthenticationError):
        await provider.get_stock("ABC")
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_invalid_json():
    provider, client = provider_for(lambda _: httpx.Response(200, text="not json"))
    with pytest.raises(ProviderResponseError):
        await provider.get_stock("ABC")
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_timeout():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    provider, client = provider_for(handler)
    with pytest.raises(ProviderTimeoutError):
        await provider.get_stock("ABC")
    await client.aclose()
