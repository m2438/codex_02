from fastapi.testclient import TestClient

from app.main import app


def test_companies_list_response_format() -> None:
    with TestClient(app) as client:
        response = client.get("/api/companies")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 30
    assert len(payload["items"]) == 30

    first_company = payload["items"][0]
    assert {
        "company_id",
        "name",
        "industry",
        "total_score",
        "priority_label",
        "signal_count",
        "data_source_type",
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
    items = [item for item in response.json()["items"] if item["data_source_type"] == "synthetic"]
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


def test_public_demo_companies_have_real_company_metadata_and_documents() -> None:
    with TestClient(app) as client:
        companies_response = client.get("/api/companies")

    assert companies_response.status_code == 200
    public_items = [item for item in companies_response.json()["items"] if item["data_source_type"] == "public_demo"]
    assert len(public_items) == 10
    assert all(item["ticker"] and item["market"] == "東証プライム" for item in public_items)

    with TestClient(app) as client:
        for item in public_items:
            detail_response = client.get(f"/api/companies/{item['company_id']}")
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["company"]["data_source_type"] == "public_demo"
            assert detail["company"]["listing_country"] == "日本"
            assert detail["company"]["is_public_company"] is True
            assert detail["company"]["selection_reason"]
            assert detail["documents"]
            for document in detail["documents"]:
                assert document["source_url"].startswith("https://")
                assert document["document_title"]
                assert document["document_type"]
                assert document["fiscal_year"]
                assert document["source_note"]
