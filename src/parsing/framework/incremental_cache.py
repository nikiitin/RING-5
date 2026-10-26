"""Bounded, human-inspectable cache support for incremental simulator parsing."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from src.core.common.file_lock import file_lock
from src.core.common.parsed_output_codec import (
    parsed_file_from_payload,
    iter_parsed_file_encoding,
    unique_json_object,
)
from src.core.models.parsed_output_models import ParsedFileResult
from src.core.common.security_limits import (
    MAX_INCREMENTAL_CACHE_BYTES,
    MAX_PARSE_FILES,
    MAX_PARSE_VARIABLES,
    MAX_PARSE_MATRIX_CELLS,
)
from src.core.models.parsing_models import ScannedVariable, StatConfig
from src.core.models.parsing_models import PARSER_RESULT_VERSION

from src.core.models.parse_failure_models import ResultAdmissionError
from src.parsing.framework.result_admission import ResultAdmission

logger = logging.getLogger(__name__)

CACHE_SCHEMA_VERSION = 2
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


@dataclass(frozen=True)
class CacheReuse:
    """Admitted current file records and the exact budget shared by changed workers."""

    var_names: tuple[str, ...]
    results: tuple[ParsedFileResult, ...]
    removed_files: tuple[str, ...]
    admission: ResultAdmission


def load_cache(
    cache_path: Path,
    expected_configuration_hash: str,
    fingerprints: tuple[tuple[str, str], ...],
) -> CacheReuse:
    """Decode and admit reusable records before accumulating typed cached values.

    A malformed/stale cache discards its provisional context before any workers
    or retained values are returned. Resource admission failures remain visible.
    """
    if type(fingerprints) is not tuple or len(fingerprints) > MAX_PARSE_FILES:
        raise ValueError("Cache reuse requires a bounded immutable fingerprint plan.")
    paths = tuple(path for path, _ in fingerprints)
    admission = ResultAdmission(paths)
    current = dict(fingerprints)
    for fingerprint in current.values():
        _digest(fingerprint)
    if not cache_path.is_file():
        return CacheReuse((), (), (), admission)
    try:
        if cache_path.stat().st_size > MAX_INCREMENTAL_CACHE_BYTES:
            raise ValueError("cache exceeds the byte limit")
        with cache_path.open("rb") as handle:
            encoded = handle.read(MAX_INCREMENTAL_CACHE_BYTES + 1)
        if len(encoded) > MAX_INCREMENTAL_CACHE_BYTES:
            raise ValueError("cache exceeds the byte limit")
        payload = json.loads(encoded.decode("utf-8"), object_pairs_hook=unique_json_object)
        if type(payload) is not dict or set(payload) != {
            "schema_version",
            "configuration_hash",
            "var_names",
            "files",
        }:
            raise ValueError("cache requires the exact current fields")
        if (
            type(payload["schema_version"]) is not int
            or payload["schema_version"] != CACHE_SCHEMA_VERSION
        ):
            raise ValueError("unsupported incremental cache schema")
        if payload["configuration_hash"] != expected_configuration_hash:
            return CacheReuse((), (), (), admission)
        names = payload["var_names"]
        if (
            type(names) is not list
            or not names
            or len(names) > MAX_PARSE_VARIABLES
            or any(type(name) is not str or not name for name in names)
            or len(set(names)) != len(names)
        ):
            raise ValueError("cache variable order is malformed")
        raw_files = payload["files"]
        if type(raw_files) is not list or len(raw_files) > MAX_PARSE_FILES:
            raise ValueError("cache files require a bounded array")
        retained: list[ParsedFileResult] = []
        seen: set[str] = set()
        cells = 0
        for raw in raw_files:
            if type(raw) is not dict or set(raw) != {"fingerprint", "result"}:
                raise ValueError("cache file record is malformed")
            fingerprint = raw["fingerprint"]
            _digest(fingerprint)
            result = parsed_file_from_payload(raw["result"])
            if result.source_path in seen or {
                variable.name for variable in result.variables
            } != set(names):
                raise ValueError("cache source/variable ownership does not match its plan")
            seen.add(result.source_path)
            cells += sum(len(variable.cells) for variable in result.variables) + len(
                result.metadata
            )
            if cells > MAX_PARSE_MATRIX_CELLS:
                raise ValueError("cache exceeds the matrix cell limit")
            if current.get(result.source_path) == fingerprint:
                admission.admit(result, source_path=result.source_path)
                retained.append(result)
        return CacheReuse(
            tuple(names), tuple(retained), tuple(sorted(seen - set(current))), admission
        )
    except ResultAdmissionError:
        raise
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        RecursionError,
    ) as exc:
        logger.warning("PARSER: ignoring invalid incremental cache %s: %s", cache_path, str(exc))
        return CacheReuse((), (), (), ResultAdmission(paths))


def _digest(value: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError("cache identities require lowercase SHA-256 digests")


def encode_cache(
    config_hash: str,
    var_names: Sequence[str],
    fingerprints: Sequence[tuple[str, str]],
    results: Sequence[ParsedFileResult],
) -> bytes:
    """Prepare bounded current cache bytes before the CSV publication transaction."""
    _digest(config_hash)
    if (
        not var_names
        or len(var_names) > MAX_PARSE_VARIABLES
        or len(set(var_names)) != len(var_names)
        or any(type(name) is not str or not name for name in var_names)
    ):
        raise ValueError("cache variable order is malformed")
    if not results or len(results) > MAX_PARSE_FILES or len(fingerprints) != len(results):
        raise ValueError("cache requires one typed result per planned fingerprint")
    by_source: dict[str, ParsedFileResult] = {}
    cells = 0
    for result in results:
        if type(result) is not ParsedFileResult:
            raise TypeError("cache requires typed file results")
        if result.source_path in by_source or {
            variable.name for variable in result.variables
        } != set(var_names):
            raise ValueError("cache source/variable ownership does not match its plan")
        cells += sum(len(variable.cells) for variable in result.variables) + len(result.metadata)
        if cells > MAX_PARSE_MATRIX_CELLS:
            raise ValueError("cache exceeds the matrix cell limit")
        by_source[result.source_path] = result
    paths = tuple(path for path, _ in fingerprints)
    if len(set(paths)) != len(paths) or set(paths) != set(by_source):
        raise ValueError("cache fingerprints must cover the exact result source paths")
    encoded = bytearray()

    def append(fragment: bytes) -> None:
        if len(encoded) + len(fragment) > MAX_INCREMENTAL_CACHE_BYTES:
            raise ValueError("PARSER: incremental cache exceeds the byte limit.")
        encoded.extend(fragment)

    encoder = json.JSONEncoder(
        ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
    )

    def record(value: object) -> None:
        for fragment in encoder.iterencode(value):
            append(fragment.encode("utf-8"))

    append(
        b'{"schema_version":'
        + str(CACHE_SCHEMA_VERSION).encode("ascii")
        + b',"configuration_hash":'
    )
    record(config_hash)
    append(b',"var_names":')
    record(list(var_names))
    append(b',"files":[')
    for index, (source_path, fingerprint) in enumerate(fingerprints):
        _digest(fingerprint)
        if index:
            append(b",")
        append(b'{"fingerprint":')
        record(fingerprint)
        append(b',"result":')
        for fragment in iter_parsed_file_encoding(by_source[source_path]):
            append(fragment)
        append(b"}")
    append(b"]}\n")
    return bytes(encoded)


def write_cache(cache_path: Path, encoded: bytes) -> None:
    # [impl->req~ring5.ingestion.incremental-parsing~1]
    """Atomically promote prepared cache bytes under the output-then-cache lock order.

    Readers consume one atomically replaced file without acquiring this write lock.
    Publication callbacks acquire this lock only while their output lock is held.
    """
    if type(encoded) is not bytes or len(encoded) > MAX_INCREMENTAL_CACHE_BYTES:
        raise ValueError("Prepared incremental cache exceeds the byte limit.")
    cache_path = cache_path.expanduser().resolve()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    with file_lock(cache_path.with_name(f".{cache_path.name}.lock")):
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{cache_path.name}.",
                suffix=".tmp",
                dir=cache_path.parent,
                delete=False,
            ) as handle:
                temporary_name = handle.name
                if handle.write(encoded) != len(encoded):
                    raise OSError("Incomplete parser cache write.")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, cache_path)
            temporary_name = None
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)
