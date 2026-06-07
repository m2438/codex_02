from fastapi.testclient import TestClient

from app.main import app


def test_company_detail_response_format() -> None:
    with TestClient(app) as client:
        response = client.get("/api/companies/1")

    assert response.status_code == 200
    payload = response.json()

    assert payload["company"]["company_id"] == 1
    assert payload["company"]["name"]
    assert payload["latest_financial_metrics"]["fiscal_year"] == "2025"
    assert payload["cre_signals"]
    assert payload["documents"]

    score = payload["score_breakdown"]
    assert score["total_score"] == sum(score["component_scores"].values())
    assert score["priority_label"] in {"高", "中", "低"}
    assert set(score["component_scores"]) == {
        "signal_score",
        "financial_score",
        "strategic_event_score",
        "fit_score",
    }
    assert score["component_details"]["signal_score"]["max_points"] == 35
    assert score["component_details"]["financial_score"]["max_points"] == 25
    assert score["component_details"]["strategic_event_score"]["max_points"] == 25
    assert score["component_details"]["fit_score"]["max_points"] == 15
    assert score["component_details"]["signal_score"]["reason"]


def test_company_score_response_format() -> None:
    with TestClient(app) as client:
        response = client.get("/api/companies/1/score")

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_id"] == 1
    assert payload["total_score"] == sum(payload["component_scores"].values())
    assert payload["recommended_action"]
    assert payload["component_details"]["fit_score"]["max_points"] == 15
