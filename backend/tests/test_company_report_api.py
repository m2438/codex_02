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
    assert payload["generated_by"] == "phase4a_report_service"
    assert payload["signal_count"] >= 1
    assert payload["preview"]
    assert payload["markdown_content"].startswith("# ")
    assert "## 1. エグゼクティブサマリー" in payload["markdown_content"]
    assert "## 3. スコア内訳と評点理由" in payload["markdown_content"]
    assert "## 9. 追加ヒアリングで確認すべき事項" in payload["markdown_content"]
    assert "## 10. 根拠資料・根拠文" in payload["markdown_content"]
    assert "## 11. 留意事項" in payload["markdown_content"]


def test_company_report_api_returns_404_for_unknown_company() -> None:
    with TestClient(app) as client:
        response = client.get("/api/companies/9999/report")

    assert response.status_code == 404


def test_public_demo_company_report_includes_public_information_caveat() -> None:
    with TestClient(app) as client:
        companies_response = client.get("/api/companies")
        public_company = next(item for item in companies_response.json()["items"] if item["data_source_type"] == "public_demo")
        response = client.get(f"/api/companies/{public_company['company_id']}/report")

    assert response.status_code == 200
    payload = response.json()
    assert payload["generation_status"] == "generated"
    assert payload["preview"]
    assert payload["markdown_content"]
    assert "公開情報に基づく営業仮説" in payload["markdown_content"]
    assert "正式なCRE方針や実際の提案機会を断定" in payload["markdown_content"]
    assert "URL: https://" in payload["markdown_content"]
    assert "追加検証" in payload["markdown_content"] or "追加確認" in payload["markdown_content"]
