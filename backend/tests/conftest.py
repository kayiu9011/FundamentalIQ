import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers.mock import MockStockDataProvider


@pytest.fixture
def client():
    app = create_app(Settings(data_provider_mode="mock", cache_ttl_seconds=0), MockStockDataProvider())
    with TestClient(app) as test_client:
        yield test_client

