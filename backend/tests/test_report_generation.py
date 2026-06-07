from datetime import UTC, date, datetime

from app.models import CRESignal, Company, Document, FinancialMetric, Score
from app.services.reporting import generate_company_report


def test_generate_company_report_includes_required_japanese_markdown_sections() -> None:
    company = Company(
        id=1,
        ticker="9001",
        name="サンプル上場企業01株式会社",
        market="東証プライム",
        industry="電気機器",
        headquarters_location="東京都千代田区",
        employee_count=5000,
        revenue=200_000_000_000,
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
    assert "# サンプル上場企業01株式会社 CRE営業仮説レポート" in report.markdown_content
    for heading in [
        "## Executive summary",
        "## CRE sales priority",
        "## Detected CRE-related signals",
        "## Financial observations",
        "## Suggested sales hypothesis",
        "## Recommended first approach",
        "## Evidence and source documents",
        "## Caveats",
    ]:
        assert heading in report.markdown_content
    assert "主要拠点での設備更新と能力増強を進めます。" in report.markdown_content
