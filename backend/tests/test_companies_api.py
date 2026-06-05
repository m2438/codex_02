from fastapi.testclient import TestClient

from app.main import app


def test_companies_list_response_format() -> None:
    with TestClient(app) as client:
        response = client.get("/api/companies")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 20
    assert len(payload["items"]) == 20

    first_company = payload["items"][0]
    assert {
        "company_id",
        "name",
        "industry",
        "total_score",
        "priority_label",
        "signal_count",
    }.issubset(first_company)
    assert first_company["signal_count"] >= 1
    assert first_company["priority_label"] in {"高", "中", "低"}


def test_company_signals_include_evidence_and_source_reference() -> None:
    with TestClient(app) as client:
        response = client.get("/api/companies/1/signals")

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_id"] == 1
    assert payload["total"] >= 1
    for signal in payload["items"]:
        assert signal["evidence_text"]
        assert signal["source_reference"]
        assert signal["confidence"] in {"high", "medium", "low"}
