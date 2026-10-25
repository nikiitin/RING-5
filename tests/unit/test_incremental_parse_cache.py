"""Security and invalidation tests for the inspectable incremental parse cache."""

from __future__ import annotations

import json

import pytest

import src.parsing.framework.incremental_cache as cache_module
from pathlib import Path

from src.core.common.input_identity import fingerprint_inputs
from src.core.models.parsing_models import ScannedVariable, StatConfig
from src.core.models.parsing_models import SourceInstance
from src.parsing.framework.incremental_cache import (
    configuration_hash,
    load_cache,
    write_cache,
)


def test_cache_is_plain_json_and_rejects_stale_or_malformed_records(tmp_path: Path) -> None:
    # [test->req~ring5.ingestion.incremental-parsing~1]
    source = tmp_path / "stats.txt"
    source.write_text("simTicks 100\n", encoding="utf-8")
    fingerprints = fingerprint_inputs([str(source)], "simple")
    config = StatConfig(name="simTicks", type="scalar", params={"source_type": "scalar"})
    config_hash = configuration_hash("stats.txt", "simple", [config], None)
    cache = tmp_path / "cache.json"

    write_cache(
        cache,
        config_hash,
        ["simTicks"],
        fingerprints,
        {str(source.resolve()): {"simTicks": "100"}},
    )
    payload = json.loads(cache.read_text(encoding="utf-8"))
    assert payload["files"][str(source.resolve())]["cells"] == {"simTicks": "100"}
    assert load_cache(cache, config_hash)[1][str(source.resolve())][1] == {"simTicks": "100"}

    changed_config = configuration_hash(
        "stats.txt",
        "simple",
        [config],
        [
            ScannedVariable(
                name="other",
                type="scalar",
                source_type="scalar",
                instances=(SourceInstance("other", ()),),
            )
        ],
    )
    assert load_cache(cache, changed_config) == ([], {})

    cache.write_text('{"schema_version": 1, "files":', encoding="utf-8")
    assert load_cache(cache, config_hash) == ([], {})


def test_config_aware_fingerprint_includes_the_companion_configuration(tmp_path: Path) -> None:
    source = tmp_path / "stats.txt"
    config = tmp_path / "config.ini"
    source.write_text("simTicks 100\n", encoding="utf-8")
    config.write_text("[system]\ncpus=2\n", encoding="utf-8")

    before = fingerprint_inputs([str(source)], "config_aware")
    config.write_text("[system]\ncpus=4\n", encoding="utf-8")
    after = fingerprint_inputs([str(source)], "config_aware")

    assert before != after


def test_parser_semantic_revision_invalidates_pre_fix_cached_measurements(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "stats.txt"
    source.write_text("simTicks 100\n", encoding="utf-8")
    fingerprints = fingerprint_inputs([str(source)], "simple")
    config = StatConfig(
        "missing",
        "distribution",
        params={"minimum": 0, "maximum": 1, "source_type": "distribution"},
    )
    current_revision = cache_module.PARSER_RESULT_VERSION
    monkeypatch.setattr(cache_module, "PARSER_RESULT_VERSION", current_revision - 1)
    old_hash = configuration_hash("stats.txt", "simple", [config], None)
    cache = tmp_path / "cache.json"
    write_cache(
        cache, old_hash, ["missing"], fingerprints, {str(source.resolve()): {"missing..0": "0.0"}}
    )
    monkeypatch.setattr(cache_module, "PARSER_RESULT_VERSION", current_revision)
    current_hash = configuration_hash("stats.txt", "simple", [config], None)
    assert current_hash != old_hash
    assert load_cache(cache, current_hash) == ([], {})
