"""Known native width and metadata reject before label, worker or cache allocation."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.models.parsed_output_models import ParsedColumn
from src.core.models.parsing_models import StatConfig
from src.core.models.parse_failure_models import ParseDataValueError
from src.parsing.gem5.impl import source_bindings


def config(name="d", maximum=1):
    return StatConfig(
        name,
        "distribution",
        params={
            "source_type": "distribution",
            "minimum": 0,
            "maximum": maximum,
            "bucket_size": 1,
            "zero_policy": "missing",
        },
    )


@pytest.mark.parametrize(
    "configs,files,metadata",
    [
        ([config(maximum=9998)], 1, ()),
        ([config("a", 4998), config("b", 4998)], 1, ()),
        (
            [config(maximum=9997)],
            1,
            (ParsedColumn("sim_path", "text", None), ParsedColumn("config_json", "text", None)),
        ),
        ([config(maximum=1997)], 501, ()),
    ],
)
def test_physical_width_and_matrix_admit_before_native_labels(configs, files, metadata):
    with patch.object(
        source_bindings, "native_bucket_label", side_effect=AssertionError("allocated label")
    ):
        with pytest.raises(ParseDataValueError, match="physical column"):
            source_bindings.resolve_sources(
                configs, None, file_count=files, metadata_columns=metadata
            )


def test_full_metadata_size_is_counted_per_selected_file_before_worker_allocation(monkeypatch):
    monkeypatch.setattr(source_bindings, "MAX_PARSE_RESULT_BYTES", 1000)
    with pytest.raises(ParseDataValueError, match="Repeated per-file layouts"):
        source_bindings.resolve_sources([config()], None, file_count=10, metadata_columns=())


def test_aggregate_schema_budget_rejects_before_retaining_an_oversized_binding(monkeypatch):
    from src.core.common import parsed_output_codec

    monkeypatch.setattr(parsed_output_codec, "MAX_PARSED_SCHEMA_BYTES", 200)
    with pytest.raises(ParseDataValueError, match="schema"):
        source_bindings.resolve_sources([config()], None, file_count=1, metadata_columns=())


def test_same_native_layout_object_is_shared_by_all_selected_workers(tmp_path: Path):
    from src.parsing.gem5.impl.strategies.simple import SimpleStatsStrategy

    plan = source_bindings.resolve_sources([config()], None, file_count=2, metadata_columns=())
    files = (str(tmp_path / "one"), str(tmp_path / "two"))
    works = SimpleStatsStrategy().get_work_items(files, plan)
    assert works[0]._specs["d"].layout is works[1]._specs["d"].layout is plan.accumulators[0].layout
    assert works[0]._accumulators["d"] is not works[1]._accumulators["d"]


def test_source_binding_work_is_bounded_separately_from_logical_physical_width(monkeypatch):
    from src.core.models.parsing_models import ScannedVariable, SourceInstance
    from src.core.models.source_evidence import ResolvedSourceKind

    metadata = ScannedVariable(
        r"cpu\d+",
        "scalar",
        source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
        instances=(SourceInstance("cpu0", ("0",)), SourceInstance("cpu1", ("1",))),
    )
    request = StatConfig(
        "mean", "scalar", source_name=r"cpu\d+", is_regex=True, params={"source_type": "scalar"}
    )
    monkeypatch.setattr(source_bindings, "MAX_PARSE_MATRIX_CELLS", 3)
    with pytest.raises(ValueError, match="source-binding workload"):
        source_bindings.resolve_sources([request], [metadata], file_count=2, metadata_columns=())


def test_oversized_logical_name_rejects_before_schema_json_or_native_labels(monkeypatch):
    from src.core.common import parsed_output_codec
    from src.core.common.safe_regex import MAX_INPUT_LENGTH
    from dataclasses import replace

    def no_encoding(*args, **kwargs):
        raise AssertionError("Oversized schema fields must reject before encoding.")

    monkeypatch.setattr(parsed_output_codec, "_schema_record", no_encoding)
    with pytest.raises(ValueError, match="bounded non-empty"):
        source_bindings.resolve_sources(
            [replace(config(name="d" * (MAX_INPUT_LENGTH + 1)), source_name="d")],
            None,
            file_count=1,
            metadata_columns=(),
        )
