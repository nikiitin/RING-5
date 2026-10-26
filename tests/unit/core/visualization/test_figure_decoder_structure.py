"""Explicit styling decoders admit current structures without losing supplied fields."""

from copy import deepcopy
from typing import Any, cast

import numpy as np
import pytest

from src.core.models.visualization.axis_config import AxesConfig, AxisConfig
from src.core.models.visualization.data_label_config import DataLabelConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.legend_config import (
    ColorbarConfig,
    LegendConfig,
    LegendSpacingConfig,
)
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.web.rendering.config_builder import ConfigSpecBuilder

DECODERS = [
    FigureConfig,
    AxisConfig,
    AxesConfig,
    LegendConfig,
    LegendSpacingConfig,
    ColorbarConfig,
    SeriesStyleConfig,
    DataLabelConfig,
]


@pytest.mark.parametrize("model", DECODERS, ids=lambda model: model.__name__)
@pytest.mark.parametrize("value", [None, [], False, 0, ""])
def test_standalone_decoders_reject_falsy_nonobjects(model: Any, value: Any) -> None:
    with pytest.raises(TypeError, match="object with text field names"):
        model.from_dict(value)


@pytest.mark.parametrize("model", DECODERS, ids=lambda model: model.__name__)
def test_standalone_decoders_reject_unknown_and_nontext_fields(model: Any) -> None:
    for value in ({"unsupported_field": True}, {7: "unsupported"}):
        with pytest.raises(TypeError, match="Unsupported|text field names"):
            model.from_dict(value)


@pytest.mark.parametrize("model", DECODERS, ids=lambda model: model.__name__)
def test_empty_and_default_roundtrips_preserve_current_models(model: Any) -> None:
    expected = model()
    assert model.from_dict({}) == expected
    assert model.from_dict(expected.to_dict()) == expected


# Paths use integer segments only for explicit list entries in these test payloads.
Path = tuple[str | int, ...]


def _payload(path: Path, value: Any) -> dict[str, Any]:
    """Build one nested supplied value without adding unrelated configuration."""
    root: dict[str, Any] = {}
    current: Any = root
    for index, segment in enumerate(path):
        if index == len(path) - 1:
            if isinstance(segment, int):
                current.append(value)
            else:
                current[segment] = value
            break
        next_value: Any = [] if isinstance(path[index + 1], int) else {}
        if isinstance(segment, int):
            current.append(next_value)
        else:
            current[segment] = next_value
        current = next_value
    return root


OBJECT_PATHS: list[Path] = [
    ("dimensions",),
    ("dimensions", "margins"),
    ("typography",),
    ("axes",),
    ("axes", "x"),
    ("axes", "y"),
    ("legends", 0),
    ("legends", 0, "spacing"),
    ("legends", 0, "colorbar"),
    ("annotations", 0),
    ("series_styles", 0),
    ("reference_lines", 0),
    ("trace_overrides",),
    ("trace_overrides", "A"),
    ("metadata",),
    ("traces", 0),
    ("axes", "x", "label_aliases"),
]
ARRAY_PATHS: list[Path] = [
    ("legends",),
    ("annotations",),
    ("series_styles",),
    ("reference_lines",),
    ("traces",),
    ("color_palette",),
    ("hatching_sequence",),
    ("axes", "x", "tick_values"),
    ("axes", "x", "tick_text"),
    ("axes", "x", "range"),
    ("axes", "x", "category_order"),
    ("axes", "group_order"),
]


@pytest.mark.parametrize("path", OBJECT_PATHS)
@pytest.mark.parametrize("value", [[], False, 0, ""])
def test_supplied_object_fields_reject_wrong_falsy_containers(path: Path, value: Any) -> None:
    with pytest.raises((TypeError, ValueError), match="must be an object"):
        FigureConfig.from_dict(_payload(path, value))


@pytest.mark.parametrize("path", [path for path in OBJECT_PATHS if path[-1] != "label_aliases"])
def test_required_objects_do_not_interpret_null_as_defaults(path: Path) -> None:
    with pytest.raises((TypeError, ValueError), match="must be an object"):
        FigureConfig.from_dict(_payload(path, None))


@pytest.mark.parametrize("path", ARRAY_PATHS)
@pytest.mark.parametrize("value", [None, {}, False, 0, ""])
def test_supplied_array_fields_reject_wrong_falsy_containers(path: Path, value: Any) -> None:
    if path[0] == "axes" and value is None:
        # These leaf fields explicitly use None for native/default ordering and ticks.
        decoded: Any = FigureConfig.from_dict(_payload(path, value))
        for field in path:
            decoded = getattr(decoded, cast(str, field))
        assert decoded is None
    else:
        with pytest.raises(TypeError, match="must be an array"):
            FigureConfig.from_dict(_payload(path, value))


@pytest.mark.parametrize("path", [("data_labels",), ("axes", "y2")])
@pytest.mark.parametrize("value", [[], False, 0, ""])
def test_nullable_objects_reject_nonnull_wrong_shapes(path: Path, value: Any) -> None:
    with pytest.raises(TypeError, match="must be an object"):
        FigureConfig.from_dict(_payload(path, value))


@pytest.mark.parametrize(
    "path",
    [
        p
        for p in OBJECT_PATHS
        if p
        not in [("metadata",), ("traces", 0), ("trace_overrides",), ("axes", "x", "label_aliases")]
    ],
)
def test_nested_model_fields_reject_unknown_names(path: Path) -> None:
    with pytest.raises(TypeError, match="Unsupported"):
        FigureConfig.from_dict(_payload(path, {"unsupported_field": True}))


@pytest.mark.parametrize(
    "field", ["legends", "annotations", "series_styles", "reference_lines", "traces"]
)
def test_one_bad_record_cannot_disappear_among_valid_records(field: str) -> None:
    with pytest.raises(TypeError, match=rf"{field}\[1\].*object"):
        FigureConfig.from_dict({field: [{}, False]})


def test_one_bad_named_override_cannot_disappear() -> None:
    with pytest.raises(TypeError, match="trace_overrides.*bad.*object"):
        FigureConfig.from_dict({"trace_overrides": {"good": {}, "bad": False}})


@pytest.mark.parametrize(
    "path", [("metadata",), ("traces", 0), ("trace_overrides",), ("axes", "x", "label_aliases")]
)
def test_open_maps_require_text_keys_without_losing_unknown_names(path: Path) -> None:
    with pytest.raises(TypeError, match="text field names"):
        FigureConfig.from_dict(_payload(path, {7: "value"}))


def test_partial_objects_preserve_margins_and_explicit_secondary_axis() -> None:
    spec = FigureConfig.from_dict(
        {
            "dimensions": {"margins": {"left": 23.5}},
            "axes": {"y2": {}},
            "data_labels": {},
        }
    )
    assert spec.dimensions.margins.left == 23.5
    assert spec.dimensions.width == 7.0
    assert spec.axes.y2 == AxisConfig()
    assert spec.data_labels == DataLabelConfig()
    absent = FigureConfig.from_dict({"axes": {"y2": None}, "data_labels": None})
    assert absent.axes.y2 is None
    assert absent.data_labels is None


def test_raw_trace_records_and_metadata_keep_owned_containers_and_arbitrary_values() -> None:
    values = np.array([1.25, 2.75])
    trace = {
        "trace_type": "plugin",
        "subclass_option": {7: values},
        "custom_data": [None, "mixed", 3],
    }
    metadata: dict[str, Any] = {"optional": None, "plugin": {7: values}}
    source: dict[str, Any] = {"traces": [trace], "metadata": metadata}
    spec = FigureConfig.from_dict(source)
    decoded_trace = cast(Any, spec.traces[0])
    assert decoded_trace == trace
    assert decoded_trace is not trace
    assert spec.traces is not source["traces"]
    assert decoded_trace["subclass_option"][7] is values
    assert spec.metadata is not metadata
    assert cast(Any, spec.metadata)["plugin"][7] is values
    assert source["metadata"] == metadata
    encoded = spec.to_dict()
    np.testing.assert_array_equal(encoded["traces"][0]["subclass_option"][7], values)
    np.testing.assert_array_equal(encoded["metadata"]["plugin"][7], values)


@pytest.mark.parametrize("invalid", [False, True])
def test_nested_decoding_does_not_mutate_input_on_success_or_failure(invalid: bool) -> None:
    source: dict[str, Any] = {
        "dimensions": {"margins": {"left": 21.5}},
        "legends": [{"spacing": {"borderpad": 0.75}, "colorbar": {"title_side": "left"}}],
        "series_styles": [{"line_width": 3.25}],
        "axes": {"x": {"range": [1.0, 4.0], "tick_values": [1, "mixed"]}},
    }
    if invalid:
        source["series_styles"].append(False)
    before = deepcopy(source)
    if invalid:
        with pytest.raises(TypeError, match="series_styles"):
            FigureConfig.from_dict(source)
    else:
        spec = FigureConfig.from_dict(source)
        assert spec.legends[0].spacing.borderpad == 0.75
        assert spec.axes.x.range == [1.0, 4.0]
        assert spec.axes.x.tick_values == [1, "mixed"]
    assert source == before


def test_structural_admission_preserves_scalar_construction_policy() -> None:
    style = SeriesStyleConfig.from_dict({"line_width": "2.5", "marker_size": 6.8, "color": None})
    assert style.line_width == 2.5
    assert style.marker_size == 6
    assert style.color == "None"
    labels = DataLabelConfig.from_dict({"enabled": "false", "font_size": "11", "threshold": "1.5"})
    assert labels.enabled is True
    assert labels.font_size == 11
    assert labels.threshold == 1.5
    spec = FigureConfig.from_dict(
        {"enable_stripes": "false", "axes": {"top_axis_line_width": "1.25"}}
    )
    assert spec.enable_stripes is True
    assert spec.axes.top_axis_line_width == 1.25


def test_flat_plugin_projection_retains_its_current_namespace() -> None:
    config = {
        "series_styles": {"A": {"line_width": 2.5, "plugin_option": {"name": "Owned by plugin"}}},
        "plugin_layout": {"columns": 3},
    }
    before = deepcopy(config)
    spec = ConfigSpecBuilder.from_config(cast(Any, config), "line")
    assert spec.trace_overrides["A"].line_width == 2.5
    assert spec.trace_overrides["A"].opacity is None
    assert config == before
