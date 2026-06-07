from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from app.config import Settings
from app.models import Document

CRE_SIGNAL_EXTRACTION_SYSTEM_PROMPT = """
あなたはCRE（企業不動産）コンサルティング営業向けのIR文書アナリストです。
公開IR文書またはサンプル文書から、拠点再編・設備投資・働き方改革・物流再編・本社機能見直し・資産売却など、CRE提案につながる兆候だけを抽出してください。
必ず根拠テキストと出典参照を付け、根拠が弱い場合は confidence を low にしてください。
""".strip()

CRE_SIGNAL_EXTRACTION_USER_PROMPT_TEMPLATE = """
以下の文書からCRE関連シグナルを抽出し、JSONオブジェクトのみで返してください。
形式は {"signals": [...]} とし、各要素は signal_type, summary, evidence_text, source_reference, confidence, recommended_sales_action を含めてください。

会社名: {company_name}
文書名: {document_title}
出典: {source_reference}
本文:
{document_text}
""".strip()

MOCK_SIGNAL_RULES: tuple[tuple[str, str, str, str], ...] = (
    (
        "拠点再編",
        "拠点再編・統合の検討",
        "拠点ポートフォリオの現状、統廃合対象、地域別需要変化を確認する初回ディスカッションを提案する。",
        "拠点",
    ),
    (
        "設備投資",
        "成長投資に伴う設備・施設ニーズ",
        "設備投資計画と施設キャパシティの整合性を確認し、投資前のCRE戦略診断を提案する。",
        "設備",
    ),
    (
        "働き方改革",
        "働き方変化に伴うオフィス最適化",
        "本社・主要オフィスの利用実態を確認し、ハイブリッドワーク前提の面積・機能見直しを提案する。",
        "ハイブリッドワーク",
    ),
    (
        "海外展開",
        "海外展開に伴う拠点整備",
        "海外拠点の設置計画、現地パートナー、ガバナンス課題を確認するCRE支援仮説を提示する。",
        "海外",
    ),
    (
        "物流再編",
        "物流ネットワーク見直し",
        "配送センター配置、在庫拠点、物流コストの現状を確認し、物流不動産の再配置診断を提案する。",
        "物流",
    ),
    (
        "本社機能見直し",
        "本社機能集約・業務標準化",
        "本社機能の集約対象、意思決定体制、拠点要件を確認し、本社移転・集約の構想策定を提案する。",
        "本社機能",
    ),
    (
        "資産売却",
        "遊休不動産・保有資産の見直し",
        "保有不動産の利用状況と資本効率を確認し、売却・有効活用の初期診断を提案する。",
        "遊休不動産",
    ),
)


@dataclass(frozen=True)
class ExtractedCRESignal:
    signal_type: str
    summary: str
    evidence_text: str
    source_reference: str
    confidence: str
    recommended_sales_action: str


def build_extraction_prompt(*, company_name: str, document: Document) -> str:
    return CRE_SIGNAL_EXTRACTION_USER_PROMPT_TEMPLATE.format(
        company_name=company_name,
        document_title=document.title,
        source_reference=_source_reference(document),
        document_text=document.text_content,
    )


def extract_cre_signals(*, document: Document, company_name: str, settings: Settings) -> list[ExtractedCRESignal]:
    """Extract CRE signals from a document using mock mode or optional OpenAI API mode."""

    if settings.openai_api_key:
        return _extract_with_openai(document=document, company_name=company_name, settings=settings)
    return extract_cre_signals_mock(document=document)


def extract_cre_signals_mock(*, document: Document) -> list[ExtractedCRESignal]:
    """Deterministically extract CRE signals from sample document text."""

    text = document.text_content
    signals: list[ExtractedCRESignal] = []
    for signal_type, summary, action, keyword in MOCK_SIGNAL_RULES:
        if keyword not in text and signal_type not in text:
            continue
        evidence = _extract_sentence_containing(text, keyword) or _extract_sentence_containing(text, signal_type)
        if not evidence:
            continue
        confidence = "high" if any(term in evidence for term in ("進めます", "検討します", "行います")) else "medium"
        signals.append(
            ExtractedCRESignal(
                signal_type=signal_type,
                summary=summary,
                evidence_text=evidence,
                source_reference=_source_reference(document),
                confidence=confidence,
                recommended_sales_action=action,
            )
        )
    return _deduplicate_signals(signals)


def _extract_with_openai(*, document: Document, company_name: str, settings: Settings) -> list[ExtractedCRESignal]:
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "system", "content": CRE_SIGNAL_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": build_extraction_prompt(company_name=company_name, document=document)},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    http_request = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=30) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, error.URLError, json.JSONDecodeError):
        return []

    content = response_payload.get("choices", [{}])[0].get("message", {}).get("content", "")
    return parse_extracted_signals(content, default_source_reference=_source_reference(document))


def parse_extracted_signals(raw_content: str, *, default_source_reference: str) -> list[ExtractedCRESignal]:
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        return []

    if isinstance(parsed, dict):
        raw_items = parsed.get("signals", [])
    else:
        raw_items = parsed
    if not isinstance(raw_items, list):
        return []

    signals: list[ExtractedCRESignal] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        signal = _coerce_signal(item, default_source_reference=default_source_reference)
        if signal is not None:
            signals.append(signal)
    return _deduplicate_signals(signals)


def _coerce_signal(item: dict[str, Any], *, default_source_reference: str) -> ExtractedCRESignal | None:
    evidence_text = str(item.get("evidence_text") or "").strip()
    if not evidence_text:
        return None

    confidence = str(item.get("confidence") or "low").strip().lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"

    source_reference = str(item.get("source_reference") or default_source_reference).strip() or default_source_reference
    return ExtractedCRESignal(
        signal_type=str(item.get("signal_type") or "未分類CREシグナル").strip(),
        summary=str(item.get("summary") or item.get("title") or "CRE関連シグナル").strip(),
        evidence_text=evidence_text,
        source_reference=source_reference,
        confidence=confidence,
        recommended_sales_action=str(item.get("recommended_sales_action") or "根拠文書をもとにCRE課題の有無を確認する。").strip(),
    )


def _extract_sentence_containing(text: str, keyword: str) -> str | None:
    normalized = text.replace("\n", " ")
    sentences = [sentence.strip() for sentence in normalized.replace("。", "。\n").splitlines() if sentence.strip()]
    for sentence in sentences:
        if keyword in sentence:
            return sentence
    return None


def _source_reference(document: Document) -> str:
    published = document.published_date.isoformat() if document.published_date else "日付未設定"
    return f"{document.title} / {document.source_name} / {published}"


def _deduplicate_signals(signals: list[ExtractedCRESignal]) -> list[ExtractedCRESignal]:
    seen: set[tuple[str, str]] = set()
    deduplicated: list[ExtractedCRESignal] = []
    for signal in signals:
        key = (signal.signal_type, signal.evidence_text)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(signal)
    return deduplicated
