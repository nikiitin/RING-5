"""Explicit source requests remain immutable independently of editor and frame state."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace

import pandas as pd
import pytest

from src.core.common.import_options_codec import ImportOptionsCodec
from src.core.common.source_context_codec import SourceContextCodec
from src.core.models.import_models import ImportColumnCorrection, ImportOptions
from src.core.models.parsing_models import StatConfig
from src.core.models.source_context_models import (
    CsvSourceContext,
    InferredCsvPolicy,
    ReviewedCsvPolicy,
)
from src.core.state.repositories.data_repository import DataRepository


def _parser():
    return SourceContextCodec.parser(
        stats_path="original",
        stats_pattern="stats.txt",
        strategy_type="simple",
        variables=[
            StatConfig(
                name="label",
                type="configuration",
                params={"source_type": "configuration", "on_empty": "NA"},
            )
        ],
        scanned_variables=[],
        simulator="gem5",
        scan_limit=0,
        strict=False,
    )


def test_parser_request_owns_exact_variables_and_discovery_policy() -> None:
    source = _parser()
    assert SourceContextCodec.decode(SourceContextCodec.encode(source)) == source
    configs = SourceContextCodec.variables(source)
    configs[0].params["on_empty"] = "changed"
    assert SourceContextCodec.variables(source)[0].params["on_empty"] == "NA"
    assert source.scan_limit == 0
    assert source.strict is False
    assert replace(source, scan_limit=None).scan_limit is None
    assert replace(source, simulator=None).simulator is None
    with pytest.raises(FrozenInstanceError):
        source.stats_path = "changed"


def test_reviewed_policy_exact_codec_and_defensive_wire_projection() -> None:
    options = ImportOptions(
        encoding="utf-8",
        delimiter=";",
        header_row=2,
        trim_whitespace=False,
        null_values=("MISSING",),
        column_types=(ImportColumnCorrection("label", "text"),),
        preview_rows=7,
    )
    source = CsvSourceContext("input.csv", ReviewedCsvPolicy(options))
    encoded = SourceContextCodec.encode(source)
    assert SourceContextCodec.decode(encoded) == source
    payload = SourceContextCodec.to_payload(source)
    payload["policy"]["options"]["null_values"].append("NA")
    assert options.null_values == ("MISSING",)
    assert SourceContextCodec.to_payload(source)["policy"]["rejected_rows"] == "exclude"
    assert ImportOptionsCodec.from_payload(ImportOptionsCodec.to_payload(options)) == options


@pytest.mark.parametrize(
    "field,value",
    [
        ("header_row", 1.5),
        ("header_row", True),
        ("preview_rows", 1.5),
        ("trim_whitespace", 1),
        ("null_values", ["NA"]),
        ("column_types", [ImportColumnCorrection("v", "text")]),
        ("column_types", ({"column": "v", "import_as": "text"},)),
    ],
)
def test_import_policy_rejects_mutable_or_wrong_typed_fields(field, value) -> None:
    with pytest.raises((TypeError, ValueError)):
        ImportOptions(**{field: value})


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(extra=True),
        lambda p: p.pop("options"),
        lambda p: p.update(rejected_rows="fill"),
        lambda p: p["options"].update(extra=True),
        lambda p: p["options"].update(header_row=True),
    ],
)
def test_reviewed_policy_rejects_unknown_or_missing_wire_fields(mutate) -> None:
    payload = SourceContextCodec.csv_policy_payload(ReviewedCsvPolicy(ImportOptions()))
    mutate(payload)
    with pytest.raises((TypeError, ValueError)):
        SourceContextCodec.csv_policy_from_payload(payload)


def test_inferred_policy_retains_exact_configuration_column_order() -> None:
    source = CsvSourceContext("input.csv", InferredCsvPolicy(("z", "a")))
    assert SourceContextCodec.decode(SourceContextCodec.encode(source)) == source
    with pytest.raises(ValueError):
        InferredCsvPolicy(("z", "z"))
    with pytest.raises(TypeError):
        InferredCsvPolicy(["z"])


def test_origin_roundtrip_owns_steps_and_keeps_partial_distinct() -> None:
    steps = [{"type": "columnSelector", "columns": ["label"]}]
    origin = SourceContextCodec.origin(_parser(), steps, complete=False)
    steps[0]["columns"].append("other")
    assert SourceContextCodec.transformations(origin) == [
        {"type": "columnSelector", "columns": ["label"]}
    ]
    restored = SourceContextCodec.origin_from_payload(
        json.loads(json.dumps(SourceContextCodec.origin_payload(origin)))
    )
    assert restored == origin
    assert restored.complete is False


def test_named_selection_undo_redo_and_arbitrary_revision_restore_exact_origin() -> None:
    repository = DataRepository()
    source_a = SourceContextCodec.origin(CsvSourceContext("a.csv", InferredCsvPolicy()))
    source_b = SourceContextCodec.origin(CsvSourceContext("b.csv", InferredCsvPolicy()))
    repository.add_dataset("a", pd.DataFrame({"v": [1.0]}), origin=source_a)
    original_revision = repository.get_dataset_lineage("a").current_revision_id
    repository.set_data(pd.DataFrame({"v": [2.0]}))
    assert repository.get_loaded_origin() is None
    repository.undo_dataset()
    assert repository.get_loaded_origin() == source_a
    assert repository.get_data()["v"].tolist() == [1.0]
    repository.redo_dataset()
    assert repository.get_loaded_origin() is None
    repository.add_dataset("b", pd.DataFrame({"v": [3.0]}), origin=source_b)
    assert repository.get_loaded_origin() == source_b
    repository.select_dataset("a")
    assert repository.get_loaded_origin() is None
    repository.restore_dataset_revision(original_revision)
    assert repository.get_loaded_origin() == source_a
    repository.remove_dataset("a")
    assert repository.get_loaded_origin() == source_b
    repository.clear_data()
    assert repository.get_loaded_origin() is None


def test_invalid_origin_rejection_preserves_frame_revision_and_origin() -> None:
    repository = DataRepository()
    origin = SourceContextCodec.origin(CsvSourceContext("a.csv", InferredCsvPolicy()))
    repository.add_dataset("a", pd.DataFrame({"v": [1.0]}), origin=origin)
    before = repository.get_dataset_lineage()
    malformed = replace(origin, transformations_json='[{"not":"runnable"},null]')
    with pytest.raises(TypeError, match="objects"):
        repository.set_data(pd.DataFrame({"v": [2.0]}), origin=malformed)
    assert repository.get_data()["v"].tolist() == [1.0]
    assert repository.get_loaded_origin() == origin
    assert repository.get_dataset_lineage() == before


def test_recipe_capture_uses_loaded_origin_and_applied_steps_exactly_once() -> None:
    from src.core.models.recipe_models import RecipeSource
    from src.core.services.data_services.analysis_recipe_service import AnalysisRecipeService
    from src.core.state.repository_state_manager import RepositoryStateManager

    state = RepositoryStateManager()
    source = CsvSourceContext("actual.csv", InferredCsvPolicy(("label",)))
    step = {"type": "columnSelector", "columns": ["label", "value"]}
    origin = SourceContextCodec.origin(source, [step])
    state.set_data(pd.DataFrame({"label": ["NA"], "value": [1.0]}), origin=origin)
    state.set_csv_path("unloaded.csv")
    state.set_stats_path("new-parser-request")
    state.set_use_parser(True)
    service = AnalysisRecipeService(state)
    recipe = service.capture("automatic")
    assert recipe.source.path == "actual.csv"
    assert recipe.source.csv_policy == InferredCsvPolicy(("label",))
    assert recipe.transformations == (step,)
    additional = {"type": "columnSelector", "columns": ["value"]}
    assert service.capture("additional", transformations=[additional]).transformations == (
        step,
        additional,
    )
    explicit = service.capture("explicit", source=RecipeSource(kind="csv", path="declared.csv"))
    assert explicit.source.path == "declared.csv"
    assert explicit.transformations == ()
    assert service.loads(service.dumps(recipe)) == recipe
    state.set_data(pd.DataFrame({"value": [2.0]}))
    with pytest.raises(ValueError, match="explicit reusable source"):
        service.capture("edited")


def test_partial_and_undeclared_backend_automatic_capture_refuse_without_guessing() -> None:
    from src.core.models.recipe_models import RecipeSource
    from src.core.services.data_services.analysis_recipe_service import AnalysisRecipeService
    from src.core.state.repository_state_manager import RepositoryStateManager

    state = RepositoryStateManager()
    service = AnalysisRecipeService(state)
    state.set_data(
        pd.DataFrame({"label": ["NA"]}), origin=SourceContextCodec.origin(_parser(), complete=False)
    )
    with pytest.raises(ValueError, match="partial"):
        service.capture("partial")
    state.set_data(
        pd.DataFrame({"label": ["NA"]}),
        origin=SourceContextCodec.origin(replace(_parser(), simulator=None)),
    )
    with pytest.raises(ValueError, match="no declared simulator"):
        service.capture("undeclared")
    explicit = service.capture("declared", source=RecipeSource(kind="csv", path="caller.csv"))
    assert explicit.source.path == "caller.csv"


def test_parser_recipe_capture_preserves_all_actual_request_arguments() -> None:
    from src.core.services.data_services.analysis_recipe_service import AnalysisRecipeService
    from src.core.state.repository_state_manager import RepositoryStateManager

    state = RepositoryStateManager()
    request = replace(_parser(), scan_limit=None)
    state.set_data(pd.DataFrame({"label": ["NA"]}), origin=SourceContextCodec.origin(request))
    service = AnalysisRecipeService(state)
    recipe = service.capture("resolved")
    assert recipe.source.path == request.stats_path
    assert recipe.source.pattern == request.stats_pattern
    assert recipe.source.strategy == request.strategy_type
    assert recipe.source.simulator == "gem5"
    assert recipe.source.parser_contract_version == "10"
    assert recipe.source.scan_limit is None
    assert recipe.source.strict is False
    assert service.loads(service.dumps(recipe)) == recipe


def test_portfolio_origin_is_explicit_integrity_covered_and_restored_before_editor() -> None:
    from src.core.services.data_services.portfolio_service import PortfolioService
    from src.core.services.portfolio_integrity_service import PortfolioIntegrityService
    from src.core.state.repository_state_manager import RepositoryStateManager

    state = RepositoryStateManager()
    origin = SourceContextCodec.origin(
        CsvSourceContext("actual.csv", InferredCsvPolicy(("label",)))
    )
    data = pd.DataFrame({"label": ["NA"], "numeric": [1.25]})
    state.set_data(data, origin=origin)
    state.set_stats_path("unloaded-editor-request")
    service = PortfolioService(state)
    payload = json.loads(service.serialize_workspace(data, [], {}, 0, origin=origin))
    from src.core.models.portfolio_contract import CURRENT_PORTFOLIO_SCHEMA_VERSION

    assert payload["schema_version"] == CURRENT_PORTFOLIO_SCHEMA_VERSION
    assert payload["loaded_origin"]["source"]["path"] == "actual.csv"
    assert PortfolioIntegrityService.verify(payload).checksum_valid
    state.set_data(pd.DataFrame({"other": [3.0]}))
    state.restore_session(payload)
    pd.testing.assert_frame_equal(state.get_data(), data)
    assert state.get_loaded_origin() == origin
    payload["loaded_origin"]["source"]["path"] = "tampered.csv"
    assert not PortfolioIntegrityService.verify(payload).checksum_valid


def test_source_encoding_counts_exact_escaped_utf8_bytes(monkeypatch) -> None:
    from src.core.common import source_context_codec

    source = CsvSourceContext('μ\\"\n.csv', InferredCsvPolicy(("label",)))
    encoded = SourceContextCodec.encode(source)
    size = len(encoded.encode("utf-8"))
    monkeypatch.setattr(source_context_codec, "MAX_PARSE_RESULT_BYTES", size)
    assert SourceContextCodec.encode(source) == encoded
    monkeypatch.setattr(source_context_codec, "MAX_PARSE_RESULT_BYTES", size - 1)
    with pytest.raises(ValueError, match="byte budget"):
        SourceContextCodec.encode(source)
    assert source.policy.configuration_columns == ("label",)


def test_parser_metadata_budget_rejects_before_encoder_allocation(monkeypatch) -> None:
    from src.core.common import source_context_codec

    def forbidden(*args, **kwargs):
        pytest.fail("Over-budget metadata reached JSON encoding")

    monkeypatch.setattr(source_context_codec.json.JSONEncoder, "iterencode", forbidden)
    with pytest.raises(ValueError, match="budget"):
        SourceContextCodec.parser(
            stats_path="inputs",
            stats_pattern="stats.txt",
            strategy_type="simple",
            variables=[
                StatConfig(
                    "label",
                    "configuration",
                    params={
                        "source_type": "configuration",
                        "on_empty": "x" * 100,
                    },
                )
            ],
            scanned_variables=[],
            simulator="gem5",
            scan_limit=None,
            strict=False,
            metadata_byte_limit=20,
        )


def test_scanner_payload_owner_preserves_optional_observed_bounds_exactly() -> None:
    from src.core.models.parsing_models import SourceInstance
    from src.parsing.gem5.models import Gem5ScannedVariable

    scanned = Gem5ScannedVariable(
        "d",
        "distribution",
        entries=["-2", "4"],
        source_type="distribution",
        instances=(SourceInstance("d", ()),),
        minimum=-2.0,
        maximum=4.0,
    )
    source = SourceContextCodec.parser(
        stats_path="inputs",
        stats_pattern="stats.txt",
        strategy_type="simple",
        variables=[
            StatConfig(
                "d",
                "distribution",
                params={
                    "source_type": "distribution",
                    "minimum": -2,
                    "maximum": 4,
                },
            )
        ],
        scanned_variables=[scanned.to_dict()],
        simulator="gem5",
        scan_limit=0,
        strict=True,
    )
    assert SourceContextCodec.scanned_payloads(source) == [scanned.to_dict()]
    assert SourceContextCodec.decode(SourceContextCodec.encode(source)) == source
    payload = SourceContextCodec.scanned_payloads(source)[0]
    assert type(payload["minimum"]) is float
    assert type(payload["maximum"]) is float
    payload["minimum"] = -100.0
    assert SourceContextCodec.scanned_payloads(source)[0]["minimum"] == -2.0
    generic = SourceContextCodec.scanned_variables(source)[0]
    assert generic.source_type == "distribution"
    assert generic.instances == scanned.instances


@pytest.mark.parametrize(
    "field,value",
    [
        ("minimum", True),
        ("minimum", "0"),
        ("minimum", None),
        ("maximum", float("inf")),
        ("extra", 1),
    ],
)
def test_scanner_payload_owner_rejects_unknown_and_invalid_retained_fields(field, value) -> None:
    from src.core.models.parsing_models import SourceInstance, ScannedVariable

    payload = ScannedVariable(
        "d", "distribution", source_type="distribution", instances=(SourceInstance("d", ()),)
    ).to_dict()
    payload[field] = value
    with pytest.raises((TypeError, ValueError)):
        SourceContextCodec.parser(
            stats_path="inputs",
            stats_pattern="stats.txt",
            strategy_type="simple",
            variables=[
                StatConfig(
                    "d",
                    "distribution",
                    statistics_only=True,
                    params={"source_type": "distribution", "statistics": ["mean"]},
                )
            ],
            scanned_variables=[payload],
            simulator="gem5",
            scan_limit=None,
            strict=False,
        )
