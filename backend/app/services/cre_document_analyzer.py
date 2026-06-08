from __future__ import annotations

from dataclasses import dataclass
from textwrap import shorten
import json
from urllib.request import Request, urlopen

from app.models import Document
from app.services.ir_settings import IRPipelineSettings

META_EVIDENCE_PATTERNS = ["CRE観点", "確認対象", "営業仮説", "分析方針", "正式方針や提案機会", "公開IR資料からCRE観点"]

CRE_KEYWORDS = [
    "設備投資", "拠点再編", "工場", "研究所", "物流拠点", "店舗", "本社", "不動産", "遊休資産", "建替え", "老朽化",
    "BCP", "防災", "脱炭素", "省エネ", "再生可能エネルギー", "ROIC", "PBR", "資本効率", "事業ポートフォリオ", "人的資本", "働き方",
]


@dataclass(frozen=True)
class ExtractedSignal:
    signal_type: str
    summary: str
    evidence_text: str
    source_document: str
    source_url: str | None
    confidence: str
    recommended_sales_action: str
    extracted_by: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def _sentences(text: str) -> list[str]:
    normalized = text.replace("\r", "\n").replace("。", "。\n")
    return [line.strip() for line in normalized.splitlines() if line.strip()]


def extract_rule_based(document: Document, *, limit: int = 12) -> list[ExtractedSignal]:
    signals: list[ExtractedSignal] = []
    seen: set[tuple[str, str]] = set()
    for sentence in _sentences(document.text_content or ""):
        matched = [keyword for keyword in CRE_KEYWORDS if keyword.lower() in sentence.lower()]
        for keyword in matched:
            if is_meta_evidence(sentence):
                continue
            evidence = shorten(sentence, width=260, placeholder="…")
            key = (keyword, evidence)
            if key in seen:
                continue
            seen.add(key)
            confidence = "medium" if len(evidence) >= 40 else "low"
            signals.append(
                ExtractedSignal(
                    signal_type=keyword,
                    summary=f"{keyword}に関する公開IR記載をCRE営業仮説の確認候補として抽出しました。",
                    evidence_text=evidence,
                    source_document=document.title,
                    source_url=document.source_url,
                    confidence=confidence,
                    recommended_sales_action="正式方針や提案機会とは断定せず、対象拠点・投資時期・所管部門・個別不動産情報を一次情報で確認する。",
                    extracted_by="rule_based",
                )
            )
            if len(signals) >= limit:
                return signals
    return signals


def is_meta_evidence(text: str) -> bool:
    return any(pattern in text for pattern in META_EVIDENCE_PATTERNS)


def extract_with_openai(settings: IRPipelineSettings, document: Document, candidates: list[ExtractedSignal]) -> list[ExtractedSignal]:
    if settings.effective_analysis_mode != "openai":
        return candidates
    candidate_text = "\n".join(f"- {item.signal_type}: {item.evidence_text}" for item in candidates[:20])
    if not candidate_text:
        candidate_text = shorten(document.text_content or "", width=6000, placeholder="…")
    prompt = {
        "document": {"title": document.title, "type": document.document_type, "source_url": document.source_url, "fiscal_year": document.fiscal_year},
        "instruction": "公開IR資料の候補本文からCRE営業仮説シグナルをJSON配列で抽出。断定表現を避ける。各要素はsignal_type, summary, evidence_text, source_document, source_url, confidence, recommended_sales_actionを含める。evidence_textは資料本文または抽出PDFテキスト中の具体的記載・要約に限定し、分析方針やCRE観点のメタ説明は根拠にしない。根拠が弱い場合はconfidence=low。",
        "candidate_text": candidate_text,
    }
    try:
        body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "あなたは日本語のCRE営業支援アナリストです。公開情報に基づく仮説として慎重に表現します。"},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        request = Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed OpenAI API endpoint.
            payload = json.loads(response.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        raw_items = parsed.get("signals", parsed if isinstance(parsed, list) else [])
        extracted: list[ExtractedSignal] = []
        for item in raw_items:
            evidence = str(item.get("evidence_text") or "").strip()
            if not evidence:
                continue
            confidence = str(item.get("confidence") or "low") if str(item.get("confidence") or "low") in {"high", "medium", "low"} else "low"
            if is_meta_evidence(evidence):
                confidence = "low"
                continue
            extracted.append(ExtractedSignal(
                signal_type=str(item.get("signal_type") or "CRE確認候補"),
                summary=str(item.get("summary") or "公開IR資料からCRE観点の確認候補を抽出しました。"),
                evidence_text=shorten(evidence, width=300, placeholder="…"),
                source_document=str(item.get("source_document") or document.title),
                source_url=str(item.get("source_url") or document.source_url or "") or None,
                confidence=confidence,
                recommended_sales_action=str(item.get("recommended_sales_action") or "一次情報確認と個別ヒアリングで検証する。"),
                extracted_by="openai",
            ))
        return extracted or candidates
    except Exception:
        return candidates
