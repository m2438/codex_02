from fastapi.testclient import TestClient

from app.main import app


def test_companies_list_response_format() -> None:
    with TestClient(app) as client:
        response = client.get("/api/companies")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 10
    assert len(payload["items"]) == 10

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


def test_seed_data_does_not_include_synthetic_companies() -> None:
    with TestClient(app) as client:
        response = client.get("/api/companies")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 10
    assert all(item["data_source_type"] == "public_demo" for item in items)
    assert all(not item["ticker"].startswith("S") for item in items)


def test_public_demo_companies_have_real_company_metadata_and_japanese_documents() -> None:
    with TestClient(app) as client:
        companies_response = client.get("/api/companies")

    assert companies_response.status_code == 200
    public_items = [item for item in companies_response.json()["items"] if item["data_source_type"] == "public_demo"]
    assert len(public_items) == 10
    assert all(item["ticker"] and item["market"] == "東証プライム" for item in public_items)

    non_securities_document_companies = 0
    with TestClient(app) as client:
        for item in public_items:
            detail_response = client.get(f"/api/companies/{item['company_id']}")
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["company"]["data_source_type"] == "public_demo"
            assert detail["company"]["listing_country"] == "日本"
            assert detail["company"]["is_public_company"] is True
            assert detail["company"]["selection_reason"]
            assert len(detail["documents"]) >= 2
            if any("有価証券報告書" not in document["document_type"] for document in detail["documents"]):
                non_securities_document_companies += 1
            for document in detail["documents"]:
                assert document["source_url"].startswith("https://")
                assert document["document_title"]
                assert document["document_type"]
                assert document["fiscal_year"]
                assert document["source_note"]
                assert document["document_language"] == "ja" or "日本語版URLは手動確認が必要" in document["source_note"]
    assert non_securities_document_companies >= 2
