from app.services.scoring import (
    COMPONENT_MAX_POINTS,
    FinancialInputs,
    SignalInputs,
    calculate_sales_priority_score,
    priority_label,
)


def test_priority_label_thresholds() -> None:
    assert priority_label(85) == "高"
    assert priority_label(84) == "中"
    assert priority_label(50) == "中"
    assert priority_label(49) == "低"


def test_component_max_points_sum_to_100() -> None:
    assert COMPONENT_MAX_POINTS == {
        "signal_score": 35,
        "financial_score": 25,
        "strategic_event_score": 25,
        "fit_score": 15,
    }
    assert sum(COMPONENT_MAX_POINTS.values()) == 100


def test_scoring_returns_explainable_component_scores() -> None:
    result = calculate_sales_priority_score(
        company_name="テスト株式会社",
        financial=FinancialInputs(
            revenue=1_500_000,
            revenue_growth_pct=8.5,
            operating_margin_pct=11.0,
            capex_amount=250_000,
            cash_and_equivalents=500_000,
        ),
        signals=[
            SignalInputs(signal_type="拠点再編", confidence="high"),
            SignalInputs(signal_type="設備投資", confidence="medium"),
            SignalInputs(signal_type="働き方改革", confidence="medium"),
        ],
    )

    assert result.total_score == sum(result.component_scores.values())
    assert result.total_score <= 100
    assert result.priority_label in {"高", "中", "低"}
    assert set(result.component_scores) == set(COMPONENT_MAX_POINTS)
    for key, detail in result.component_details.items():
        assert detail.score == result.component_scores[key]
        assert detail.max_points == COMPONENT_MAX_POINTS[key]
        assert detail.reason
    assert "テスト株式会社" in result.explanation
    assert result.recommended_action


def test_public_demo_scores_are_calculated_from_scoring_logic() -> None:
    from app.seed import PUBLIC_COMPANY_SEEDS

    for seed in PUBLIC_COMPANY_SEEDS:
        result = calculate_sales_priority_score(
            company_name=seed["name"],
            financial=FinancialInputs(
                revenue=seed["revenue"],
                revenue_growth_pct=seed["growth"],
                operating_margin_pct=seed["margin"],
                capex_amount=seed["capex"],
                cash_and_equivalents=seed["cash"],
            ),
            signals=[SignalInputs(signal_type=signal["type"], confidence=signal["confidence"]) for signal in seed["signals"]],
        )
        assert result.priority_label == priority_label(result.total_score)
        assert result.total_score == sum(result.component_scores.values())
