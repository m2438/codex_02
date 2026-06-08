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
        }


def parse_bool(value: str | bool | None, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


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
    )
