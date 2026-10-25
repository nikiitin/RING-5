"""Typed observations and guarded accumulator lifecycle preserve scientific values."""

from __future__ import annotations

import math
from collections.abc import Callable
from types import MappingProxyType
from typing import Any, cast

import pytest

from src.core.models.data_models import ParseVariableConfig
from src.core.models.parsing_models import StatParamValue
from src.parsing.gem5.types.base import Observation, StatContent, StatResult, StatType
from src.parsing.gem5.types.configuration import Configuration
from src.parsing.gem5.types.distribution import Distribution
from src.parsing.gem5.types.histogram import Histogram
from src.parsing.gem5.types.scalar import Scalar
from src.parsing.gem5.types.vector import Vector

Accumulator = StatType[StatContent, StatResult]
_CASES: list[tuple[Callable[[], Accumulator], Observation]] = [
    (lambda: Scalar(), 1.25),
    (lambda: Configuration(), "literal 001 % Ω"),
    (lambda: Vector(entries=["001"]), {"001": 1.25}),
    (lambda: Distribution(minimum=0, maximum=0), {"underflows": 0, "0": 1.25, "overflows": 0}),
    (lambda: Histogram(), {"-1-0": 1.25}),
]


@pytest.mark.parametrize(("factory", "observation"), _CASES)
def test_lifecycle_has_one_order_and_idempotent_completed_stages(
    factory: Callable[..., Accumulator], observation: Observation
) -> None:
    stat = factory()
    stat.add_observation(observation)
    with pytest.raises(AttributeError, match="balance_content.*reduce_duplicates"):
        _ = stat.reduced_content
    with pytest.raises(RuntimeError, match="balance_content"):
        stat.reduce_duplicates()
    assert not stat.is_reduced
    assert not stat.is_balanced
    stat.balance_content()
    initial_content = stat.content
    stat.balance_content()
    assert stat.content == initial_content
    with pytest.raises(AttributeError, match="reduce_duplicates"):
        _ = stat.reduced_content
    with pytest.raises(RuntimeError, match="after balancing"):
        stat.add_observation(observation)
    stat.reduce_duplicates()
    initial_result = stat.reduced_content
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content == initial_result
    assert stat.is_balanced and stat.is_reduced
    with pytest.raises(RuntimeError, match="after balancing"):
        stat.add_observation(observation)


@pytest.mark.parametrize(("factory", "observation"), _CASES)
def test_setter_and_unknown_attributes_are_not_observation_routes(
    factory: Callable[..., Accumulator], observation: Observation
) -> None:
    stat = factory()
    with pytest.raises(AttributeError):
        cast(Any, stat).content = observation
    with pytest.raises(AttributeError):
        cast(Any, stat).unsupported = observation
    assert not stat.is_balanced


@pytest.mark.parametrize("factory", [Scalar, lambda: Vector(entries=["a"]), Histogram])
def test_excess_observations_do_not_advance_lifecycle(factory: Callable[..., Accumulator]) -> None:
    stat = factory()
    value = 1.5 if isinstance(stat, Scalar) else {"a": 1.5}
    stat.add_observation(value)
    stat.add_observation(value)
    with pytest.raises(RuntimeError, match="More .*than expected"):
        stat.balance_content()
    assert not stat.is_balanced
    assert not stat.is_reduced
    with pytest.raises(RuntimeError, match="balance_content"):
        stat.reduce_duplicates()
    with pytest.raises(AttributeError):
        _ = stat.reduced_content


@pytest.mark.parametrize("bad", [True, "1.25", None, [1.25], {"a": 1.25}])
def test_scalar_rejects_other_observation_shapes_atomically(bad: Any) -> None:
    stat = Scalar()
    with pytest.raises(TypeError, match="numeric measurement"):
        stat.add_observation(bad)
    assert stat.content == []
    stat.add_observation(1.25)
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content == 1.25


@pytest.mark.parametrize("bad", [True, 1.25, None, ["text"], {"a": 1.25}])
def test_configuration_rejects_nontext_without_coercion(bad: Any) -> None:
    stat = Configuration(on_empty="")
    with pytest.raises(TypeError, match="must be text"):
        stat.add_observation(bad)
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content == ""


@pytest.mark.parametrize("factory", [lambda: Vector(entries=["a", "b"]), Histogram])
@pytest.mark.parametrize("bad", [1.25, "1.25", {1: 2}, {"a": True}, {"a": [2]}, {"a": 1, "b": "2"}])
def test_entry_kinds_reject_coercible_or_list_values_before_mutating(
    factory: Callable[..., Accumulator], bad: Any
) -> None:
    stat = factory()
    with pytest.raises(TypeError):
        stat.add_observation(bad)
    content = stat.content
    assert isinstance(content, dict)
    assert not any(content.values())
    stat.add_observation({"a": 1.5, "b": 2.5})
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content == {"a": 1.5, "b": 2.5}


def test_frame_and_read_views_are_owned_defensive_values() -> None:
    values = {"001": 1.5, "1": 2.5}
    entries = ["001", "1"]
    stat = Vector(entries=entries)
    stat.add_observation(MappingProxyType(values))
    values["001"] = 90
    entries.append("extra")
    content = stat.content
    content["001"][0] = 99
    stat.entries.append("unexpected")
    stat.balance_content()
    stat.reduce_duplicates()
    result = stat.reduced_content
    result["001"] = 88
    assert stat.entries == ["001", "1"]
    assert stat.reduced_content == {"001": 1.5, "1": 2.5}


def test_histogram_derives_raw_views_and_rebinning_from_one_frame_store() -> None:
    stat = Histogram(repeat=2, bins=2, max_range=10, statistics=["mean"])
    raw = {"0-9": 10.5, "mean": 2.5}
    stat.add_observation(raw)
    raw["0-9"] = 99
    stat.add_observation({"0-9": 20.5, "10-19": 2.5})
    view = stat.content
    view["0-9"][0] = 99
    assert math.isnan(view["10-19"][0])
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content["0-9"] == 15.5
    assert stat.reduced_content["10+"] == 1.25
    assert math.isnan(stat.reduced_content["mean"])
    assert not hasattr(stat, "_observations")
    assert not hasattr(stat, "_content")


@pytest.mark.parametrize("value", [0.0, -1.25, math.nan, math.inf, -math.inf])
def test_numeric_points_preserve_zero_fractional_and_nonfinite_values(value: Any) -> None:
    stat = Scalar()
    stat.add_observation(value)
    stat.balance_content()
    stat.reduce_duplicates()
    if math.isnan(value):
        assert math.isnan(stat.reduced_content)
    else:
        assert stat.reduced_content == value


def test_nonfinite_frequency_frames_remain_ieee_values_without_fabrication() -> None:
    stat = Distribution(minimum=0, maximum=0, repeat=2)
    for value in (math.inf, -math.inf):
        stat.add_observation({"underflows": 0, "0": value, "overflows": 0})
    stat.balance_content()
    stat.reduce_duplicates()
    assert math.isnan(stat.reduced_content["0"])
    assert stat.reduced_content["underflows"] == 0
    assert stat.reduced_content["overflows"] == 0


def test_vector_missing_entry_does_not_shift_another_frames_measurement() -> None:
    stat = Vector(repeat=2, entries=["a", "b"])
    stat.add_observation({"a": 1.5})
    stat.add_observation({"b": 2.5})
    stat.balance_content()
    stat.reduce_duplicates()
    assert all(math.isnan(value) for value in stat.reduced_content.values())
    assert stat.padded_count == 2


def test_distribution_failed_frame_validation_is_atomic() -> None:
    stat = Distribution(minimum=0, maximum=1)
    with pytest.raises(RuntimeError, match="Boundary buckets"):
        stat.add_observation({"underflows": 0, "0": 3, "overflows": 0})
    content = stat.content
    assert isinstance(content, dict)
    assert not any(content.values())
    stat.add_observation({"underflows": 0, "0": 3.5, "1": 4.5, "overflows": 0})
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content == {"underflows": 0.0, "0": 3.5, "1": 4.5, "overflows": 0.0}


@pytest.mark.parametrize("repeat", [True, False, 1.0, "1", None, 0, -1])
@pytest.mark.parametrize(
    "factory",
    [Scalar, Configuration, lambda **kw: Vector(entries=[], **kw), Histogram, Distribution],
)
def test_repeat_requires_positive_integer(factory: Callable[..., Accumulator], repeat: Any) -> None:
    with pytest.raises((TypeError, ValueError), match="repeat"):
        factory(repeat=repeat)


@pytest.mark.parametrize("factory", [Scalar, Configuration, Vector, Histogram, Distribution])
def test_constructor_rejects_unknown_options(factory: Callable[..., Accumulator]) -> None:
    with pytest.raises(TypeError, match="unexpected keyword"):
        factory(retired_option=True)


@pytest.mark.parametrize("factory", [Vector, Histogram, Distribution])
def test_constructor_rejects_string_list_options(factory: Callable[..., Accumulator]) -> None:
    option = "entries" if factory is Vector else "statistics"
    with pytest.raises(TypeError, match="list of text"):
        factory(**{option: "a,b"})


@pytest.mark.parametrize("value", [True, "1", None, math.nan, math.inf, -1])
def test_histogram_rejects_invalid_geometry(value: Any) -> None:
    with pytest.raises((TypeError, ValueError)):
        Histogram(max_range=value)


@pytest.mark.parametrize("value", [True, 1.5, "1", None, -1])
def test_histogram_rejects_invalid_bin_count(value: Any) -> None:
    with pytest.raises((TypeError, ValueError)):
        Histogram(bins=value)


def test_configuration_preserves_literal_text_and_first_observation_policy() -> None:
    stat = Configuration(repeat=1, on_empty="fallback")
    stat.add_observation("001 % Ω")
    stat.add_observation("later")
    snapshot = stat.content
    snapshot[0] = "mutated"
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content == "001 % Ω"


@pytest.mark.parametrize("minimum,maximum", [(0.0, 1.0), (-1.0, 1), (0, 0.0)])
def test_integral_distribution_metadata_reaches_exact_constructor_without_truncation(
    minimum: float, maximum: float
) -> None:
    from src.core.common.stat_config_codec import StatConfigCodec
    from src.core.models.parsing_models import StatConfig
    from src.parsing.gem5.impl.source_bindings import resolve_sources
    from src.parsing.gem5.types.type_mapper import TypeMapper

    config = StatConfig(
        "d",
        "distribution",
        params={"source_type": "distribution", "minimum": minimum, "maximum": maximum},
    )
    validated = StatConfigCodec.validate(config)
    stat = TypeMapper.create_stat(resolve_sources([validated], None).accumulators[0])
    assert isinstance(stat, Distribution)
    assert stat.minimum == minimum and type(stat.minimum) is int
    assert stat.maximum == maximum and type(stat.maximum) is int
    assert config.params["minimum"] == minimum
    assert config.params["maximum"] == maximum


@pytest.mark.parametrize("minimum,maximum", [(0.5, 1.0), (-1.5, 1), (0, 0.5)])
def test_fractional_distribution_geometry_is_visible_and_stays_an_editor_draft(
    minimum: float, maximum: float
) -> None:
    from src.core.common.stat_config_codec import StatConfigCodec, StatConfigDraftIncomplete
    from src.core.models.parsing_models import StatConfig

    params: dict[str, StatParamValue] = {
        "source_type": "distribution",
        "minimum": minimum,
        "maximum": maximum,
    }
    config = StatConfig("d", "distribution", params=params)
    with pytest.raises(ValueError, match="fixed-unit.*integral bounds"):
        StatConfigCodec.validate(config)
    draft: ParseVariableConfig = {"name": "d", "type": "distribution", "params": params}
    with pytest.raises(StatConfigDraftIncomplete, match="fixed-unit.*integral bounds"):
        StatConfigCodec.from_draft(draft)
    assert StatConfigCodec.to_snapshot(draft) == {"state": "draft", "fields": draft}


def test_statistics_only_distribution_needs_no_unused_geometry() -> None:
    from src.core.models.parsing_models import StatConfig
    from src.parsing.gem5.impl.source_bindings import resolve_sources
    from src.parsing.gem5.types.type_mapper import TypeMapper

    config = StatConfig(
        "d",
        "distribution",
        statistics_only=True,
        params={"source_type": "distribution", "statistics": ["mean"]},
    )
    stat = TypeMapper.create_stat(resolve_sources([config], None).accumulators[0])
    stat.add_observation({"mean": 1.5})
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content == {"mean": 1.5}


def test_explicit_empty_configuration_fallback_survives_codec_and_worker() -> None:
    from src.core.common.stat_config_codec import StatConfigCodec
    from src.core.models.parsing_models import StatConfig
    from src.parsing.gem5.impl.source_bindings import resolve_sources
    from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
    from src.parsing.gem5.types.type_mapper import TypeMapper

    config = StatConfig(
        "label", "configuration", params={"source_type": "configuration", "on_empty": ""}
    )
    assert StatConfigCodec.from_payload(StatConfigCodec.to_payload(config)).params["on_empty"] == ""
    plan = resolve_sources([config], None)
    stat = TypeMapper.create_stat(plan.accumulators[0])
    worker = Gem5ParseWork("unused", {"label": stat}, plan)
    worker._process_output("")
    stat.balance_content()
    stat.reduce_duplicates()
    assert stat.reduced_content == ""
