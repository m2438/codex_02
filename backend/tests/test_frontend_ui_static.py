from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_dashboard_title_and_summary_cards_are_sales_bi_oriented() -> None:
    page = read("frontend/src/app/page.tsx")
    assert "<h1>CRE営業支援BI</h1>" in page
    assert "CRE Sales Intelligence Dashboard" not in page
    assert 'label="実在企業デモ"' not in page
    assert "publicDemoCount" not in page


def test_rank_table_does_not_show_data_source() -> None:
    rank_table = read("frontend/src/components/CompanyRankTable.tsx")
    assert "データ種別" not in rank_table
    assert "data-source-badge" not in rank_table
    assert "dataSourceLabel" not in rank_table


def test_report_ui_uses_structured_report_instead_of_preview_or_raw_markdown() -> None:
    detail = read("frontend/src/components/CompanyDetail.tsx")
    assert "report.preview" not in detail
    assert "markdown-report" not in detail
    assert "report.markdown_content" not in detail
    assert "score-detail-table" in detail
    assert "renderInlineMarkdown" in detail


def test_score_repeated_reason_text_is_not_rendered_in_score_panel() -> None:
    score_breakdown = read("frontend/src/components/ScoreBreakdown.tsx")
    assert "score-bar__reason" not in score_breakdown
    assert "確認しました" not in score_breakdown
