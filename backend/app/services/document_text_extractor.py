from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path

from app.models import Company, Document
from app.services.ir_settings import IRPipelineSettings


@dataclass(frozen=True)
class TextExtractionResult:
    status: str
    document_id: int
    saved_path: str | None
    extracted_char_count: int
    error_message: str | None = None

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


class DocumentTextExtractor:
    def __init__(self, settings: IRPipelineSettings) -> None:
        self.settings = settings

    def extract_pdf_text(self, company: Company, document: Document, pdf_path: str) -> TextExtractionResult:
        try:
            import fitz  # PyMuPDF

            text_parts: list[str] = []
            with fitz.open(pdf_path) as pdf:
                for page in pdf:
                    text_parts.append(page.get_text("text"))
            extracted = "\n".join(part.strip() for part in text_parts if part.strip())
            saved_path = self._save_text(company, document, extracted)
            return TextExtractionResult("success", document.id, str(saved_path), len(extracted))
        except Exception as exc:  # PyMuPDF can raise several document-specific exceptions.
            return TextExtractionResult("failed", document.id, None, 0, str(exc))

    def _save_text(self, company: Company, document: Document, text: str) -> Path:
        storage_dir = self.settings.storage_dir / "extracted_text" / company.ticker
        storage_dir.mkdir(parents=True, exist_ok=True)
        saved_path = storage_dir / f"document_{document.id}.txt"
        header = (
            f"company_id={company.id}\ncompany_name={company.name}\ndocument_id={document.id}\n"
            f"title={document.title}\ndocument_type={document.document_type}\nfiscal_year={document.fiscal_year}\n"
            f"source_url={document.source_url or ''}\nextracted_at={datetime.now(UTC).isoformat()}\n\n"
        )
        saved_path.write_text(header + text, encoding="utf-8")
        return saved_path
