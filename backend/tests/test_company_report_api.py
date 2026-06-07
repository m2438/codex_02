from fastapi.testclient import TestClient

from app.main import app


def test_company_report_api_response_format() -> None:
    with TestClient(app) as client:
        response = client.get("/api/companies/1/report")

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_id"] == 1
    assert payload["title"]
    assert payload["generation_status"] == "generated"
    assert payload["generated_at"]
    assert payload["generated_by"] == "phase3_report_service"
    assert payload["signal_count"] >= 1
    assert payload["preview"]
    assert payload["markdown_content"].startswith("# ")
    assert "## Executive summary" in payload["markdown_content"]
    assert "## Evidence and source documents" in payload["markdown_content"]
    assert "## Caveats" in payload["markdown_content"]


def test_company_report_api_returns_404_for_unknown_company() -> None:
    with TestClient(app) as client:
        response = client.get("/api/companies/9999/report")

    assert response.status_code == 404
