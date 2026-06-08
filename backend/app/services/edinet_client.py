from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.models import Company
from app.services.ir_settings import IRPipelineSettings

EDINET_LIST_URL = "https://disclosure.edinet-fsa.go.jp/api/v2/documents.json"
EDINET_DOCUMENT_URL = "https://disclosure.edinet-fsa.go.jp/api/v2/documents/{doc_id}"
SECURITIES_REPORT_FORM_CODES = {"030000"}
SUPPORTED_DOCUMENT_TYPES = {
    "有価証券報告書": SECURITIES_REPORT_FORM_CODES,
    # Future extension points: 半期報告書, 四半期報告書, 訂正有価証券報告書.
}


@dataclass(frozen=True)
class EdinetFetchResult:
    company_id: int
    company_name: str
    target_date: str
    search_start_date: str
    search_end_date: str
    lookback_days: int
    document_type: str
    doc_id: str | None
    status: str
    error_message: str | None = None
    saved_path: str | None = None
    dry_run: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


class EdinetClient:
    """EDINET adapter for lookback-period list search followed by document download."""

    def __init__(self, settings: IRPipelineSettings) -> None:
        self.settings = settings

    def fetch_latest_securities_report(
        self,
        company: Company,
        *,
        target_date: date | None = None,
        lookback_days: int | None = None,
        document_type: str = "有価証券報告書",
    ) -> EdinetFetchResult:
        end = target_date or date.today()
        days = max(1, int(lookback_days or self.settings.edinet_lookback_days or 365))
        start = end - timedelta(days=days - 1)
        if not self.settings.fetch_enabled:
            return self._result(company, start, end, days, document_type, None, "skipped", "IR_FETCH_ENABLED=false のため外部取得を行いません。")
        if not company.edinet_code:
            return self._result(company, start, end, days, document_type, None, "skipped", "EDINETコードが未登録のため取得対象外です。")
        if self.settings.dry_run:
            msg = f"dry-run: EDINETコード={company.edinet_code}、書類種別={document_type}、検索期間={start.isoformat()}〜{end.isoformat()}（lookback_days={days}）で検索予定です。"
            return self._result(company, start, end, days, document_type, None, "dry_run", msg, dry_run=True)
        if not self.settings.edinet_api_key:
            return self._result(company, start, end, days, document_type, None, "failed", "EDINET_API_KEY が未設定または無効です。バックエンド環境変数を確認してください。")

        try:
            doc = self._find_latest_document(company.edinet_code, start, end, document_type)
            if doc is None:
                msg = (
                    f"対象期間にdocIDが見つかりませんでした。検索期間={start.isoformat()}〜{end.isoformat()}、"
                    f"EDINETコード={company.edinet_code}、書類種別={document_type}、検索日数={days}。"
                )
                return self._result(company, start, end, days, document_type, None, "skipped", msg)
            doc_id = str(doc["docID"])
            saved_path = self._download_document(doc_id, company, end)
            return self._result(company, start, end, days, document_type, doc_id, "success", saved_path=str(saved_path))
        except HTTPError as exc:
            return self._result(company, start, end, days, document_type, None, "failed", f"EDINET API HTTPエラー: {exc.code} {exc.reason}")
        except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            return self._result(company, start, end, days, document_type, None, "failed", f"EDINET取得エラー: {exc}")

    def _find_latest_document(self, edinet_code: str, search_start: date, search_end: date, document_type: str) -> dict[str, object] | None:
        form_codes = SUPPORTED_DOCUMENT_TYPES.get(document_type, SECURITIES_REPORT_FORM_CODES)
        latest: dict[str, object] | None = None
        days = (search_end - search_start).days
        for offset in range(days + 1):
            search_date = search_end - timedelta(days=offset)
            query = urlencode({"date": search_date.isoformat(), "type": 2, "Subscription-Key": self.settings.edinet_api_key})
            request = Request(f"{EDINET_LIST_URL}?{query}", headers={"User-Agent": "cre-sales-intelligence-demo/0.1"})
            with urlopen(request, timeout=20) as response:  # noqa: S310 - URL is fixed EDINET endpoint.
                data = json.loads(response.read().decode("utf-8"))
            candidates = [
                item for item in data.get("results", [])
                if item.get("edinetCode") == edinet_code
                and item.get("formCode") in form_codes
                and document_type in str(item.get("docDescription", ""))
            ]
            if candidates:
                latest = candidates[0]
                break
        return latest

    def _download_document(self, doc_id: str, company: Company, target_date: date) -> Path:
        storage_dir = self.settings.storage_dir / "edinet" / company.ticker
        storage_dir.mkdir(parents=True, exist_ok=True)
        query = urlencode({"type": 2, "Subscription-Key": self.settings.edinet_api_key})
        request = Request(f"{EDINET_DOCUMENT_URL.format(doc_id=doc_id)}?{query}", headers={"User-Agent": "cre-sales-intelligence-demo/0.1"})
        with urlopen(request, timeout=30) as response:  # noqa: S310 - URL is fixed EDINET endpoint.
            content = response.read()
        saved_path = storage_dir / f"{target_date.isoformat()}_{doc_id}.pdf"
        saved_path.write_bytes(content)
        return saved_path

    @staticmethod
    def _result(company: Company, search_start: date, search_end: date, lookback_days: int, document_type: str, doc_id: str | None, status: str, error_message: str | None = None, *, saved_path: str | None = None, dry_run: bool = False) -> EdinetFetchResult:
        return EdinetFetchResult(
            company_id=company.id,
            company_name=company.name,
            target_date=search_end.isoformat(),
            search_start_date=search_start.isoformat(),
            search_end_date=search_end.isoformat(),
            lookback_days=lookback_days,
            document_type=document_type,
            doc_id=doc_id,
            status=status,
            error_message=error_message,
            saved_path=saved_path,
            dry_run=dry_run,
        )
