"""Immutable results for validated browser uploads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.core.models.portfolio_integrity_models import PortfolioIntegrityStatus
from src.core.models.portfolio_bundle_models import PortfolioBundleInfo

BrowserUploadKind = Literal["csv", "json", "excel", "portfolio", "bundle"]
BrowserUploadRequest = Literal["auto", "dataset", "portfolio", "bundle"]


@dataclass(frozen=True)
class BrowserUpload:
    # [impl->req~ring5.ingestion.browser-upload~1]
    """Validated, session-staged browser upload awaiting explicit use."""

    file_name: str
    content_type: str
    kind: BrowserUploadKind
    size_bytes: int
    source_sha256: str
    source_path: str
    import_path: str | None = None
    columns: tuple[str, ...] = ()
    row_count: int | None = None
    sheet_name: str | None = None
    portfolio_schema_version: int | None = None
    portfolio_plot_count: int | None = None
    portfolio_has_data: bool | None = None
    portfolio_integrity_status: PortfolioIntegrityStatus | None = None
    portfolio_signing_key_id: str | None = None
    bundle_info: PortfolioBundleInfo | None = None
    origin_display: str | None = None

    def __post_init__(self) -> None:
        """Reject inconsistent results crossing the web/core boundary."""
        if not self.file_name or self.size_bytes <= 0:
            raise ValueError("Browser upload metadata is incomplete.")
        if len(self.source_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.source_sha256
        ):
            raise ValueError("Browser upload source_sha256 must be a lowercase SHA-256 digest.")
        if self.kind == "portfolio":
            if self.import_path is not None or self.portfolio_schema_version is None:
                raise ValueError("Portfolio upload metadata is inconsistent.")
        elif self.kind == "bundle":
            if self.import_path is not None or self.bundle_info is None:
                raise ValueError("Portfolio bundle upload metadata is inconsistent.")
        elif self.import_path is None or self.row_count is None:
            raise ValueError("Dataset upload metadata is inconsistent.")
