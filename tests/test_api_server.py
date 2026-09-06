import pytest

from app.api.server import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "polyarb-engine"


def test_paper_endpoint(client):
    res = client.get("/api/paper")
    assert res.status_code == 200
    data = res.get_json()
    assert "current_balance_usdc" in data
    assert "roi_pct" in data


def test_dashboard_endpoint(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "PolyArb Terminal" in html
    assert "Negative Risk" in html
