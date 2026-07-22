"""Portable, versioned exchange for saved shaper-pipeline configurations."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from typing import Any, cast

from src.core.common.security_limits import (
    MAX_PIPELINE_CONFIG_BYTES,
    MAX_PIPELINE_CONFIG_DEPTH,
    MAX_PIPELINE_CONFIG_DESCRIPTION_LENGTH,
    MAX_PIPELINE_CONFIG_NAME_LENGTH,
    MAX_PIPELINE_CONFIG_STEPS,
    MAX_PIPELINE_CONFIG_STRING_LENGTH,
)
from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.validation import validate_shaper_config

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
_LEGACY_FIELDS = {"name", "description", "shapers", "csv_path", "timestamp"}


def _reject_json_constant(constant: str) -> float:
    """Reject the non-standard NaN and infinity tokens accepted by ``json``."""
    raise ValueError(f"non-finite number {constant}")


@dataclass(frozen=True)
class _PipelineConfigDocument:
    """Validated internal representation of an exchange document."""

    name: str
    description: str
    shapers: tuple[ShaperStepConfig, ...]
    csv_path: str | None
    migrated: bool


class PipelineConfigExchangeService:
    """Validate, migrate, and serialize portable pipeline configurations."""

    @staticmethod
    def dumps(
        name: str,
        description: str,
        shapers: list[ShaperStepConfig],
        csv_path: str | None = None,
    ) -> bytes:
        """Return deterministic versioned JSON for one pipeline configuration.

        Args:
            name: Human-readable configuration name.
            description: Optional human-readable explanation.
            shapers: Ordered flat shaper configurations.
            csv_path: Optional source CSV association.

        Returns:
            Stable UTF-8 JSON bytes.

        Raises:
            TypeError: An input has the wrong shape.
            ValueError: The configuration is invalid or cannot be serialized.
        """
        # [impl->req~ring5.shaping.config-import-export~1]
        document = PipelineConfigExchangeService._validate_document(
            {
                "format": PIPELINE_CONFIG_FORMAT,
                "schema_version": PIPELINE_CONFIG_SCHEMA_VERSION,
                "name": name,
                "description": description,
                "shapers": shapers,
                "csv_path": csv_path,
            },
            migrated=False,
        )
        payload = {
            "format": PIPELINE_CONFIG_FORMAT,
            "schema_version": PIPELINE_CONFIG_SCHEMA_VERSION,
            "name": document.name,
            "description": document.description,
            "shapers": list(document.shapers),
            "csv_path": document.csv_path,
        }
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
        """Load one bounded current or legacy pipeline configuration document.

        Args:
            payload: UTF-8 JSON text or bytes.

        Returns:
            Validated current document with migration provenance.

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

        migrated = "format" not in value and "schema_version" not in value
        if migrated:
            unknown = sorted(set(value) - _LEGACY_FIELDS)
            if unknown or not {"name", "shapers"}.issubset(value):
                raise ValueError("Legacy pipeline configuration has missing or unsupported fields.")
            value = {
                "format": PIPELINE_CONFIG_FORMAT,
                "schema_version": PIPELINE_CONFIG_SCHEMA_VERSION,
                "name": value["name"],
                "description": value.get("description", ""),
                "shapers": PipelineConfigExchangeService._migrate_legacy_shapers(value["shapers"]),
                "csv_path": value.get("csv_path"),
            }
        else:
            required = {"format", "schema_version", "name", "shapers"}
            if not required.issubset(value):
                raise ValueError("Pipeline configuration has missing or unsupported fields.")
            if value["format"] != PIPELINE_CONFIG_FORMAT:
                raise ValueError(f"Unsupported pipeline configuration format {value['format']!r}.")
            version = value["schema_version"]
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
        return PipelineConfigExchangeService._validate_document(value, migrated=migrated)

    @staticmethod
    def _validate_document(value: dict[str, Any], *, migrated: bool) -> _PipelineConfigDocument:
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

        PipelineConfigExchangeService._validate_json_value(value, depth=0)
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
        csv_path = value.get("csv_path")
        if csv_path is not None and not isinstance(csv_path, str):
            raise ValueError("Pipeline configuration csv_path must be text or null.")
        shapers = value.get("shapers")
        if not isinstance(shapers, list):
            raise ValueError("Pipeline configuration shapers must be a list.")

        validated: list[ShaperStepConfig] = []
        counter = [0]
        for index, step in enumerate(shapers):
            validated.append(
                PipelineConfigExchangeService._validate_step(
                    step,
                    location=str(index),
                    depth=0,
                    counter=counter,
                )
            )
        return _PipelineConfigDocument(
            name=name,
            description=description,
            shapers=tuple(validated),
            csv_path=csv_path,
            migrated=migrated,
        )

    @staticmethod
    def _validate_step(
        value: object,
        *,
        location: str,
        depth: int,
        counter: list[int],
    ) -> ShaperStepConfig:
        counter[0] += 1
        if counter[0] > MAX_PIPELINE_CONFIG_STEPS:
            raise ValueError(
                f"Pipeline configuration exceeds the {MAX_PIPELINE_CONFIG_STEPS}-step limit."
            )
        if depth > MAX_PIPELINE_CONFIG_DEPTH:
            raise ValueError("Pipeline configuration nesting is too deep.")
        if not isinstance(value, dict):
            raise ValueError(f"Pipeline step {location} must be an object.")
        shaper_type = value.get("type")
        if not isinstance(shaper_type, str) or not shaper_type:
            raise ValueError(f"Pipeline step {location} must declare a shaper type.")
        if shaper_type not in ShaperFactory.get_available_types():
            raise ValueError(f"Pipeline step {location} uses unknown shaper type {shaper_type!r}.")

        step = cast(ShaperStepConfig, copy.deepcopy(value))
        complete, missing = validate_shaper_config(shaper_type, step)
        if not complete:
            raise ValueError(
                f"Pipeline step {location} ({shaper_type}) is missing: "
                + ", ".join(missing or ())
                + "."
            )
        try:
            ShaperFactory.create_shaper(shaper_type, step)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Pipeline step {location} ({shaper_type}) is invalid: {exc}") from exc
        if shaper_type == "mean":
            replacing_column = step.get("replacingColumn")  # type: ignore[typeddict-item]
            if not isinstance(replacing_column, str) or not replacing_column:
                raise ValueError(f"Pipeline step {location} (mean) is missing: replacingColumn.")

        if shaper_type == "splitApply":
            groups = step.get("groups", [])  # type: ignore[typeddict-item]
            if isinstance(groups, list):
                for group_index, group in enumerate(groups):
                    if not isinstance(group, dict):
                        continue
                    nested = group.get("pipeline", [])
                    if not isinstance(nested, list):
                        continue
                    for nested_index, nested_step in enumerate(nested):
                        PipelineConfigExchangeService._validate_step(
                            nested_step,
                            location=f"{location}.{group_index}.{nested_index}",
                            depth=depth + 1,
                            counter=counter,
                        )
        return step

    @staticmethod
    def _migrate_legacy_shapers(value: object) -> object:
        """Normalize legacy mean grouping fields, including nested pipelines."""
        migrated = copy.deepcopy(value)
        if not isinstance(migrated, list):
            return migrated
        for step in migrated:
            if not isinstance(step, dict):
                continue
            if (
                step.get("type") == "mean"
                and "groupingColumns" not in step
                and isinstance(step.get("groupingColumn"), str)
            ):
                step["groupingColumns"] = [step.pop("groupingColumn")]
            if step.get("type") != "splitApply":
                continue
            groups = step.get("groups")
            if not isinstance(groups, list):
                continue
            for group in groups:
                if isinstance(group, dict) and "pipeline" in group:
                    group["pipeline"] = PipelineConfigExchangeService._migrate_legacy_shapers(
                        group["pipeline"]
                    )
        return migrated

    @staticmethod
    def _validate_json_value(value: object, *, depth: int) -> None:
        if depth > MAX_PIPELINE_CONFIG_DEPTH:
            raise ValueError("Pipeline configuration nesting is too deep.")
        if isinstance(value, str):
            if len(value) > MAX_PIPELINE_CONFIG_STRING_LENGTH:
                raise ValueError(
                    "Pipeline configuration text value exceeds "
                    f"{MAX_PIPELINE_CONFIG_STRING_LENGTH} characters."
                )
            return
        if value is None or isinstance(value, (bool, int)):
            return
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("Pipeline configuration numbers must be finite.")
            return
        if isinstance(value, list):
            for item in value:
                PipelineConfigExchangeService._validate_json_value(item, depth=depth + 1)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError("Pipeline configuration object keys must be text.")
                PipelineConfigExchangeService._validate_json_value(key, depth=depth + 1)
                PipelineConfigExchangeService._validate_json_value(item, depth=depth + 1)
            return
        raise ValueError("Pipeline configuration contains a non-JSON value.")
