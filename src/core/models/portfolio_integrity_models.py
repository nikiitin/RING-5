"""Immutable results for portfolio integrity inspection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PortfolioIntegrityStatus = Literal[
    "legacy-unverified",
    "checksum-valid",
    "signature-unverified",
    "signature-valid",
    "modified",
    "signature-invalid",
    "invalid-manifest",
]


@dataclass(frozen=True)
class PortfolioIntegritySection:
    # [impl->req~ring5.portfolio.signed-manifests~1]
    """Checksum result for one human-readable part of a portfolio.

    Attributes:
        name: Stable section name: ``inputs``, ``configuration``, or ``outputs``.
        expected_sha256: Digest recorded in the manifest.
        actual_sha256: Digest calculated from the portfolio being inspected.
        matches: Whether the recorded and calculated digests match.
    """

    name: str
    expected_sha256: str
    actual_sha256: str
    matches: bool


@dataclass(frozen=True)
class PortfolioIntegrityReport:
    # [impl->req~ring5.portfolio.signed-manifests~1]
    """Result of checking a portfolio manifest and its optional signature.

    ``checksum_valid`` answers whether the saved content is unchanged.
    ``signature_valid`` is ``None`` when no secret was supplied or no
    signature exists; a checksum alone does not authenticate who created it.

    Attributes:
        status: Stable machine-readable verification outcome.
        message: Concise human-readable interpretation.
        checksum_valid: Whole-document checksum result, or ``None`` for legacy
            and structurally invalid manifests.
        signature_present: Whether the manifest carries an HMAC signature.
        signature_valid: Signature result, or ``None`` when not checked.
        key_id: Non-secret identifier recorded for the signing key.
        sections: Input, configuration, and output checksum results.
    """

    status: PortfolioIntegrityStatus
    message: str
    checksum_valid: bool | None
    signature_present: bool
    signature_valid: bool | None
    key_id: str | None
    sections: tuple[PortfolioIntegritySection, ...] = ()

    @property
    def safe_to_restore(self) -> bool:
        """Whether content checks permit restoration under the default policy."""
        return self.status in {
            "legacy-unverified",
            "checksum-valid",
            "signature-unverified",
            "signature-valid",
        }
