import re

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import Settings
from app.models.financial import FinancialData
from app.schemas.screening import ScreeningRuleset, StockScreenResponse
from app.screening.criteria import criteria_catalog, default_ruleset
from app.screening.engine import screen_financials
from app.services.stock_service import StockService

router = APIRouter(prefix="/api")
SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")


def stock_service(request: Request) -> StockService:
    service = getattr(request.app.state, "stock_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail={"code": "provider_not_configured", "message": "Financial Modeling Prep mode requires FMP_API_KEY"})
    return service


def settings(request: Request) -> Settings:
    return request.app.state.settings


def valid_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not SYMBOL_PATTERN.fullmatch(normalized):
        raise HTTPException(status_code=422, detail={"code": "invalid_symbol", "message": "Ticker must be 1–10 letters, numbers, periods, or hyphens and begin with a letter"})
    return normalized


@router.get("/health")
async def health(config: Settings = Depends(settings)) -> dict[str, object]:
    return {"status": "ok", "application": config.app_name, "provider_mode": config.data_provider_mode}


@router.get("/config/status")
async def config_status(config: Settings = Depends(settings)) -> dict[str, object]:
    return {"provider_mode": config.data_provider_mode, "live_provider_ready": config.live_ready,
        "cache_ttl_seconds": config.cache_ttl_seconds}


@router.get("/stocks/{symbol}", response_model=FinancialData)
async def get_stock(symbol: str, service: StockService = Depends(stock_service)) -> FinancialData:
    return await service.get_stock(valid_symbol(symbol))


@router.get("/stocks/{symbol}/screen", response_model=StockScreenResponse)
async def screen_stock(symbol: str, service: StockService = Depends(stock_service),
        config: Settings = Depends(settings)) -> StockScreenResponse:
    company = await service.get_stock(valid_symbol(symbol))
    rules = default_ruleset(config.minimum_data_coverage)
    return StockScreenResponse(company=company, screening=screen_financials(company, rules))


@router.post("/stocks/{symbol}/screen", response_model=StockScreenResponse)
async def custom_screen_stock(symbol: str, rules: ScreeningRuleset,
        service: StockService = Depends(stock_service)) -> StockScreenResponse:
    company = await service.get_stock(valid_symbol(symbol))
    return StockScreenResponse(company=company, screening=screen_financials(company, rules))


@router.get("/screening/criteria")
async def screening_criteria(config: Settings = Depends(settings)) -> dict[str, object]:
    return criteria_catalog(default_ruleset(config.minimum_data_coverage))

