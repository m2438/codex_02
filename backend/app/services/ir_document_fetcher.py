from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from app.models import Company, Document
from app.services.ir_settings import IRPipelineSettings

DOWNLOAD_CHUNK_SIZE = 1024 * 1024
PDF_KEYWORDS = ["有価証券報告書", "統合報告書", "annual report", "securities report", "yuho", "annual", "report"]


class FileSizeLimitExceededError(Exception):
    def __init__(self, max_file_mb: int) -> None:
        super().__init__(f"PDFファイルサイズが上限{max_file_mb}MBを超えました。")
        self.max_file_mb = max_file_mb


class PdfLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            attr = dict(attrs)
            self._href = attr.get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._href = None
            self._text = []


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
    original_html_url: str | None = None
    selected_pdf_url: str | None = None
    pdf_candidate_count: int | None = None

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


class IRDocumentFetcher:
    """Fetch manually registered IR URLs and, for a single HTML page, resolve a PDF link."""

    def __init__(self, settings: IRPipelineSettings) -> None:
        self.settings = settings

    def fetch_document(self, company: Company, document: Document) -> DocumentFetchResult:
        if not self.settings.fetch_enabled:
            return self._result(company, document, "skipped", error_message="IR_FETCH_ENABLED=false のため外部取得を行いません。")
        if not document.source_url:
            return self._result(company, document, "skipped", error_message="source_url が未登録です。")
        if self.settings.dry_run:
            msg = f"dry-run: URL={document.source_url} を確認し、HTMLの場合はページ内PDFリンクのみ探索してPDF保存・テキスト抽出を予定しています。"
            return self._result(company, document, "dry_run", error_message=msg, dry_run=True)
        try:
            http_status, content_type, content = self._download(document.source_url, timeout=25)
            selected_pdf_url = document.source_url
            candidate_count: int | None = None
            original_html_url: str | None = None
            if self._is_html(content_type, document.source_url):
                original_html_url = document.source_url
                candidates = extract_pdf_links(content.decode("utf-8", errors="ignore"), document.source_url)
                candidate_count = len(candidates)
                if not candidates:
                    return self._result(company, document, "skipped", http_status=http_status, content_type=content_type, file_size_bytes=len(content), error_message="HTMLページ内のPDF候補数0件のため取得できませんでした。", original_html_url=original_html_url, pdf_candidate_count=0)
                selected_pdf_url = choose_pdf_link(candidates, document)
                http_status, content_type, content = self._download(selected_pdf_url, timeout=30)

            if "pdf" not in content_type.lower() and not selected_pdf_url.lower().split("?")[0].endswith(".pdf"):
                return self._result(company, document, "skipped", http_status=http_status, content_type=content_type, file_size_bytes=len(content), error_message="選択URLがPDFではありません。", original_html_url=original_html_url, selected_pdf_url=selected_pdf_url, pdf_candidate_count=candidate_count)
            saved_path = self._save(company, document, content)
            fetched_at = datetime.now(UTC)
            return self._result(company, document, "success", http_status=http_status, content_type=content_type, file_size_bytes=len(content), fetched_at=fetched_at.isoformat(), saved_path=str(saved_path), original_html_url=original_html_url, selected_pdf_url=selected_pdf_url, pdf_candidate_count=candidate_count)
        except FileSizeLimitExceededError as exc:
            return self._result(company, document, "failed", error_message=str(exc))
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return self._result(company, document, "failed", error_message=str(exc))

    def _download(self, url: str, *, timeout: int) -> tuple[int, str, bytes]:
        request = Request(url, headers={"User-Agent": "cre-sales-intelligence-demo/0.1"})
        max_bytes = self.settings.max_file_mb * 1024 * 1024
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL is manually registered public IR URL.
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    advertised_size = int(content_length)
                except ValueError:
                    advertised_size = 0
                if advertised_size > max_bytes:
                    raise FileSizeLimitExceededError(self.settings.max_file_mb)
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise FileSizeLimitExceededError(self.settings.max_file_mb)
                chunks.append(chunk)
            return response.status, response.headers.get("Content-Type", ""), b"".join(chunks)

    @staticmethod
    def _is_html(content_type: str, url: str) -> bool:
        return "text/html" in content_type.lower() or url.lower().split("?")[0].endswith((".html", "/"))

    def _save(self, company: Company, document: Document, content: bytes) -> Path:
        storage_dir = self.settings.storage_dir / "manual_url" / company.ticker
        storage_dir.mkdir(parents=True, exist_ok=True)
        saved_path = storage_dir / f"document_{document.id}.pdf"
        saved_path.write_bytes(content)
        return saved_path

    @staticmethod
    def _result(company: Company, document: Document, status: str, *, http_status: int | None = None, content_type: str | None = None, file_size_bytes: int | None = None, fetched_at: str | None = None, saved_path: str | None = None, error_message: str | None = None, dry_run: bool = False, original_html_url: str | None = None, selected_pdf_url: str | None = None, pdf_candidate_count: int | None = None) -> DocumentFetchResult:
        return DocumentFetchResult(company.id, document.id, document.title, selected_pdf_url or document.source_url, status, http_status, content_type, file_size_bytes, fetched_at, saved_path, error_message, dry_run, original_html_url, selected_pdf_url, pdf_candidate_count)


def extract_pdf_links(html: str, base_url: str) -> list[dict[str, str]]:
    parser = PdfLinkParser()
    parser.feed(html)
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for href, text in parser.links:
        if ".pdf" not in href.lower():
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append({"url": absolute, "text": text, "href": href})
    return links


def choose_pdf_link(candidates: list[dict[str, str]], document: Document) -> str:
    fiscal = str(document.fiscal_year or "")
    title = f"{document.title} {document.document_type}".lower()
    def score(candidate: dict[str, str]) -> int:
        haystack = f"{candidate.get('url', '')} {candidate.get('text', '')}".lower()
        value = 10 if ".pdf" in candidate.get("url", "").lower() else 0
        for keyword in PDF_KEYWORDS:
            if keyword.lower() in haystack:
                value += 5
        for token in [document.document_type, fiscal, fiscal.replace("fy", ""), title]:
            token = str(token or "").lower()
            if token and token in haystack:
                value += 8
        return value
    return max(candidates, key=score)["url"]
