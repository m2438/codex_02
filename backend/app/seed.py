from datetime import date

from sqlalchemy.orm import Session

from app.models import CRESignal, Company, Document, FinancialMetric, Score
from app.services.scoring import FinancialInputs, SignalInputs, calculate_sales_priority_score

INDUSTRIES = [
    "電気機器",
    "輸送用機器",
    "情報・通信業",
    "小売業",
    "化学",
    "医薬品",
    "機械",
    "食料品",
    "建設業",
    "不動産業",
]

SIGNAL_PATTERNS = [
    ("拠点再編", "国内拠点の再編検討", "国内の生産・営業拠点について、地域需要に合わせた再配置と統合を検討しています。"),
    ("設備投資", "成長領域への設備投資", "成長事業に対応するため、主要拠点での設備更新と能力増強を進めます。"),
    ("働き方改革", "本社機能と働き方の見直し", "ハイブリッドワーク定着を踏まえ、本社機能とオフィス利用の最適化を進めます。"),
    ("海外展開", "海外事業拡大に伴う拠点整備", "海外売上の拡大に合わせ、アジア地域で販売・サービス拠点の整備を検討します。"),
    ("物流再編", "物流ネットワークの効率化", "物流費上昇に対応するため、配送センター配置と在庫拠点の見直しを行います。"),
    ("本社機能見直し", "グループ本社機能の集約", "グループ経営管理の高度化に向け、本社機能の集約と業務標準化を進めます。"),
    ("資産売却", "政策保有資産と遊休資産の見直し", "資本効率向上のため、遊休不動産を含む保有資産の見直しを進めます。"),
]


def seed_database(db: Session) -> None:
    """Seed deterministic sample data when the SQLite database is empty."""

    if db.query(Company).first() is not None:
        return

    for index in range(1, 21):
        industry = INDUSTRIES[(index - 1) % len(INDUSTRIES)]
        company = Company(
            ticker=f"9{index:03d}",
            name=f"サンプル上場企業{index:02d}株式会社",
            market="東証プライム",
            industry=industry,
            headquarters_location=["東京都千代田区", "大阪市北区", "名古屋市中村区", "福岡市博多区"][index % 4],
            employee_count=4_000 + index * 850,
            revenue=180_000_000_000 + index * 27_500_000_000,
            fiscal_year="2025",
        )
        db.add(company)
        db.flush()

        primary_pattern = SIGNAL_PATTERNS[(index - 1) % len(SIGNAL_PATTERNS)]
        secondary_pattern = SIGNAL_PATTERNS[(index + 2) % len(SIGNAL_PATTERNS)]
        document = Document(
            company_id=company.id,
            document_type="統合報告書",
            title=f"{company.name} 2025年3月期 統合報告書（サンプル）",
            source_url=None,
            source_name="サンプルIR文書",
            published_date=date(2025, 6, min(28, index)),
            fiscal_year="2025",
            text_content=(
                f"{primary_pattern[2]} また、{secondary_pattern[2]} "
                "本テキストはCRE Sales Intelligenceデモ用の合成サンプルであり、実在企業の開示情報ではありません。"
            ),
            is_sample=True,
        )
        db.add(document)
        db.flush()

        revenue_growth = round(1.5 + (index % 8) * 1.3, 1)
        operating_margin = round(3.5 + (index % 7) * 1.4, 1)
        capex_amount = 35_000 + index * 9_000
        metric = FinancialMetric(
            company_id=company.id,
            fiscal_year="2025",
            revenue_growth_pct=revenue_growth,
            operating_margin_pct=operating_margin,
            capex_amount=capex_amount,
            cash_and_equivalents=80_000 + index * 12_000,
            segment_change_note="成長投資と事業ポートフォリオ見直しを進めるサンプル設定です。",
            source_document_id=document.id,
        )
        db.add(metric)

        signal_records: list[CRESignal] = []
        for signal_index, pattern in enumerate([primary_pattern, secondary_pattern], start=1):
            confidence = "high" if (index + signal_index) % 3 == 0 else "medium"
            signal_records.append(
                CRESignal(
                    company_id=company.id,
                    document_id=document.id,
                    signal_type=pattern[0],
                    title=pattern[1],
                    description=(
                        f"{pattern[0]}に関する記述があり、CRE戦略・拠点ポートフォリオ見直しの営業仮説につながります。"
                    ),
                    evidence_text=pattern[2],
                    source_reference=f"{document.title} / サンプル本文",
                    confidence=confidence,
                    confidence_reason="サンプル文書内に対象テーマの明示的な記述があるため。",
                    extracted_by="seed_mock",
                )
            )
        db.add_all(signal_records)
        db.flush()

        result = calculate_sales_priority_score(
            signals=[SignalInputs(signal_type=s.signal_type, confidence=s.confidence) for s in signal_records],
            financial=FinancialInputs(
                revenue_growth_pct=metric.revenue_growth_pct,
                operating_margin_pct=metric.operating_margin_pct,
                capex_amount=metric.capex_amount,
            ),
            company_name=company.name,
        )
        db.add(
            Score(
                company_id=company.id,
                total_score=result.total_score,
                priority_label=result.priority_label,
                signal_score=result.signal_score,
                financial_score=result.financial_score,
                strategic_event_score=result.strategic_event_score,
                fit_score=result.fit_score,
                explanation=result.explanation,
                recommended_action=result.recommended_action,
                calculated_at=result.calculated_at,
            )
        )

    db.commit()
