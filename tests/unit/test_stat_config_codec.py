"""One runnable parser configuration contract across editor and wire boundaries."""

from copy import deepcopy
import math

import pytest

from src.core.common.stat_config_codec import StatConfigCodec
from src.core.models.parsing_models import StatConfig
from src.parsing.gem5.types.type_mapper import TypeMapper
from src.parsing.gem5.impl.source_bindings import resolve_sources


def test_draft_wire_and_typed_value_share_one_owned_configuration() -> None:
    draft = {
        "name": "renamed",
        "source_name": "cpu.ipc",
        "type": "vector",
        "_id": "editor",
        "repeat": 2,
        "params": {"entries": ["0"], "statistics": ["mean"], "source_type": "vector"},
    }
    before = deepcopy(draft)
    configured = StatConfigCodec.from_draft(draft)
    payload = StatConfigCodec.to_payload(configured)
    assert "_id" not in payload
    assert set(payload) == {
        "name",
        "type",
        "source_name",
        "repeat",
        "params",
        "statistics_only",
        "is_regex",
        "keep_indices",
    }
    assert configured.name == "renamed"
    assert configured.source_name == "cpu.ipc"
    assert configured.params["entries"] == ["0"]
    assert configured.params["statistics"] == ["mean"]
    assert StatConfigCodec.from_payload(payload) == configured
    payload["params"]["entries"].append("changed")
    assert configured.params["entries"] == ["0"]
    assert draft == before
    assert TypeMapper.create_stat(resolve_sources([configured], None).accumulators[0]).entries == [
        "0",
        "mean",
    ]


@pytest.mark.parametrize("repeat", [True, 0, -1, 1.5, "2", None])
def test_repeat_cannot_be_coerced_or_defaulted(repeat) -> None:
    with pytest.raises((TypeError, ValueError), match="repeat"):
        StatConfigCodec.validate(
            StatConfig(name="x", type="scalar", repeat=repeat, params={"source_type": "scalar"})
        )


@pytest.mark.parametrize(
    "field",
    ["alias", "vectorEntries", "statisticsOnly", "keepIndices", "onEmpty", "patternSelection"],
)
def test_retired_draft_field_is_rejected(field: str) -> None:
    with pytest.raises(ValueError, match="Unsupported parser draft fields"):
        StatConfigCodec.from_draft({"name": "x", "type": "scalar", field: "old"})


def test_runnable_entry_point_rejects_dictionary_and_duck_shapes() -> None:
    class PretendConfig:
        name = "x"
        type = "scalar"
        repeat = 1
        statistics_only = False
        params = {}

    for value in [{"name": "x", "type": "scalar"}, PretendConfig()]:
        with pytest.raises(TypeError, match="StatConfig"):
            StatConfigCodec.validate(value)


def test_histogram_statistics_only_never_discovers_raw_buckets() -> None:
    config = StatConfig(
        name="hist",
        type="histogram",
        statistics_only=True,
        params={"statistics": ["mean", "stdev"], "source_type": "histogram"},
    )
    stat = TypeMapper.create_stat(resolve_sources([config], None).accumulators[0])
    stat.add_observation({"0-3": 4.0, "mean": 2.0})
    assert stat.entries == ["mean", "stdev"]
    stat.balance_content()
    stat.reduce_duplicates()
    assert set(stat.reduced_content) == {"mean", "stdev"}
    assert stat.reduced_content["mean"] == 2
    assert math.isnan(stat.reduced_content["stdev"])


def test_configuration_uses_only_current_constructor_spelling() -> None:
    from src.parsing.gem5.types.configuration import Configuration

    assert Configuration(on_empty="missing").on_empty == "missing"
    with pytest.raises(TypeError, match="unexpected keyword argument.*onEmpty"):
        Configuration(onEmpty="retired")


@pytest.mark.parametrize(
    "draft",
    [
        {},
        {"type": "scalar"},
        {"name": "", "type": "scalar"},
        {"name": "x", "type": "vector", "params": {"entries": []}},
        {"name": "x", "type": "distribution"},
    ],
)
def test_incomplete_editor_state_is_an_explicit_nonexecutable_snapshot(draft) -> None:
    from src.core.common.stat_config_codec import StatConfigDraftIncomplete

    snapshot = StatConfigCodec.to_snapshot({**draft, "_id": "browser-only"})
    assert snapshot == {"state": "draft", "fields": draft}
    restored = StatConfigCodec.from_snapshot(snapshot)
    assert restored == {**draft, "_id": ""}
    with pytest.raises(StatConfigDraftIncomplete):
        StatConfigCodec.from_draft(restored)


def test_complete_snapshot_uses_the_exact_runnable_codec_and_new_ui_identity() -> None:
    snapshot = StatConfigCodec.to_snapshot(
        {"name": "x", "type": "scalar", "params": {"source_type": "scalar"}, "_id": "private"}
    )
    assert snapshot["state"] == "runnable"
    assert snapshot["config"] == StatConfigCodec.to_payload(
        StatConfig(name="x", type="scalar", params={"source_type": "scalar"})
    )
    assert StatConfigCodec.from_snapshot(snapshot)["_id"] == ""


@pytest.mark.parametrize(
    "draft",
    [
        {"name": "x", "type": "scalar", "statistics_only": "yes"},
        {"name": "x", "type": "scalar", "repeat": "2"},
        {"name": "x", "type": "scalar", "alias": "retired"},
    ],
)
def test_unsupported_editor_shape_is_not_saved_as_a_draft_fallback(draft) -> None:
    with pytest.raises((TypeError, ValueError)):
        StatConfigCodec.to_snapshot(draft)


def test_portfolio_saves_and_restores_an_unfinished_editor_without_running_it() -> None:
    import json
    from src.core.services.data_services.portfolio_service import PortfolioService
    from src.core.state.repository_state_manager import RepositoryStateManager
    from src.core.models.portfolio_contract import (
        CURRENT_PORTFOLIO_SCHEMA_VERSION,
        CURRENT_PORTFOLIO_VERSION,
        validate_portfolio_schema,
    )

    original = RepositoryStateManager()
    original.set_parse_variables([{"name": "", "type": "vector", "params": {"entries": []}}])
    payload = json.loads(
        PortfolioService(original).serialize_workspace(
            None, [], {}, 0, parse_variables=original.get_parse_variables()
        )
    )
    assert payload["schema_version"] == CURRENT_PORTFOLIO_SCHEMA_VERSION
    assert payload["version"] == CURRENT_PORTFOLIO_VERSION
    validate_portfolio_schema(payload)
    restored = RepositoryStateManager()
    restored.restore_session(payload)
    variables = restored.get_parse_variables()
    assert variables[0]["name"] == ""
    assert variables[0]["params"]["entries"] == []
    assert variables[0]["_id"]
    assert variables[0]["_id"] != original.get_parse_variables()[0]["_id"]


def test_recipe_templates_use_the_same_runnable_decoder_after_materialization() -> None:
    from src.core.models.recipe_models import AnalysisRecipe, RecipeSource, RecipeParameter
    from src.core.services.data_services.analysis_recipe_service import AnalysisRecipeService

    payload = StatConfigCodec.to_payload(
        StatConfig(name="ipc", type="scalar", params={"source_type": "scalar"})
    )
    payload["repeat"] = "{{repetitions}}"
    recipe = AnalysisRecipe(
        name="Typed parser operand",
        source=RecipeSource(kind="parser", path="/simulations", variables=(payload,)),
        parameters=(RecipeParameter("repetitions", "integer", default=3),),
    )
    exported = AnalysisRecipeService.dumps(recipe)
    restored = AnalysisRecipeService.loads(exported)
    resolved = AnalysisRecipeService.materialize(restored, {})
    configured = StatConfigCodec.from_payload(resolved.source.variables[0])
    assert configured.repeat == 3
    assert payload["repeat"] == "{{repetitions}}"
    assert TypeMapper.create_stat(resolve_sources([configured], None).accumulators[0]).repeat == 3


def test_summary_roles_follow_the_selected_simulator_metadata() -> None:
    from src.core.services.data_services.variable_service import VariableService

    entries = ["mean", "custom_summary", "cpu0"]
    custom_stats = frozenset({"custom_summary"})
    assert VariableService.filter_internal_stats(entries, custom_stats) == ["cpu0", "mean"]
    snapshot = [
        {
            "name": "v",
            "type": "vector",
            "entries": entries,
            "source_type": "vector",
            "instances": [{"source_name": "v", "indices": []}],
        }
    ]
    assert VariableService.aggregate_discovered_entries(snapshot, "v", custom_stats) == [
        "cpu0",
        "mean",
    ]
    with pytest.raises(TypeError, match="internal_stats"):
        VariableService.filter_internal_stats(entries)


def test_custom_backend_options_have_one_nested_owned_draft_representation() -> None:
    configured = StatConfig(
        name="output",
        type="custom_stat",
        params={"scale": 2, "name": "backend operand", "source_type": "custom_stat"},
    )
    draft = StatConfigCodec.to_draft(configured, "ui-only")
    assert draft["params"] == {"scale": 2, "name": "backend operand", "source_type": "custom_stat"}
    assert draft["name"] == "output"
    assert StatConfigCodec.from_draft(draft) == configured
    snapshot = StatConfigCodec.to_snapshot(draft)
    assert StatConfigCodec.from_draft(StatConfigCodec.from_snapshot(snapshot)) == configured
    draft["params"]["scale"] = 9
    assert configured.params["scale"] == 2


@pytest.mark.parametrize(
    "field", ["entries", "statistics", "source_type", "selected_sources", "on_empty"]
)
def test_flat_current_option_spellings_are_not_an_alternate_draft_route(field: str) -> None:
    with pytest.raises(ValueError, match="Unsupported parser draft fields"):
        StatConfigCodec.from_draft({"name": "x", "type": "scalar", field: []})


def test_scanner_projection_keeps_metadata_roles_and_does_not_require_runnable_bounds() -> None:
    vector = StatConfigCodec.from_scanned(
        {
            "name": "v",
            "type": "vector",
            "entries": ["cpu0", "mean"],
            "source_type": "vector",
            "instances": [{"source_name": "v", "indices": []}],
        },
        frozenset({"mean"}),
    )
    assert vector["params"] == {
        "entries": ["cpu0"],
        "statistics": ["mean"],
        "source_type": "vector",
    }
    assert StatConfigCodec.from_draft(vector).params == vector["params"]
    distribution = StatConfigCodec.from_scanned(
        {
            "name": "d",
            "type": "distribution",
            "entries": [],
            "source_type": "distribution",
            "instances": [{"source_name": "d", "indices": []}],
        },
        frozenset(),
    )
    assert StatConfigCodec.to_snapshot(distribution)["state"] == "draft"


@pytest.mark.parametrize("kind", ["vector", "distribution", "histogram"])
def test_statistics_only_without_selected_summaries_is_a_nonexecutable_editor_draft(
    kind: str,
) -> None:
    from src.core.common.stat_config_codec import StatConfigDraftIncomplete

    draft = {
        "name": "v",
        "type": kind,
        "statistics_only": True,
        "params": {"statistics": [], "source_type": kind},
    }
    assert StatConfigCodec.to_snapshot(draft)["state"] == "draft"
    with pytest.raises(StatConfigDraftIncomplete, match="Select at least one summary"):
        StatConfigCodec.from_draft(draft)
    with pytest.raises(ValueError, match="requires at least one selected summary"):
        StatConfigCodec.validate(
            StatConfig(name="v", type=kind, statistics_only=True, params={"source_type": kind})
        )


@pytest.mark.parametrize(
    "kind,params,statistics_only",
    [
        ("scalar", {}, False),
        ("vector", {"entries": ["0"], "statistics": ["mean"]}, False),
        ("distribution", {"minimum": 0, "maximum": 8, "statistics": ["mean"]}, False),
        ("histogram", {"bins": 4, "max_range": 16, "statistics": ["mean"]}, False),
        ("histogram", {"statistics": ["mean"]}, True),
        ("configuration", {"on_empty": "unknown"}, False),
    ],
)
def test_each_builtin_type_roundtrips_one_nested_current_contract(
    kind, params, statistics_only
) -> None:
    configured = StatConfig(
        name="renamed",
        source_name="source",
        type=kind,
        params={**params, "source_type": kind},
        statistics_only=statistics_only,
        repeat=2,
    )
    normalized = StatConfigCodec.validate(configured)
    draft = StatConfigCodec.to_draft(configured, "browser")
    assert set(draft) == {
        "name",
        "type",
        "source_name",
        "repeat",
        "params",
        "statistics_only",
        "is_regex",
        "keep_indices",
        "_id",
    }
    assert StatConfigCodec.from_draft(draft) == normalized
    assert StatConfigCodec.from_payload(StatConfigCodec.to_payload(configured)) == normalized
    assert draft["params"] is not configured.params
