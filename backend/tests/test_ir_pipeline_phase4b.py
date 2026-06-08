from __future__ import annotations

from datetime import date
from pathlib import Path

from app.models import Company, Document
from app.services.cre_document_analyzer import extract_rule_based
from app.services.edinet_client import EdinetClient
from app.services.ir_document_fetcher import choose_pdf_link, extract_pdf_links
from app.services.ir_settings import IRPipelineSettings


def settings(tmp_path: Path, *, fetch_enabled: bool = True, dry_run: bool = False) -> IRPipelineSettings:
    return IRPipelineSettings(
        edinet_api_key="dummy",
        openai_api_key="",
        fetch_enabled=fetch_enabled,
        analysis_mode="mock",
        dry_run=dry_run,
        storage_dir=tmp_path,
        edinet_lookback_days=365,
    )


def company() -> Company:
    return Company(id=1, ticker="TEST", name="テスト株式会社", market="東証", industry="製造", headquarters_location="東京", employee_count=1, revenue=1, fiscal_year="2025", edinet_code="E00000")


def document() -> Document:
    return Document(id=10, company_id=1, document_type="有価証券報告書", title="有価証券報告書 2025", source_url="https://example.com/ir/index.html", source_name="IR", fiscal_year="2025", text_content="", is_sample=False)


def test_edinet_uses_lookback_days_in_dry_run(tmp_path: Path) -> None:
    result = EdinetClient(settings(tmp_path, dry_run=True)).fetch_latest_securities_report(company(), target_date=date(2026, 6, 8), lookback_days=30)
    assert result.search_start_date == "2026-05-10"
    assert result.search_end_date == "2026-06-08"
    assert result.lookback_days == 30
    assert "lookback_days=30" in (result.error_message or "")


def test_edinet_docid_not_found_error_contains_search_period(monkeypatch, tmp_path: Path) -> None:
    client = EdinetClient(settings(tmp_path))
    monkeypatch.setattr(client, "_find_latest_document", lambda *args, **kwargs: None)
    result = client.fetch_latest_securities_report(company(), target_date=date(2026, 6, 8), lookback_days=7)
    assert result.status == "skipped"
    assert "2026-06-02〜2026-06-08" in (result.error_message or "")
    assert "EDINETコード=E00000" in (result.error_message or "")
    assert "検索日数=7" in (result.error_message or "")


def test_extract_pdf_links_from_html_and_resolve_relative_url() -> None:
    html = '<html><body><a href="../pdf/securities_2025.pdf">有価証券報告書 2025</a></body></html>'
    links = extract_pdf_links(html, "https://example.com/ir/library/index.html")
    assert links == [{"url": "https://example.com/ir/pdf/securities_2025.pdf", "text": "有価証券報告書 2025", "href": "../pdf/securities_2025.pdf"}]


def test_choose_pdf_link_prefers_document_type_and_fiscal_year() -> None:
    candidates = [
        {"url": "https://example.com/a/annual_2024.pdf", "text": "Annual Report 2024", "href": "annual_2024.pdf"},
        {"url": "https://example.com/a/securities_2025.pdf", "text": "有価証券報告書 2025", "href": "securities_2025.pdf"},
    ]
    assert choose_pdf_link(candidates, document()) == "https://example.com/a/securities_2025.pdf"


def test_rule_based_evidence_ignores_meta_policy_text() -> None:
    doc = document()
    doc.text_content = "CRE観点では拠点再編、工場を確認対象とする。\n新工場への設備投資を進めます。"
    signals = extract_rule_based(doc)
    assert signals
    assert all("CRE観点" not in item.evidence_text for item in signals)
