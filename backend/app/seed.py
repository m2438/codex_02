from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TypedDict

from sqlalchemy import inspect, text
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


# Phase 4A public_demo dataset: selected from Japanese listed companies with official IR pages
# where an annual securities report or securities-report-derived financial report is publicly available.
# The document text stores short CRE-oriented summaries only; it intentionally avoids long copyrighted excerpts.
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
    }
    for column_name, definition in document_columns.items():
        if column_name not in existing_document_columns:
            db.execute(text(f"ALTER TABLE documents ADD COLUMN {column_name} {definition}"))
    db.commit()


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
        document = Document(
            company_id=company.id,
            document_type=seed["document_type"],
            title=seed["document_title"],
            source_url=seed["source_url"],
            source_name="公式IR資料",
            retrieved_at=datetime.now(UTC),
            source_note=seed["source_note"],
            published_date=date(int(seed["fiscal_year"]), 6, 30),
            fiscal_year=seed["fiscal_year"],
            text_content=(
                f"{seed['profile']}。公開IR資料に基づくCRE分析用の短い要約: "
                + " ".join(signal_texts)
                + " 本テキストは公開情報に基づく営業仮説用の要約であり、当該企業の正式なCRE方針を断定しません。"
            ),
            is_sample=False,
        )
        db.add(document)
        db.flush()

        metric = FinancialMetric(
            company_id=company.id,
            fiscal_year=seed["fiscal_year"],
            revenue_growth_pct=seed["growth"],
            operating_margin_pct=seed["margin"],
            capex_amount=seed["capex"],
            cash_and_equivalents=seed["cash"],
            segment_change_note=(
                "公式IR資料を参照し、CREデモ用のスコアリング入力として百万円単位に正規化した概算値です。"
                "実営業で利用する場合は原資料の一次情報を再確認してください。"
            ),
            source_document_id=document.id,
        )
        db.add(metric)

        signal_records: list[CRESignal] = []
        for signal_seed in seed["signals"]:
            title, _ = SIGNAL_PATTERNS[signal_seed["type"]]
            evidence_text = seed["evidence_by_signal"][signal_seed["type"]]
            signal_records.append(
                CRESignal(
                    company_id=company.id,
                    document_id=document.id,
                    signal_type=signal_seed["type"],
                    title=title,
                    description=(
                        f"公開IR資料から{signal_seed['type']}に関する可能性が示唆されます。"
                        "CRE観点では追加確認により営業仮説を具体化する必要があります。"
                    ),
                    evidence_text=evidence_text,
                    source_reference=f"{document.title} / {document.source_url}",
                    confidence=signal_seed["confidence"],
                    confidence_reason="公開IR資料の短い要約に基づくデモ用シグナルです。実営業では一次情報と個別ヒアリングで検証してください。",
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
    """Seed deterministic synthetic and public-demo data when the SQLite database is empty."""

    _ensure_phase4a_columns(db)
    first_company = db.query(Company).order_by(Company.id).first()
    if first_company is not None and first_company.name.startswith("サンプル上場企業"):
        for model in (Score, CRESignal, FinancialMetric, Document, Company):
            db.query(model).delete()
        db.commit()

    if db.query(Company).filter(Company.data_source_type == "synthetic").count() == 0:
        _seed_synthetic_companies(db)

    db.query(Company).filter(Company.data_source_type.is_(None)).update({Company.data_source_type: "synthetic"})
    db.query(Company).filter(Company.listing_country.is_(None)).update({Company.listing_country: "日本"})
    db.query(Company).filter(Company.selection_reason.is_(None)).update({Company.selection_reason: "合成デモデータ"})
    public_tickers = {seed["ticker"] for seed in PUBLIC_COMPANY_SEEDS}
    synthetic_companies = db.query(Company).filter(Company.data_source_type == "synthetic").order_by(Company.id).all()
    for index, company in enumerate(synthetic_companies, start=1):
        if company.ticker in public_tickers or company.ticker.startswith("9"):
            company.ticker = f"S{index:03d}"
    db.commit()

    if db.query(Company).filter(Company.data_source_type == "public_demo").count() < len(PUBLIC_COMPANY_SEEDS):
        existing_public_tickers = {ticker for (ticker,) in db.query(Company.ticker).filter(Company.data_source_type == "public_demo").all()}
        _seed_public_demo_companies(db, existing_public_tickers=existing_public_tickers)


def _seed_synthetic_companies(db: Session) -> None:
    for index, seed in enumerate(COMPANY_SEEDS, start=1):
        company = Company(
            ticker=f"S{index:03d}",
            name=seed["name"],
            market="東証プライム",
            industry=seed["industry"],
            headquarters_location=seed["location"],
            employee_count=seed["employees"],
            revenue=seed["revenue"],
            fiscal_year="2025",
            data_source_type="synthetic",
            listing_country="日本",
            is_public_company=True,
            selection_reason="業種分散とCRE営業デモの比較容易性を目的とした合成サンプル企業です。",
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
            retrieved_at=datetime.now(UTC),
            source_note="Phase 3.5合成デモ用のサンプルIR文書です。",
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
