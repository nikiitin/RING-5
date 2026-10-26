"""Current source identity, execution planning and resource-bound contracts."""

from src.core.models.source_evidence import ResolvedSourceKind


from src.core.models.portfolio_contract import (
    CURRENT_PORTFOLIO_SCHEMA_VERSION,
    CURRENT_PORTFOLIO_VERSION,
)

from dataclasses import asdict
from unittest.mock import patch

import pytest

from src.core.common.stat_config_codec import StatConfigCodec, StatConfigDraftIncomplete
from src.core.models.parsing_models import ScannedVariable, SourceInstance, StatConfig
from src.parsing.gem5.impl import source_bindings as bindings
from src.parsing.gem5.impl.scanning.pattern_aggregator import PatternAggregator
from src.parsing.gem5.impl.strategies.simple import SimpleStatsStrategy
from src.parsing.gem5.types.type_mapper import TypeMapper


def _scalar_pattern() -> ScannedVariable:
    return ScannedVariable(
        r"cpu\d+.ipc",
        "vector",
        source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
        instances=(SourceInstance("cpu0.ipc", ("0",)), SourceInstance("cpu1.ipc", ("1",))),
    )


def _request(**updates) -> StatConfig:
    return StatConfig(
        **{
            "name": "IPC",
            "type": "vector",
            "source_name": r"cpu\d+.ipc",
            "repeat": 3,
            "params": {"source_type": "scalar"},
            **updates,
        }
    )


def test_source_record_roundtrip_is_explicit_owned_and_preserves_leading_zero_indices() -> None:
    payload = {"source_name": "cpu012.cache3.ipc", "indices": ["012", "3"]}
    source = SourceInstance.from_dict(payload)
    payload["indices"].append("external")
    assert source.indices == ("012", "3")
    assert source.to_dict() == {"source_name": "cpu012.cache3.ipc", "indices": ["012", "3"]}


@pytest.mark.parametrize("missing", ["source_evidence", "instances"])
def test_scanned_metadata_cannot_omit_source_identity(missing: str) -> None:
    payload = _scalar_pattern().to_dict()
    payload.pop(missing)
    with pytest.raises(ValueError, match="requires exactly the current fields"):
        ScannedVariable.from_dict(payload)


def test_retired_source_and_selection_representations_are_rejected() -> None:
    metadata = _scalar_pattern().to_dict()
    metadata["pattern_indices"] = ["0", "1"]
    with pytest.raises(ValueError, match="requires exactly the current fields"):
        ScannedVariable.from_dict(metadata)
    with pytest.raises(ValueError, match="Unsupported vector statistic options"):
        StatConfigCodec.validate(_request(params={"source_type": "scalar", "parsed_ids": ["0"]}))
    with pytest.raises(ValueError, match="not a scanned pattern instance"):
        bindings.resolve_sources(
            [_request(params={"source_type": "scalar", "selected_sources": ["0"]})],
            [_scalar_pattern()],
        )


def test_raw_kind_is_required_and_cannot_be_inferred_from_output_representation() -> None:
    config = StatConfig("ipc", "scalar")
    with pytest.raises(ValueError, match="source_type"):
        StatConfigCodec.from_payload(asdict(config))
    draft = {"name": "ipc", "type": "scalar", "params": {}}
    assert StatConfigCodec.to_snapshot(draft)["state"] == "draft"
    with pytest.raises(StatConfigDraftIncomplete, match="raw source type"):
        StatConfigCodec.from_draft(draft)


def test_scalar_pattern_entry_schema_has_no_second_caller_selection_route() -> None:
    with pytest.raises(ValueError, match="derive only"):
        StatConfigCodec.validate(_request(params={"source_type": "scalar", "entries": ["0"]}))
    plan = bindings.resolve_sources([_request()], [_scalar_pattern()])
    spec = plan.accumulators[0]
    assert spec.output_name == "IPC"
    assert spec.output_type == "vector"
    assert spec.repeat == 3
    assert spec.entries == ("0", "1")
    assert "entries" not in spec.config.params
    assert list(plan.routes) == ["cpu0.ipc", "cpu1.ipc"]
    assert [route.targets[0].entry_name for route in plan.routes.values()] == ["0", "1"]
    assert TypeMapper.create_stat(spec).entries == ["0", "1"]


def test_concrete_selection_and_keep_indices_are_independent_of_output_alias() -> None:
    request = _request(params={"source_type": "scalar", "selected_sources": ["cpu1.ipc"]})
    plan = bindings.resolve_sources([request], [_scalar_pattern()])
    assert list(plan.routes) == ["cpu1.ipc"]
    assert plan.accumulators[0].entries == ("1",)
    kept = bindings.resolve_sources([_request(keep_indices=True)], [_scalar_pattern()])
    assert [(s.output_name, s.output_type, s.repeat) for s in kept.accumulators] == [
        ("cpu0.ipc", "scalar", 3),
        ("cpu1.ipc", "scalar", 3),
    ]
    assert all(spec.config.name == "IPC" for spec in kept.accumulators)


def test_genuine_vector_patterns_multiply_spatial_and_temporal_lifecycles() -> None:
    metadata = ScannedVariable(
        r"cpu\d+.v",
        "vector",
        ["a"],
        source_evidence=ResolvedSourceKind("vector", "backend_metadata"),
        instances=(SourceInstance("cpu0.v", ("0",)), SourceInstance("cpu1.v", ("1",))),
    )
    request = StatConfig(
        "V",
        "vector",
        repeat=3,
        source_name=r"cpu\d+.v",
        params={"source_type": "vector", "entries": ["a"]},
    )
    spec = bindings.resolve_sources([request], [metadata]).accumulators[0]
    assert spec.repeat == 6
    assert spec.entries == ("a",)
    assert spec.config.repeat == 3


def test_source_aliases_have_separate_accumulators_without_identity_routing() -> None:
    configs = [
        StatConfig("source", "scalar", params={"source_type": "scalar"}),
        StatConfig("renamed", "scalar", source_name="source", params={"source_type": "scalar"}),
    ]
    plan = bindings.resolve_sources(configs, None)
    assert [target.output_name for target in plan.routes["source"].targets] == ["source", "renamed"]
    accumulators = SimpleStatsStrategy()._map_variables(plan.accumulators)
    assert set(accumulators) == {"source", "renamed"}
    assert accumulators["source"] is not accumulators["renamed"]
    accumulators["source"].add_observation(2.0)
    assert accumulators["renamed"].content == []
    with pytest.raises(TypeError, match="AccumulatorSpec"):
        TypeMapper.create_stat(configs[0])


def test_duplicate_outputs_conflicting_kinds_and_forged_coordinates_fail() -> None:
    with pytest.raises(ValueError, match="Duplicate parser output"):
        bindings.resolve_sources([_request(), _request()], [_scalar_pattern()])
    with pytest.raises(ValueError, match="contradicts"):
        bindings.resolve_sources(
            [_request(params={"source_type": "vector", "entries": ["a"]})], [_scalar_pattern()]
        )
    forged = ScannedVariable(
        r"cpu\d+.ipc",
        "vector",
        source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
        instances=(SourceInstance("cpu0.ipc", ("9",)),),
    )
    with pytest.raises(ValueError, match="coordinates"):
        bindings.resolve_sources([_request()], [forged])


def test_heterogeneous_numeric_families_remain_literal_without_guessing_source_kind() -> None:
    values = [
        ScannedVariable(
            "l0_cntrl0.delay",
            "distribution",
            source_evidence=ResolvedSourceKind("distribution", "backend_metadata"),
            instances=(SourceInstance("l0_cntrl0.delay", ()),),
        ),
        ScannedVariable(
            "l1_cntrl0.delay",
            "histogram",
            source_evidence=ResolvedSourceKind("histogram", "backend_metadata"),
            instances=(SourceInstance("l1_cntrl0.delay", ()),),
        ),
    ]
    assert PatternAggregator.aggregate_patterns(values) == values


def test_empty_selection_is_incomplete_and_never_means_all_sources() -> None:
    draft = {
        "name": "IPC",
        "source_name": r"cpu\d+.ipc",
        "type": "vector",
        "params": {"source_type": "scalar", "selected_sources": []},
    }
    assert StatConfigCodec.to_snapshot(draft)["state"] == "draft"
    with pytest.raises(ValueError, match="concrete non-empty"):
        bindings.resolve_sources([_request(params=draft["params"])], [_scalar_pattern()])


@pytest.mark.parametrize("limit", ["MAX_REGEX_CANDIDATES", "MAX_REGEX_MATCH_ATTEMPTS"])
def test_pattern_resolution_preserves_candidate_and_attempt_bounds(limit: str) -> None:
    with patch.object(bindings, limit, 1):
        with pytest.raises(ValueError, match="candidate"):
            bindings.resolve_sources([_request()], [_scalar_pattern()])


def test_resolution_preserves_deadline_and_selected_source_cap(monkeypatch) -> None:
    with patch.object(bindings.time, "monotonic", side_effect=[0.0, 10.0]):
        with pytest.raises(ValueError, match="deadline"):
            bindings.resolve_sources([_request()], [_scalar_pattern()])
    monkeypatch.setenv("RING5_MAX_VAR_REPEAT", "1")
    with pytest.raises(RuntimeError, match="cap of 1"):
        bindings.resolve_sources([_request()], [_scalar_pattern()])


def test_routes_are_immutable_and_exact_filter_names_cannot_be_regexes() -> None:
    plan = bindings.resolve_sources([_request()], [_scalar_pattern()])
    with pytest.raises(TypeError):
        plan.routes["other"] = plan.routes["cpu0.ipc"]
    assert bindings.literal_source_filter("cpu0.ipc") == r"cpu0\.ipc"
    with pytest.raises(ValueError, match="exact statistic identifier"):
        bindings.literal_source_filter(r"cpu\d+.ipc")


@pytest.mark.parametrize("entries", [["0"], ["-1"], ["0", "0-0"]])
def test_histogram_vector_requests_reject_alternate_point_labels(entries):
    with pytest.raises(ValueError, match="inclusive range labels"):
        bindings.resolve_sources(
            [StatConfig("h", "vector", params={"source_type": "histogram", "entries": entries})], []
        )


def test_keeping_indices_on_literal_sources_is_not_a_runnable_codec_value():
    with pytest.raises(ValueError, match="requires a numeric source pattern"):
        StatConfigCodec.validate(
            StatConfig("ipc", "scalar", keep_indices=True, params={"source_type": "scalar"})
        )
    with pytest.raises(StatConfigDraftIncomplete, match="numeric pattern"):
        StatConfigCodec.from_draft(
            {
                "name": "ipc",
                "type": "scalar",
                "keep_indices": True,
                "params": {"source_type": "scalar"},
            }
        )


@pytest.mark.parametrize("field", ["minimum", "maximum"])
@pytest.mark.parametrize("value", [True, "3", float("nan"), float("inf"), -float("inf"), []])
def test_retired_scan_bounds_reject_wire_and_direct_values(field, value):
    from src.core.models.parsing_models import ScannedVariable

    literal = ScannedVariable(
        "d",
        "distribution",
        ["0"],
        source_evidence=ResolvedSourceKind("distribution", "backend_metadata"),
        instances=(SourceInstance("d", ()),),
    ).to_dict()
    wire = {**literal, field: value}
    with pytest.raises((TypeError, ValueError)):
        ScannedVariable.from_dict(wire)
    with pytest.raises((TypeError, ValueError)):
        ScannedVariable.from_dict(wire)
    with pytest.raises((TypeError, ValueError)):
        ScannedVariable(
            "d",
            "distribution",
            ["0"],
            source_evidence=ResolvedSourceKind("distribution", "backend_metadata"),
            instances=(SourceInstance("d", ()),),
            **{field: value},
        )


def test_scan_geometry_fields_and_count_shadow_are_rejected():
    model = ScannedVariable(
        "d",
        "distribution",
        ["0"],
        source_evidence=ResolvedSourceKind("distribution", "backend_metadata"),
        instances=(SourceInstance("d", ()),),
    )
    wire = model.to_dict()
    assert "minimum" not in wire and "maximum" not in wire
    for extra in (
        {"minimum": None},
        {"maximum": None},
        {"count": 2},
        {"minimum": 2, "maximum": 1},
        {"minimum": 0, "maximum": 1.5},
    ):
        with pytest.raises(ValueError, match="requires exactly the current fields"):
            ScannedVariable.from_dict({**wire, **extra})
    assert ScannedVariable.from_dict(wire) == model


def test_retired_scan_geometry_rejection_preserves_parser_metadata():
    from src.core.state.repositories.parser_state_repository import ParserStateRepository

    repository = ParserStateRepository()
    original = ScannedVariable(
        "ipc",
        "scalar",
        [],
        source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
        instances=(SourceInstance("ipc", ()),),
    ).to_dict()
    repository.set_scanned_variables([original])
    invalid = {**original, "minimum": "invalid"}
    with pytest.raises(ValueError, match="requires exactly the current fields"):
        repository.set_scanned_variables([original, invalid])
    assert repository.get_scanned_variables() == [original]


@pytest.mark.parametrize("value", [True, "invalid", float("nan"), float("inf"), None])
def test_portfolio_and_recipe_admission_reject_retired_scan_geometry_fields(value):
    from src.core.models.portfolio_contract import validate_portfolio_schema
    from src.core.models.recipe_models import AnalysisRecipe, RecipeSource
    from src.core.services.data_services.analysis_recipe_service import AnalysisRecipeService

    record = ScannedVariable(
        "ipc",
        "scalar",
        [],
        source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
        instances=(SourceInstance("ipc", ()),),
    ).to_dict()
    record["minimum"] = value
    portfolio = {
        "schema_version": CURRENT_PORTFOLIO_SCHEMA_VERSION,
        "version": CURRENT_PORTFOLIO_VERSION,
        "parser_strategy": "simple",
        "simulator": "gem5",
        "environment_metadata": {},
        "integrity_manifest": {},
        "parse_variables": [],
        "scanned_variables": [record],
    }
    with pytest.raises((TypeError, ValueError)):
        validate_portfolio_schema(portfolio)
    configured = StatConfigCodec.to_payload(
        StatConfig("ipc", "scalar", params={"source_type": "scalar"})
    )
    recipe = AnalysisRecipe(
        name="Bad range",
        source=RecipeSource(
            kind="parser", path="simulations", variables=(configured,), scanned_variables=(record,)
        ),
    )
    with pytest.raises((TypeError, ValueError)):
        AnalysisRecipeService.dumps(recipe)


def test_manual_pattern_projection_uses_concrete_records_without_guessing_kind_or_mutating_inputs():
    from copy import deepcopy
    from src.core.common.source_matching import matching_source_instances

    values = [
        ScannedVariable(
            name,
            kind,
            [],
            source_evidence=ResolvedSourceKind(kind, "backend_metadata"),
            instances=(SourceInstance(name, ()),),
        ).to_dict()
        for name, kind in [
            ("l00_cpu1.v", "vector"),
            ("l1_cpu00.v", "histogram"),
            ("other", "scalar"),
        ]
    ]
    before = deepcopy(values)
    assert matching_source_instances(r"l\d+_cpu\d+.v", values) == [
        {"source_name": "l00_cpu1.v", "indices": ["00", "1"]},
        {"source_name": "l1_cpu00.v", "indices": ["1", "00"]},
    ]
    assert values == before


@pytest.mark.parametrize("bound", ["MAX_REGEX_CANDIDATES", "MAX_REGEX_MATCH_ATTEMPTS"])
def test_manual_pattern_projection_enforces_source_budgets(monkeypatch, bound):
    from src.core.common import source_matching

    monkeypatch.setattr(source_matching, bound, 1)
    values = [_scalar_pattern().to_dict()]
    with pytest.raises(ValueError, match="candidate"):
        source_matching.matching_source_instances(r"cpu\d+.ipc", values)


def test_manual_pattern_projection_propagates_matching_timeout_and_rejects_duplicate_metadata(
    monkeypatch,
):
    from src.core.common import source_matching
    from src.core.common.safe_regex import SafeRegexError

    values = [_scalar_pattern().to_dict()]
    with pytest.raises(ValueError, match="more than once"):
        source_matching.matching_source_instances(r"cpu\d+.ipc", values + values)
    monkeypatch.setattr(source_matching, "MAX_REGEX_EXPANSION_SECONDS", -1)
    with pytest.raises(SafeRegexError, match="deadline"):
        source_matching.matching_source_instances(r"cpu\d+.ipc", values)


@pytest.mark.parametrize("is_pattern", [True, False])
def test_regex_candidate_cap_applies_before_private_record_allocation(monkeypatch, is_pattern):
    metadata = ScannedVariable(
        r"cpu\d+.ipc",
        "vector",
        [],
        source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
        instances=tuple(SourceInstance(f"cpu{index}.ipc", (str(index),)) for index in range(10)),
    )
    monkeypatch.setattr(bindings, "MAX_REGEX_CANDIDATES", 2)
    request = (
        _request()
        if is_pattern
        else StatConfig("cpu0.ipc", "scalar", params={"source_type": "scalar"})
    )
    with patch.object(bindings, "_ScannedSource", wraps=bindings._ScannedSource) as allocate:
        if is_pattern:
            with pytest.raises(ValueError, match="candidate limit"):
                bindings.resolve_sources([request], [metadata])
            assert allocate.call_count == 2
        else:
            assert set(bindings.resolve_sources([request], [metadata]).routes) == {"cpu0.ipc"}
            assert allocate.call_count == 10
