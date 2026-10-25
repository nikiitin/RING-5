"""Canonical contracts agree across constructors, factory and pipeline admission."""

from __future__ import annotations

import copy
from typing import Annotated, Any, Literal, NotRequired, Required, TypedDict, cast
from collections.abc import Sequence

import pandas as pd
import pytest

from src.core.common import security_limits
from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.data_services.pipeline_config_exchange_service import (
    PipelineConfigExchangeService,
)
from src.core.services.shapers.definition import ShaperDefinition
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.pipeline_service import PipelineService, PipelineStepError
from src.core.services.shapers.shaper import Shaper

VALID: dict[str, dict[str, Any]] = {
    "mean": {
        "meanVars": ["v"],
        "meanAlgorithm": "arithmean",
        "groupingColumns": [],
        "replacingColumn": "bench",
    },
    "columnSelector": {"columns": []},
    "conditionSelector": {"column": "bench", "mode": "in", "values": ["a", 1, None]},
    "itemSelector": {"column": "bench", "strings": ["a"]},
    "normalize": {
        "normalizeVars": ["v"],
        "normalizerColumn": "policy",
        "normalizerValue": "",
        "groupBy": ["bench"],
    },
    "pivotLonger": {
        "id_vars": ["bench"],
        "value_vars": ["v"],
        "var_name": "metric",
        "value_name": "value",
        "selection_filters": {},
    },
    "pivotWider": {"index": ["bench"], "columns": "policy", "values": "v"},
    "sort": {"order_dict": {"bench": [1, "a", None]}},
    "splitApply": {
        "joinColumns": ["bench"],
        "groups": [{"columns": ["v"]}, {"columns": ["w"], "pipeline": []}],
    },
    "transformer": {"column": "v", "target_type": "scalar"},
    "deriveColumn": {
        "dest": "label",
        "op": "concat",
        "sources": ["bench", "bench"],
        "separator": "",
    },
    "groupCardinalitySelector": {"groupBy": ["bench"], "countColumn": "policy", "count": 0},
    "groupPredicateSelector": {
        "groupBy": ["bench"],
        "baselineColumn": "policy",
        "baselineValue": "base",
        "predicateColumn": "v",
    },
}


@pytest.mark.parametrize("identifier", VALID)
def test_all_definition_entry_points_agree(identifier: str) -> None:
    """Every strategy accepts the same current config, including supported defaults."""
    config = cast(ShaperStepConfig, {"type": identifier, **copy.deepcopy(VALID[identifier])})
    original = copy.deepcopy(config)
    definition = ShaperFactory.get_definition(identifier)
    ShaperFactory.validate_config(identifier, config)
    assert isinstance(ShaperFactory.create_shaper(identifier, config), definition.implementation)
    assert isinstance(definition.implementation(dict(config)), definition.implementation)
    ShaperFactory.validate_pipeline([config])
    payload = PipelineConfigExchangeService.dumps("Contract", "", [config])
    assert PipelineConfigExchangeService.loads(payload).shapers == (config,)
    assert config == original


@pytest.mark.parametrize("identifier", VALID)
def test_unknown_fields_rejected_by_every_constructor(identifier: str) -> None:
    config = {**copy.deepcopy(VALID[identifier]), "retired_field": True}
    with pytest.raises(ValueError, match="unsupported fields.*retired_field"):
        ShaperFactory.get_definition(identifier).implementation(config)
    with pytest.raises(ValueError, match="unsupported fields.*retired_field"):
        ShaperFactory.validate_config(identifier, config)


@pytest.mark.parametrize(
    ("identifier", "field", "value"),
    [
        ("mean", "meanAlgorithm", "average"),
        ("mean", "replacingColumn", ""),
        ("mean", "meanVars", [1]),
        ("normalize", "normalizeSd", 1),
        ("normalize", "normalizerVars", "v"),
        ("sort", "order_dict", {"bench": True}),
        ("conditionSelector", "threshold", True),
        ("transformer", "target_type", "categorical"),
        ("itemSelector", "strings", [123]),
        ("pivotLonger", "selection_strategy", "ignore"),
        ("deriveColumn", "zero_denominator", "zero"),
        ("deriveColumn", "scalar", float("nan")),
        ("groupCardinalitySelector", "count", True),
        ("groupCardinalitySelector", "count", -1),
        ("groupPredicateSelector", "action", "ignore"),
        ("splitApply", "groups", [{"columns": ["v"], "extra": 1}, {"columns": ["w"]}]),
    ],
)
def test_wrong_types_and_modes_are_not_coerced(identifier: str, field: str, value: Any) -> None:
    config = {**copy.deepcopy(VALID[identifier]), field: value}
    with pytest.raises((TypeError, ValueError)):
        ShaperFactory.create_shaper(identifier, cast(ShaperStepConfig, config))


def test_constructor_owns_nested_configuration() -> None:
    config = {"order_dict": {"bench": ["a", "b"]}}
    shaper = ShaperFactory.get_definition("sort").implementation(config)
    config["order_dict"]["bench"].reverse()
    data = pd.DataFrame({"bench": ["b", "a"]})
    assert shaper(data)["bench"].tolist() == ["a", "b"]


class PluginConfig(TypedDict):
    type: Required[Literal["testPlugin"]]
    amount: int
    label: NotRequired[str]


class Plugin(Shaper):
    calls = 0

    def __call__(self, frame: pd.DataFrame) -> pd.DataFrame:
        self.calls += 1
        return frame.assign(result=self.params["amount"])


def _validate_plugin(config: Any) -> None:
    if config["amount"] < 0:
        raise ValueError("amount cannot be negative")


@pytest.fixture
def plugin(monkeypatch: pytest.MonkeyPatch) -> ShaperDefinition:
    monkeypatch.setattr(ShaperFactory, "_definitions", dict(ShaperFactory._definitions))
    definition = ShaperDefinition(
        "testPlugin", Plugin, "Test plugin", PluginConfig, _validate_plugin
    )
    ShaperFactory.register(definition)
    return definition


def test_plugin_definition_and_exact_constructor_identity(plugin: ShaperDefinition) -> None:
    assert ShaperFactory.get_available_types()[-1] == "testPlugin"
    assert "Test plugin" not in ShaperFactory.get_display_name_map()
    assert Plugin({"amount": 2, "label": "optional"}).params["amount"] == 2
    with pytest.raises(ValueError, match="amount"):
        Plugin({})
    with pytest.raises(TypeError, match="integer"):
        Plugin({"amount": True})
    with pytest.raises(ValueError, match="negative"):
        Plugin({"amount": -1})

    class Unregistered(Plugin):
        pass

    with pytest.raises(ValueError, match="no registered definition"):
        Unregistered({"amount": 2})
    config = cast(ShaperStepConfig, {"type": "testPlugin", "amount": 3})
    assert PipelineService.process_pipeline(pd.DataFrame({"v": [1]}), [config])[
        "result"
    ].tolist() == [3]


def test_plugin_collisions_and_wrong_discriminators_rejected(plugin: ShaperDefinition) -> None:
    with pytest.raises(ValueError, match="already registered"):
        ShaperFactory.register(plugin)

    class AliasConfig(TypedDict):
        type: Required[Literal["aliasPlugin"]]

    with pytest.raises(ValueError, match="only one definition"):
        ShaperFactory.register(
            ShaperDefinition("aliasPlugin", Plugin, "Alias", AliasConfig, _validate_plugin)
        )
    with pytest.raises(TypeError, match="Literal must match"):
        ShaperFactory.register(
            ShaperDefinition("other", Plugin, "Other", PluginConfig, _validate_plugin)
        )
    with pytest.raises(TypeError, match="ShaperDefinition"):
        ShaperFactory.register("retired two-argument contract")  # type: ignore[arg-type]


def _split(inner: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "splitApply",
        "joinColumns": ["bench"],
        "groups": [
            {"columns": ["v"], "pipeline": inner},
            {"columns": ["w"], "pipeline": []},
        ],
    }


def test_nested_invalid_step_is_rejected_before_execution(
    plugin: ShaperDefinition, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(Plugin, "__call__", lambda self, frame: calls.append(True) or frame)
    config = cast(
        list[ShaperStepConfig],
        [
            {"type": "testPlugin", "amount": 1},
            _split([{"type": "transformer", "column": "v"}]),
        ],
    )
    with pytest.raises(PipelineStepError, match="target_type") as error:
        PipelineService.process_pipeline(pd.DataFrame({"bench": ["a"], "v": [1], "w": [2]}), config)
    assert error.value.step_index == 1
    assert not calls


def test_nested_depth_step_and_cycle_budgets() -> None:
    leaf = {"type": "sort", "order_dict": {}}
    excessive_steps = _split([leaf] * security_limits.MAX_PIPELINE_CONFIG_STEPS)
    with pytest.raises(ValueError, match="step limit"):
        ShaperFactory.validate_pipeline([excessive_steps])
    deep = leaf
    for _ in range(security_limits.MAX_PIPELINE_CONFIG_DEPTH + 2):
        deep = _split([deep])
    with pytest.raises(ValueError, match="nesting is too deep"):
        ShaperFactory.get_definition("splitApply").implementation(deep)
    cycle = _split([])
    cycle["groups"][0]["pipeline"].append(cycle)
    with pytest.raises(ValueError, match="cyclic configuration"):
        ShaperFactory.validate_pipeline([cycle])


@pytest.mark.parametrize("key", [1, "01", "+1", " 1", "1 ", "١", "", "2", "1" * 1000])
def test_pivot_filter_keys_have_one_lossless_json_representation(key: Any) -> None:
    config = {
        **VALID["pivotLonger"],
        "extract_pattern": r"cpu(\d+)",
        "selection_filters": {key: ["0"]},
    }
    with pytest.raises((TypeError, ValueError)):
        ShaperFactory.get_definition("pivotLonger").implementation(config)


def test_pivot_whole_match_group_zero_remains_supported() -> None:
    config = {
        **VALID["pivotLonger"],
        "value_vars": ["cpu0", "cpu1"],
        "extract_pattern": r"cpu(\d+)",
        "extract_group_indices": [0],
        "selection_filters": {"0": ["cpu0"]},
    }
    frame = pd.DataFrame({"bench": ["a"], "cpu0": [1], "cpu1": [2]})
    result = ShaperFactory.get_definition("pivotLonger").implementation(config)(frame)
    assert result["metric"].tolist() == ["cpu0"]
    encoded = PipelineConfigExchangeService.dumps(
        "Whole match", "", [cast(ShaperStepConfig, {"type": "pivotLonger", **config})]
    )
    assert PipelineConfigExchangeService.loads(encoded).shapers[0]["selection_filters"] == {
        "0": ["cpu0"]
    }


def test_maximum_supported_nesting_roundtrips_through_exchange() -> None:
    step = {"type": "sort", "order_dict": {}}
    for _ in range(security_limits.MAX_PIPELINE_CONFIG_DEPTH):
        step = _split([step])
    ShaperFactory.validate_pipeline([step])
    encoded = PipelineConfigExchangeService.dumps("Nested", "", [step])
    assert PipelineConfigExchangeService.loads(encoded).shapers == (step,)


def test_generic_pipeline_mapping_is_validated_before_ownership_copy() -> None:
    from types import MappingProxyType

    config = MappingProxyType({"type": "columnSelector", "columns": ["v"]})
    frame = pd.DataFrame({"v": [1], "w": [2]})
    result = PipelineService.process_pipeline(frame, (config,))
    assert list(result) == ["v"]
    assert list(frame) == ["v", "w"]


def test_unsupported_plugin_values_are_rejected_before_file_publication(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.core.services.data_services.config_service import ConfigService

    class BinaryConfig(TypedDict):
        type: Required[Literal["binaryPlugin"]]
        payload: str

    class BinaryPlugin(Shaper):
        def __call__(self, frame: pd.DataFrame) -> pd.DataFrame:
            return frame.copy()

    monkeypatch.setattr(ShaperFactory, "_definitions", dict(ShaperFactory._definitions))
    ShaperFactory.register(
        ShaperDefinition(
            "binaryPlugin", BinaryPlugin, "Binary plugin", BinaryConfig, lambda config: None
        )
    )
    monkeypatch.setattr(ConfigService, "_config_dir", tmp_path)

    def must_not_copy(value: Any) -> Any:
        raise AssertionError("Non-JSON configuration reached ownership copy")

    monkeypatch.setattr("src.core.services.shapers.factory.deepcopy", must_not_copy)
    with pytest.raises(ValueError, match="non-JSON"):
        ConfigService.save_configuration(
            "Binary", "", [{"type": "binaryPlugin", "payload": b"unsupported JSON"}]
        )
    assert not list(tmp_path.iterdir())


def test_concurrent_registration_publishes_exactly_one_definition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from concurrent.futures import ThreadPoolExecutor

    monkeypatch.setattr(ShaperFactory, "_definitions", dict(ShaperFactory._definitions))
    definition = ShaperDefinition(
        "testPlugin", Plugin, "Concurrent plugin", PluginConfig, _validate_plugin
    )

    def register(index: int) -> bool:
        try:
            ShaperFactory.register(definition)
        except ValueError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(register, range(32)))
    assert sum(results) == 1
    assert ShaperFactory.get_definition("testPlugin") is definition


def test_validator_return_contract_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ShaperFactory, "_definitions", dict(ShaperFactory._definitions))
    validator = cast(Any, lambda config: False)
    definition = ShaperDefinition("testPlugin", Plugin, "Wrong validator", PluginConfig, validator)
    ShaperFactory.register(definition)
    with pytest.raises(TypeError, match="return None"):
        Plugin({"amount": 1})


@pytest.mark.parametrize("baseline", [0, 1, False, True, 1.5])
def test_numeric_and_boolean_baseline_operands_remain_typed(baseline: Any) -> None:
    from src.core.services.shapers.impl.normalize import Normalize
    from src.core.services.shapers.impl.selector_algorithms.group_predicate_selector import (
        GroupPredicateSelector,
    )

    other = "other"
    frame = pd.DataFrame({"bench": ["a", "a"], "policy": [baseline, other], "v": [2.0, 6.0]})
    normalized = Normalize(
        {
            "normalizeVars": ["v"],
            "normalizerColumn": "policy",
            "normalizerValue": baseline,
            "groupBy": ["bench"],
        }
    )(frame)
    assert normalized["v"].tolist() == [1.0, 3.0]
    filtered = GroupPredicateSelector(
        {
            "groupBy": ["bench"],
            "baselineColumn": "policy",
            "baselineValue": baseline,
            "predicateColumn": "v",
            "action": "keep",
            "drop_when": "zero",
        }
    )(frame.assign(v=[0.0, 6.0]))
    assert len(filtered) == 2
    assert frame["v"].tolist() == [2.0, 6.0]


def test_value_mapping_preserves_numeric_boolean_and_null_results() -> None:
    from src.core.services.shapers.impl.derive_column import DeriveColumn

    frame = pd.DataFrame({"key": ["a", "b", "c"]})
    config = {
        "type": "deriveColumn",
        "op": "map",
        "dest": "value",
        "sources": ["key"],
        "mapping": {"a": 2.5, "b": False, "c": None},
    }
    result = DeriveColumn(config)(frame)
    assert result["value"].iloc[0] == 2.5
    assert result["value"].iloc[1] is False
    assert pd.isna(result["value"].iloc[2])
    assert "value" not in frame
    payload = PipelineConfigExchangeService.dumps("Typed mapping", "", [config])
    restored = PipelineConfigExchangeService.loads(payload)
    assert restored.shapers == (config,)


@pytest.mark.parametrize(
    "annotation",
    [
        Any,
        object,
        bytes,
        list,
        list[Any],
        tuple[str, ...],
        Sequence[str],
        dict[int, str],
        Annotated[str, "metadata"],
    ],
)
def test_unsupported_schema_is_rejected_before_registration(
    annotation: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ShaperFactory, "_definitions", dict(ShaperFactory._definitions))
    original = dict(ShaperFactory._definitions)
    schema = TypedDict(
        "UnsupportedConfig", {"type": Required[Literal["unsupportedPlugin"]], "payload": annotation}
    )

    class NeverConstructed(Shaper):
        def __init__(self, params: dict[str, Any]) -> None:
            raise AssertionError("Schema preflight constructed a plugin")

        def __call__(self, frame: pd.DataFrame) -> pd.DataFrame:
            return frame.copy()

    def never_validate(config: Any) -> None:
        raise AssertionError("Schema preflight executed a plugin validator")

    with pytest.raises(TypeError, match="unsupportedPlugin.payload.*unsupported schema annotation"):
        ShaperFactory.register(
            ShaperDefinition(
                "unsupportedPlugin", NeverConstructed, "Unsupported", schema, never_validate
            )
        )
    assert ShaperFactory._definitions == original


class RecursiveNode(TypedDict, total=False):
    label: str
    children: list[RecursiveNode]


class RecursiveConfig(TypedDict):
    type: Required[Literal["recursivePlugin"]]
    root: RecursiveNode


class RecursivePlugin(Shaper):
    def __call__(self, frame: pd.DataFrame) -> pd.DataFrame:
        return frame.copy()


def test_recursive_schema_accepts_bounded_values_and_rejects_runtime_cycles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ShaperFactory, "_definitions", dict(ShaperFactory._definitions))
    ShaperFactory.register(
        ShaperDefinition(
            "recursivePlugin", RecursivePlugin, "Recursive", RecursiveConfig, lambda config: None
        )
    )
    RecursivePlugin({"root": {"label": "root", "children": [{"label": "leaf"}]}})
    cycle: dict[str, Any] = {"label": "root"}
    cycle["children"] = [cycle]
    with pytest.raises(ValueError, match="cyclic configuration"):
        RecursivePlugin({"root": cycle})
    deep: dict[str, Any] = {"label": "leaf"}
    for _ in range(security_limits.MAX_PIPELINE_CONFIG_VALUE_DEPTH):
        deep = {"children": [deep]}
    with pytest.raises(ValueError, match="nesting is too deep"):
        RecursivePlugin({"root": deep})


def test_runtime_value_budget_rejects_before_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.core.services.shapers.definition.MAX_PIPELINE_CONFIG_VALUE_ITEMS", 4)

    def must_not_copy(value: Any) -> Any:
        raise AssertionError("Oversized configuration reached ownership copy")

    monkeypatch.setattr("src.core.services.shapers.factory.deepcopy", must_not_copy)
    with pytest.raises(ValueError, match="value budget exceeded"):
        ShaperFactory.validate_pipeline(
            [{"type": "sort", "order_dict": {"bench": ["a", "b", "c"]}}]
        )


def test_large_integer_is_rejected_before_conversion_or_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def must_not_copy(value: Any) -> Any:
        raise AssertionError("Oversized integer reached ownership copy")

    monkeypatch.setattr("src.core.services.shapers.factory.deepcopy", must_not_copy)
    config = {
        "type": "groupCardinalitySelector",
        "groupBy": ["bench"],
        "countColumn": "policy",
        "count": 1 << (security_limits.MAX_PIPELINE_CONFIG_BYTES * 4),
    }
    with pytest.raises(ValueError, match="value budget exceeded"):
        ShaperFactory.validate_pipeline([config])


def test_value_budgets_aggregate_across_pipeline_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.services.shapers.definition import ConfigValueBudget, validate_config_values

    first = {"type": "sort", "order_dict": {}}
    monkeypatch.setattr("src.core.services.shapers.definition.MAX_PIPELINE_CONFIG_BYTES", 45)
    validate_config_values(first, budget=ConfigValueBudget())
    with pytest.raises(ValueError, match="value budget exceeded"):
        ShaperFactory.validate_pipeline([first, first])


def test_value_preflight_retains_public_step_location() -> None:
    with pytest.raises(PipelineStepError, match="finite") as error:
        PipelineService.process_pipeline(
            pd.DataFrame({"v": [1]}),
            [
                {"type": "sort", "order_dict": {}},
                {
                    "type": "conditionSelector",
                    "column": "v",
                    "mode": "greater_than",
                    "threshold": float("nan"),
                },
            ],
        )
    assert error.value.step_index == 1
    assert error.value.shaper_type == "conditionSelector"
