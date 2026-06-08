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


def test_compact_dashboard_header_removes_redundant_status_copy() -> None:
    page = read("frontend/src/app/page.tsx")
    assert "dashboard-toolbar" in page
    assert "日本国内の上場企業について、日本語の公開IR資料に基づくCRE営業仮説、スコアリング理由、根拠資料を確認する営業支援ダッシュボードです。" not in page
    assert "公開情報ベース分析" not in page
    assert "バックエンド:" not in page
    assert "hero-status" not in page


def test_rank_table_does_not_show_data_source() -> None:
    rank_table = read("frontend/src/components/CompanyRankTable.tsx")
    assert "データ種別" not in rank_table
    assert "data-source-badge" not in rank_table
    assert "dataSourceLabel" not in rank_table


def test_financial_metrics_ui_uses_new_label_and_visible_scale() -> None:
    detail = read("frontend/src/components/CompanyDetail.tsx")
    assert "財務関連指標" in detail
    assert "最新財務メトリクス" not in detail
    assert "metric-gauge__tick--middle" in detail
    assert "midpointLabel" in detail
    assert "公式IR資料を参照し、CREデモ用のスコアリング入力として百万円単位に正規化した概算値です" not in detail


def test_report_ui_uses_structured_report_instead_of_preview_or_raw_markdown() -> None:
    detail = read("frontend/src/components/CompanyDetail.tsx")
    assert "report.preview" not in detail
    assert "markdown-report" not in detail
    assert "report.markdown_content" not in detail
    assert "score-detail-table" in detail
    assert "renderInlineMarkdown" in detail


def test_score_panel_removes_recommended_action_and_long_reason() -> None:
    score_breakdown = read("frontend/src/components/ScoreBreakdown.tsx")
    assert "score-bar__reason" not in score_breakdown
    assert "確認しました" not in score_breakdown
    assert "推奨アクション" not in score_breakdown
    assert "recommended_action" not in score_breakdown
    assert "score.explanation" not in score_breakdown


def test_documents_panel_is_last_and_omits_source_note() -> None:
    detail = read("frontend/src/components/CompanyDetail.tsx")
    assert detail.rfind('className="panel documents-panel"') > detail.rfind('className="panel report-panel"')
    assert detail.rfind('className="panel documents-panel"') > detail.rfind("CREシグナル")
    assert "document.source_note" not in detail


def test_caveats_section_uses_compact_caution_class() -> None:
    detail = read("frontend/src/components/CompanyDetail.tsx")
    css = read("frontend/src/app/globals.css")
    assert "section.id === 'caveats'" in detail
    assert "report-section--caution" in css
    assert ".report-section--caution li" in css
    assert "font-size: 11px" in css


def test_phase4b_panel_copy_removed_and_operation_panel_label_used() -> None:
    panel = read("frontend/src/components/IRPipelinePanel.tsx")
    assert "Phase 4B 操作パネル" not in panel
    assert "<h3>操作パネル</h3>" in panel
    assert "公開情報に基づく営業仮説生成用です。企業IRサイト全体のクロールは行いません。" not in panel


def test_detail_notice_card_and_report_disclaimer_are_not_rendered_at_top() -> None:
    detail = read("frontend/src/components/CompanyDetail.tsx")
    assert "公開情報ベースの営業仮説に関する注意" not in detail
    assert "structuredReport.disclaimer" not in detail
    assert "本分析は公開情報に基づく営業仮説であり、当該企業の正式なCRE方針や実際の提案機会を断定するものではありません。" not in detail


def test_report_meta_uses_compact_inline_structure() -> None:
    detail = read("frontend/src/components/CompanyDetail.tsx")
    css = read("frontend/src/app/globals.css")
    assert "report-meta-line" in detail
    assert "report-meta-card" not in detail
    assert ".report-meta-line" in css
    assert "font-size: 12px" in css


def test_button_actions_refetch_company_detail_and_report_after_completion() -> None:
    detail = read("frontend/src/components/CompanyDetail.tsx")
    panel = read("frontend/src/components/IRPipelinePanel.tsx")
    assert "getCompanyDetail(companyId)" in detail
    assert "getCompanyReport(companyId)" in detail
    assert "onRefresh?.()" in panel
    assert "finally" in panel


def test_edinet_button_removed_and_edinet_docid_shown_without_url_link() -> None:
    panel = read("frontend/src/components/IRPipelinePanel.tsx")
    detail = read("frontend/src/components/CompanyDetail.tsx")
    assert "EDINET取得" not in panel
    assert "postEdinetFetch" not in panel
    assert "document.source_url?.startsWith('http')" in detail
    assert "EDINET docID" in detail
