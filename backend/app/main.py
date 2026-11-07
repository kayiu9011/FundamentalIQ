import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.api import router
from app.core.config import Settings, get_settings
from app.providers.base import ProviderError, StockDataProvider
from app.providers.financial_modeling_prep import FinancialModelingPrepStockDataProvider
from app.providers.mock import MockStockDataProvider
from app.services.stock_service import StockService

logger = logging.getLogger("fundamentaliq")


def create_app(config: Settings | None = None, provider: StockDataProvider | None = None) -> FastAPI:
    chosen = config or get_settings()
    service: StockService | None = None
    if provider is not None:
        service = StockService(provider, chosen.cache_ttl_seconds)
    elif chosen.data_provider_mode == "mock":
        service = StockService(MockStockDataProvider(), chosen.cache_ttl_seconds)
    elif chosen.live_ready:
        service = StockService(FinancialModelingPrepStockDataProvider(
            chosen.fmp_api_key,
            chosen.fmp_base_url,
        ), chosen.cache_ttl_seconds)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        if service:
            await service.close()

    app = FastAPI(title="FundamentalIQ API", version="0.1.0", lifespan=lifespan)
    app.state.settings = chosen
    app.state.stock_service = service
    app.include_router(router)

    @app.exception_handler(ProviderError)
    async def provider_exception(_: Request, exc: ProviderError) -> JSONResponse:
        logger.warning("Provider error: %s", exc.code)
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": str(exc)}})

    @app.exception_handler(RequestValidationError)
    async def validation_exception(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"field": ".".join(str(p) for p in item["loc"] if p != "body"), "message": item["msg"]} for item in exc.errors()]
        return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Request validation failed", "details": details}})

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        async def index() -> FileResponse:
            return FileResponse(frontend_dist / "index.html")
    else:
        @app.get("/", include_in_schema=False)
        async def no_frontend() -> JSONResponse:
            return JSONResponse({"message": "Build the frontend with npm run build in frontend/", "docs": "/docs"})
    return app


app = create_app()
