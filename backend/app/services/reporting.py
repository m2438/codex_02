from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.models import CRESignal, Company, Document, FinancialMetric, Score
from app.services.scoring import COMPONENT_LABELS, build_component_details
from app.services.signal_extraction import extract_cre_signals_mock


@dataclass(frozen=True)
class CompanyReportResult:
    company_id: int
    title: str
    markdown_content: str
    generation_status: str
    generated_at: datetime
    generated_by: str
    signal_count: int
    structured_report: dict[str, object]


def format_million_yen_to_oku(value: int) -> str:
    """Format values stored in million yen as oku-yen for Japanese business reports."""

    oku = value / 100
    if oku >= 10_000:
        return f"{oku / 10_000:.1f}兆円"
    return f"{oku:,.0f}億円"


def generate_company_report(
    *,
    company: Company,
    latest_metric: FinancialMetric | None,
    latest_score: Score | None,
) -> CompanyReportResult:
    """Generate a Japanese Markdown CRE sales intelligence report from stored records."""

    generated_at = datetime.now(UTC)
    signals = sorted(company.cre_signals, key=lambda signal: signal.id)
    documents = sorted(company.documents, key=lambda document: document.id)
    title = f"{company.name} CRE営業仮説レポート"
    sections = [
        {"id": "executive_summary", "number": 1, "title": "エグゼクティブサマリー", "body": _executive_summary(company=company, score=latest_score, signals=signals, metric=latest_metric)},
        {"id": "priority", "number": 2, "title": "CRE営業優先度の判定", "body": _priority_section(score=latest_score)},
        {"id": "score_details", "number": 3, "title": "スコア内訳と評点理由", "body": _score_detail_section(score=latest_score, signals=signals, metric=latest_metric)},
        {"id": "signal_analysis", "number": 4, "title": "CRE需要兆候の詳細分析", "body": _signals_section(signals=signals, documents=documents)},
        {"id": "financial_view", "number": 5, "title": "財務・投資余力に関する所見", "body": _financial_section(company=company, metric=latest_metric)},
        {"id": "strategic_connection", "number": 6, "title": "経営課題・中期施策との接続仮説", "body": _strategic_connection(company=company, signals=signals, metric=latest_metric)},
        {"id": "proposal_themes", "number": 7, "title": "想定されるCRE提案テーマ", "body": _sales_hypothesis(company=company, signals=signals, metric=latest_metric)},
        {"id": "first_approach", "number": 8, "title": "初回アプローチ仮説", "body": _first_approach(score=latest_score, signals=signals)},
        {"id": "hearing_questions", "number": 9, "title": "追加ヒアリングで確認すべき事項", "body": _hearing_questions(signals=signals, metric=latest_metric)},
        {"id": "evidence", "number": 10, "title": "根拠資料・根拠文", "body": _evidence_section(signals=signals, documents=documents)},
        {"id": "caveats", "number": 11, "title": "留意事項", "body": _caveats_section(company=company)},
    ]
    markdown_parts = [f"# {title}", ""]
    for section in sections:
        markdown_parts.extend([f"## {section['number']}. {section['title']}", str(section["body"]), ""])
    markdown = "\n".join(markdown_parts)
    structured_report = {
        "title": title,
        "disclaimer": "本分析は公開情報に基づく営業仮説であり、当該企業の正式なCRE方針や実際の提案機会を断定するものではありません。",
        "sections": [{**section, "items": _plain_items(str(section["body"]))} for section in sorted(sections, key=lambda section: int(section["number"]))],
        "score_components": _structured_score_components(score=latest_score, signals=signals, metric=latest_metric),
        "documents": [_document_payload(document) for document in documents],
        "signals": [_signal_payload(signal) for signal in signals],
    }
    return CompanyReportResult(
        company_id=company.id,
        title=title,
        markdown_content=markdown,
        generation_status="generated",
        generated_at=generated_at,
        generated_by="phase4a_report_service",
        signal_count=len(signals),
        structured_report=structured_report,
    )


def _executive_summary(*, company: Company, score: Score | None, signals: list[CRESignal], metric: FinancialMetric | None) -> str:
    priority = score.priority_label if score else "未評価"
    total_score = f"{score.total_score}点" if score else "未評価"
    signal_types = "、".join(dict.fromkeys(signal.signal_type for signal in signals)) or "明確なCREシグナルなし"
    revenue_text = format_million_yen_to_oku(company.revenue)
    capex_text = format_million_yen_to_oku(metric.capex_amount) if metric else "未登録"
    if company.data_source_type == "public_demo":
        return (
            f"{company.name}は{company.industry}の{company.market}上場企業であり、本レポートは公開IR資料に基づく営業仮説です。"
            f"売上高は{revenue_text}、直近設備投資額は{capex_text}としてスコアリング入力に正規化しています。"
            f"公開情報から読み取れるCRE関連の確認候補は **{signal_types}** です。"
            f"営業優先度はスコアリングロジックに基づき **{priority}（{total_score}）** と算定されますが、"
            "これは当該企業の正式なCRE方針や実際の提案機会を断定するものではありません。"
            "実営業では一次情報、個別不動産情報、顧客ヒアリングによる追加検証が必要です。"
        )
    return (
        f"{company.name}は{company.industry}の{company.market}上場を想定した合成サンプル企業です。"
        f"売上高は{revenue_text}、直近設備投資額は{capex_text}の設定で、"
        f"検出シグナルは **{signal_types}** です。"
        f"CRE営業優先度は **{priority}（{total_score}）** と判定されます。"
        "本判定は、根拠文、財務指標、戦略イベント、CRE支援テーマへの適合度を接続したデモ用分析であり、"
        "実際の営業活動前には公開資料・一次情報・顧客ヒアリングによる追加検証が必要です。"
    )


def _priority_section(*, score: Score | None) -> str:
    if score is None:
        return "- 優先度: 未評価\n- 判定要約: スコア情報が未登録のため、公開情報の追加確認後に再評価します。"
    summary = "重点アプローチ候補" if score.priority_label == "高" else "継続確認候補" if score.priority_label == "中" else "モニタリング候補"
    return "\n".join(
        [
            f"- 優先度: **{score.priority_label}**",
            f"- 総合スコア: **{score.total_score}点 / 100点**",
            f"- 判定要約: {summary}として、公開IR資料で確認できるCRE関連テーマを初回面談の確認仮説に整理します。",
            "- 本判定は公開情報に基づく営業仮説であり、正式方針・案件化状況は一次情報とヒアリングで確認します。",
        ]
    )


def _score_detail_section(*, score: Score | None, signals: list[CRESignal], metric: FinancialMetric | None) -> str:
    if score is None:
        return "- スコア内訳は未登録です。"
    signal_types = "、".join(dict.fromkeys(signal.signal_type for signal in signals)) or "該当なし"
    high_signals = [signal.signal_type for signal in signals if signal.confidence == "high"]
    financial_context = "財務指標は未登録です。"
    if metric is not None:
        financial_context = (
            f"FY{metric.fiscal_year}の売上成長率{metric.revenue_growth_pct:.1f}%、営業利益率{metric.operating_margin_pct:.1f}%、"
            f"設備投資額{format_million_yen_to_oku(metric.capex_amount)}、現預金等{format_million_yen_to_oku(metric.cash_and_equivalents)}を確認。"
        )
    lines = [
        f"- **CRE関連シグナル（signal_score）**: {score.signal_score}点  ",
        f"  - 評価対象: 登録済みCREシグナル（{signal_types}）と各シグナルの根拠文。",
        f"  - 評価観点: 拠点再編、工場・研究所・物流拠点、設備投資、老朽化・更新、BCP、脱炭素、省エネ、働き方などが複数資料で確認できるか。",
        f"  - 根拠・判断理由: 高信頼シグナルは{ '、'.join(high_signals) if high_signals else '該当なし' }です。公開IR資料の根拠文から、CRE観点で追加確認すべき拠点・投資・施設運営テーマの幅と具体性を評価しました。",
        f"- **財務・投資余力（financial_score）**: {score.financial_score}点  ",
        "  - 評価対象: 売上高、売上成長率、営業利益率、設備投資額、現預金等。",
        "  - 評価観点: 大型投資・施設更新・拠点再配置を検討し得る事業規模と投資余力が公開資料上の数値と整合するか。",
        f"  - 根拠・判断理由: {financial_context} 財務数値は提案機会の断定ではなく、投資前レビュー、PM/CM、更新投資ロードマップの検討余地を測る補助指標として扱いました。",
        f"- **戦略イベント（strategic_event_score）**: {score.strategic_event_score}点  ",
        f"  - 評価対象: {signal_types}のうち、中期施策、構造改革、資本効率、事業ポートフォリオ、拠点投資に接続しやすいテーマ。",
        "  - 評価観点: 公開資料上の経営課題とCRE論点が同じ文脈で説明できるか。",
        "  - 根拠・判断理由: 設備投資、脱炭素、BCP、構造改革などが確認できる場合、施設・不動産を単体ではなく経営施策の実行基盤として検討する余地があると評価しました。",
        f"- **提案適合度（fit_score）**: {score.fit_score}点  ",
        "  - 評価対象: CRE戦略、PM/CM、拠点ポートフォリオ診断、遊休資産活用、省エネ改修、ワークプレイス改革などへの接続性。",
        "  - 評価観点: 初回面談で根拠資料を示しながら、過度に断定せず確認質問として提示できるテーマか。",
        "  - 根拠・判断理由: シグナルと財務・投資余力が同時に確認できるテーマは、公開情報ベースの仮説として提案入口を設計しやすい一方、正式な方針・案件化状況は追加ヒアリングで確認が必要です。",
        f"- **合計**: {score.total_score}点 / 100点",
    ]
    return "\n".join(lines)


def _plain_items(body: str) -> list[str]:
    return [line[2:].strip() for line in body.splitlines() if line.startswith("- ")]


def _document_payload(document: Document) -> dict[str, object]:
    return {
        "document_id": document.id,
        "title": document.title,
        "document_type": document.document_type,
        "fiscal_year": document.fiscal_year,
        "source_url": document.source_url,
        "source_note": document.source_note,
        "document_language": getattr(document, "document_language", "ja"),
        "published_date": document.published_date.isoformat() if document.published_date else None,
    }


def _signal_payload(signal: CRESignal) -> dict[str, object]:
    return {
        "signal_type": signal.signal_type,
        "title": signal.title,
        "confidence": signal.confidence,
        "evidence_text": signal.evidence_text,
        "source_reference": signal.source_reference,
    }


def _structured_score_components(*, score: Score | None, signals: list[CRESignal], metric: FinancialMetric | None) -> list[dict[str, object]]:
    if score is None:
        return []

    signal_types = "、".join(dict.fromkeys(signal.signal_type for signal in signals)) or "該当なし"
    high_signals = "、".join(dict.fromkeys(signal.signal_type for signal in signals if signal.confidence == "high")) or "該当なし"
    financial_context = "財務指標は未登録です。"
    if metric is not None:
        financial_context = (
            f"FY{metric.fiscal_year}の売上成長率{metric.revenue_growth_pct:.1f}%、営業利益率{metric.operating_margin_pct:.1f}%、"
            f"設備投資額{format_million_yen_to_oku(metric.capex_amount)}、現預金等{format_million_yen_to_oku(metric.cash_and_equivalents)}。"
        )

    return [
        {
            "label": "CRE関連シグナル",
            "evaluation_target": f"登録済みCREシグナル（{signal_types}）と各シグナルの根拠文",
            "evaluation_viewpoint": "拠点再編、工場・研究所・物流拠点、設備投資、老朽化・更新、BCP、脱炭素、省エネ、働き方などが公開資料上で具体的に確認できるか。",
            "rationale": f"高信頼シグナルは{high_signals}です。公開IR資料の根拠文から、CRE観点で追加確認すべき拠点・投資・施設運営テーマの幅と具体性を評価しました。",
            "score_text": f"{score.signal_score}/35",
            "details": [
                f"評価対象: 登録済みCREシグナル（{signal_types}）と各シグナルの根拠文。",
                "評価観点: 拠点再編、工場・研究所・物流拠点、設備投資、老朽化・更新、BCP、脱炭素、省エネ、働き方などが公開資料上で具体的に確認できるか。",
                f"根拠・判断理由: 高信頼シグナルは{high_signals}です。公開IR資料の根拠文から、CRE観点で追加確認すべき拠点・投資・施設運営テーマの幅と具体性を評価しました。",
            ],
        },
        {
            "label": "財務・投資余力",
            "evaluation_target": "売上高、売上成長率、営業利益率、設備投資額、現預金等",
            "evaluation_viewpoint": "大型投資・施設更新・拠点再配置を検討し得る事業規模と投資余力が、公開資料上の数値と整合するか。",
            "rationale": f"{financial_context} 財務数値は提案機会の断定ではなく、投資前レビュー、PM/CM、更新投資ロードマップの検討余地を測る補助指標として扱いました。",
            "score_text": f"{score.financial_score}/25",
            "details": [
                "評価対象: 売上高、売上成長率、営業利益率、設備投資額、現預金等。",
                "評価観点: 大型投資・施設更新・拠点再配置を検討し得る事業規模と投資余力が、公開資料上の数値と整合するか。",
                f"根拠・判断理由: {financial_context} 財務数値は提案機会の断定ではなく、投資前レビュー、PM/CM、更新投資ロードマップの検討余地を測る補助指標として扱いました。",
            ],
        },
        {
            "label": "戦略イベント",
            "evaluation_target": f"{signal_types}のうち、中期施策、構造改革、資本効率、事業ポートフォリオ、拠点投資に接続しやすいテーマ",
            "evaluation_viewpoint": "公開資料上の経営課題とCRE論点が、同じ経営文脈で説明できるか。",
            "rationale": "設備投資、脱炭素、BCP、構造改革などが確認できる場合、施設・不動産を単体ではなく経営施策の実行基盤として検討する余地があると評価しました。",
            "score_text": f"{score.strategic_event_score}/25",
            "details": [
                f"評価対象: {signal_types}のうち、中期施策、構造改革、資本効率、事業ポートフォリオ、拠点投資に接続しやすいテーマ。",
                "評価観点: 公開資料上の経営課題とCRE論点が、同じ経営文脈で説明できるか。",
                "根拠・判断理由: 設備投資、脱炭素、BCP、構造改革などが確認できる場合、施設・不動産を単体ではなく経営施策の実行基盤として検討する余地があると評価しました。",
            ],
        },
        {
            "label": "提案適合度",
            "evaluation_target": "CRE戦略、PM/CM、拠点ポートフォリオ診断、遊休資産活用、省エネ改修、ワークプレイス改革などへの接続性",
            "evaluation_viewpoint": "初回面談で根拠資料を示しながら、過度に断定せず確認質問として提示できるテーマか。",
            "rationale": "シグナルと財務・投資余力が同時に確認できるテーマは、公開情報ベースの仮説として提案入口を設計しやすい一方、正式な方針・案件化状況は追加ヒアリングで確認が必要です。",
            "score_text": f"{score.fit_score}/15",
            "details": [
                "評価対象: CRE戦略、PM/CM、拠点ポートフォリオ診断、遊休資産活用、省エネ改修、ワークプレイス改革などへの接続性。",
                "評価観点: 初回面談で根拠資料を示しながら、過度に断定せず確認質問として提示できるテーマか。",
                "根拠・判断理由: シグナルと財務・投資余力が同時に確認できるテーマは、公開情報ベースの仮説として提案入口を設計しやすい一方、正式な方針・案件化状況は追加ヒアリングで確認が必要です。",
            ],
        },
    ]


def _signals_section(*, signals: list[CRESignal], documents: list[Document]) -> str:
    if not signals:
        mock_signals = [signal for document in documents for signal in extract_cre_signals_mock(document=document)]
        if not mock_signals:
            return "- 現時点で根拠付きCREシグナルは検出されていません。低信頼として継続モニタリングが妥当です。"
        return "\n".join(
            f"- **{signal.signal_type}**: {signal.summary}（信頼度: {signal.confidence}）。根拠が限定的なため追加確認が必要です。"
            for signal in mock_signals
        )
    lines = []
    for signal in signals:
        confidence_note = "営業仮説の入口として扱いやすい" if signal.confidence == "high" else "追加ヒアリングで具体化が必要"
        lines.append(
            f"- **{signal.signal_type}**（信頼度: {signal.confidence}）: {signal.description} "
            f"根拠文は「{signal.evidence_text}」であり、{confidence_note}シグナルです。"
        )
    lines.append(
        "- 上記シグナルは単独では断定材料ではありません。公開情報からはCRE需要の可能性が示唆されるにとどまり、"
        "拠点ポートフォリオ、投資計画、不動産コスト、BCP、脱炭素対応の実態は追加確認が必要です。"
    )
    return "\n".join(lines)


def _financial_section(*, company: Company, metric: FinancialMetric | None) -> str:
    if metric is None:
        return "- 財務関連指標は未登録です。財務余力の評価は保留してください。"

    insights = _financial_insights(metric=metric)
    return "\n".join(
        [
            f"- 対象年度: FY{metric.fiscal_year}",
            f"- 売上高: {format_million_yen_to_oku(company.revenue)}",
            f"- 売上成長率: {metric.revenue_growth_pct:.1f}%",
            f"- 営業利益率: {metric.operating_margin_pct:.1f}%",
            f"- 設備投資額: {format_million_yen_to_oku(metric.capex_amount)}",
            f"- 現預金等: {format_million_yen_to_oku(metric.cash_and_equivalents)}",
            *[f"- 所見: {insight}" for insight in insights],
        ]
    )


def _financial_insights(*, metric: FinancialMetric) -> list[str]:
    insights: list[str] = []
    if metric.revenue_growth_pct >= 5.0:
        insights.append("売上成長率が高く、事業拡大に伴う営業・物流・生産・研究開発拠点の増強需要を確認する余地があります。")
    elif metric.revenue_growth_pct <= 1.0:
        insights.append("売上成長率が低位のため、拠点再編、低稼働資産の見直し、既存ポートフォリオの資産効率改善を確認する段階です。")
    else:
        insights.append("売上成長率は安定圏にあり、新規拡張と既存拠点最適化のどちらを優先するかを事業別に確認する必要があります。")

    if metric.operating_margin_pct >= 12.0:
        insights.append("営業利益率が高く、拠点高度化、省エネ、BCP、研究開発・製造品質向上への投資余力を仮説化できます。")
    elif metric.operating_margin_pct <= 5.0:
        insights.append("営業利益率が低位のため、大型新規投資よりも既存資産活用、賃借条件見直し、保全・エネルギーコスト改善型CRE施策が入口になり得ます。")
    else:
        insights.append("営業利益率は中位であり、投資採算性を確認しながら更新投資・省エネ投資・拠点再配置を選別する提案が適します。")

    if metric.capex_amount >= 300_000:
        insights.append("設備投資額が大きく、工場・研究所・物流施設の建替え、設備更新、施工計画、PM/CM支援の具体論点につながりやすい状況です。")
    elif metric.capex_amount <= 100_000:
        insights.append("設備投資額は相対的に小さく、当面の大型投資案件よりも既存拠点の用途見直し、保全計画、ポートフォリオ整理を優先確認します。")
    else:
        insights.append("設備投資額は中位であり、進行中投資の有無、更新周期、発注者側のプロジェクト管理体制を確認する価値があります。")

    if metric.cash_and_equivalents >= 1_000_000:
        insights.append("現預金等が大きく、投資余力、M&A後の拠点統合、遊休資産活用、建替え・再開発の優先順位を確認できます。")
    elif metric.cash_and_equivalents <= 250_000:
        insights.append("現預金等は限定的であり、段階投資、投資回収、外部資金、リース・賃借戦略を含めたCRE施策の採算性確認が重要です。")
    else:
        insights.append("現預金等は一定水準にあり、自己資金投資と賃借・外部資金活用のバランスを確認しながらCREテーマを絞り込めます。")
    return insights


def _strategic_connection(*, company: Company, signals: list[CRESignal], metric: FinancialMetric | None) -> str:
    signal_types = {signal.signal_type for signal in signals}
    points = []
    if {"構造改革", "資産売却", "拠点再編"} & signal_types:
        points.append("構造改革・資本効率改善の文脈では、遊休資産の活用、売却、賃貸化、拠点統合による固定費最適化が論点になります。")
    if {"設備投資", "建替え", "R&D拠点拡張"} & signal_types:
        points.append("成長投資・研究開発投資の文脈では、施設基本構想、投資予算管理、工期・品質・コストを統合するPM/CM支援が接続しやすいと考えられます。")
    if {"脱炭素", "BCP", "物流再編"} & signal_types:
        points.append("サステナビリティ、BCP、物流効率化の文脈では、拠点配置、エネルギー性能、バックアップ拠点、配送網の再設計を一体で確認する必要があります。")
    if metric and metric.cash_and_equivalents >= 300_000:
        points.append("現預金等の設定が相対的に厚く、投資余力や財務安全性を踏まえた中長期CREロードマップ提案の余地があります。")
    if not points:
        points.append("現時点のシグナルは限定的であるため、中期経営計画の更新、主要拠点投資、組織再編の有無を継続的に確認する段階です。")
    return "\n".join(f"- {point}" for point in points)


def _sales_hypothesis(*, company: Company, signals: list[CRESignal], metric: FinancialMetric | None) -> str:
    signal_types = {signal.signal_type for signal in signals}
    hypotheses = []
    if {"拠点再編", "物流再編", "海外展開", "BCP"} & signal_types:
        hypotheses.append("国内外拠点ポートフォリオ診断、物流・営業・生産拠点の再配置シナリオ策定")
    if {"働き方改革", "本社機能見直し"} & signal_types:
        hypotheses.append("本社・オフィス機能の集約、面積最適化、ハイブリッドワーク前提のワークプレイス戦略")
    if {"設備投資", "建替え", "R&D拠点拡張"} & signal_types:
        hypotheses.append("大型投資・建替え・R&D拠点整備に対する基本構想、PM/CM、コスト・スケジュール管理")
    if {"資産売却", "構造改革"} & signal_types:
        hypotheses.append("遊休資産・低稼働資産の棚卸し、売却/賃貸/再開発の比較検討、ROIC改善に向けたCRE施策")
    if {"脱炭素"} & signal_types:
        hypotheses.append("保有施設の省エネ診断、ZEB/再エネ導入ロードマップ、脱炭素投資とCRE投資計画の統合")
    if metric and metric.capex_amount >= 120_000:
        hypotheses.append("設備投資額の大きさを踏まえた投資前レビュー、プロジェクトガバナンス、発注者支援")
    if not hypotheses:
        hypotheses.append("現時点ではCREテーマの顕在度が低いため、公開資料更新時のモニタリングと初期ヒアリング設計")
    return "\n".join(f"- {theme}" for theme in dict.fromkeys(hypotheses))


def _first_approach(*, score: Score | None, signals: list[CRESignal]) -> str:
    base_action = score.recommended_action if score is not None else "IR文書の根拠を提示し、CRE課題の有無を確認する。"
    top_signal = signals[0].signal_type if signals else "CRE戦略"
    return "\n".join(
        [
            f"- 初回面談では「{top_signal}」を入口テーマとして、経営企画・総務・不動産管掌部門に仮説を提示する。",
            f"- 推奨アクション: {base_action}",
            "- 提案資料では、根拠テキスト、財務・投資余力、想定CREテーマ、確認したい論点を1枚に整理する。",
            "- 断定的な提案ではなく、『公開情報ベースの仮説』として提示し、現在の検討状況と担当部門を確認する。",
        ]
    )


def _hearing_questions(*, signals: list[CRESignal], metric: FinancialMetric | None) -> str:
    questions = [
        "- 中期経営計画、構造改革、資本効率改善施策の中で、拠点・不動産に関するKPIや意思決定テーマはあるか。",
        "- 主要拠点の稼働率、老朽化、BCP、脱炭素対応、更新投資の優先順位はどのように整理されているか。",
        "- CRE、不動産、総務、経営企画、事業部門、財務部門の役割分担と意思決定プロセスはどうなっているか。",
    ]
    if any(signal.signal_type in {"設備投資", "建替え", "R&D拠点拡張"} for signal in signals):
        questions.append("- 大型投資案件について、基本構想、予算管理、発注方式、PM/CM体制に外部支援余地はあるか。")
    if metric and metric.cash_and_equivalents >= 300_000:
        questions.append("- 投資余力をどの領域に振り向ける方針か、CRE投資と事業投資の優先順位は整理されているか。")
    return "\n".join(questions)


def _evidence_section(*, signals: list[CRESignal], documents: list[Document]) -> str:
    signal_lines = [
        f"- {signal.signal_type}: 「{signal.evidence_text}」  \n  出典: {signal.source_reference} / 信頼度: {signal.confidence}"
        for signal in signals
    ]
    document_lines = [
        f"- 文書ID {document.id}: {document.title} / {document.source_name} / "
        f"{document.published_date.isoformat() if document.published_date else '日付未設定'} / サンプル: {document.is_sample}  "
        f"\n  URL: {document.source_url or 'なし'}  "
        f"\n  備考: {document.source_note or 'なし'}"
        for document in documents
    ]
    if not signal_lines:
        signal_lines = ["- 根拠付きCREシグナルは未登録です。"]
    if not document_lines:
        document_lines = ["- 参照文書は未登録です。"]
    return "\n".join(["### 根拠文", *signal_lines, "", "### 参照資料", *document_lines])


def _caveats_section(*, company: Company) -> str:
    common = [
        "- 本レポートは営業デモ用であり、投資判断、与信判断、法務判断を目的としたものではありません。",
        "- 実際の営業活動前には、最新の有価証券報告書、統合報告書、決算説明資料、顧客ヒアリングで追加検証してください。",
        "- 根拠が不足するシグナルは低信頼として扱い、断定ではなく仮説として提示してください。",
        "- OpenAI APIモードを利用する場合も、APIキーはバックエンド環境変数でのみ管理し、フロントエンドには露出しません。",
    ]
    if company.data_source_type == "public_demo":
        return "\n".join(
            [
                "- 本分析は公開情報に基づく営業仮説であり、当該企業の正式なCRE方針や実際の提案機会を断定するものではありません。",
                "- 個別不動産の状況、投資意思決定、担当部門、検討時期は公開資料のみでは確認できないため、一次情報の再確認および個別ヒアリングが必要です。",
                "- 企業の経営状態や保有不動産に関する記述は、公開資料から確認できる範囲の事実とCRE観点の仮説を分けて扱ってください。",
                *common,
            ]
        )
    return "\n".join(
        [
            "- 本レポートはデモ用の合成サンプルデータまたは公開情報ベースの文書を前提に生成しています。",
            "- 企業名、財務数値、シグナルはデモ品質確認用であり、実在企業の開示や営業先情報を示すものではありません。",
            *common,
        ]
    )
