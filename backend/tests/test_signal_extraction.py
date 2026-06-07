from datetime import date

from app.models import Document
from app.services.signal_extraction import extract_cre_signals_mock, parse_extracted_signals


def test_mock_cre_signal_extraction_is_deterministic_and_evidence_based() -> None:
    document = Document(
        id=101,
        company_id=1,
        document_type="統合報告書",
        title="サンプル統合報告書",
        source_name="サンプルIR文書",
        published_date=date(2025, 6, 1),
        fiscal_year="2025",
        text_content=(
            "国内の生産・営業拠点について、地域需要に合わせた再配置と統合を検討しています。"
            "ハイブリッドワーク定着を踏まえ、本社機能とオフィス利用の最適化を進めます。"
        ),
        is_sample=True,
    )

    first = extract_cre_signals_mock(document=document)
    second = extract_cre_signals_mock(document=document)

    assert first == second
    assert {signal.signal_type for signal in first} >= {"拠点再編", "働き方改革", "本社機能見直し"}
    for signal in first:
        assert signal.summary
        assert signal.evidence_text
        assert signal.source_reference == "サンプル統合報告書 / サンプルIR文書 / 2025-06-01"
        assert signal.confidence in {"high", "medium", "low"}
        assert signal.recommended_sales_action


def test_parse_extracted_signals_discards_items_without_evidence() -> None:
    raw_content = """
    {
      "signals": [
        {
          "signal_type": "拠点再編",
          "summary": "拠点再編の兆候",
          "evidence_text": "拠点の再配置を検討しています。",
          "source_reference": "統合報告書 p.10",
          "confidence": "high",
          "recommended_sales_action": "拠点再編テーマで初回面談を打診する。"
        },
        {
          "signal_type": "設備投資",
          "summary": "根拠不足",
          "evidence_text": "",
          "source_reference": "統合報告書 p.12",
          "confidence": "high",
          "recommended_sales_action": "投資計画を確認する。"
        }
      ]
    }
    """

    signals = parse_extracted_signals(raw_content, default_source_reference="既定出典")

    assert len(signals) == 1
    assert signals[0].signal_type == "拠点再編"
    assert signals[0].confidence == "high"
