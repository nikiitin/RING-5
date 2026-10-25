"""Portable, versioned exchange for saved shaper-pipeline configurations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from dataclasses import dataclass
from typing import Any

from src.core.common.security_limits import (
    MAX_PIPELINE_CONFIG_BYTES,
    MAX_PIPELINE_CONFIG_DESCRIPTION_LENGTH,
    MAX_PIPELINE_CONFIG_NAME_LENGTH,
)
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.definition import validate_config_values

PIPELINE_CONFIG_FORMAT = "ring5.pipeline-configuration"
PIPELINE_CONFIG_SCHEMA_VERSION = 1

_CURRENT_FIELDS = {
    "format",
    "schema_version",
    "name",
    "description",
    "shapers",
    "csv_path",
    "timestamp",
}


def _reject_json_constant(constant: str) -> float:
    """Reject the non-standard NaN and infinity tokens accepted by ``json``."""
    raise ValueError(f"non-finite number {constant}")


@dataclass(frozen=True)
class _PipelineConfigDocument:
    """Validated internal representation of an exchange document."""

    name: str
    description: str
    shapers: tuple[Mapping[str, object], ...]
    csv_path: str | None


class PipelineConfigExchangeService:
    """Validate and serialize portable pipeline configurations."""

    @staticmethod
    def dumps(
        name: str,
        description: str,
        shapers: Sequence[Mapping[str, object]],
        csv_path: str | None = None,
        *,
        timestamp: str | None = None,
    ) -> bytes:
        """Return deterministic versioned JSON for one pipeline configuration.

        Args:
            name: Human-readable configuration name.
            description: Optional human-readable explanation.
            shapers: Ordered flat shaper configurations.
            csv_path: Optional source CSV association.
            timestamp: Optional local catalog timestamp.

        Returns:
            Stable UTF-8 JSON bytes.

        Raises:
            TypeError: An input has the wrong shape.
            ValueError: The configuration is invalid or cannot be serialized.
        """
        # [impl->req~ring5.shaping.config-import-export~1]
        current: dict[str, Any] = {
            "format": PIPELINE_CONFIG_FORMAT,
            "schema_version": PIPELINE_CONFIG_SCHEMA_VERSION,
            "name": name,
            "description": description,
            "shapers": list(ShaperFactory.validate_pipeline(shapers)),
            "csv_path": csv_path,
        }
        if timestamp is not None:
            current["timestamp"] = timestamp
        document = PipelineConfigExchangeService._validate_document(current)
        payload = {
            "format": PIPELINE_CONFIG_FORMAT,
            "schema_version": PIPELINE_CONFIG_SCHEMA_VERSION,
            "name": document.name,
            "description": document.description,
            "shapers": list(document.shapers),
            "csv_path": document.csv_path,
        }
        if timestamp is not None:
            payload["timestamp"] = timestamp
        try:
            encoded = (
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                    allow_nan=False,
                )
                + "\n"
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("Pipeline configuration contains non-JSON values.") from exc
        if len(encoded) > MAX_PIPELINE_CONFIG_BYTES:
            raise ValueError("Pipeline configuration JSON exceeds the 256 KiB limit.")
        return encoded

    @staticmethod
    def loads(payload: str | bytes | bytearray) -> _PipelineConfigDocument:
        """Load one bounded current pipeline configuration document.

        Args:
            payload: UTF-8 JSON text or bytes.

        Returns:
            Validated current document.

        Raises:
            TypeError: Payload is not text or bytes.
            ValueError: Payload is malformed, unsupported, or invalid.
        """
        # [impl->req~ring5.shaping.config-import-export~1]
        if isinstance(payload, str):
            raw = payload.encode("utf-8")
        elif isinstance(payload, (bytes, bytearray)):
            raw = bytes(payload)
        else:
            raise TypeError("Pipeline configuration import expects JSON text or bytes.")
        if len(raw) > MAX_PIPELINE_CONFIG_BYTES:
            raise ValueError("Pipeline configuration JSON exceeds the 256 KiB limit.")

        try:
            value = json.loads(
                raw.decode("utf-8"),
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
            raise ValueError("Pipeline configuration is not valid finite UTF-8 JSON.") from exc
        if not isinstance(value, dict):
            raise ValueError("Pipeline configuration JSON must contain one object.")

        return PipelineConfigExchangeService._validate_document(value)

    @staticmethod
    def _validate_document(value: dict[str, Any]) -> _PipelineConfigDocument:
        try:
            validate_config_values(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Pipeline configuration contains invalid JSON values: {exc}") from exc
        required = {"format", "schema_version", "name", "shapers"}
        if not required.issubset(value):
            raise ValueError("Pipeline configuration has missing or unsupported fields.")
        if value.get("format") != PIPELINE_CONFIG_FORMAT:
            raise ValueError(f"Unsupported pipeline configuration format {value.get('format')!r}.")
        version = value.get("schema_version")
        if isinstance(version, bool) or not isinstance(version, int):
            raise ValueError("Pipeline configuration schema_version must be an integer.")
        if version != PIPELINE_CONFIG_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported pipeline configuration schema version {version!r}; "
                f"expected {PIPELINE_CONFIG_SCHEMA_VERSION}."
            )

        unknown = sorted(set(value) - _CURRENT_FIELDS)
        if unknown:
            raise ValueError(
                "Pipeline configuration has unsupported fields: " + ", ".join(unknown) + "."
            )

        name = value.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Pipeline configuration name must not be empty.")
        name = name.strip()
        if len(name) > MAX_PIPELINE_CONFIG_NAME_LENGTH:
            raise ValueError(
                f"Pipeline configuration name exceeds {MAX_PIPELINE_CONFIG_NAME_LENGTH} characters."
            )
        description = value.get("description", "")
        if not isinstance(description, str):
            raise ValueError("Pipeline configuration description must be text.")
        if len(description) > MAX_PIPELINE_CONFIG_DESCRIPTION_LENGTH:
            raise ValueError(
                "Pipeline configuration description exceeds "
                f"{MAX_PIPELINE_CONFIG_DESCRIPTION_LENGTH} characters."
            )
        if "timestamp" in value and not isinstance(value["timestamp"], str):
            raise ValueError("Pipeline configuration timestamp must be text.")
        csv_path = value.get("csv_path")
        if csv_path is not None and not isinstance(csv_path, str):
            raise ValueError("Pipeline configuration csv_path must be text or null.")
        shapers = value.get("shapers")
        if not isinstance(shapers, list):
            raise ValueError("Pipeline configuration shapers must be a list.")

        validated = ShaperFactory.validate_pipeline(shapers)
        return _PipelineConfigDocument(
            name=name,
            description=description,
            shapers=tuple(validated),
            csv_path=csv_path,
        )
