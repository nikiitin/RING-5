"""Declared logical layout discovery and native cell controls use one UI owner."""

from collections.abc import Generator
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.core.common.distribution_metadata import with_distribution_layouts
from src.core.models.distribution_geometry import DistributionGeometry
from src.core.models.native_distribution_layout import (
    DistributionColumn,
    NativeDistributionLayout,
    OpaqueDistributionLayout,
)
from src.core.models.plot_config import PlotConfig
from src.web.components.plotting.config import histogram_config
from src.web.state.ui_state_manager import WidgetKeyBuilder


def frame(kind: str) -> pd.DataFrame:
    bindings = (
        DistributionColumn("physical..left", "underflows", "underflow", None),
        DistributionColumn("cell", "0.25", "bucket", 0),
        DistributionColumn("right", "overflows", "overflow", None),
    )
    layout = (
        NativeDistributionLayout(DistributionGeometry(0.25, 0.25, 1), "missing", bindings)
        if kind == "native"
        else OpaqueDistributionLayout(
            tuple(DistributionColumn(b.column, b.source_label, "source", None) for b in bindings)
        )
    )
    return with_distribution_layouts(
        pd.DataFrame(
            {
                "physical..left": [0.0],
                "cell": [2.0],
                "right": [0.0],
                "ordinary..0-9": [4.0],
                "only_sd..0.sd": [0.1],
                "group": ["A"],
            }
        ),
        {"logical": layout},
    )


@pytest.fixture
def widgets() -> Generator[tuple[MagicMock, MagicMock], None, None]:
    with (
        patch.object(histogram_config, "st") as st,
        patch.object(histogram_config, "render_common_config") as common,
    ):
        st.selectbox.side_effect = lambda _label, options, **kwargs: options[kwargs["index"]]
        st.checkbox.side_effect = lambda _label, **kwargs: kwargs["value"]
        st.number_input.side_effect = lambda _label, **kwargs: kwargs["value"]
        common.side_effect = lambda _data, saved, _id: deepcopy(saved)
        yield st, common


@pytest.mark.parametrize("kind", ["native", "opaque"])
def test_discovery_uses_logical_keys_without_physical_prefix_aliases(kind: str) -> None:
    # [test->req~ring5.figure.histogram-controls~2]
    data = frame(kind)
    before = deepcopy(data.attrs)
    assert histogram_config._detect_histogram_variables(data) == ["logical", "ordinary"]
    assert data.attrs == before


def test_invalid_reserved_layout_rejects_without_generic_fallback() -> None:
    data = frame("native")
    del data.attrs["ring5.distribution_layouts"]["logical"]["columns"][1]["native_index"]
    with pytest.raises(ValueError, match="current fields"):
        histogram_config._detect_histogram_variables(data)


@pytest.mark.parametrize("kind", ["native", "opaque"])
def test_unbound_auxiliary_columns_cannot_reintroduce_a_native_prefix_alias(kind: str) -> None:
    # [test->req~ring5.figure.histogram-controls~2]
    data = frame(kind)
    data["physical..auxiliary"] = [5.0]
    before = deepcopy(data.attrs)
    assert histogram_config._detect_histogram_variables(data) == ["logical", "ordinary"]
    assert data.attrs == before


@pytest.mark.parametrize("cumulative", [False, True])
@pytest.mark.parametrize("normalization", ["count", "probability", "percent", "density"])
def test_native_controls_offer_only_supported_mass_or_cdf_modes(
    widgets: tuple[MagicMock, MagicMock], cumulative: bool, normalization: str
) -> None:
    # [test->req~ring5.figure.histogram-controls~2]
    # [test->req~ring5.figure.histogram-cumulative~2]
    st, common = widgets
    data = frame("native")
    original = data.copy(deep=True)
    attrs = deepcopy(data.attrs)
    saved: PlotConfig = {
        "histogram_variable": "logical",
        "group_by": "group",
        "bucket_size": 10,
        "normalization": normalization,
        "cumulative": cumulative,
    }
    before = deepcopy(saved)
    result = histogram_config.render(data, saved, 7)
    assert result["histogram_variable"] == "logical" and result["group_by"] == "group"
    assert "bucket_size" not in result
    st.number_input.assert_not_called()
    expected = ["count", "probability", "percent"] + (["density"] if cumulative else [])
    norm = next(c for c in st.selectbox.call_args_list if c.args[0] == "Normalization")
    assert norm.kwargs["options"] == expected
    assert result["normalization"] == (normalization if normalization in expected else "count")
    assert result["cumulative"] is cumulative
    assert common.call_args.args[1]["xlabel"] == "Native bucket"
    assert norm.kwargs["key"] == WidgetKeyBuilder.plot_key(7, "widgets.histogram_norm")
    if cumulative:
        assert norm.kwargs["format_func"]("density") == "CDF"
    assert saved == before and data.attrs == attrs
    pd.testing.assert_frame_equal(data, original)


@pytest.mark.parametrize("override", [{"xlabel": "Chosen"}, {"xaxis_title": "Precise axis"}])
def test_native_common_labels_preserve_explicit_overrides(
    widgets: tuple[MagicMock, MagicMock], override: PlotConfig
) -> None:
    _, common = widgets
    saved: PlotConfig = {"histogram_variable": "logical", **override}
    before = deepcopy(saved)
    result = histogram_config.render(frame("native"), saved, 3)
    assert result["xlabel"] == (override.get("xlabel") or override["xaxis_title"])
    assert common.call_args.args[1] is not saved
    assert saved == before


def test_opaque_controls_explain_missing_grid_and_never_offer_rebin(
    widgets: tuple[MagicMock, MagicMock],
) -> None:
    st, common = widgets
    result = histogram_config.render(
        frame("opaque"), {"histogram_variable": "logical", "bucket_size": 3}, 1
    )
    st.warning.assert_called_once()
    assert "no declared native grid" in st.warning.call_args.args[0]
    st.number_input.assert_not_called()
    assert "bucket_size" not in result
    assert "xlabel" not in common.call_args.args[1]


def test_ordinary_histogram_keeps_generic_rebin_and_density_controls(
    widgets: tuple[MagicMock, MagicMock],
) -> None:
    st, common = widgets
    saved: PlotConfig = {
        "histogram_variable": "ordinary",
        "bucket_size": 5,
        "normalization": "density",
    }
    result = histogram_config.render(frame("native"), saved, 2)
    assert result["bucket_size"] == 5 and result["normalization"] == "density"
    st.number_input.assert_called_once()
    assert common.call_args.args[1] == saved
    norm = next(c for c in st.selectbox.call_args_list if c.args[0] == "Normalization")
    assert norm.kwargs["options"] == ["count", "probability", "percent", "density"]
    assert norm.kwargs["format_func"]("density") == "density"


def test_real_editor_preserves_native_grid_precision_and_policy_across_reruns() -> None:
    """Streamlit empty values and serialized doubles preserve the declared draft."""
    script = """from copy import deepcopy
import streamlit as st
from src.web.components.data_source.variable_editor import VariableEditor
original = {"name": "h", "type": "distribution", "params": {"source_type": "distribution"}}
config = deepcopy(original)
VariableEditor.render_distribution_config(None, config, original, "real", None, "stats.txt")
st.session_state["result"] = config
st.session_state["original"] = original
"""
    app = AppTest.from_string(script).run(timeout=15)
    assert not app.exception
    assert [(widget.label, widget.value) for widget in app.number_input] == [
        ("Minimum value", None),
        ("Maximum value", None),
        ("Native bucket size", None),
    ]
    assert app.session_state["result"]["params"] == {
        "source_type": "distribution",
        "minimum": None,
        "maximum": None,
        "bucket_size": None,
        "zero_policy": "missing",
    }
    precise = 0.2500000000000001
    app.number_input[0].set_value(precise)
    app.number_input[1].set_value(1.2500000000000002)
    app.number_input[2].set_value(precise)
    app.selectbox[0].select("nozero").run(timeout=15)
    assert not app.exception
    expected = {
        "source_type": "distribution",
        "minimum": precise,
        "maximum": 1.2500000000000002,
        "bucket_size": precise,
        "zero_policy": "nozero",
    }
    assert app.session_state["result"]["params"] == expected
    assert app.session_state["original"]["params"] == {"source_type": "distribution"}
    app.run(timeout=15)
    assert not app.exception
    assert app.session_state["result"]["params"] == expected


@pytest.mark.parametrize(
    "override, expected",
    [
        ({}, "Native bucket"),
        ({"xlabel": "Chosen"}, "Chosen"),
        ({"xaxis_title": "Precise axis"}, "Precise axis"),
    ],
)
def test_real_native_controls_preserve_labels_and_cdf_without_rebin(
    override: PlotConfig, expected: str
) -> None:
    # [test->req~ring5.figure.histogram-controls~2]
    # [test->req~ring5.figure.histogram-cumulative~2]
    script = """from copy import deepcopy
import streamlit as st
from tests.unit.test_native_distribution_ui import frame
from src.web.components.plotting.config import histogram_config
data = frame("native")
saved = CONFIG
before = deepcopy(saved)
attrs = deepcopy(data.attrs)
result = histogram_config.render(data, saved, 7)
assert before == saved and attrs == data.attrs
st.session_state["result"] = result
st.session_state["saved"] = saved
"""
    saved: PlotConfig = {"histogram_variable": "logical", "bucket_size": 9, **override}
    app = AppTest.from_string(script.replace("CONFIG", repr(saved))).run(timeout=15)
    assert not app.exception
    result = app.session_state["result"]
    assert result["histogram_variable"] == "logical" and result["xlabel"] == expected
    assert "bucket_size" not in result and not app.number_input
    assert app.session_state["saved"] == saved
    assert next(widget for widget in app.text_input if widget.label == "X-label").value == expected
    normalization = next(widget for widget in app.selectbox if widget.label == "Normalization")
    assert normalization.options == ["count", "probability", "percent"]
    next(widget for widget in app.checkbox if widget.label == "Cumulative").check().run(timeout=15)
    assert not app.exception
    normalization = next(widget for widget in app.selectbox if widget.label == "Normalization")
    assert normalization.options == ["count", "probability", "percent", "CDF"]
    normalization.select("CDF").run(timeout=15)
    assert not app.exception
    assert app.session_state["result"]["normalization"] == "density"
    assert app.session_state["result"]["cumulative"] is True
