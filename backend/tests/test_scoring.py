from app.services.scoring import FinancialInputs, SignalInputs, calculate_sales_priority_score, priority_label


def test_priority_label_thresholds() -> None:
    assert priority_label(80) == "高"
    assert priority_label(60) == "中"
    assert priority_label(59) == "低"


def test_scoring_returns_explainable_component_scores() -> None:
    result = calculate_sales_priority_score(
        company_name="テスト株式会社",
        financial=FinancialInputs(revenue_growth_pct=8.5, operating_margin_pct=11.0, capex_amount=150_000),
        signals=[
            SignalInputs(signal_type="拠点再編", confidence="high"),
            SignalInputs(signal_type="設備投資", confidence="medium"),
            SignalInputs(signal_type="働き方改革", confidence="medium"),
        ],
    )

    assert result.total_score == sum(result.component_scores.values())
    assert result.total_score <= 100
    assert result.priority_label in {"高", "中", "低"}
    assert set(result.component_scores) == {
        "signal_score",
        "financial_score",
        "strategic_event_score",
        "fit_score",
    }
    assert "テスト株式会社" in result.explanation
    assert result.recommended_action
