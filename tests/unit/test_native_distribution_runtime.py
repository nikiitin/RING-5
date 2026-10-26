"""Real native text observes declared storage cells without positional fabrication."""

from __future__ import annotations

import math
from pathlib import Path
from typing import cast
from src.core.models.parsed_output_models import ParsedFileResult

import pytest

from src.core.models.parsing_models import StatConfig
from src.core.models.native_distribution_layout import (
    NativeDistributionLayout,
    OpaqueDistributionLayout,
    ZeroPolicy,
)
from src.core.models.parse_failure_models import ParseDataValueError
from src.parsing.gem5.impl.source_bindings import SourcePlan, resolve_sources
from src.parsing.gem5.impl.strategies.simple import SimpleStatsStrategy

pytestmark = pytest.mark.xdist_group("perl_pool")
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/gem5_native_text"


def request(
    *,
    minimum: float = 0,
    maximum: float = 1,
    bucket_size: float = 1,
    policy: ZeroPolicy = "missing",
    repeat: int = 1,
    name: str = "out",
) -> StatConfig:
    return StatConfig(
        name,
        "distribution",
        source_name="d",
        repeat=repeat,
        params={
            "source_type": "distribution",
            "minimum": minimum,
            "maximum": maximum,
            "bucket_size": bucket_size,
            "zero_policy": policy,
        },
    )


def parse(
    tmp_path: Path, text: str, configs: list[StatConfig]
) -> tuple[ParsedFileResult, SourcePlan]:
    source = tmp_path / "stats.txt"
    source.write_text(text)
    plan = resolve_sources(configs, None, file_count=1, metadata_columns=())
    work = SimpleStatsStrategy().get_work_items((str(source),), plan)[0]
    return work(), plan


@pytest.mark.parametrize(
    "fixture,geometry",
    [
        ("integer", (0, 1, 1)),
        ("offset_unit", (0.25, 1.25, 1)),
        ("nonunit", (0.25, 5.75, 2.5)),
        ("negative", (-1.25, 1.25, 0.5)),
        ("nozero", (0.25, 2.25, 1)),
        ("nozero_half", (0.25, 2.25, 0.5)),
        ("nozero_wider", (-0.75, 3.25, 1)),
        ("empty_dist", (0, 1, 1)),
        ("oneline_integer", (0, 1, 1)),
        ("oneline_offset", (0.25, 1.25, 1)),
    ],
)
def test_pinned_native_text_uses_full_precision_declared_cells(
    tmp_path: Path, fixture: str, geometry: tuple[float, float, float]
) -> None:
    # [test->req~ring5.ingestion.distribution~2]
    text = (FIXTURES / f"{fixture}.txt").read_text()
    # The fixture owns the actual source name; source identity is independent of the alias.
    name = next(line.split("::")[0] for line in text.splitlines() if "::" in line)
    config = request(minimum=geometry[0], maximum=geometry[1], bucket_size=geometry[2])
    from dataclasses import replace

    result, plan = parse(tmp_path, text, [replace(config, source_name=name)])
    variable = result.variables[0]
    assert variable.layout is plan.accumulators[0].layout
    assert type(variable.layout) is NativeDistributionLayout
    assert variable.layout.geometry.bucket_size == geometry[2]
    assert tuple(cell.column for cell in variable.cells) == tuple(
        c.column for c in variable.layout.columns
    )


@pytest.mark.parametrize("policy,expected,missing", [("missing", math.nan, 3), ("nozero", 0.0, 0)])
def test_sparse_actual_observation_applies_only_explicit_omission_policy(
    tmp_path: Path, policy: ZeroPolicy, expected: float, missing: int
) -> None:
    # [test->req~ring5.ingestion.distribution~2]
    result, _ = parse(tmp_path, "d::samples 2\nd::1 2\n", [request(policy=policy)])
    values = {cell.column: cast(float, cell.value) for cell in result.variables[0].cells}
    assert math.isnan(values["out..0"]) if math.isnan(expected) else values["out..0"] == expected
    assert result.variables[0].missing_measurements == missing


@pytest.mark.parametrize("policy", ["missing", "nozero"])
def test_absent_whole_source_and_missing_repeat_remain_absent(
    tmp_path: Path, policy: ZeroPolicy
) -> None:
    absent, _ = parse(tmp_path, "other 2\n", [request(policy=policy)])
    assert all(math.isnan(cast(float, cell.value)) for cell in absent.variables[0].cells)
    incomplete, _ = parse(tmp_path, "d::samples 2\nd::1 2\n", [request(policy=policy, repeat=2)])
    assert all(math.isnan(cast(float, cell.value)) for cell in incomplete.variables[0].cells)


def test_sparse_repeated_native_headers_do_not_zip_unrelated_entries(tmp_path: Path) -> None:
    text = "d::samples 1\nd::0 2\nd::samples 1\nd::1 4\n"
    result, _ = parse(tmp_path, text, [request(policy="nozero", repeat=2)])
    assert [cell.value for cell in result.variables[0].cells] == [0, 1, 2, 0]


def test_header_free_complete_frames_keep_actual_fractional_means(tmp_path: Path) -> None:
    text = (
        "d::underflows 0\nd::0 1\nd::1 2\nd::overflows 0\nd::underflows 0"
        "\nd::0 2\nd::1 3\nd::overflows 0\n"
    )
    result, _ = parse(tmp_path, text, [request(repeat=2)])
    assert [cell.value for cell in result.variables[0].cells] == [0, 1.5, 2.5, 0]


def test_late_first_samples_header_binds_existing_summary_to_frame_zero(tmp_path: Path) -> None:
    config = request(policy="nozero")
    from dataclasses import replace

    config = replace(config, params={**config.params, "statistics": ["mean"]})
    result, _ = parse(tmp_path, "d::mean 2\nd::samples 1\nd::0 2\n", [config])
    assert result.variables[0].cells[-1].value == 2


def test_measured_nan_is_not_an_omitted_zero(tmp_path: Path) -> None:
    result, _ = parse(tmp_path, "d::samples 1\nd::0 nan\nd::1 2\n", [request(policy="nozero")])
    assert math.isnan(cast(float, result.variables[0].cells[1].value))
    assert result.variables[0].missing_measurements == 0


@pytest.mark.parametrize("values", ["1", "1 2 3", "1 2 nan"])
def test_oneline_requires_exact_allocated_cell_count_without_padding(
    tmp_path: Path, values: str
) -> None:
    payload = " | ".join(values.split())
    text = f"d::bucket_size 1\nd::min_bucket 0\nd::max_bucket 1\nd::samples 1\nd | {payload}\n"
    with pytest.raises(ParseDataValueError, match="cell count"):
        parse(tmp_path, text, [request(policy="nozero")])


def test_oneline_rounded_header_checks_each_target_declared_grid(tmp_path: Path) -> None:
    text = (
        "d::bucket_size 0.500000\nd::min_bucket 0.250000\nd::max_bucket"
        " 1.250000\nd::samples 1\nd | 1 | 2 | 3 | 4\n"
    )
    result, plan = parse(
        tmp_path,
        text,
        [
            request(minimum=0.25, maximum=1.25, bucket_size=0.5),
            request(minimum=0.2500001, maximum=1.2500001, bucket_size=0.5, name="other"),
        ],
    )
    assert len(result.variables) == 2
    assert isinstance(plan.accumulators[0].layout, NativeDistributionLayout)
    assert isinstance(plan.accumulators[1].layout, NativeDistributionLayout)
    assert (
        plan.accumulators[0].layout.geometry.minimum != plan.accumulators[1].layout.geometry.minimum
    )
    with pytest.raises(ParseDataValueError, match="Printed geometry"):
        parse(tmp_path, text, [request(minimum=0.2501, maximum=1.2501, bucket_size=0.5)])


@pytest.mark.parametrize("policy,accepted", [("nozero", True), ("missing", False)])
def test_oneline_omitted_zero_bound_requires_nozero_declaration(
    tmp_path: Path, policy: ZeroPolicy, accepted: bool
) -> None:
    text = "d::bucket_size 1\nd::max_bucket 1\nd::samples 1\nd | 1 | 2\n"
    if accepted:
        result, _ = parse(tmp_path, text, [request(policy=policy)])
        assert [cell.value for cell in result.variables[0].cells] == [0, 1, 2, 0]
    else:
        with pytest.raises(ParseDataValueError, match="reported width"):
            parse(tmp_path, text, [request(policy=policy)])


@pytest.mark.parametrize(
    "declared,layout_type", [("vector", type(None)), ("distribution", OpaqueDistributionLayout)]
)
def test_identical_literal_text_keeps_explicit_declaration_distinction(
    tmp_path: Path, declared: str, layout_type: type[object]
) -> None:
    config = StatConfig(
        "out",
        "vector",
        source_name="d",
        params={"source_type": declared, "entries": ["0-1", "samples"]},
    )
    result, _ = parse(tmp_path, "d::samples 1\nd::0-1 2\n", [config])
    assert type(result.variables[0].layout) is layout_type
    assert [cell.value for cell in result.variables[0].cells] == [2, 1]


@pytest.mark.parametrize(
    "label,accepted", [("0", True), ("0-1", True), ("0.25", False), ("0.25-1.75", False)]
)
def test_explicit_generic_histogram_preserves_only_supported_integer_labels(
    tmp_path: Path, label: str, accepted: bool
) -> None:
    config = StatConfig("out", "histogram", source_name="d", params={"source_type": "distribution"})
    if accepted:
        result, _ = parse(tmp_path, f"d::samples 1\nd::{label} 2\n", [config])
        assert result.variables[0].layout is None
        assert any(cell.value == 2 for cell in result.variables[0].cells)
    else:
        with pytest.raises(ParseDataValueError, match="fractional native"):
            parse(tmp_path, f"d::samples 1\nd::{label} 2\n", [config])


def test_positive_native_width_may_round_to_zero_at_explicit_printer_precision(
    tmp_path: Path,
) -> None:
    text = "d::bucket_size 0\nd::min_bucket 0\nd::max_bucket 0\nd::samples 1\nd | 2 | 3\n"
    result, _ = parse(tmp_path, text, [request(maximum=0, bucket_size=0.5, policy="nozero")])
    assert [cell.value for cell in result.variables[0].cells] == [0, 2, 3, 0]
    assert isinstance(result.variables[0].layout, NativeDistributionLayout)
    assert result.variables[0].layout.geometry.bucket_size == 0.5


@pytest.mark.parametrize(
    "width,low,high,cells,accepted",
    [
        ("1", "0", "1", "2 | 3", True),
        ("1", "0", "1", "2 | 3 | 4", False),
        ("0.500000", "0.250000", "1.250000", "1 | 2 | 3 | 4", False),
    ],
)
def test_explicit_distribution_to_generic_histogram_oneline_tail_and_count_contract(
    tmp_path: Path, width: str, low: str, high: str, cells: str, accepted: bool
) -> None:
    config = StatConfig("out", "histogram", source_name="d", params={"source_type": "distribution"})
    text = (
        f"d::bucket_size {width}\nd::min_bucket {low}\nd::max_bucket {high}\n"
        f"d::samples 5\nd::underflows 5\nd | {cells}\nd::overflows 6\n"
    )
    if accepted:
        result, _ = parse(tmp_path, text, [config])
        values = {cell.column: cast(float, cell.value) for cell in result.variables[0].cells}
        assert values["out..0-0"] == 2 and values["out..1-1"] == 3
        assert values["out..underflows"] == 5 and values["out..overflows"] == 6
        assert result.variables[0].layout is None
    else:
        with pytest.raises(ParseDataValueError, match="cell count|native Distribution grid"):
            parse(tmp_path, text, [config])
