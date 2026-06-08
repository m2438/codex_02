from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, UTC
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.models import Company
from app.services.ir_settings import IRPipelineSettings

EDINET_LIST_URL = "https://disclosure.edinet-fsa.go.jp/api/v2/documents.json"
EDINET_DOCUMENT_URL = "https://disclosure.edinet-fsa.go.jp/api/v2/documents/{doc_id}"
SECURITIES_REPORT_FORM_CODES = {"030000"}


@dataclass(frozen=True)
class EdinetFetchResult:
    company_id: int
    company_name: str
    target_date: str
    document_type: str
    doc_id: str | None
    status: str
    error_message: str | None = None
    saved_path: str | None = None
    dry_run: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "company_id": self.company_id,
            "company_name": self.company_name,
            "target_date": self.target_date,
            "document_type": self.document_type,
            "doc_id": self.doc_id,
            "status": self.status,
            "error_message": self.error_message,
            "saved_path": self.saved_path,
            "dry_run": self.dry_run,
        }


class EdinetClient:
    """Small EDINET adapter for document list search followed by document download."""

    def __init__(self, settings: IRPipelineSettings) -> None:
        self.settings = settings

    def fetch_latest_securities_report(self, company: Company, *, target_date: date | None = None) -> EdinetFetchResult:
        document_type = "有価証券報告書"
        target = target_date or date.today()
        if not self.settings.fetch_enabled:
            return self._result(company, target, document_type, None, "skipped", "IR_FETCH_ENABLED=false のため外部取得を行いません。")
        if not company.edinet_code:
            return self._result(company, target, document_type, None, "skipped", "EDINETコードが未登録のため取得対象外です。")
        if self.settings.dry_run:
            return self._result(company, target, document_type, None, "dry_run", "dry-run: EDINET書類一覧API検索と書類取得API呼び出しを予定しています。", dry_run=True)
        if not self.settings.edinet_api_key:
            return self._result(company, target, document_type, None, "failed", "EDINET_API_KEY が未設定です。バックエンド環境変数に設定してください。")

        try:
            doc = self._find_latest_document(company.edinet_code, target)
            if doc is None:
                return self._result(company, target, document_type, None, "skipped", "対象期間に有価証券報告書のdocIDが見つかりませんでした。")
            doc_id = str(doc["docID"])
            saved_path = self._download_document(doc_id, company, target)
            return self._result(company, target, document_type, doc_id, "success", saved_path=str(saved_path))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            return self._result(company, target, document_type, None, "failed", str(exc))

    def _find_latest_document(self, edinet_code: str, target_date: date) -> dict[str, object] | None:
        # EDINET list API is date-based. Search backwards to tolerate weekends/holidays and filing date variance.
        for offset in range(0, 45):
            search_date = target_date - timedelta(days=offset)
            query = urlencode({"date": search_date.isoformat(), "type": 2, "Subscription-Key": self.settings.edinet_api_key})
            request = Request(f"{EDINET_LIST_URL}?{query}", headers={"User-Agent": "cre-sales-intelligence-demo/0.1"})
            with urlopen(request, timeout=20) as response:  # noqa: S310 - URL is fixed EDINET endpoint.
                payload = response.read().decode("utf-8")
            import json

            data = json.loads(payload)
            candidates = [
                item for item in data.get("results", [])
                if item.get("edinetCode") == edinet_code
                and item.get("formCode") in SECURITIES_REPORT_FORM_CODES
                and "有価証券報告書" in str(item.get("docDescription", ""))
            ]
            if candidates:
                return candidates[0]
        return None

    def _download_document(self, doc_id: str, company: Company, target_date: date) -> Path:
        storage_dir = self.settings.storage_dir / "edinet" / company.ticker
        storage_dir.mkdir(parents=True, exist_ok=True)
        query = urlencode({"type": 2, "Subscription-Key": self.settings.edinet_api_key})
        request = Request(f"{EDINET_DOCUMENT_URL.format(doc_id=doc_id)}?{query}", headers={"User-Agent": "cre-sales-intelligence-demo/0.1"})
        with urlopen(request, timeout=30) as response:  # noqa: S310 - URL is fixed EDINET endpoint.
            content = response.read()
        saved_path = storage_dir / f"{target_date.isoformat()}_{doc_id}.zip"
        saved_path.write_bytes(content)
        return saved_path

    @staticmethod
    def _result(company: Company, target_date: date, document_type: str, doc_id: str | None, status: str, error_message: str | None = None, *, saved_path: str | None = None, dry_run: bool = False) -> EdinetFetchResult:
        return EdinetFetchResult(
            company_id=company.id,
            company_name=company.name,
            target_date=target_date.isoformat(),
            document_type=document_type,
            doc_id=doc_id,
            status=status,
            error_message=error_message,
            saved_path=saved_path,
            dry_run=dry_run,
        )
