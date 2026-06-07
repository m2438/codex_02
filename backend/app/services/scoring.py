from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class FinancialInputs:
    revenue_growth_pct: float
    operating_margin_pct: float
    capex_amount: int
    revenue: int = 0
    cash_and_equivalents: int = 0
    total_assets: int = 0


@dataclass(frozen=True)
class SignalInputs:
    signal_type: str
    confidence: str


@dataclass(frozen=True)
class ComponentScoreDetail:
    score: int
    max_points: int
    reason: str


@dataclass(frozen=True)
class ScoreResult:
    total_score: int
    priority_label: str
    signal_score: int
    financial_score: int
    strategic_event_score: int
    fit_score: int
    explanation: str
    recommended_action: str
    calculated_at: datetime
    component_reasons: dict[str, str]

    @property
    def component_scores(self) -> dict[str, int]:
        return {
            "signal_score": self.signal_score,
            "financial_score": self.financial_score,
            "strategic_event_score": self.strategic_event_score,
            "fit_score": self.fit_score,
        }

    @property
    def component_details(self) -> dict[str, ComponentScoreDetail]:
        return build_component_details(component_scores=self.component_scores, component_reasons=self.component_reasons)


COMPONENT_MAX_POINTS = {
    "signal_score": 35,
    "financial_score": 25,
    "strategic_event_score": 25,
    "fit_score": 15,
}

COMPONENT_LABELS = {
    "signal_score": "CRE関連シグナル",
    "financial_score": "財務・投資余力",
    "strategic_event_score": "戦略イベント",
    "fit_score": "提案適合度",
}

CONFIDENCE_WEIGHTS = {
    "high": 12,
    "medium": 8,
    "low": 4,
}

STRATEGIC_SIGNAL_TYPES = {
    "拠点再編",
    "設備投資",
    "海外展開",
    "本社機能見直し",
    "資産売却",
    "物流再編",
    "脱炭素",
    "建替え",
    "BCP",
    "R&D拠点拡張",
    "構造改革",
}
FIT_SIGNAL_TYPES = {
    "拠点再編",
    "本社機能見直し",
    "働き方改革",
    "設備投資",
    "物流再編",
    "資産売却",
    "脱炭素",
    "建替え",
    "BCP",
    "R&D拠点拡張",
}
HIGH_FIT_SIGNAL_TYPES = {"拠点再編", "物流再編", "本社機能見直し", "資産売却", "建替え", "R&D拠点拡張"}


def priority_label(total_score: int) -> str:
    if total_score >= 85:
        return "高"
    if total_score >= 50:
        return "中"
    return "低"


def _confidence_reason(signals: list[SignalInputs], score: int) -> str:
    high_count = sum(1 for signal in signals if signal.confidence == "high")
    medium_count = sum(1 for signal in signals if signal.confidence == "medium")
    low_count = sum(1 for signal in signals if signal.confidence == "low")
    unique_types = len({signal.signal_type for signal in signals})
    return (
        f"CRE関連シグナル{len(signals)}件（高{high_count}件・中{medium_count}件・低{low_count}件）と"
        f"テーマの多様性{unique_types}種類を評価し、最大35点中{score}点としました。"
    )


def _financial_score(financial: FinancialInputs) -> tuple[int, str]:
    revenue_points = 7 if financial.revenue >= 1_000_000 else 5 if financial.revenue >= 500_000 else 3 if financial.revenue else 0
    capex_points = 8 if financial.capex_amount >= 250_000 else 6 if financial.capex_amount >= 120_000 else 4 if financial.capex_amount >= 50_000 else 1
    cash_points = (
        5
        if financial.cash_and_equivalents >= 700_000
        else 4
        if financial.cash_and_equivalents >= 300_000
        else 2
        if financial.cash_and_equivalents >= 80_000
        else 0
    )
    growth_points = 3 if financial.revenue_growth_pct >= 6 else 2 if financial.revenue_growth_pct >= 2 else 1
    margin_points = 2 if financial.operating_margin_pct >= 9 else 1 if financial.operating_margin_pct >= 4 else 0
    score = min(COMPONENT_MAX_POINTS["financial_score"], revenue_points + capex_points + cash_points + growth_points + margin_points)
    reason = (
        f"売上規模{revenue_points}点、設備投資{capex_points}点、現預金等{cash_points}点、"
        f"成長率{growth_points}点、営業利益率{margin_points}点を積み上げ、最大25点中{score}点としました。"
    )
    return score, reason


def _strategic_event_score(signals: list[SignalInputs]) -> tuple[int, str]:
    strategic_types = [signal.signal_type for signal in signals if signal.signal_type in STRATEGIC_SIGNAL_TYPES]
    unique_strategic_types = set(strategic_types)
    confidence_bonus = sum(2 for signal in signals if signal.signal_type in STRATEGIC_SIGNAL_TYPES and signal.confidence == "high")
    score = min(COMPONENT_MAX_POINTS["strategic_event_score"], len(unique_strategic_types) * 7 + confidence_bonus)
    reason = (
        f"中計・構造改革・資本効率・拠点投資に接続しやすいテーマ{len(unique_strategic_types)}種類"
        f"（{ '、'.join(unique_strategic_types) if unique_strategic_types else '該当なし' }）と高信頼度補正を評価し、"
        f"最大25点中{score}点としました。"
    )
    return score, reason


def _fit_score(signals: list[SignalInputs], financial: FinancialInputs) -> tuple[int, str]:
    signal_types = {signal.signal_type for signal in signals}
    core_fit_points = min(9, len(signal_types & FIT_SIGNAL_TYPES) * 3)
    high_fit_points = min(4, len(signal_types & HIGH_FIT_SIGNAL_TYPES) * 2)
    investment_points = 2 if financial.capex_amount >= 120_000 or financial.cash_and_equivalents >= 300_000 else 0
    score = min(COMPONENT_MAX_POINTS["fit_score"], core_fit_points + high_fit_points + investment_points)
    reason = (
        f"CRE戦略、PM/CM、再開発、遊休資産活用、不動産ポートフォリオ最適化に直結するテーマ適合性"
        f"{core_fit_points + high_fit_points}点と投資余力補正{investment_points}点により、最大15点中{score}点としました。"
    )
    return score, reason


def build_component_details(
    *, component_scores: dict[str, int], component_reasons: dict[str, str] | None = None
) -> dict[str, ComponentScoreDetail]:
    reasons = component_reasons or {}
    return {
        key: ComponentScoreDetail(
            score=component_scores[key],
            max_points=COMPONENT_MAX_POINTS[key],
            reason=reasons.get(key, f"{COMPONENT_LABELS[key]}を評価し、最大{COMPONENT_MAX_POINTS[key]}点中{component_scores[key]}点としました。"),
        )
        for key in COMPONENT_MAX_POINTS
    }


def calculate_sales_priority_score(
    *,
    signals: list[SignalInputs],
    financial: FinancialInputs,
    company_name: str = "対象企業",
) -> ScoreResult:
    """Calculate an explainable 100-point CRE sales priority score from sample data."""

    unique_signal_bonus = min(6, max(0, len({signal.signal_type for signal in signals}) - 1) * 2)
    raw_signal_score = sum(CONFIDENCE_WEIGHTS.get(signal.confidence, 4) for signal in signals) + unique_signal_bonus
    signal_score = min(COMPONENT_MAX_POINTS["signal_score"], raw_signal_score)
    financial_score, financial_reason = _financial_score(financial)
    strategic_event_score, strategic_reason = _strategic_event_score(signals)
    fit_score, fit_reason = _fit_score(signals, financial)

    component_reasons = {
        "signal_score": _confidence_reason(signals, signal_score),
        "financial_score": financial_reason,
        "strategic_event_score": strategic_reason,
        "fit_score": fit_reason,
    }
    total_score = min(100, signal_score + financial_score + strategic_event_score + fit_score)
    label = priority_label(total_score)

    explanation = (
        f"{company_name}は、根拠付きCRE関連シグナル、財務規模・投資余力、戦略イベント、提案適合度を"
        f"合計100点満点で評価した結果、{total_score}点となり営業優先度を{label}と判定しました。"
        "高判定は85点以上、中判定は50点以上、低判定は50点未満です。"
    )
    if label == "高":
        recommended_action = (
            "経営企画・総務・不動産管掌部門に対し、根拠シグナルを提示したうえで、"
            "拠点ポートフォリオ診断、投資計画とCRE戦略の整合、PM/CM支援余地を早期に確認する。"
        )
    elif label == "中":
        recommended_action = (
            "IR上の変化テーマを入口に、拠点再編・設備投資・本社機能見直しの具体化状況をヒアリングし、"
            "課題が顕在化している部門を特定する。"
        )
    else:
        recommended_action = (
            "現時点では継続モニタリングを基本とし、中期経営計画や投資計画の更新時にCRE論点の有無を再確認する。"
        )

    return ScoreResult(
        total_score=total_score,
        priority_label=label,
        signal_score=signal_score,
        financial_score=financial_score,
        strategic_event_score=strategic_event_score,
        fit_score=fit_score,
        explanation=explanation,
        recommended_action=recommended_action,
        calculated_at=datetime.now(UTC),
        component_reasons=component_reasons,
    )
