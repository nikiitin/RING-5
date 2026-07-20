"""Versioned shaper-pipeline configuration exchange tests."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from typing import cast

import pytest

from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.data_services.config_service import ConfigService
from src.core.services.data_services.pipeline_config_exchange_service import (
    PIPELINE_CONFIG_FORMAT,
    PipelineConfigExchangeService,
)


@pytest.fixture
def config_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Use one isolated saved-configuration catalog."""
    ConfigService._config_dir = tmp_path
    yield tmp_path
    ConfigService.reset_caches()


def _pipeline() -> list[ShaperStepConfig]:
    return cast(
        list[ShaperStepConfig],
        [
            {"type": "columnSelector", "columns": ["benchmark", "ipc"]},
            {"type": "sort", "order_dict": {"benchmark": ["mcf", "xalanc"]}},
        ],
    )


def test_export_is_deterministic_versioned_and_validated() -> None:
    # [test->req~ring5.shaping.config-import-export~1]
    first = ConfigService.export_configuration(
        "Reviewed pipeline",
        "Keeps the publication columns in review order.",
        _pipeline(),
        "/results/data.csv",
    )
    second = ConfigService.export_configuration(
        "Reviewed pipeline",
        "Keeps the publication columns in review order.",
        _pipeline(),
        "/results/data.csv",
    )

    assert first == second
    document = json.loads(first)
    assert document["format"] == PIPELINE_CONFIG_FORMAT
    assert document["schema_version"] == 1
    assert document["shapers"] == _pipeline()
    assert "timestamp" not in document


def test_import_migrates_legacy_record_and_preserves_content(config_dir: Path) -> None:
    # [test->req~ring5.shaping.config-import-export~1]
    legacy_pipeline = cast(
        list[ShaperStepConfig],
        [
            {
                "type": "mean",
                "meanVars": ["ipc"],
                "meanAlgorithm": "arithmean",
                "groupingColumn": "benchmark",
                "replacingColumn": "benchmark",
            }
        ],
    )
    legacy = {
        "name": "Legacy pipeline",
        "description": "Created before portable exchange.",
        "timestamp": "20260101_120000",
        "shapers": legacy_pipeline,
        "csv_path": "/results/legacy.csv",
    }

    result = ConfigService.import_configuration(json.dumps(legacy))
    saved = ConfigService.load_configuration(result.path)

    assert result.migrated is True
    assert result.conflict_resolution == "none"
    assert result.shapers[0]["groupingColumns"] == ["benchmark"]  # type: ignore[typeddict-item]
    assert "groupingColumn" not in result.shapers[0]
    assert saved["format"] == PIPELINE_CONFIG_FORMAT
    assert saved["schema_version"] == 1
    assert saved["csv_path"] == "/results/legacy.csv"


def test_import_conflicts_can_stop_rename_or_replace(config_dir: Path) -> None:
    # [test->req~ring5.shaping.config-import-export~1]
    original = ConfigService.export_configuration("Shared", "First", _pipeline())
    ConfigService.import_configuration(original)

    with pytest.raises(ValueError, match="already exists"):
        ConfigService.import_configuration(original)

    renamed = ConfigService.import_configuration(original, conflict="rename")
    assert renamed.name == "Shared (2)"
    assert renamed.conflict_resolution == "renamed"

    updated = ConfigService.export_configuration("Shared", "Updated", _pipeline())
    replaced = ConfigService.import_configuration(updated, conflict="replace")
    logical_names = [
        ConfigService.load_configuration(entry["path"])["name"]
        for entry in ConfigService.load_saved_configs()
    ]
    assert replaced.conflict_resolution == "replaced"
    assert logical_names.count("Shared") == 1
    assert "Shared (2)" in logical_names
    assert ConfigService.load_configuration(replaced.path)["description"] == "Updated"


@pytest.mark.parametrize(
    ("document", "message"),
    [
        (
            {
                "format": PIPELINE_CONFIG_FORMAT,
                "schema_version": 2,
                "name": "x",
                "shapers": [],
                "future_field": True,
            },
            "schema version",
        ),
        (
            {
                "format": PIPELINE_CONFIG_FORMAT,
                "schema_version": 1,
                "name": "x",
                "shapers": [],
                "unexpected": True,
            },
            "unsupported fields",
        ),
        (
            {
                "format": PIPELINE_CONFIG_FORMAT,
                "schema_version": 1,
                "name": "x",
                "shapers": [{"type": "missingPlugin"}],
            },
            "unknown shaper type",
        ),
        (
            {
                "format": PIPELINE_CONFIG_FORMAT,
                "schema_version": 1,
                "name": "x",
                "shapers": [{"type": "columnSelector", "columns": []}],
            },
            "is missing",
        ),
        (
            {
                "format": PIPELINE_CONFIG_FORMAT,
                "schema_version": 1,
                "name": "x",
                "shapers": [
                    {
                        "type": "mean",
                        "meanVars": ["ipc"],
                        "meanAlgorithm": "arithmean",
                        "groupingColumns": ["benchmark"],
                    }
                ],
            },
            "replacingColumn",
        ),
    ],
)
def test_import_rejects_unsupported_or_invalid_documents(
    document: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        PipelineConfigExchangeService.loads(json.dumps(document))


def test_import_rejects_wrong_types_nonfinite_numbers_and_oversized_payload() -> None:
    with pytest.raises(TypeError, match="text or bytes"):
        PipelineConfigExchangeService.loads({})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite UTF-8 JSON"):
        PipelineConfigExchangeService.loads('{"value": NaN}')
    with pytest.raises(ValueError, match="256 KiB"):
        PipelineConfigExchangeService.loads(b"x" * (256 * 1024 + 1))
    with pytest.raises(ValueError, match="conflict policy"):
        ConfigService.import_configuration("{}", conflict="merge")  # type: ignore[arg-type]
