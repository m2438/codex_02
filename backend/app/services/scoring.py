from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class FinancialInputs:
    revenue_growth_pct: float
    operating_margin_pct: float
    capex_amount: int


@dataclass(frozen=True)
class SignalInputs:
    signal_type: str
    confidence: str


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

    @property
    def component_scores(self) -> dict[str, int]:
        return {
            "signal_score": self.signal_score,
            "financial_score": self.financial_score,
            "strategic_event_score": self.strategic_event_score,
            "fit_score": self.fit_score,
        }


CONFIDENCE_WEIGHTS = {
    "high": 10,
    "medium": 7,
    "low": 4,
}

STRATEGIC_SIGNAL_TYPES = {"拠点再編", "設備投資", "海外展開", "本社機能見直し", "資産売却"}
FIT_SIGNAL_TYPES = {"拠点再編", "本社機能見直し", "働き方改革", "設備投資", "物流再編"}


def priority_label(total_score: int) -> str:
    if total_score >= 80:
        return "高"
    if total_score >= 60:
        return "中"
    return "低"


def calculate_sales_priority_score(
    *,
    signals: list[SignalInputs],
    financial: FinancialInputs,
    company_name: str = "対象企業",
) -> ScoreResult:
    """Calculate an explainable CRE sales priority score from sample data."""

    raw_signal_score = sum(CONFIDENCE_WEIGHTS.get(signal.confidence, 4) for signal in signals)
    signal_score = min(30, raw_signal_score)

    growth_points = 10 if financial.revenue_growth_pct >= 8 else 7 if financial.revenue_growth_pct >= 3 else 4
    margin_points = 8 if financial.operating_margin_pct >= 10 else 6 if financial.operating_margin_pct >= 5 else 3
    capex_points = 7 if financial.capex_amount >= 120_000 else 5 if financial.capex_amount >= 60_000 else 2
    financial_score = min(25, growth_points + margin_points + capex_points)

    strategic_event_score = min(
        25,
        sum(8 for signal in signals if signal.signal_type in STRATEGIC_SIGNAL_TYPES),
    )
    fit_score = min(20, 5 + sum(5 for signal in signals if signal.signal_type in FIT_SIGNAL_TYPES))

    total_score = min(100, signal_score + financial_score + strategic_event_score + fit_score)
    label = priority_label(total_score)

    explanation = (
        f"{company_name}は、公開IR風サンプル文書上で{len(signals)}件のCRE関連シグナルが確認され、"
        f"シグナル({signal_score}点)、財務余力({financial_score}点)、戦略イベント({strategic_event_score}点)、"
        f"CRE提案適合度({fit_score}点)から営業優先度を{label}と判定しました。"
    )
    recommended_action = (
        "初回接点では、根拠文書に基づき拠点ポートフォリオ、設備投資計画、働き方の変化を確認し、"
        "CRE戦略診断の仮説提案につなげる。"
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
    )
