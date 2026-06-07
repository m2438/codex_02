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


def test_seed_companies_use_demo_names_and_multiple_high_priority_candidates() -> None:
    with TestClient(app) as client:
        response = client.get("/api/companies")

    assert response.status_code == 200
    items = response.json()["items"]
    assert all(not item["name"].startswith("サンプル上場企業") for item in items)
    assert [item["name"] for item in items] == [
        "AAA株式会社", "BBB株式会社", "CCC株式会社", "DDD株式会社", "EEE株式会社",
        "FFF株式会社", "GGG株式会社", "HHH株式会社", "III株式会社", "JJJ株式会社",
        "KKK株式会社", "LLL株式会社", "MMM株式会社", "NNN株式会社", "OOO株式会社",
        "PPP株式会社", "QQQ株式会社", "RRR株式会社", "SSS株式会社", "TTT株式会社",
    ]
    priority_counts = {label: sum(1 for item in items if item["priority_label"] == label) for label in {"高", "中", "低"}}
    assert 4 <= priority_counts["高"] <= 6
    assert 8 <= priority_counts["中"] <= 10
