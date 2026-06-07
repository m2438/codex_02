from datetime import UTC, date, datetime

from app.models import CRESignal, Company, Document, FinancialMetric, Score
from app.services.reporting import generate_company_report


def test_generate_company_report_includes_required_japanese_markdown_sections() -> None:
    company = Company(
        id=1,
        ticker="9001",
        name="AAA株式会社",
        market="東証プライム",
        industry="電気機器",
        headquarters_location="東京都千代田区",
        employee_count=5000,
        revenue=1_200_000,
        fiscal_year="2025",
    )
    document = Document(
        id=11,
        company_id=1,
        document_type="統合報告書",
        title="2025年3月期 統合報告書（サンプル）",
        source_name="サンプルIR文書",
        published_date=date(2025, 6, 1),
        fiscal_year="2025",
        text_content="主要拠点での設備更新と能力増強を進めます。",
        is_sample=True,
    )
    signal = CRESignal(
        id=21,
        company_id=1,
        document_id=11,
        signal_type="設備投資",
        title="成長領域への設備投資",
        description="設備投資に関する記述があり、CRE戦略の営業仮説につながります。",
        evidence_text="主要拠点での設備更新と能力増強を進めます。",
        source_reference="2025年3月期 統合報告書（サンプル） / サンプル本文",
        confidence="high",
        confidence_reason="明示的な記述があるため。",
        extracted_by="seed_mock",
    )
    metric = FinancialMetric(
        id=31,
        company_id=1,
        fiscal_year="2025",
        revenue_growth_pct=8.2,
        operating_margin_pct=11.0,
        capex_amount=140_000,
        cash_and_equivalents=220_000,
        segment_change_note="成長投資を進めるサンプル設定です。",
        source_document_id=11,
    )
    score = Score(
        id=41,
        company_id=1,
        total_score=82,
        priority_label="高",
        signal_score=30,
        financial_score=25,
        strategic_event_score=12,
        fit_score=15,
        explanation="設備投資を根拠に高優先度と判定しました。",
        recommended_action="設備投資計画とCRE戦略の整合性を確認する。",
        calculated_at=datetime.now(UTC),
    )
    company.documents = [document]
    company.cre_signals = [signal]
    company.financial_metrics = [metric]
    company.scores = [score]

    report = generate_company_report(company=company, latest_metric=metric, latest_score=score)

    assert report.generation_status == "generated"
    assert report.signal_count == 1
    assert "# AAA株式会社 CRE営業仮説レポート" in report.markdown_content
    for heading in [
        "## 1. エグゼクティブサマリー",
        "## 2. CRE営業優先度の判定",
        "## 3. スコア内訳と評点理由",
        "## 4. CRE需要兆候の詳細分析",
        "## 5. 財務・投資余力に関する所見",
        "## 6. 経営課題・中期施策との接続仮説",
        "## 7. 想定されるCRE提案テーマ",
        "## 8. 初回アプローチ仮説",
        "## 9. 追加ヒアリングで確認すべき事項",
        "## 10. 根拠資料・根拠文",
        "## 11. 留意事項",
    ]:
        assert heading in report.markdown_content
    assert "主要拠点での設備更新と能力増強を進めます。" in report.markdown_content
    assert "PM/CM" in report.markdown_content
    assert "追加検証" in report.markdown_content
    assert "1.2兆円" in report.markdown_content


def _build_report_with_metric(metric: FinancialMetric) -> str:
    company = Company(
        id=2,
        ticker="9999",
        name="財務テスト株式会社",
        market="東証プライム",
        industry="テスト業",
        headquarters_location="東京都千代田区",
        employee_count=1000,
        revenue=900_000,
        fiscal_year=metric.fiscal_year,
    )
    score = Score(
        id=50 + metric.id,
        company_id=2,
        total_score=60,
        priority_label="中",
        signal_score=20,
        financial_score=15,
        strategic_event_score=15,
        fit_score=10,
        explanation="テスト用の評点理由です。",
        recommended_action="テスト用の推奨アクションです。",
        calculated_at=datetime.now(UTC),
    )
    company.documents = []
    company.cre_signals = []
    company.financial_metrics = [metric]
    company.scores = [score]
    return generate_company_report(company=company, latest_metric=metric, latest_score=score).markdown_content


def test_priority_section_omits_overall_reason_label() -> None:
    metric = FinancialMetric(
        id=1,
        company_id=2,
        fiscal_year="2025",
        revenue_growth_pct=3.0,
        operating_margin_pct=8.0,
        capex_amount=150_000,
        cash_and_equivalents=400_000,
        segment_change_note="テスト",
    )
    markdown = _build_report_with_metric(metric)
    priority_section = markdown.split("## 2. CRE営業優先度の判定", 1)[1].split("## 3.", 1)[0]
    assert "全体評点理由" not in priority_section
    assert "テスト用の評点理由" not in priority_section
    assert "公開情報に基づく営業仮説" in priority_section


def test_financial_section_omits_old_fixed_note_and_changes_by_metrics() -> None:
    high_metric = FinancialMetric(
        id=2,
        company_id=2,
        fiscal_year="2025",
        revenue_growth_pct=8.0,
        operating_margin_pct=15.0,
        capex_amount=400_000,
        cash_and_equivalents=1_500_000,
        segment_change_note="旧注釈ではない高成長設定",
    )
    low_metric = FinancialMetric(
        id=3,
        company_id=2,
        fiscal_year="2025",
        revenue_growth_pct=0.2,
        operating_margin_pct=3.0,
        capex_amount=50_000,
        cash_and_equivalents=120_000,
        segment_change_note="旧注釈ではない低成長設定",
    )
    high_markdown = _build_report_with_metric(high_metric)
    low_markdown = _build_report_with_metric(low_metric)
    old_note = "公式IR資料を参照し、CREデモ用のスコアリング入力として百万円単位に正規化した概算値です。"
    assert old_note not in high_markdown
    assert old_note not in low_markdown
    assert "事業拡大に伴う営業・物流・生産・研究開発拠点の増強需要" in high_markdown
    assert "拠点再編、低稼働資産の見直し" in low_markdown
    assert high_markdown != low_markdown
