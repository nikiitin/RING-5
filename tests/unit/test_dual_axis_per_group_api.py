"""Tests for the headless dual-axis API surface, per-group dot-line, and the
matplotlib line-marker fix.

Covers:
  * ``FigureSpec`` / ``DualAxisOpts`` -> flat dual-axis config keys (+ builder).
  * ``build_right_axis_traces`` per-group mode -> one polyline per x-category
    (NaN breaks between groups).
  * ``MatplotlibTraceRenderer._draw_line`` now honours markers (dual-engine parity).
"""

import math

import matplotlib
import pandas as pd
import pytest

from src.core.models.visualization.trace_config import LineTraceConfig
from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
    build_right_axis_traces,
)
from ring5.figure_spec import DualAxisOpts, FigureSpec, FigureSpecBuilder
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

pytestmark = pytest.mark.public_api

# FigureSpec / DualAxisOpts -> flat config


def test_dual_axis_opts_emits_flat_keys() -> None:
    spec = FigureSpec(
        x="benchmark",
        group="policy",
        y_columns=["a", "b"],
        dual_axis=DualAxisOpts(
            columns=["metric"],
            kind="dots",
            show_lines=True,
            per_group=True,
            dot_size=4,
            dot_symbol="circle",
            line_width=1.4,
            color="#F2B705",
            ylabel="Right",
            y_range=(0.7, 4.0),
        ),
    )
    cfg = spec.to_config()
    assert cfg["dual_axis"] is True
    assert cfg["y_columns_right"] == ["metric"]
    assert cfg["right_axis_type"] == "dots"
    assert cfg["right_show_lines"] is True
    assert cfg["right_line_per_group"] is True
    assert cfg["right_dot_size"] == 4
    assert cfg["right_line_width"] == 1.4
    assert cfg["ylabel_right"] == "Right"
    assert cfg["range_y2"] == [0.7, 4.0]
    # single colour -> series_styles entry for every right column
    assert cfg["series_styles"]["metric"] == {"color": "#F2B705", "use_color": True}


def test_no_dual_axis_emits_no_keys() -> None:
    cfg = FigureSpec(x="b", group="p", y_columns=["a"]).to_config()
    assert "dual_axis" not in cfg
    assert "y_columns_right" not in cfg


def test_builder_dual_axis() -> None:
    spec = (
        FigureSpecBuilder()
        .data(x="b", group="p", y_columns=["a"])
        .dual_axis(columns=["m"], per_group=True, color="#123456")
        .build()
    )
    assert spec.dual_axis is not None
    assert spec.dual_axis.per_group is True
    cfg = spec.to_config()
    assert cfg["right_line_per_group"] is True
    assert cfg["series_styles"]["m"]["color"] == "#123456"


# per-group dot-line (NaN breaks between x-categories)


def _grouped_frame() -> pd.DataFrame:
    # two categories (A, B), two groups each; __x_coord pre-mapped.
    return pd.DataFrame(
        {
            "benchmark": ["A", "A", "B", "B"],
            "policy": ["p1", "p2", "p1", "p2"],
            "metric": [1.0, 2.0, 3.0, 4.0],
            "__x_coord": [0.0, 1.0, 2.5, 3.5],
        }
    )


def test_per_group_line_inserts_break_between_categories() -> None:
    cfg = {
        "x": "benchmark",
        "xaxis_order": ["A", "B"],
        "right_show_lines": True,
        "right_line_per_group": True,
    }
    traces = build_right_axis_traces(_grouped_frame(), "__x_coord", ["metric"], "dots", 0.8, cfg)
    assert len(traces) == 1
    line = traces[0]
    assert isinstance(line, LineTraceConfig)
    # 4 real points + 1 NaN separator between the two groups.
    assert len(line.x) == 5
    nan_idx = [i for i, v in enumerate(line.y) if isinstance(v, float) and math.isnan(v)]
    assert nan_idx == [2]  # break sits between group A (0,1) and group B (3,4)
    assert line.x[:2] == [0.0, 1.0]
    assert line.x[3:] == [2.5, 3.5]


def test_continuous_line_when_not_per_group() -> None:
    cfg = {"x": "benchmark", "right_show_lines": True, "right_line_per_group": False}
    traces = build_right_axis_traces(_grouped_frame(), "__x_coord", ["metric"], "dots", 0.8, cfg)
    line = traces[0]
    assert len(line.x) == 4  # no break
    assert not any(isinstance(v, float) and math.isnan(v) for v in line.y)


# _draw_line honours markers (matplotlib <-> plotly parity)


def test_draw_line_renders_markers() -> None:
    fig, ax = plt.subplots()
    spec = LineTraceConfig(
        name="L", x=[0, 1, 2], y=[1, 2, 3], show_markers=True, marker_symbol="diamond"
    )
    MatplotlibTraceRenderer._draw_line(spec, ax)
    drawn = ax.get_lines()[0]
    assert drawn.get_marker() == "D"  # diamond -> matplotlib "D"
    plt.close(fig)


def test_draw_line_no_markers_when_disabled() -> None:
    fig, ax = plt.subplots()
    spec = LineTraceConfig(name="L", x=[0, 1], y=[1, 2], show_markers=False)
    MatplotlibTraceRenderer._draw_line(spec, ax)
    assert ax.get_lines()[0].get_marker() in ("None", "")
    plt.close(fig)
