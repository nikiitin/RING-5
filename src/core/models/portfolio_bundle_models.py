"""Immutable metadata and contents for portable analysis bundles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

from src.core.models.dataset_workspace_models import DatasetSnapshotInfo
from src.core.models.portfolio_integrity_models import PortfolioIntegrityReport
from src.core.models.portfolio_models import PortfolioData

PortfolioBundleArtifactRole = Literal[
    "portfolio",
    "source-manifest",
    "environment-metadata",
    "python-requirements",
    "dataset-snapshot",
    "result",
]


@dataclass(frozen=True, slots=True)
class PortfolioBundleArtifact:
    # [impl->req~ring5.portfolio.portable-bundles~1]
    """One checksummed file carried by a portable bundle.

    Attributes:
        path: Safe relative POSIX path inside the bundle.
        role: Machine-readable purpose of the file.
        size_bytes: Uncompressed file size.
        sha256: Lowercase SHA-256 digest of the exact bytes.
        media_type: Portable content type recorded by the producer.
    """

    path: str
    role: PortfolioBundleArtifactRole
    size_bytes: int
    sha256: str
    media_type: str


@dataclass(frozen=True, slots=True)
class PortfolioBundleInfo:
    # [impl->req~ring5.portfolio.portable-bundles~1]
    """Validated, human-readable summary of a portable analysis bundle.

    Attributes:
        name: Bundle display name.
        format_version: Portable bundle format version.
        portfolio_schema_version: Schema version of the contained portfolio.
        portfolio_created_at: Original portfolio save timestamp, when recorded.
        size_bytes: Compressed bundle size.
        source_count: Number of recorded source locations.
        requirement_count: Number of pinned Python package requirements.
        portfolio_integrity: Checksum and optional signature status.
        dataset_snapshot: Included exact snapshot metadata, if any.
        result_names: Safe paths of included generated results.
        artifacts: Every checksummed member in stable path order.
    """

    name: str
    format_version: int
    portfolio_schema_version: int
    portfolio_created_at: str | None
    size_bytes: int
    source_count: int
    requirement_count: int
    portfolio_integrity: PortfolioIntegrityReport
    dataset_snapshot: DatasetSnapshotInfo | None
    result_names: tuple[str, ...]
    artifacts: tuple[PortfolioBundleArtifact, ...]


@dataclass(frozen=True, slots=True)
class PortfolioBundleResult:
    """One generated result recovered from a validated bundle.

    Attributes:
        name: Relative result path inside the bundle's ``results`` directory.
        media_type: Recorded content type.
        data: Exact checksum-verified result bytes.
    """

    name: str
    media_type: str
    data: bytes


@dataclass(frozen=True, slots=True)
class PortfolioBundleContents:
    """Validated portable bundle content returned without changing application state.

    Attributes:
        info: Inspectable bundle summary and integrity evidence.
        portfolio: Migrated portfolio ready for explicit restoration.
        source_manifest: Recorded source provenance; it contains no source file bytes.
        requirements: Pinned Python dependencies captured from the saved environment.
        dataset_snapshot: Exact reusable snapshot bytes, if included.
        results: Checksum-verified generated result files.
    """

    info: PortfolioBundleInfo
    portfolio: PortfolioData
    source_manifest: Mapping[str, Any]
    requirements: str
    dataset_snapshot: bytes | None
    results: tuple[PortfolioBundleResult, ...]
