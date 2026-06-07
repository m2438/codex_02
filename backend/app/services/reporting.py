from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.models import CRESignal, Company, Document, FinancialMetric, Score
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


def generate_company_report(
    *,
    company: Company,
    latest_metric: FinancialMetric | None,
    latest_score: Score | None,
) -> CompanyReportResult:
    """Generate a Japanese Markdown report from stored database records."""

    generated_at = datetime.now(UTC)
    signals = sorted(company.cre_signals, key=lambda signal: signal.id)
    documents = sorted(company.documents, key=lambda document: document.id)
    title = f"{company.name} CRE営業仮説レポート"
    markdown = "\n".join(
        [
            f"# {title}",
            "",
            "## Executive summary",
            _executive_summary(company=company, score=latest_score, signals=signals),
            "",
            "## CRE sales priority",
            _priority_section(score=latest_score),
            "",
            "## Detected CRE-related signals",
            _signals_section(signals=signals, documents=documents),
            "",
            "## Financial observations",
            _financial_section(metric=latest_metric),
            "",
            "## Suggested sales hypothesis",
            _sales_hypothesis(company=company, signals=signals, metric=latest_metric),
            "",
            "## Recommended first approach",
            _first_approach(score=latest_score, signals=signals),
            "",
            "## Evidence and source documents",
            _evidence_section(signals=signals, documents=documents),
            "",
            "## Caveats",
            _caveats_section(),
            "",
        ]
    )
    return CompanyReportResult(
        company_id=company.id,
        title=title,
        markdown_content=markdown,
        generation_status="generated",
        generated_at=generated_at,
        generated_by="phase3_report_service",
        signal_count=len(signals),
    )


def _executive_summary(*, company: Company, score: Score | None, signals: list[CRESignal]) -> str:
    priority = score.priority_label if score else "未評価"
    total_score = f"{score.total_score}点" if score else "未評価"
    signal_types = "、".join(dict.fromkeys(signal.signal_type for signal in signals)) or "明確なCREシグナルなし"
    return (
        f"{company.name}は{company.industry}の{company.market}上場サンプル企業です。"
        f"現在のCRE営業優先度は **{priority}（{total_score}）** で、"
        f"主な検出シグナルは **{signal_types}** です。"
        "初回接点では、公開IR風サンプル文書の根拠に基づき、拠点・投資・働き方の変化を確認することが有効です。"
    )


def _priority_section(*, score: Score | None) -> str:
    if score is None:
        return "- 優先度: 未評価\n- 理由: スコア情報が未登録です。"
    return "\n".join(
        [
            f"- 優先度: **{score.priority_label}**",
            f"- 総合スコア: **{score.total_score}点**",
            f"- CREシグナル: {score.signal_score}点",
            f"- 財務余力: {score.financial_score}点",
            f"- 戦略イベント: {score.strategic_event_score}点",
            f"- 提案適合度: {score.fit_score}点",
            f"- 判定理由: {score.explanation}",
        ]
    )


def _signals_section(*, signals: list[CRESignal], documents: list[Document]) -> str:
    if not signals:
        mock_signals = [signal for document in documents for signal in extract_cre_signals_mock(document=document)]
        if not mock_signals:
            return "- 現時点で根拠付きCREシグナルは検出されていません。"
        return "\n".join(
            f"- **{signal.signal_type}**: {signal.summary}（信頼度: {signal.confidence}）"
            for signal in mock_signals
        )
    return "\n".join(
        f"- **{signal.signal_type}**: {signal.description}（信頼度: {signal.confidence}）"
        for signal in signals
    )


def _financial_section(*, metric: FinancialMetric | None) -> str:
    if metric is None:
        return "- 財務メトリクスは未登録です。"
    return "\n".join(
        [
            f"- 対象年度: FY{metric.fiscal_year}",
            f"- 売上成長率: {metric.revenue_growth_pct:.1f}%",
            f"- 営業利益率: {metric.operating_margin_pct:.1f}%",
            f"- 設備投資額: {metric.capex_amount:,}百万円",
            f"- 現預金等: {metric.cash_and_equivalents:,}百万円",
            f"- 観察コメント: {metric.segment_change_note}",
        ]
    )


def _sales_hypothesis(*, company: Company, signals: list[CRESignal], metric: FinancialMetric | None) -> str:
    signal_types = {signal.signal_type for signal in signals}
    hypotheses = []
    if {"拠点再編", "物流再編", "海外展開"} & signal_types:
        hypotheses.append("拠点ポートフォリオ再配置や新規拠点整備の検討余地がある。")
    if {"働き方改革", "本社機能見直し"} & signal_types:
        hypotheses.append("本社・オフィス機能の最適化、集約、面積見直しの検討余地がある。")
    if {"設備投資", "資産売却"} & signal_types:
        hypotheses.append("投資計画や保有資産見直しと連動したCRE戦略テーマがある。")
    if metric and metric.capex_amount >= 100_000:
        hypotheses.append("設備投資額が大きく、投資前後の施設計画・不動産コスト管理を提案できる可能性がある。")
    if not hypotheses:
        hypotheses.append("既存シグナルは限定的なため、経営課題ヒアリングを通じてCRE論点を確認する。")
    return "\n".join(f"- {company.name}では{hypothesis}" for hypothesis in hypotheses)


def _first_approach(*, score: Score | None, signals: list[CRESignal]) -> str:
    if score is not None:
        base_action = score.recommended_action
    else:
        base_action = "IR文書の根拠を提示し、CRE課題の有無を確認する。"
    top_signal = signals[0].signal_type if signals else "CRE戦略"
    return "\n".join(
        [
            f"- 初回面談では「{top_signal}」を入口テーマとして、経営企画・総務・不動産管掌部門に仮説を提示する。",
            f"- 推奨アクション: {base_action}",
            "- 提案資料では、根拠テキスト、想定インパクト、確認したい論点を1枚に整理する。",
        ]
    )


def _evidence_section(*, signals: list[CRESignal], documents: list[Document]) -> str:
    signal_lines = [
        f"- {signal.signal_type}: \"{signal.evidence_text}\"  \n  出典: {signal.source_reference}"
        for signal in signals
    ]
    document_lines = [
        f"- 文書ID {document.id}: {document.title} / {document.source_name} / "
        f"{document.published_date.isoformat() if document.published_date else '日付未設定'}"
        for document in documents
    ]
    if not signal_lines:
        signal_lines = ["- 根拠付きCREシグナルは未登録です。"]
    if not document_lines:
        document_lines = ["- 参照文書は未登録です。"]
    return "\n".join(["### 根拠テキスト", *signal_lines, "", "### 参照文書", *document_lines])


def _caveats_section() -> str:
    return "\n".join(
        [
            "- 本レポートはデモ用のサンプルデータまたは公開IR文書を前提に生成しています。",
            "- 実在企業の投資判断、与信判断、法務判断を目的としたものではありません。",
            "- 根拠が不足するシグナルは低信頼として扱い、営業時には一次情報で再確認してください。",
            "- OpenAI APIモードを利用する場合も、APIキーはバックエンド環境変数でのみ管理し、フロントエンドには露出しません。",
        ]
    )
