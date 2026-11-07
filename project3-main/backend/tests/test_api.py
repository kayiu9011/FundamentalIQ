from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["provider_mode"] == "mock"


def test_config_never_exposes_key(client):
    body = client.get("/api/config/status").json()
    assert body == {"provider_mode": "mock", "live_provider_ready": False, "cache_ttl_seconds": 0}


def test_stock_lookup(client):
    response = client.get("/api/stocks/NOVA")
    assert response.status_code == 200
    assert response.json()["is_mock"] is True


def test_default_screen(client):
    body = client.get("/api/stocks/NOVA/screen").json()
    assert body["screening"]["score"] == 100
    assert len(body["screening"]["metrics"]) == 10


def test_custom_screen(client):
    rules = client.get("/api/screening/criteria").json()["ruleset"]
    rules["thresholds"]["return_on_equity_min"] = .5
    response = client.post("/api/stocks/NOVA/screen", json=rules)
    assert response.status_code == 200
    roe = next(m for m in response.json()["screening"]["metrics"] if m["key"] == "return_on_equity")
    assert roe["status"] == "FAIL"


def test_invalid_custom_threshold(client):
    rules = client.get("/api/screening/criteria").json()["ruleset"]
    rules["thresholds"]["current_ratio_min"] = -1
    response = client.post("/api/stocks/NOVA/screen", json=rules)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_invalid_ticker(client):
    response = client.get("/api/stocks/%24BAD")
    assert response.status_code == 422


def test_not_found(client):
    response = client.get("/api/stocks/ZZZZ")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "stock_not_found"


def test_mock_mode_needs_no_key(client):
    assert client.get("/api/stocks/SKYH").status_code == 200


def test_live_mode_without_key_has_clear_error():
    app = create_app(Settings(data_provider_mode="fmp", fmp_api_key=""))
    with TestClient(app) as client:
        response = client.get("/api/stocks/AAPL")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "provider_not_configured"
