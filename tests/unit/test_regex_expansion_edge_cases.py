"""Numeric source matching exercises the production resolver, never a copied expansion."""

import pytest

from src.core.models.parsing_models import ScannedVariable, SourceInstance, StatConfig
from src.parsing.gem5.impl.source_bindings import resolve_sources


def _literal(name):
    return ScannedVariable(
        name, "scalar", [], source_type="scalar", instances=(SourceInstance(name, ()),)
    )


def test_literal_dots_do_not_match_other_hierarchy_separators():
    config = StatConfig("system.cpu.ipc", "scalar", params={"source_type": "scalar"})
    plan = resolve_sources([config], [_literal("systemXcpuXipc")])
    assert set(plan.routes) == {"system.cpu.ipc"}


@pytest.mark.parametrize("pattern", [r"system.cpu\d+.ipc", r"system\.cpu\d+\.ipc"])
def test_numeric_patterns_preserve_literal_dots_and_leading_zero_coordinates(pattern):
    config = StatConfig(pattern, "vector", params={"source_type": "scalar"})
    plan = resolve_sources([config], [_literal("system.cpu012.ipc"), _literal("systemXcpu1Xipc")])
    assert set(plan.routes) == {"system.cpu012.ipc"}
    assert plan.accumulators[0].entries == ("012",)


@pytest.mark.parametrize("scanned", [None, [], [_literal("simTicks")]])
def test_missing_pattern_instances_reject_before_worker_allocation(scanned):
    with pytest.raises(ValueError, match="source records|no scanned instances"):
        resolve_sources(
            [StatConfig(r"cpu\d+.ipc", "scalar", params={"source_type": "scalar"})], scanned
        )


@pytest.mark.parametrize("pattern", [r"cpu[", r"cpu(\d+", r"cpu.*", ""])
def test_invalid_and_non_numeric_patterns_are_rejected(pattern):
    with pytest.raises(ValueError):
        resolve_sources(
            [StatConfig(pattern, "scalar", is_regex=True, params={"source_type": "scalar"})],
            [_literal("cpu0")],
        )


def test_overlapping_outputs_have_independent_specs_and_shared_exact_source_routes():
    values = [_literal("cpu0.ipc"), _literal("cpu1.ipc")]
    requests = [
        StatConfig(
            "all",
            "scalar",
            source_name=r"cpu\d+.ipc",
            is_regex=True,
            params={"source_type": "scalar"},
        ),
        StatConfig(
            "selected",
            "scalar",
            source_name=r"cpu\d+.ipc",
            is_regex=True,
            params={"source_type": "scalar", "selected_sources": ["cpu1.ipc"]},
        ),
    ]
    plan = resolve_sources(requests, values)
    assert [spec.repeat for spec in plan.accumulators] == [2, 1]
    assert [target.output_name for target in plan.routes["cpu1.ipc"].targets] == ["all", "selected"]
    assert requests[0].params == {"source_type": "scalar"}
