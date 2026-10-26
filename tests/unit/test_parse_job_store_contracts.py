"""Durable parse jobs admit one bounded current request and typed output format."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.common import parsed_output_codec
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parse_job_models import ParseJobRequest, ParseJobStatus
from src.core.models.parsed_output_models import (
    ParsedCell,
    ParsedFileResult,
    ParsedOutput,
    ParsedVariableResult,
)
from src.core.models.parsing_models import StatConfig
from src.core.services.parse_job_service import build_parse_job_request
from src.core.services.parse_job_store import (
    MAX_REQUEST_JSON_BYTES,
    InvalidStoredOutput,
    ParseJobStore,
)


def _request(root: Path, file_count: int = 1) -> ParseJobRequest:
    inputs = root / "inputs"
    inputs.mkdir()
    (inputs / "stats.txt").write_text("simTicks 1.25\n")
    for index in range(1, file_count):
        source = inputs / f"run-{index}"
        source.mkdir()
        (source / "stats.txt").write_text("simTicks 1.25\n")
    return build_parse_job_request(
        stats_path=str(inputs),
        stats_pattern="stats.txt",
        variables=[
            StatConfig("value", "scalar", source_name="simTicks", params={"source_type": "scalar"})
        ],
        strategy_type="simple",
    )


def _output(root: Path, request: ParseJobRequest) -> ParsedOutput:
    sources = [signature.path for signature in request.file_signatures]
    files = [
        ParsedFileResult(
            source,
            (
                ParsedVariableResult(
                    "value", "number", "scalar", (ParsedCell("value", "number", 1.25),), layout=None
                ),
            ),
        )
        for source in sources
    ]
    return ParsedOutputIO.publish(
        root / "output.csv", ParsedOutputIO.resolve(files, ["value"], sources)
    )


@pytest.mark.parametrize("file_count", [1, 3])
def test_cached_success_progress_is_complete_when_inserted_and_reopened(
    tmp_path: Path, file_count: int
) -> None:
    request = _request(tmp_path, file_count)
    output = _output(tmp_path, request)
    path = tmp_path / "jobs.sqlite3"
    store = ParseJobStore(path)
    queued = store.create_job("queued", request, tmp_path / "queued", 1)
    assert queued.completed_files == 0 and queued.total_files == file_count
    assert queued.progress == 0.0
    cached = store.create_job(
        "cached",
        request,
        tmp_path / "cached",
        1,
        status=ParseJobStatus.SUCCEEDED,
        published_output=output,
        cache_hit=True,
    )
    assert cached.completed_files == cached.total_files == file_count
    assert cached.progress == 1.0
    assert cached.cache_hit and cached.status == ParseJobStatus.SUCCEEDED
    assert ParseJobStore(path).get_job("cached") == cached
    assert cached.published_output == output
    assert ParsedOutputIO.to_frame(output)["value"].tolist() == [1.25] * file_count


def test_sqlite_reopens_exact_current_request_and_output_descriptors(tmp_path: Path) -> None:
    request = _request(tmp_path)
    output = _output(tmp_path, request)
    path = tmp_path / "jobs.sqlite3"
    store = ParseJobStore(path)
    store.create_job("job", request, tmp_path / "attempt", 1)
    store.transition("job", ParseJobStatus.RUNNING, "Running")
    terminal = store.transition(
        "job", ParseJobStatus.SUCCEEDED, "Ready", output=output, published_output=output
    )
    store.remember_published(request.fingerprint, output)
    reopened = ParseJobStore(path)
    assert reopened.get_job("job") == terminal
    assert reopened.get_request("job") == request
    published = reopened.get_published(request.fingerprint)
    assert published == output
    assert published is not None
    assert ParsedOutputIO.to_frame(published)["value"].tolist() == [1.25]
    with closing(sqlite3.connect(path)) as connection, connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert {row[1] for row in connection.execute("PRAGMA table_info(jobs)")} >= {
            "output_json",
            "published_json",
        }


@pytest.mark.parametrize("version", [0, 2, -1])
def test_populated_unversioned_and_unknown_formats_reject_without_migrating(
    tmp_path: Path, version: int
) -> None:
    path = tmp_path / "jobs.sqlite3"
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("CREATE TABLE facts(value TEXT)")
        connection.execute("INSERT INTO facts VALUES ('retained')")
        connection.execute(f"PRAGMA user_version={version}")
    with pytest.raises(ValueError, match="Unsupported parse job store format"):
        ParseJobStore(path)
    with closing(sqlite3.connect(path)) as connection, connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == version
        assert connection.execute("SELECT value FROM facts").fetchone() == ("retained",)
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall() == [("facts",)]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("path", 1),
        ("size", True),
        ("size", "1"),
        ("size", -1),
        ("mtime_ns", False),
        ("mtime_ns", "1"),
        ("mtime_ns", 1 << 200),
    ],
)
def test_source_signatures_reject_wrong_types_before_coercion(
    tmp_path: Path, field: str, value: Any
) -> None:
    request = _request(tmp_path)
    payload = json.loads(ParseJobStore._encode_request(request))
    payload["file_signatures"][0][field] = value
    with pytest.raises((TypeError, ValueError)):
        ParseJobStore._decode_request(json.dumps(payload))


@pytest.mark.parametrize(
    "change",
    [
        "top-key",
        "signature-key",
        "incremental-string",
        "fingerprint-uppercase",
        "source-kind",
        "source-key",
    ],
)
def test_current_request_fields_are_exact_before_job_construction(
    tmp_path: Path, change: str
) -> None:
    request = _request(tmp_path)
    payload = json.loads(ParseJobStore._encode_request(request))
    if change == "top-key":
        payload["variables_json"] = "[]"
    elif change == "signature-key":
        payload["file_signatures"][0]["unknown"] = "ignored"
    elif change == "incremental-string":
        payload["incremental"] = "false"
    elif change == "fingerprint-uppercase":
        payload["fingerprint"] = "A" * 64
    elif change == "source-kind":
        payload["source_context"] = {
            "kind": "csv",
            "path": "input.csv",
            "policy": {"kind": "inferred", "configuration_columns": []},
        }
    else:
        payload["source_context"]["extra"] = True
    with pytest.raises((TypeError, ValueError)):
        ParseJobStore._decode_request(json.dumps(payload))


def test_request_byte_limit_is_checked_before_json_decoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decode = MagicMock(side_effect=AssertionError("Oversized request reached JSON decoder"))
    monkeypatch.setattr("src.core.services.parse_job_store.json", SimpleNamespace(loads=decode))
    with pytest.raises(ValueError, match="1 MB"):
        ParseJobStore._decode_request(" " * (MAX_REQUEST_JSON_BYTES + 1))
    decode.assert_not_called()


def test_output_descriptor_limit_is_checked_before_json_decoding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    output = _output(tmp_path, request)
    path = tmp_path / "jobs.sqlite3"
    store = ParseJobStore(path)
    store.remember_published(request.fingerprint, output)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("UPDATE published_results SET output_json=?", (" " * 257,))
    decode = MagicMock(side_effect=AssertionError("Oversized descriptor reached JSON decoder"))
    monkeypatch.setattr(parsed_output_codec, "MAX_PARSED_DESCRIPTOR_BYTES", 256)
    monkeypatch.setattr(parsed_output_codec, "json", SimpleNamespace(loads=decode))
    with pytest.raises(InvalidStoredOutput):
        store.get_published(request.fingerprint)
    decode.assert_not_called()


@pytest.mark.parametrize("change", ["version", "unknown", "missing"])
def test_current_output_descriptor_rejects_unknown_or_missing_fields(
    tmp_path: Path, change: str
) -> None:
    request = _request(tmp_path)
    output = _output(tmp_path, request)
    path = tmp_path / "jobs.sqlite3"
    store = ParseJobStore(path)
    store.remember_published(request.fingerprint, output)
    payload = json.loads(parsed_output_codec.encode_parsed_output(output))
    if change == "version":
        payload["version"] = 2
    elif change == "unknown":
        payload["metadata"] = {}
    else:
        del payload["schema"]
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("UPDATE published_results SET output_json=?", (json.dumps(payload),))
    with pytest.raises(InvalidStoredOutput):
        store.get_published(request.fingerprint)
