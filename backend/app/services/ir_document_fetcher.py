from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.models import Company, Document
from app.services.ir_settings import IRPipelineSettings

MAX_DOWNLOAD_BYTES = 30 * 1024 * 1024


@dataclass(frozen=True)
class DocumentFetchResult:
    company_id: int
    document_id: int | None
    title: str
    target_url: str | None
    status: str
    http_status: int | None = None
    content_type: str | None = None
    file_size_bytes: int | None = None
    fetched_at: str | None = None
    saved_path: str | None = None
    error_message: str | None = None
    dry_run: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


class IRDocumentFetcher:
    """Fetch manually registered IR document URLs without crawling company sites."""

    def __init__(self, settings: IRPipelineSettings) -> None:
        self.settings = settings

    def fetch_document(self, company: Company, document: Document) -> DocumentFetchResult:
        if not self.settings.fetch_enabled:
            return self._result(company, document, "skipped", error_message="IR_FETCH_ENABLED=false のため外部取得を行いません。")
        if not document.source_url:
            return self._result(company, document, "skipped", error_message="source_url が未登録です。")
        if self.settings.dry_run:
            return self._result(company, document, "dry_run", error_message="dry-run: 登録URLのContent-Type確認とPDF保存を予定しています。", dry_run=True)
        try:
            request = Request(document.source_url, headers={"User-Agent": "cre-sales-intelligence-demo/0.1"})
            with urlopen(request, timeout=25) as response:  # noqa: S310 - URL is manually registered public IR URL.
                http_status = response.status
                content_type = response.headers.get("Content-Type", "")
                content = response.read(MAX_DOWNLOAD_BYTES + 1)
            if len(content) > MAX_DOWNLOAD_BYTES:
                return self._result(company, document, "failed", http_status=http_status, content_type=content_type, error_message="ファイルサイズが上限30MBを超えました。")
            if "pdf" not in content_type.lower() and not document.source_url.lower().split("?")[0].endswith(".pdf"):
                return self._result(company, document, "skipped", http_status=http_status, content_type=content_type, file_size_bytes=len(content), error_message="PDFではないURLまたはHTMLページのため保存対象外です。PDFリンクの自動探索は行いません。")
            saved_path = self._save(company, document, content)
            fetched_at = datetime.now(UTC)
            return self._result(company, document, "success", http_status=http_status, content_type=content_type, file_size_bytes=len(content), fetched_at=fetched_at.isoformat(), saved_path=str(saved_path))
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return self._result(company, document, "failed", error_message=str(exc))

    def _save(self, company: Company, document: Document, content: bytes) -> Path:
        storage_dir = self.settings.storage_dir / "manual_url" / company.ticker
        storage_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"document_{document.id}.pdf"
        saved_path = storage_dir / safe_name
        saved_path.write_bytes(content)
        return saved_path

    @staticmethod
    def _result(company: Company, document: Document, status: str, *, http_status: int | None = None, content_type: str | None = None, file_size_bytes: int | None = None, fetched_at: str | None = None, saved_path: str | None = None, error_message: str | None = None, dry_run: bool = False) -> DocumentFetchResult:
        return DocumentFetchResult(company.id, document.id, document.title, document.source_url, status, http_status, content_type, file_size_bytes, fetched_at, saved_path, error_message, dry_run)
