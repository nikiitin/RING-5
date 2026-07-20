"""Public accessible-theme audit and dual-engine redundant encodings."""

from __future__ import annotations

import matplotlib.figure
import pandas as pd
import plotly.graph_objects as go
import pytest
from typing import cast

import ring5

pytestmark = pytest.mark.public_api


def test_accessible_theme_passes_audit_and_encodes_lines_and_bars_without_color_alone() -> None:
    # [test->req~ring5.figure.accessible-themes~1]
    data = pd.DataFrame(
        {
            "phase": [1, 2, 1, 2],
            "variant": ["baseline", "baseline", "candidate", "candidate"],
            "ipc": [1.0, 1.1, 1.2, 1.4],
        }
    )
    with ring5.Session() as session:
        line_config = session.apply_accessible_theme(
            {"x": "phase", "y": "ipc", "color": "variant"},
            "line",
        )
        report = session.audit_figure_accessibility(
            line_config,
            "line",
            series_count=2,
        )
        line_plot = session.create_plot("line", data=data, config=line_config)
        plotly_lines = session.render(line_plot, engine="plotly")
        matplotlib_lines = session.render(line_plot, engine="matplotlib")

        bar_config = session.apply_accessible_theme(
            {"x": "phase", "y": "ipc", "color": "variant"},
            "bar",
        )
        bar_plot = session.create_plot("bar", data=data, config=bar_config)
        plotly_bars = session.render(bar_plot, engine="plotly")
        matplotlib_bars = session.render(bar_plot, engine="matplotlib")

    assert isinstance(report, ring5.AccessibilityReport)
    assert report.passed
    assert report.minimum_contrast_ratio == pytest.approx(3.87)
    assert isinstance(plotly_lines, go.Figure)
    assert all(isinstance(trace, go.Scatter) for trace in plotly_lines.data)
    line_traces = [cast(go.Scatter, trace) for trace in plotly_lines.data]
    assert [trace.marker.symbol for trace in line_traces] == ["circle", "square"]
    assert all(trace.mode == "lines+markers" for trace in line_traces)
    assert isinstance(matplotlib_lines, matplotlib.figure.Figure)
    assert [line.get_marker() for line in matplotlib_lines.axes[0].lines] == ["o", "s"]

    assert isinstance(plotly_bars, go.Figure)
    assert all(isinstance(trace, go.Bar) for trace in plotly_bars.data)
    bar_traces = [cast(go.Bar, trace) for trace in plotly_bars.data]
    assert [trace.marker.pattern.shape for trace in bar_traces] == ["/", "\\"]
    assert isinstance(matplotlib_bars, matplotlib.figure.Figure)
    bar_hatches = {
        patch.get_hatch() for container in matplotlib_bars.axes[0].containers for patch in container
    }
    assert bar_hatches == {"/", "\\"}


def test_accessibility_public_errors_are_typed() -> None:
    # [test->req~ring5.figure.accessible-themes~1]
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="mapping"):
            session.apply_accessible_theme([], "line")  # type: ignore[arg-type]
        with pytest.raises(ring5.DataValidationError, match="mapping"):
            session.audit_figure_accessibility([], "line")  # type: ignore[arg-type]
        with pytest.raises(ring5.DataValidationError, match="plot type"):
            session.apply_accessible_theme({}, "")
        with pytest.raises(ring5.DataValidationError, match="positive integer"):
            session.audit_figure_accessibility({}, "line", series_count=0)
