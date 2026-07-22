"""Security and invalidation tests for the inspectable incremental parse cache."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.models import ScannedVariable, StatConfig
from src.parsing.framework.incremental_cache import (
    configuration_hash,
    fingerprint_inputs,
    load_cache,
    write_cache,
)


def test_cache_is_plain_json_and_rejects_stale_or_malformed_records(tmp_path: Path) -> None:
    # [test->req~ring5.ingestion.incremental-parsing~1]
    source = tmp_path / "stats.txt"
    source.write_text("simTicks 100\n", encoding="utf-8")
    fingerprints = fingerprint_inputs([str(source)], "simple")
    config = StatConfig(name="simTicks", type="scalar")
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
        [ScannedVariable(name="other", type="scalar")],
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
