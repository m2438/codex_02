from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import Settings


@dataclass(frozen=True)
class IRPipelineSettings:
    edinet_api_key: str
    openai_api_key: str
    fetch_enabled: bool
    analysis_mode: str
    dry_run: bool
    storage_dir: Path
    max_file_mb: int
    edinet_lookback_days: int

    @property
    def effective_analysis_mode(self) -> str:
        if self.analysis_mode == "openai" and self.openai_api_key:
            return "openai"
        return "mock"

    def public_status(self) -> dict[str, object]:
        return {
            "fetch_enabled": self.fetch_enabled,
            "dry_run": self.dry_run,
            "analysis_mode": self.analysis_mode,
            "effective_analysis_mode": self.effective_analysis_mode,
            "edinet_api_key_configured": bool(self.edinet_api_key),
            "openai_api_key_configured": bool(self.openai_api_key),
            "storage_dir": str(self.storage_dir),
            "max_file_mb": self.max_file_mb,
            "edinet_lookback_days": self.edinet_lookback_days,
        }


def parse_bool(value: str | bool | None, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_positive_int(value: str | int | None, *, default: int) -> int:
    try:
        parsed = int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def build_ir_settings(settings: Settings) -> IRPipelineSettings:
    mode = (settings.ir_analysis_mode or "mock").strip().lower()
    if mode not in {"mock", "openai"}:
        mode = "mock"
    return IRPipelineSettings(
        edinet_api_key=settings.edinet_api_key,
        openai_api_key=settings.openai_api_key,
        fetch_enabled=parse_bool(settings.ir_fetch_enabled, default=False),
        analysis_mode=mode,
        dry_run=parse_bool(settings.ir_fetch_dry_run, default=True),
        storage_dir=Path(settings.ir_fetch_storage_dir),
        max_file_mb=parse_positive_int(settings.ir_fetch_max_file_mb, default=100),
        edinet_lookback_days=max(1, int(settings.edinet_lookback_days or 365)),
    )
