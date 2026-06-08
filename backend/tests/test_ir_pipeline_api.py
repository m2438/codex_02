from fastapi.testclient import TestClient

from app.main import app


def test_edinet_fetch_dry_run_response_format() -> None:
    with TestClient(app) as client:
        response = client.post("/api/companies/1/documents/fetch-edinet")

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_id"] == 1
    assert payload["status"] in {"dry_run", "skipped", "failed"}
    assert payload["pipeline"]["dry_run"] is True
    assert {"company_id", "company_name", "target_date", "document_type", "doc_id", "status", "error_message"}.issubset(payload["result"])


def test_manual_documents_fetch_dry_run_response_format_and_history() -> None:
    with TestClient(app) as client:
        response = client.post("/api/companies/1/documents/fetch")
        runs_response = client.get("/api/companies/1/fetch-runs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"dry_run", "skipped"}
    assert payload["pipeline"]["fetch_enabled"] is False or payload["pipeline"]["dry_run"] is True
    assert payload["results"]
    assert {"document_id", "target_url", "status", "error_message", "dry_run"}.issubset(payload["results"][0])

    assert runs_response.status_code == 200
    runs = runs_response.json()
    assert runs["total"] >= 1
    assert {"run_type", "status", "started_at", "completed_at", "dry_run"}.issubset(runs["items"][0])


def test_analyze_api_mock_mode_and_analysis_history() -> None:
    with TestClient(app) as client:
        response = client.post("/api/companies/1/analyze")
        runs_response = client.get("/api/companies/1/analysis-runs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pipeline"]["effective_analysis_mode"] in {"mock", "openai"}
    assert payload["status"] in {"success", "skipped"}
    assert "created_signal_count" in payload
    assert payload["results"]

    assert runs_response.status_code == 200
    runs = runs_response.json()
    assert runs["total"] >= 1
    assert runs["items"][0]["run_type"] in {"mock", "openai"}
    assert runs["items"][0]["analysis_input_source"] in {"extracted_pdf_text", "existing_db_text", "mock_seed_text"}


def test_documents_endpoint_includes_pipeline_status() -> None:
    with TestClient(app) as client:
        response = client.get("/api/companies/1/documents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_id"] == 1
    assert payload["items"]
    assert "pipeline" in payload
    assert "latest_fetch_at" in payload
    assert "fetched_file_path" in payload["items"][0]


def test_company_detail_includes_edinet_and_pipeline_status_without_breaking_report_api() -> None:
    with TestClient(app) as client:
        detail_response = client.get("/api/companies/1")
        report_response = client.get("/api/companies/1/report")

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["company"]["edinet_code"]
    assert detail["pipeline_status"]["config"]["effective_analysis_mode"] == "mock"

    assert report_response.status_code == 200
    report = report_response.json()
    assert report["generation_status"] == "generated"

from pathlib import Path

from app.models import Company
from app.services.edinet_client import EdinetClient
from app.services.ir_settings import IRPipelineSettings


def test_edinet_client_fails_safely_when_api_key_missing_after_enabled() -> None:
    settings = IRPipelineSettings(
        edinet_api_key="",
        openai_api_key="",
        fetch_enabled=True,
        analysis_mode="mock",
        dry_run=False,
        storage_dir=Path("/tmp/ir-fetch-test"),
        edinet_lookback_days=365,
    )
    company = Company(
        id=999,
        ticker="TEST",
        name="テスト株式会社",
        market="東証プライム",
        industry="テスト",
        headquarters_location="東京都",
        employee_count=1,
        revenue=1,
        fiscal_year="2025",
        edinet_code="E00000",
    )

    result = EdinetClient(settings).fetch_latest_securities_report(company)

    assert result.status == "failed"
    assert "EDINET_API_KEY" in (result.error_message or "")
