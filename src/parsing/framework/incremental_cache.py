"""Bounded, human-inspectable cache support for incremental simulator parsing."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from src.core.common.security_limits import (
    MAX_INCREMENTAL_CACHE_BYTES,
    MAX_INCREMENTAL_CACHE_COLUMNS,
    MAX_PARSE_FILES,
    MAX_PARSE_VARIABLES,
)
from src.core.models import ScannedVariable, StatConfig
from src.core.models.parsing_models import PARSER_RESULT_VERSION

logger = logging.getLogger(__name__)

CACHE_SCHEMA_VERSION = 1
DEFAULT_CACHE_NAME = ".ring5-incremental-parse.json"


def configuration_hash(
    stats_pattern: str,
    strategy_type: str,
    variables: Sequence[StatConfig],
    scanned_vars: Sequence[ScannedVariable] | None,
) -> str:
    """Return a stable digest of every setting that can change parsed columns or values."""
    scanned_payload = [variable.to_dict() for variable in (scanned_vars or ())]
    payload = {
        "cache_schema": CACHE_SCHEMA_VERSION,
        "parser_result_version": PARSER_RESULT_VERSION,
        "stats_pattern": stats_pattern,
        "strategy": strategy_type,
        "variables": [asdict(variable) for variable in variables],
        "scanned_variables": scanned_payload,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_cache(
    cache_path: Path,
    expected_configuration_hash: str,
) -> tuple[list[str], dict[str, tuple[str, dict[str, str]]]]:
    """Load a matching JSON cache; return an empty cache for stale or malformed content."""
    if not cache_path.is_file():
        return [], {}
    try:
        size = cache_path.stat().st_size
        if size > MAX_INCREMENTAL_CACHE_BYTES:
            raise ValueError(
                f"cache is larger than {MAX_INCREMENTAL_CACHE_BYTES // (1024 * 1024)} MiB"
            )
        with cache_path.open("rb") as handle:
            raw_payload = handle.read(MAX_INCREMENTAL_CACHE_BYTES + 1)
        if len(raw_payload) > MAX_INCREMENTAL_CACHE_BYTES:
            raise ValueError(
                f"cache is larger than {MAX_INCREMENTAL_CACHE_BYTES // (1024 * 1024)} MiB"
            )
        payload = json.loads(raw_payload.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("cache root is not an object")
        if payload.get("schema_version") != CACHE_SCHEMA_VERSION:
            return [], {}
        if payload.get("configuration_hash") != expected_configuration_hash:
            return [], {}

        raw_names = payload.get("var_names")
        raw_files = payload.get("files")
        if (
            not isinstance(raw_names, list)
            or len(raw_names) > MAX_PARSE_VARIABLES
            or not all(isinstance(name, str) and name for name in raw_names)
        ):
            raise ValueError("var_names must be non-empty strings")
        if not isinstance(raw_files, dict) or len(raw_files) > MAX_PARSE_FILES:
            raise ValueError("files must be a bounded object")

        files: dict[str, tuple[str, dict[str, str]]] = {}
        for source_path, record in raw_files.items():
            if not isinstance(source_path, str) or not source_path or not isinstance(record, dict):
                raise ValueError("cache file records are malformed")
            fingerprint = record.get("fingerprint")
            cells = record.get("cells")
            if (
                not isinstance(fingerprint, str)
                or len(fingerprint) != 64
                or any(character not in "0123456789abcdef" for character in fingerprint)
            ):
                raise ValueError("cache fingerprint is malformed")
            if (
                not isinstance(cells, dict)
                or len(cells) > MAX_INCREMENTAL_CACHE_COLUMNS
                or not all(
                    isinstance(column, str) and column and isinstance(value, str)
                    for column, value in cells.items()
                )
            ):
                raise ValueError("cache cells are malformed or exceed their bound")
            files[source_path] = (fingerprint, dict(cells))
        return list(raw_names), files
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("PARSER: ignoring invalid incremental cache %s: %s", cache_path, exc)
        return [], {}


def write_cache(
    cache_path: Path,
    config_hash: str,
    var_names: Sequence[str],
    fingerprints: Sequence[tuple[str, str]],
    rows: dict[str, dict[str, str]],
) -> None:
    # [impl->req~ring5.ingestion.incremental-parsing~1]
    """Atomically persist a bounded JSON cache after the final CSV succeeds."""
    files = {
        source_path: {"fingerprint": fingerprint, "cells": rows[source_path]}
        for source_path, fingerprint in fingerprints
    }
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "configuration_hash": config_hash,
        "var_names": list(var_names),
        "files": files,
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    if len(encoded) > MAX_INCREMENTAL_CACHE_BYTES:
        raise RuntimeError(
            "PARSER: incremental cache exceeds the "
            f"{MAX_INCREMENTAL_CACHE_BYTES // (1024 * 1024)} MiB limit."
        )

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{cache_path.name}.",
            suffix=".tmp",
            dir=cache_path.parent,
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, cache_path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
