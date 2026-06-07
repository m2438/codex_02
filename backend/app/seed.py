from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TypedDict

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models import CRESignal, Company, Document, FinancialMetric, Report, Score
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


class PublicCompanySeed(CompanySeed):
    ticker: str
    market: str
    fiscal_year: str
    document_title: str
    document_type: str
    source_url: str
    source_note: str
    selection_reason: str
    evidence_by_signal: dict[str, str]


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

PUBLIC_COMPANY_SEEDS: list[PublicCompanySeed] = [
    {"ticker": "7203", "name": "トヨタ自動車株式会社", "market": "東証プライム", "industry": "輸送用機器", "profile": "自動車、モビリティ、研究開発、生産拠点を国内外に有する製造業", "location": "愛知県豊田市", "employees": 384000, "revenue": 48_036_000, "capex": 2_200_000, "cash": 9_400_000, "growth": 6.5, "margin": 9.4, "fiscal_year": "2025", "document_title": "有価証券報告書・半期報告書 2025年3月期", "document_type": "有価証券報告書", "source_url": "https://global.toyota/jp/ir/library/securities-report/index.html", "source_note": "公式IRの有価証券報告書ライブラリを参照。統合報告書・決算資料も補助的に確認。", "selection_reason": "国内最大級の製造業で、工場・研究開発・脱炭素投資などCRE論点が幅広い。", "signals": [{"type": "設備投資", "confidence": "high"}, {"type": "R&D拠点拡張", "confidence": "medium"}, {"type": "脱炭素", "confidence": "medium"}, {"type": "BCP", "confidence": "medium"}], "evidence_by_signal": {"設備投資": "公開IR資料では、自動車生産・電動化・ソフトウェア領域の競争力強化に向けた投資継続が示されている。", "R&D拠点拡張": "統合報告書等では研究開発・先進技術への継続投資が説明されている。", "脱炭素": "カーボンニュートラルや電動化対応が経営課題として説明されている。", "BCP": "グローバル供給網と生産体制の強靭化が公開資料上の確認テーマとなる。"}},
    {"ticker": "3382", "name": "株式会社セブン＆アイ・ホールディングス", "market": "東証プライム", "industry": "小売業", "profile": "国内外のコンビニエンスストア等を展開する小売グループ", "location": "東京都千代田区", "employees": 83000, "revenue": 11_972_000, "capex": 520_000, "cash": 2_000_000, "growth": 1.2, "margin": 4.5, "fiscal_year": "2024", "document_title": "Annual Securities Report FY2024", "document_type": "有価証券報告書", "source_url": "https://www.7andi.com/en/ir/file/library/pdf/25_7andi_int04_en.pdf", "source_note": "公式IR掲載の英訳Annual Securities Reportを参照。", "selection_reason": "店舗網・物流・事業ポートフォリオ見直しの観点で小売CRE仮説を示しやすい。", "signals": [{"type": "物流再編", "confidence": "medium"}, {"type": "構造改革", "confidence": "high"}, {"type": "拠点再編", "confidence": "medium"}], "evidence_by_signal": {"物流再編": "公開資料ではコンビニエンスストア事業を中心とした成長戦略と店舗・物流運営の高度化が説明されている。", "構造改革": "グループ事業の変革や価値向上施策がIR資料で説明されている。", "拠点再編": "店舗網・国内外事業運営の見直しはCRE観点で確認すべきテーマとなる。"}},
    {"ticker": "9147", "name": "NIPPON EXPRESSホールディングス株式会社", "market": "東証プライム", "industry": "陸運業", "profile": "国内外で物流、倉庫、フォワーディングを展開する総合物流企業", "location": "東京都千代田区", "employees": 73000, "revenue": 2_500_000, "capex": 120_000, "cash": 300_000, "growth": 2.0, "margin": 4.0, "fiscal_year": "2024", "document_title": "有価証券報告書 2024年12月期", "document_type": "有価証券報告書", "source_url": "https://www.nipponexpress-holdings.com/ja/ir/library/securities/", "source_note": "公式IRの有価証券報告書ライブラリおよび統合報告書2025を参照。", "selection_reason": "物流施設、倉庫ネットワーク、サステナビリティ投資のCRE論点が明確。", "signals": [{"type": "物流再編", "confidence": "high"}, {"type": "脱炭素", "confidence": "medium"}, {"type": "BCP", "confidence": "medium"}], "evidence_by_signal": {"物流再編": "統合報告書ではグローバル物流ネットワークと成長領域での物流機能強化が説明されている。", "脱炭素": "SBT認定など気候変動対応が公開情報で確認できる。", "BCP": "物流インフラとしてサプライチェーン強靭化を確認すべき企業である。"}},
    {"ticker": "9020", "name": "東日本旅客鉄道株式会社", "market": "東証プライム", "industry": "鉄道", "profile": "鉄道、駅、生活サービス、不動産・まちづくりを展開する交通インフラ企業", "location": "東京都渋谷区", "employees": 68000, "revenue": 2_730_000, "capex": 740_000, "cash": 420_000, "growth": 9.0, "margin": 12.0, "fiscal_year": "2025", "document_title": "Annual Securities Report 2025", "document_type": "有価証券報告書", "source_url": "https://www.jreast.co.jp/e/investor/securitiesreport/pdf/securitiesreport_fiscal2025.pdf", "source_note": "公式IR掲載のAnnual Securities Report 2025を参照。", "selection_reason": "鉄道設備、駅周辺開発、老朽化・BCP対応などCRE/インフラ論点が多い。", "signals": [{"type": "設備投資", "confidence": "high"}, {"type": "建替え", "confidence": "medium"}, {"type": "BCP", "confidence": "high"}, {"type": "拠点再編", "confidence": "medium"}], "evidence_by_signal": {"設備投資": "公開資料では鉄道設備、安全対策、生活ソリューションに関わる投資が説明されている。", "建替え": "駅・鉄道施設・関連施設の更新やまちづくりはCRE観点の確認事項となる。", "BCP": "交通インフラとして災害対応・安全安定輸送の継続が重要課題として説明されている。", "拠点再編": "駅周辺・沿線開発は保有資産の活用仮説につながる。"}},
    {"ticker": "3231", "name": "野村不動産ホールディングス株式会社", "market": "東証プライム", "industry": "不動産業", "profile": "住宅、オフィス、物流施設、商業施設等を展開する総合不動産グループ", "location": "東京都新宿区", "employees": 7900, "revenue": 780_000, "capex": 260_000, "cash": 100_000, "growth": 5.0, "margin": 11.0, "fiscal_year": "2025", "document_title": "Financial Report 2025 / Integrated Report 2025", "document_type": "有価証券報告書相当資料", "source_url": "https://www.nomura-re-hd.co.jp/english/ir/ir_library/annualreport.html", "source_note": "公式IRのFinancial Report 2025（有価証券報告書の要約位置づけ）と統合報告書を参照。", "selection_reason": "不動産開発・保有運営・物流施設など、CRE提案テーマと比較しやすい。", "signals": [{"type": "建替え", "confidence": "medium"}, {"type": "資産売却", "confidence": "medium"}, {"type": "脱炭素", "confidence": "medium"}], "evidence_by_signal": {"建替え": "統合報告書では不動産開発・都市開発・資産価値向上の取り組みが説明されている。", "資産売却": "不動産ポートフォリオ運営と資本効率は公開資料上の確認テーマである。", "脱炭素": "サステナビリティや環境配慮型開発が説明されている。"}},
    {"ticker": "9432", "name": "日本電信電話株式会社", "market": "東証プライム", "industry": "情報・通信業", "profile": "通信、データセンター、ICT、研究開発を展開する通信インフラ企業", "location": "東京都千代田区", "employees": 338000, "revenue": 13_374_000, "capex": 1_900_000, "cash": 1_000_000, "growth": 3.0, "margin": 14.0, "fiscal_year": "2025", "document_title": "Securities Report / Integrated Report 2025", "document_type": "有価証券報告書", "source_url": "https://group.ntt/en/ir/library/yuho/", "source_note": "公式IRのSecurities ReportページおよびIntegrated Report 2025を参照。", "selection_reason": "通信局舎、データセンター、研究開発、脱炭素投資のCRE論点が多い。", "signals": [{"type": "設備投資", "confidence": "high"}, {"type": "R&D拠点拡張", "confidence": "medium"}, {"type": "脱炭素", "confidence": "medium"}, {"type": "BCP", "confidence": "medium"}], "evidence_by_signal": {"設備投資": "統合報告書ではネットワーク・データセンター・ICT基盤への投資が説明されている。", "R&D拠点拡張": "研究開発とIOWN等の技術戦略が公開情報で説明されている。", "脱炭素": "環境・エネルギー効率化の取り組みが統合報告書に整理されている。", "BCP": "通信インフラとして冗長性・信頼性を確認すべき対象である。"}},
    {"ticker": "6503", "name": "三菱電機株式会社", "market": "東証プライム", "industry": "電気機器", "profile": "インフラ、FA、空調、半導体・デバイス等を展開する総合電機メーカー", "location": "東京都千代田区", "employees": 149000, "revenue": 5_520_000, "capex": 300_000, "cash": 870_000, "growth": 4.0, "margin": 7.0, "fiscal_year": "2025", "document_title": "Annual Securities Report for FY2025", "document_type": "有価証券報告書", "source_url": "https://www.mitsubishielectric.com/investors/library/securities_report/index.html", "source_note": "公式IRのAnnual Securities Reportページと統合報告書2025を参照。", "selection_reason": "工場、研究開発、社会インフラ、半導体・データセンター関連設備の論点がある。", "signals": [{"type": "設備投資", "confidence": "medium"}, {"type": "R&D拠点拡張", "confidence": "medium"}, {"type": "脱炭素", "confidence": "medium"}], "evidence_by_signal": {"設備投資": "有価証券報告書・統合報告書では各事業セグメントの生産・開発・品質強化が説明されている。", "R&D拠点拡張": "研究開発と技術基盤強化は公開資料上の重要テーマである。", "脱炭素": "省エネ・環境価値を提供する事業と自社環境対応が説明されている。"}},
    {"ticker": "4502", "name": "武田薬品工業株式会社", "market": "東証プライム", "industry": "医薬品", "profile": "グローバルに研究開発・製造・販売を展開する製薬企業", "location": "東京都中央区", "employees": 49000, "revenue": 4_580_000, "capex": 220_000, "cash": 520_000, "growth": 6.0, "margin": 15.0, "fiscal_year": "2024", "document_title": "Annual Report FY2024 / Annual Integrated Report 2025", "document_type": "有価証券報告書", "source_url": "https://www.takeda.com/investors/sec-filings-and-security-reports/", "source_note": "公式IRのAnnual Report（Securities Report translation）およびAnnual Integrated Reportを参照。", "selection_reason": "研究所・製造拠点・品質管理・サステナビリティ投資のCRE仮説を検討しやすい。", "signals": [{"type": "R&D拠点拡張", "confidence": "high"}, {"type": "設備投資", "confidence": "medium"}, {"type": "脱炭素", "confidence": "medium"}], "evidence_by_signal": {"R&D拠点拡張": "統合報告書では研究開発パイプラインとR&D投資の重要性が説明されている。", "設備投資": "医薬品の製造・品質・供給体制は公開資料から確認すべきテーマである。", "脱炭素": "サステナビリティと環境負荷低減に関する取り組みが説明されている。"}},
    {"ticker": "4182", "name": "三菱ガス化学株式会社", "market": "東証プライム", "industry": "化学", "profile": "基礎化学品、機能化学品、半導体関連材料等を展開する化学メーカー", "location": "東京都千代田区", "employees": 10000, "revenue": 810_000, "capex": 85_000, "cash": 170_000, "growth": 3.0, "margin": 8.0, "fiscal_year": "2025", "document_title": "Annual Securities Report 2025", "document_type": "有価証券報告書", "source_url": "https://www.mgc.co.jp/eng/ir/library/report.html", "source_note": "公式IRのSecurities Reportsページを参照。", "selection_reason": "化学プラント、研究開発、半導体材料、脱炭素・安全対策のCRE論点がある。", "signals": [{"type": "設備投資", "confidence": "medium"}, {"type": "脱炭素", "confidence": "medium"}, {"type": "BCP", "confidence": "medium"}], "evidence_by_signal": {"設備投資": "公開資料では化学品・機能材料事業の生産・開発基盤が説明されている。", "脱炭素": "化学メーカーとして環境対応や排出削減を確認すべき対象である。", "BCP": "化学プラントの安全・安定操業はCRE/施設管理上の確認テーマとなる。"}},
    {"ticker": "9531", "name": "東京ガス株式会社", "market": "東証プライム", "industry": "電気・ガス業", "profile": "都市ガス、電力、エネルギーソリューション、不動産等を展開するインフラ企業", "location": "東京都港区", "employees": 15000, "revenue": 2_660_000, "capex": 300_000, "cash": 250_000, "growth": 2.5, "margin": 7.0, "fiscal_year": "2025", "document_title": "有価証券報告書・四半期報告書 2025年3月期", "document_type": "有価証券報告書", "source_url": "https://www.tokyo-gas.co.jp/IR/library/yuho_j.html", "source_note": "公式IRの有価証券報告書・四半期報告書ページおよび統合報告書2025を参照。", "selection_reason": "エネルギー供給インフラ、脱炭素、供給設備投資、不動産活用の論点がある。", "signals": [{"type": "設備投資", "confidence": "medium"}, {"type": "脱炭素", "confidence": "high"}, {"type": "BCP", "confidence": "medium"}], "evidence_by_signal": {"設備投資": "公開資料ではガス・電力等の供給インフラと設備投資が確認テーマとなる。", "脱炭素": "カーボンニュートラルやエネルギートランジションが統合報告書等で説明されている。", "BCP": "エネルギーインフラとして安定供給・災害対応を確認すべき企業である。"}},
]


def _ensure_phase4a_columns(db: Session) -> None:
    inspector = inspect(db.bind)
    existing_company_columns = {column["name"] for column in inspector.get_columns("companies")}
    company_columns = {
        "data_source_type": "VARCHAR(20) DEFAULT 'synthetic'",
        "listing_country": "VARCHAR(80) DEFAULT '日本'",
        "is_public_company": "BOOLEAN DEFAULT 1",
        "selection_reason": "TEXT DEFAULT '合成デモデータ'",
    }
    for column_name, definition in company_columns.items():
        if column_name not in existing_company_columns:
            db.execute(text(f"ALTER TABLE companies ADD COLUMN {column_name} {definition}"))

    existing_document_columns = {column["name"] for column in inspector.get_columns("documents")}
    document_columns = {
        "retrieved_at": "DATETIME",
        "source_note": "TEXT DEFAULT ''",
        "document_language": "VARCHAR(20) DEFAULT 'ja'",
    }
    for column_name, definition in document_columns.items():
        if column_name not in existing_document_columns:
            db.execute(text(f"ALTER TABLE documents ADD COLUMN {column_name} {definition}"))
    db.commit()


def _japanese_document_definitions(seed: PublicCompanySeed) -> list[dict[str, str]]:
    document_urls = {
        "7203": [
            ("有価証券報告書・半期報告書 2025年3月期", "有価証券報告書", "https://global.toyota/jp/ir/library/securities-report/index.html"),
            ("統合報告書 2025", "統合報告書", "https://global.toyota/jp/ir/library/annual/index.html"),
        ],
        "3382": [
            ("有価証券報告書 2025年2月期", "有価証券報告書", "https://www.7andi.com/ir/library/secrepo.html"),
            ("経営レポート 2025", "統合報告書", "https://www.7andi.com/ir/library/mr/index.html"),
        ],
        "9147": [
            ("有価証券報告書 2024年12月期", "有価証券報告書", "https://www.nipponexpress-holdings.com/ja/ir/library/securities/"),
            ("NXグループ 統合報告書2025", "統合報告書", "https://www.nipponexpress-holdings.com/ja/ir/library/annual/"),
        ],
        "9020": [
            ("有価証券報告書 2025年3月期", "有価証券報告書", "https://www.jreast.co.jp/company/ir/library/securitiesreport/"),
            ("JR東日本グループレポート2025（統合報告書）", "統合報告書", "https://www.jreast.co.jp/company/vision_report/report/"),
        ],
        "3231": [
            ("有価証券報告書・Financial Report 2025", "有価証券報告書相当資料", "https://www.nomura-re-hd.co.jp/ir/ir_library/"),
            ("統合レポート2025", "統合報告書", "https://www.nomura-re-hd.co.jp/ir/ir-library/integrated-report.html"),
        ],
        "9432": [
            ("有価証券報告書等 2025年3月期", "有価証券報告書", "https://group.ntt/jp/ir/library/yuho/"),
            ("統合報告書 2025（日本語版）", "統合報告書", "https://group.ntt/jp/ir/library/annual/index.html"),
        ],
        "6503": [
            ("有価証券報告書 2025年3月期", "有価証券報告書", "https://www.mitsubishielectric.co.jp/ir/data/negotiable_securities/"),
            ("統合報告書2025", "統合報告書", "https://www.mitsubishielectric.co.jp/ir/data/integrated_report/"),
        ],
        "4502": [
            ("有価証券報告書 2024年度", "有価証券報告書", "https://www.takeda.com/jp/investors/sec-filings"),
            ("統合報告書とESGデータブック", "統合報告書", "https://www.takeda.com/jp/investors/overview/"),
        ],
        "4182": [
            ("有価証券報告書 2025年3月期", "有価証券報告書", "https://www.mgc.co.jp/ir/library/report.html"),
            ("MGCレポート（統合報告書）", "統合報告書", "https://www.mgc.co.jp/ir/index.html"),
        ],
        "9531": [
            ("有価証券報告書・四半期報告書 2025年3月期", "有価証券報告書", "https://www.tokyo-gas.co.jp/IR/library/yuho_j.html"),
            ("統合報告書・決算説明会資料", "統合報告書・決算説明資料", "https://www.tokyo-gas.co.jp/IR/index.html"),
        ],
    }
    return [
        {
            "title": title,
            "document_type": document_type,
            "source_url": source_url,
            "source_note": (
                "公式IRサイトの日本語資料ページを参照。公開情報に基づく営業仮説用の要約であり、"
                "個別案件化や正式方針は原資料・ヒアリングで再確認してください。"
            ),
        }
        for title, document_type, source_url in document_urls[seed["ticker"]]
    ]


def _seed_public_demo_companies(db: Session, *, existing_public_tickers: set[str]) -> None:
    for seed in PUBLIC_COMPANY_SEEDS:
        if seed["ticker"] in existing_public_tickers:
            continue
        company = Company(
            ticker=seed["ticker"],
            name=seed["name"],
            market=seed["market"],
            industry=seed["industry"],
            headquarters_location=seed["location"],
            employee_count=seed["employees"],
            revenue=seed["revenue"],
            fiscal_year=seed["fiscal_year"],
            data_source_type="public_demo",
            listing_country="日本",
            is_public_company=True,
            selection_reason=seed["selection_reason"],
        )
        db.add(company)
        db.flush()

        signal_texts = [seed["evidence_by_signal"][signal["type"]] for signal in seed["signals"]]
        documents: list[Document] = []
        for doc_index, document_seed in enumerate(_japanese_document_definitions(seed), start=1):
            document = Document(
                company_id=company.id,
                document_type=document_seed["document_type"],
                title=document_seed["title"],
                source_url=document_seed["source_url"],
                source_name="公式IR資料（日本語）",
                retrieved_at=datetime.now(UTC),
                source_note=document_seed["source_note"],
                document_language="ja",
                published_date=date(int(seed["fiscal_year"]), min(12, 5 + doc_index), 30),
                fiscal_year=seed["fiscal_year"],
                text_content=(
                    f"{seed['profile']}。{document_seed['title']}を中心に、CRE観点では拠点再編、工場・研究所・物流拠点、"
                    "設備投資、老朽化・更新、BCP・防災、脱炭素・省エネ、不動産保有・遊休資産、"
                    "資本効率・ROIC・PBR、事業ポートフォリオ、人的資本・働き方を確認対象とする。"
                    + " ".join(signal_texts)
                    + " 本テキストは公開情報に基づく営業仮説用の要約であり、当該企業の正式なCRE方針を断定しません。"
                ),
                is_sample=False,
            )
            db.add(document)
            db.flush()
            documents.append(document)

        primary_document = documents[0]
        metric = FinancialMetric(
            company_id=company.id,
            fiscal_year=seed["fiscal_year"],
            revenue_growth_pct=seed["growth"],
            operating_margin_pct=seed["margin"],
            capex_amount=seed["capex"],
            cash_and_equivalents=seed["cash"],
            segment_change_note=(
                f"{seed['industry']}の公開IR指標を基に、売上成長率{seed['growth']}%、"
                f"営業利益率{seed['margin']}%、設備投資額{seed['capex'] / 100:,.0f}億円、"
                f"現預金等{seed['cash'] / 100:,.0f}億円をCRE仮説の入力値として整理。"
            ),
            source_document_id=primary_document.id,
        )
        db.add(metric)

        signal_records: list[CRESignal] = []
        for index, signal_seed in enumerate(seed["signals"]):
            title, _ = SIGNAL_PATTERNS[signal_seed["type"]]
            evidence_text = (
                seed["evidence_by_signal"][signal_seed["type"]]
                + " CRE観点では、対象拠点の所在、築年数・稼働率、投資予定、BCP・省エネ要件、"
                "不動産保有方針、資本効率指標との接続を追加確認することで、PM/CM、拠点ポートフォリオ、"
                "更新投資、遊休資産活用の仮説を具体化できる可能性があります。"
            )
            source_document = documents[index % len(documents)]
            signal_records.append(
                CRESignal(
                    company_id=company.id,
                    document_id=source_document.id,
                    signal_type=signal_seed["type"],
                    title=title,
                    description=(
                        f"日本語の公開IR資料から{signal_seed['type']}に関する確認候補が示唆されます。"
                        "正式方針や実際の提案機会ではなく、CRE観点で追加確認すべき営業仮説として扱います。"
                    ),
                    evidence_text=evidence_text,
                    source_reference=f"{source_document.title} / {source_document.source_url}",
                    confidence=signal_seed["confidence"],
                    confidence_reason="公開IR資料の要約に基づくデモ用シグナルです。実営業では一次情報と個別ヒアリングで検証してください。",
                    extracted_by="public_demo_seed",
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
                recommended_action=(
                    "公開情報に基づく営業仮説として、根拠資料の記載事項、関連部門、個別不動産・施設の状況を"
                    "追加確認する。正式なCRE方針や提案機会を断定せず、初回接点では確認候補として扱う。"
                ),
                calculated_at=result.calculated_at,
            )
        )

    db.commit()


def seed_database(db: Session) -> None:
    """Seed deterministic public-demo data when the SQLite database is empty or outdated."""

    _ensure_phase4a_columns(db)
    public_count = db.query(Company).filter(Company.data_source_type == "public_demo").count()
    synthetic_count = db.query(Company).filter(Company.data_source_type == "synthetic").count()
    document_count = db.query(Document).count()
    expected_document_count = len(PUBLIC_COMPANY_SEEDS) * 2

    if synthetic_count or public_count != len(PUBLIC_COMPANY_SEEDS) or document_count < expected_document_count:
        for model in (Score, CRESignal, FinancialMetric, Document, Report, Company):
            db.query(model).delete()
        db.commit()
        _seed_public_demo_companies(db, existing_public_tickers=set())
        return

    # Backfill Phase 4A compatibility fields for databases that already contain only public demo data.
    db.query(Company).filter(Company.data_source_type.is_(None)).update({Company.data_source_type: "public_demo"})
    db.query(Company).filter(Company.listing_country.is_(None)).update({Company.listing_country: "日本"})
    db.query(Document).filter(Document.document_language.is_(None)).update({Document.document_language: "ja"})
    db.commit()
