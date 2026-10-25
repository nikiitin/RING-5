"""Bounded content identity shared by all simulator result caches."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

from src.core.common.security_limits import (
    MAX_PARSE_FILES,
    MAX_PARSE_FILE_BYTES,
    MAX_PARSE_TOTAL_BYTES,
)


def fingerprint_inputs(
    file_paths: Sequence[str], strategy_type: str
) -> tuple[tuple[str, str], ...]:
    # [impl->req~ring5.ingestion.incremental-parsing~1]
    """Hash each selected stats file and any strategy-owned companion input.

    Full content hashes deliberately favor correct change detection over metadata-only shortcuts.
    The parser's existing per-file, aggregate-byte, and file-count bounds are enforced before any
    worker submission.
    """
    if len(file_paths) > MAX_PARSE_FILES:
        raise RuntimeError(
            f"PARSER: {len(file_paths)} files exceed the {MAX_PARSE_FILES}-file parse limit."
        )

    total_bytes = 0
    hashed_bytes = 0
    fingerprints: list[tuple[str, str]] = []
    for raw_path in sorted(file_paths):
        path = Path(raw_path).resolve(strict=True)
        sources = [path]
        if strategy_type == "config_aware":
            sources.append(path.parent / "config.ini")

        digest = hashlib.sha256()
        for source in sources:
            if not source.is_file():
                raise FileNotFoundError(f"PARSER: parser input not found: {source}")
            size = source.stat().st_size
            if size > MAX_PARSE_FILE_BYTES:
                raise RuntimeError(
                    "PARSER: parser input exceeds the "
                    f"{MAX_PARSE_FILE_BYTES // (1024 * 1024)} MiB per-file limit: {source}"
                )
            total_bytes += size
            if total_bytes > MAX_PARSE_TOTAL_BYTES:
                raise RuntimeError(
                    "PARSER: selected parser inputs exceed the "
                    f"{MAX_PARSE_TOTAL_BYTES // (1024 * 1024 * 1024)} GiB aggregate limit."
                )
            digest.update(source.name.encode("utf-8"))
            digest.update(b"\0")
            source_hashed_bytes = 0
            with source.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    source_hashed_bytes += len(chunk)
                    hashed_bytes += len(chunk)
                    if source_hashed_bytes > MAX_PARSE_FILE_BYTES:
                        raise RuntimeError(
                            "PARSER: parser input grew beyond the "
                            f"{MAX_PARSE_FILE_BYTES // (1024 * 1024)} MiB per-file limit "
                            f"while fingerprinting: {source}"
                        )
                    if hashed_bytes > MAX_PARSE_TOTAL_BYTES:
                        raise RuntimeError(
                            "PARSER: parser inputs grew beyond the "
                            f"{MAX_PARSE_TOTAL_BYTES // (1024 * 1024 * 1024)} GiB "
                            "aggregate limit while fingerprinting."
                        )
                    digest.update(chunk)
            digest.update(b"\0")
        fingerprints.append((str(path), digest.hexdigest()))
    return tuple(fingerprints)
