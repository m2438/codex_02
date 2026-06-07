from __future__ import annotations

from datetime import date
from typing import TypedDict

from sqlalchemy.orm import Session

from app.models import CRESignal, Company, Document, FinancialMetric, Score
from app.services.scoring import FinancialInputs, SignalInputs, calculate_sales_priority_score


class SignalSeed(TypedDict):
    type: str
    confidence: str


class CompanySeed(TypedDict):
    name: str
    industry: str
    profile: str
    location: str
    employees: int
    revenue: int  # 百万円
    capex: int  # 百万円
    cash: int  # 百万円
    growth: float
    margin: float
    signals: list[SignalSeed]


SIGNAL_PATTERNS = {
    "拠点再編": ("国内拠点の再編検討", "国内の生産・営業拠点について、地域需要に合わせた再配置と統合を検討しています。"),
    "設備投資": ("成長領域への設備投資", "成長事業に対応するため、主要拠点での設備更新と能力増強を進めます。"),
    "働き方改革": ("本社機能と働き方の見直し", "ハイブリッドワーク定着を踏まえ、本社機能とオフィス利用の最適化を進めます。"),
    "海外展開": ("海外事業拡大に伴う拠点整備", "海外売上の拡大に合わせ、アジア地域で販売・サービス拠点の整備を検討します。"),
    "物流再編": ("物流ネットワークの効率化", "物流費上昇に対応するため、配送センター配置と在庫拠点の見直しを行います。"),
    "本社機能見直し": ("グループ本社機能の集約", "グループ経営管理の高度化に向け、本社機能の集約と業務標準化を進めます。"),
    "資産売却": ("政策保有資産と遊休資産の見直し", "資本効率向上のため、遊休不動産を含む保有資産の見直しを進めます。"),
    "脱炭素": ("脱炭素投資と省エネ改修", "2030年度のCO2排出量削減目標に向け、主要施設の省エネ改修と再生可能エネルギー導入を進めます。"),
    "建替え": ("老朽化施設の建替え検討", "老朽化した研究・生産施設について、安全性と生産性を高める建替えを段階的に検討します。"),
    "BCP": ("BCPを踏まえた拠点冗長化", "災害時の事業継続性を高めるため、重要拠点のバックアップ機能とサプライチェーン冗長化を強化します。"),
    "R&D拠点拡張": ("研究開発拠点の拡張", "重点技術領域への研究開発投資を拡大し、実証設備を備えたR&D拠点の拡張を計画しています。"),
    "構造改革": ("構造改革と事業ポートフォリオ見直し", "低収益事業の構造改革と事業ポートフォリオ見直しを通じ、資本効率の改善を進めます。"),
}

COMPANY_SEEDS: list[CompanySeed] = [
    {"name": "AAA株式会社", "industry": "電気機器", "profile": "半導体・産業機器向け電子部品を国内外に展開する大手メーカー", "location": "東京都千代田区", "employees": 42600, "revenue": 2_480_000, "capex": 420_000, "cash": 820_000, "growth": 7.4, "margin": 11.8, "signals": [{"type": "拠点再編", "confidence": "high"}, {"type": "設備投資", "confidence": "high"}, {"type": "脱炭素", "confidence": "medium"}, {"type": "R&D拠点拡張", "confidence": "high"}]},
    {"name": "BBB株式会社", "industry": "輸送用機器", "profile": "完成車部品とモビリティ関連システムを扱うグローバル製造業", "location": "愛知県名古屋市", "employees": 68100, "revenue": 3_760_000, "capex": 510_000, "cash": 1_120_000, "growth": 5.8, "margin": 8.6, "signals": [{"type": "設備投資", "confidence": "high"}, {"type": "物流再編", "confidence": "high"}, {"type": "BCP", "confidence": "medium"}, {"type": "建替え", "confidence": "medium"}]},
    {"name": "CCC株式会社", "industry": "情報・通信業", "profile": "クラウド、データセンター、法人向けDXサービスを提供する情報通信企業", "location": "東京都港区", "employees": 18400, "revenue": 1_180_000, "capex": 260_000, "cash": 530_000, "growth": 9.2, "margin": 14.5, "signals": [{"type": "設備投資", "confidence": "medium"}, {"type": "本社機能見直し", "confidence": "medium"}, {"type": "脱炭素", "confidence": "medium"}]},
    {"name": "DDD株式会社", "industry": "小売業", "profile": "全国店舗網とECチャネルを持つ総合小売グループ", "location": "大阪市北区", "employees": 35300, "revenue": 1_560_000, "capex": 180_000, "cash": 310_000, "growth": 3.6, "margin": 4.9, "signals": [{"type": "物流再編", "confidence": "high"}, {"type": "拠点再編", "confidence": "medium"}, {"type": "働き方改革", "confidence": "low"}]},
    {"name": "EEE株式会社", "industry": "化学", "profile": "高機能素材、電子材料、環境関連材料を手掛ける化学メーカー", "location": "東京都中央区", "employees": 29100, "revenue": 1_920_000, "capex": 330_000, "cash": 640_000, "growth": 6.7, "margin": 10.2, "signals": [{"type": "設備投資", "confidence": "high"}, {"type": "資産売却", "confidence": "high"}, {"type": "脱炭素", "confidence": "high"}, {"type": "構造改革", "confidence": "medium"}]},
    {"name": "FFF株式会社", "industry": "医薬品", "profile": "新薬開発とライセンス事業を軸とする研究開発型製薬会社", "location": "大阪市中央区", "employees": 12200, "revenue": 820_000, "capex": 95_000, "cash": 450_000, "growth": 2.2, "margin": 16.4, "signals": [{"type": "R&D拠点拡張", "confidence": "medium"}, {"type": "働き方改革", "confidence": "medium"}]},
    {"name": "GGG株式会社", "industry": "機械", "profile": "FA機器、建設機械、保守サービスを展開する機械メーカー", "location": "京都市下京区", "employees": 23800, "revenue": 1_340_000, "capex": 160_000, "cash": 280_000, "growth": 4.9, "margin": 9.8, "signals": [{"type": "海外展開", "confidence": "medium"}, {"type": "設備投資", "confidence": "medium"}, {"type": "BCP", "confidence": "low"}]},
    {"name": "HHH株式会社", "industry": "食料品", "profile": "加工食品、冷凍食品、業務用食材を扱う食品グループ", "location": "東京都品川区", "employees": 20100, "revenue": 970_000, "capex": 120_000, "cash": 180_000, "growth": 1.8, "margin": 5.7, "signals": [{"type": "物流再編", "confidence": "medium"}, {"type": "脱炭素", "confidence": "low"}]},
    {"name": "III株式会社", "industry": "建設業", "profile": "国内大型建築、都市インフラ、エンジニアリングを展開する総合建設会社", "location": "東京都新宿区", "employees": 17300, "revenue": 1_740_000, "capex": 90_000, "cash": 360_000, "growth": 4.1, "margin": 6.8, "signals": [{"type": "本社機能見直し", "confidence": "medium"}, {"type": "脱炭素", "confidence": "medium"}, {"type": "BCP", "confidence": "medium"}]},
    {"name": "JJJ株式会社", "industry": "不動産業", "profile": "オフィス、商業、物流施設の開発・運営を行う総合不動産会社", "location": "東京都千代田区", "employees": 9800, "revenue": 760_000, "capex": 280_000, "cash": 240_000, "growth": 3.4, "margin": 18.2, "signals": [{"type": "建替え", "confidence": "medium"}, {"type": "資産売却", "confidence": "medium"}, {"type": "脱炭素", "confidence": "medium"}]},
    {"name": "KKK株式会社", "industry": "電気機器", "profile": "社会インフラ向け制御機器と保守サービスを提供する電機メーカー", "location": "東京都大田区", "employees": 31500, "revenue": 1_220_000, "capex": 140_000, "cash": 390_000, "growth": 5.1, "margin": 7.9, "signals": [{"type": "拠点再編", "confidence": "medium"}, {"type": "設備投資", "confidence": "medium"}, {"type": "本社機能見直し", "confidence": "low"}]},
    {"name": "LLL株式会社", "industry": "陸運業", "profile": "幹線輸送、倉庫、3PLを全国で展開する物流企業", "location": "東京都江東区", "employees": 47200, "revenue": 1_080_000, "capex": 220_000, "cash": 210_000, "growth": 4.7, "margin": 5.2, "signals": [{"type": "物流再編", "confidence": "high"}, {"type": "BCP", "confidence": "high"}, {"type": "脱炭素", "confidence": "medium"}, {"type": "拠点再編", "confidence": "medium"}]},
    {"name": "MMM株式会社", "industry": "精密機器", "profile": "医療機器、計測機器、産業用センサーを開発する精密機器メーカー", "location": "長野県松本市", "employees": 11600, "revenue": 690_000, "capex": 70_000, "cash": 160_000, "growth": 2.9, "margin": 10.7, "signals": [{"type": "R&D拠点拡張", "confidence": "medium"}, {"type": "設備投資", "confidence": "low"}]},
    {"name": "NNN株式会社", "industry": "サービス業", "profile": "BPO、コールセンター、人材サービスを全国展開する法人サービス企業", "location": "東京都渋谷区", "employees": 26500, "revenue": 540_000, "capex": 32_000, "cash": 120_000, "growth": 1.2, "margin": 4.4, "signals": [{"type": "働き方改革", "confidence": "medium"}]},
    {"name": "OOO株式会社", "industry": "金属製品", "profile": "建材、産業資材、環境設備向け部材を扱う素材加工メーカー", "location": "兵庫県神戸市", "employees": 14200, "revenue": 880_000, "capex": 105_000, "cash": 150_000, "growth": 2.5, "margin": 6.1, "signals": [{"type": "建替え", "confidence": "medium"}, {"type": "脱炭素", "confidence": "medium"}]},
    {"name": "PPP株式会社", "industry": "卸売業", "profile": "産業資材、食品原料、海外トレーディングを手掛ける専門商社", "location": "東京都中央区", "employees": 8300, "revenue": 1_460_000, "capex": 45_000, "cash": 290_000, "growth": 3.8, "margin": 3.9, "signals": [{"type": "海外展開", "confidence": "medium"}, {"type": "本社機能見直し", "confidence": "low"}]},
    {"name": "QQQ株式会社", "industry": "電気・ガス業", "profile": "発電、送配電、エネルギーサービスを展開するインフラ企業", "location": "福岡市博多区", "employees": 33700, "revenue": 2_120_000, "capex": 610_000, "cash": 760_000, "growth": 6.1, "margin": 7.4, "signals": [{"type": "設備投資", "confidence": "high"}, {"type": "脱炭素", "confidence": "high"}, {"type": "BCP", "confidence": "high"}, {"type": "拠点再編", "confidence": "medium"}]},
    {"name": "RRR株式会社", "industry": "小売業", "profile": "都市型店舗と物流子会社を持つ専門小売チェーン", "location": "埼玉県さいたま市", "employees": 15600, "revenue": 620_000, "capex": 65_000, "cash": 95_000, "growth": 0.8, "margin": 3.6, "signals": [{"type": "物流再編", "confidence": "low"}, {"type": "働き方改革", "confidence": "low"}]},
    {"name": "SSS株式会社", "industry": "化学", "profile": "基礎化学品と機能性樹脂を国内外に供給する素材メーカー", "location": "千葉県市原市", "employees": 19100, "revenue": 1_110_000, "capex": 135_000, "cash": 260_000, "growth": 3.2, "margin": 6.6, "signals": [{"type": "資産売却", "confidence": "medium"}, {"type": "構造改革", "confidence": "medium"}, {"type": "脱炭素", "confidence": "low"}]},
    {"name": "TTT株式会社", "industry": "情報・通信業", "profile": "決済、法人SaaS、デジタルマーケティングを展開するITサービス企業", "location": "東京都港区", "employees": 9200, "revenue": 410_000, "capex": 38_000, "cash": 210_000, "growth": 8.7, "margin": 12.1, "signals": [{"type": "働き方改革", "confidence": "medium"}, {"type": "本社機能見直し", "confidence": "medium"}]},
]


def seed_database(db: Session) -> None:
    """Seed deterministic synthetic demo data when the SQLite database is empty.

    Phase 3.5 refreshes the bundled sample dataset. If an older demo database
    still contains the previous mechanical company names, reset only the demo
    tables and reseed the synthetic sample records.
    """

    first_company = db.query(Company).order_by(Company.id).first()
    if first_company is not None and not first_company.name.startswith("サンプル上場企業"):
        return
    if first_company is not None:
        for model in (Score, CRESignal, FinancialMetric, Document, Company):
            db.query(model).delete()
        db.commit()

    for index, seed in enumerate(COMPANY_SEEDS, start=1):
        company = Company(
            ticker=f"9{index:03d}",
            name=seed["name"],
            market="東証プライム",
            industry=seed["industry"],
            headquarters_location=seed["location"],
            employee_count=seed["employees"],
            revenue=seed["revenue"],
            fiscal_year="2025",
        )
        db.add(company)
        db.flush()

        signal_texts = [SIGNAL_PATTERNS[signal["type"]][1] for signal in seed["signals"]]
        document = Document(
            company_id=company.id,
            document_type="統合報告書",
            title=f"{company.name} 2025年3月期 統合報告書（サンプル）",
            source_url=None,
            source_name="サンプルIR文書",
            published_date=date(2025, 6, min(28, index)),
            fiscal_year="2025",
            text_content=(
                f"{seed['profile']}。" + " ".join(signal_texts) +
                " 本テキストはCRE Sales Intelligenceデモ用の合成サンプルであり、実在企業の開示情報ではありません。"
            ),
            is_sample=True,
        )
        db.add(document)
        db.flush()

        metric = FinancialMetric(
            company_id=company.id,
            fiscal_year="2025",
            revenue_growth_pct=seed["growth"],
            operating_margin_pct=seed["margin"],
            capex_amount=seed["capex"],
            cash_and_equivalents=seed["cash"],
            segment_change_note=f"{seed['profile']}として、合成デモデータ上は投資計画・資本効率・拠点運営の変化を比較できる設定です。",
            source_document_id=document.id,
        )
        db.add(metric)

        signal_records: list[CRESignal] = []
        for signal_seed in seed["signals"]:
            title, evidence_text = SIGNAL_PATTERNS[signal_seed["type"]]
            signal_records.append(
                CRESignal(
                    company_id=company.id,
                    document_id=document.id,
                    signal_type=signal_seed["type"],
                    title=title,
                    description=(
                        f"{signal_seed['type']}に関する記述があり、CRE戦略・PM/CM・拠点ポートフォリオ見直しの営業仮説につながります。"
                    ),
                    evidence_text=evidence_text,
                    source_reference=f"{document.title} / サンプル本文",
                    confidence=signal_seed["confidence"],
                    confidence_reason="サンプル文書内に対象テーマの明示的な記述があるため。低信頼の場合は示唆が間接的で追加確認が必要です。",
                    extracted_by="seed_mock",
                )
            )
        db.add_all(signal_records)
        db.flush()

        result = calculate_sales_priority_score(
            signals=[SignalInputs(signal_type=s.signal_type, confidence=s.confidence) for s in signal_records],
            financial=FinancialInputs(
                revenue=company.revenue,
                revenue_growth_pct=metric.revenue_growth_pct,
                operating_margin_pct=metric.operating_margin_pct,
                capex_amount=metric.capex_amount,
                cash_and_equivalents=metric.cash_and_equivalents,
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
