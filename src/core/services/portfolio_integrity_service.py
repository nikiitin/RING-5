"""Create and verify checksummed portfolio integrity manifests."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from typing import Any, cast

from src.core.models import PortfolioIntegrityReport, PortfolioIntegritySection

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SECTION_NAMES = ("inputs", "configuration", "outputs")
_INPUT_KEYS = (
    "csv_path",
    "data_csv",
    "data_semantics",
    "parse_variables",
    "scanned_variables",
    "stats_path",
    "stats_pattern",
    "use_parser",
)
_CONFIGURATION_KEYS = (
    "config",
    "manager_history",
    "plot_counter",
    "portfolio_history",
    "shapers",
)
_OUTPUT_PLOT_KEYS = ("id", "processed_data", "processed_semantics")
_MAX_SIGNING_KEY_BYTES = 4096
_MAX_KEY_ID_LENGTH = 128


class PortfolioIntegrityError(ValueError):
    """A portfolio failed the integrity policy required for restoration."""


class PortfolioIntegrityService:
    """Build and inspect portable SHA-256 and HMAC-SHA-256 manifests.

    SHA-256 checksums detect accidental or deliberate content changes but do
    not identify the author. An optional HMAC authenticates the checksums with
    a shared secret supplied by the caller; neither the secret nor a derivative
    from which it can be recovered is written to the portfolio.
    """

    @classmethod
    def create_manifest(
        cls,
        portfolio: Mapping[str, Any],
        *,
        signing_key: str | bytes | None = None,
        key_id: str = "default",
    ) -> dict[str, Any]:
        # [impl->req~ring5.portfolio.signed-manifests~1]
        """Return a manifest for *portfolio*, optionally authenticated by HMAC.

        Args:
            portfolio: JSON-compatible portfolio without an integrity manifest.
            signing_key: Optional shared secret used only for HMAC-SHA-256.
            key_id: Non-secret label that helps recipients select the secret.

        Returns:
            JSON-compatible manifest containing whole-document and section digests.

        Raises:
            ValueError: The portfolio, key, or key identifier is invalid.
        """
        body = cls._body(portfolio)
        sections = {name: cls._digest(value) for name, value in cls._sections(body).items()}
        statement: dict[str, Any] = {
            "format": "ring5.portfolio-integrity",
            "format_version": 1,
            "checksum_algorithm": "sha256",
            "portfolio_sha256": cls._digest(body),
            "sections": sections,
        }
        signature: dict[str, str] | None = None
        if signing_key is not None:
            secret = cls._key_bytes(signing_key)
            label = cls._key_id(key_id)
            signature = {
                "algorithm": "hmac-sha256",
                "key_id": label,
                "value": hmac.new(secret, cls._canonical(statement), hashlib.sha256).hexdigest(),
            }
        return {**statement, "signature": signature}

    @classmethod
    def verify(
        cls,
        portfolio: Mapping[str, Any],
        *,
        signing_key: str | bytes | None = None,
    ) -> PortfolioIntegrityReport:
        # [impl->req~ring5.portfolio.signed-manifests~1]
        """Inspect content checksums and, when a secret is supplied, its signature.

        Args:
            portfolio: Parsed portfolio object to inspect.
            signing_key: Optional shared secret for HMAC verification.

        Returns:
            A structured result that distinguishes legacy, checksum-only,
            unverified-signature, verified-signature, and modified states.
        """
        manifest = portfolio.get("integrity_manifest")
        if manifest is None:
            return PortfolioIntegrityReport(
                status="legacy-unverified",
                message="Legacy portfolio — no integrity manifest is available.",
                checksum_valid=None,
                signature_present=False,
                signature_valid=None,
                key_id=None,
            )
        parsed = cls._parse_manifest(manifest)
        if isinstance(parsed, str):
            return PortfolioIntegrityReport(
                status="invalid-manifest",
                message=parsed,
                checksum_valid=None,
                signature_present=False,
                signature_valid=None,
                key_id=None,
            )

        statement, signature = parsed
        body = cls._body(portfolio)
        actual_sections = {name: cls._digest(value) for name, value in cls._sections(body).items()}
        recorded_sections = cast(dict[str, str], statement["sections"])
        section_results = tuple(
            PortfolioIntegritySection(
                name=name,
                expected_sha256=recorded_sections[name],
                actual_sha256=actual_sections[name],
                matches=hmac.compare_digest(recorded_sections[name], actual_sections[name]),
            )
            for name in _SECTION_NAMES
        )
        whole_matches = hmac.compare_digest(
            cast(str, statement["portfolio_sha256"]), cls._digest(body)
        )
        key_id = signature["key_id"] if signature is not None else None
        if not whole_matches or not all(section.matches for section in section_results):
            return PortfolioIntegrityReport(
                status="modified",
                message="Portfolio content does not match its integrity manifest.",
                checksum_valid=False,
                signature_present=signature is not None,
                signature_valid=None,
                key_id=key_id,
                sections=section_results,
            )

        if signature is None:
            return PortfolioIntegrityReport(
                status="checksum-valid",
                message="Checksums match. This portfolio is unchanged but not signed.",
                checksum_valid=True,
                signature_present=False,
                signature_valid=None,
                key_id=None,
                sections=section_results,
            )
        if signing_key is None:
            return PortfolioIntegrityReport(
                status="signature-unverified",
                message="Checksums match. A signature is present but its secret was not supplied.",
                checksum_valid=True,
                signature_present=True,
                signature_valid=None,
                key_id=key_id,
                sections=section_results,
            )

        secret = cls._key_bytes(signing_key)
        actual_signature = hmac.new(
            secret,
            cls._canonical(statement),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature["value"], actual_signature):
            return PortfolioIntegrityReport(
                status="signature-invalid",
                message="Checksums match, but the supplied secret does not verify the signature.",
                checksum_valid=True,
                signature_present=True,
                signature_valid=False,
                key_id=key_id,
                sections=section_results,
            )
        return PortfolioIntegrityReport(
            status="signature-valid",
            message="Checksums and signature are valid.",
            checksum_valid=True,
            signature_present=True,
            signature_valid=True,
            key_id=key_id,
            sections=section_results,
        )

    @staticmethod
    def require_restorable(
        report: PortfolioIntegrityReport,
        *,
        require_signature: bool = False,
    ) -> None:
        # [impl->req~ring5.portfolio.signed-manifests~1]
        """Raise when *report* does not satisfy the requested restore policy.

        Args:
            report: Result returned by :meth:`verify`.
            require_signature: Require a signature verified with a supplied secret.

        Raises:
            PortfolioIntegrityError: Checks fail or a required signature is unverified.
        """
        if not report.safe_to_restore:
            raise PortfolioIntegrityError(report.message)
        if require_signature and report.status != "signature-valid":
            if report.signature_present:
                raise PortfolioIntegrityError(
                    "A verified signature is required; supply the matching signing secret."
                )
            raise PortfolioIntegrityError(
                "A verified signature is required, but this portfolio is not signed."
            )

    @classmethod
    def _parse_manifest(
        cls, manifest: object
    ) -> tuple[dict[str, Any], dict[str, str] | None] | str:
        if not isinstance(manifest, Mapping):
            return "Portfolio integrity manifest must be an object."
        if set(manifest) != {
            "format",
            "format_version",
            "checksum_algorithm",
            "portfolio_sha256",
            "sections",
            "signature",
        }:
            return "Portfolio integrity manifest fields are invalid."
        if (
            manifest.get("format") != "ring5.portfolio-integrity"
            or manifest.get("format_version") != 1
            or manifest.get("checksum_algorithm") != "sha256"
        ):
            return "Portfolio integrity manifest format or algorithm is unsupported."
        digest = manifest.get("portfolio_sha256")
        sections = manifest.get("sections")
        if not cls._valid_digest(digest) or not isinstance(sections, Mapping):
            return "Portfolio integrity manifest checksums are invalid."
        if set(sections) != set(_SECTION_NAMES) or any(
            not cls._valid_digest(sections.get(name)) for name in _SECTION_NAMES
        ):
            return "Portfolio integrity manifest section checksums are invalid."
        statement: dict[str, Any] = {
            "format": manifest["format"],
            "format_version": manifest["format_version"],
            "checksum_algorithm": manifest["checksum_algorithm"],
            "portfolio_sha256": digest,
            "sections": {name: sections[name] for name in _SECTION_NAMES},
        }
        signature_raw = manifest.get("signature")
        if signature_raw is None:
            return statement, None
        if not isinstance(signature_raw, Mapping):
            return "Portfolio integrity signature must be an object or null."
        if set(signature_raw) != {"algorithm", "key_id", "value"}:
            return "Portfolio integrity signature fields are invalid."
        key_id = signature_raw.get("key_id")
        value = signature_raw.get("value")
        if (
            signature_raw.get("algorithm") != "hmac-sha256"
            or not isinstance(key_id, str)
            or not cls._valid_digest(value)
        ):
            return "Portfolio integrity signature is invalid or unsupported."
        try:
            normalized_key_id = cls._key_id(key_id)
        except ValueError as exc:
            return str(exc)
        return statement, {
            "algorithm": "hmac-sha256",
            "key_id": normalized_key_id,
            "value": cast(str, value),
        }

    @staticmethod
    def _body(portfolio: Mapping[str, Any]) -> dict[str, Any]:
        return {str(key): value for key, value in portfolio.items() if key != "integrity_manifest"}

    @staticmethod
    def _sections(body: Mapping[str, Any]) -> dict[str, Any]:
        plots = body.get("plots", [])
        plot_values = plots if isinstance(plots, list) else []
        inputs = {key: body.get(key) for key in _INPUT_KEYS}
        configuration = {key: body.get(key) for key in _CONFIGURATION_KEYS}
        configuration["plots"] = [
            (
                {str(key): value for key, value in plot.items() if key not in _OUTPUT_PLOT_KEYS}
                if isinstance(plot, Mapping)
                else plot
            )
            for plot in plot_values
        ]
        outputs = {
            "plots": [
                (
                    {key: plot.get(key) for key in _OUTPUT_PLOT_KEYS}
                    if isinstance(plot, Mapping)
                    else plot
                )
                for plot in plot_values
            ]
        }
        return {
            "inputs": inputs,
            "configuration": configuration,
            "outputs": outputs,
        }

    @classmethod
    def _digest(cls, value: object) -> str:
        return hashlib.sha256(cls._canonical(value)).hexdigest()

    @staticmethod
    def _canonical(value: object) -> bytes:
        try:
            return json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Portfolio content is not canonical JSON: {exc}") from exc

    @staticmethod
    def _valid_digest(value: object) -> bool:
        return isinstance(value, str) and _DIGEST.fullmatch(value) is not None

    @staticmethod
    def _key_bytes(value: str | bytes) -> bytes:
        if not isinstance(value, (str, bytes)):
            raise ValueError("Portfolio signing keys must be text or bytes.")
        secret = value.encode("utf-8") if isinstance(value, str) else value
        if not secret:
            raise ValueError("Portfolio signing keys cannot be empty.")
        if len(secret) > _MAX_SIGNING_KEY_BYTES:
            raise ValueError(
                f"Portfolio signing keys cannot exceed {_MAX_SIGNING_KEY_BYTES} bytes."
            )
        return secret

    @staticmethod
    def _key_id(value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Portfolio signing key IDs must be non-empty text.")
        if len(value) > _MAX_KEY_ID_LENGTH:
            raise ValueError(
                f"Portfolio signing key IDs cannot exceed {_MAX_KEY_ID_LENGTH} characters."
            )
        if any(ord(character) < 32 for character in value):
            raise ValueError("Portfolio signing key IDs cannot contain control characters.")
        return value
