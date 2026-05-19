from fastapi.testclient import TestClient
from app.main import app

def test_analyze():
    with TestClient(app) as client:
        response = client.post(
            "/analyze",
            json={
                "code": "def foo(x):\n    return x * 2",
                "analysis_mode": "static",
                "llm_provider": "none"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "static_result" in data["result"]
        assert "risk_level" in data["result"]["static_result"]["risk_analysis"]