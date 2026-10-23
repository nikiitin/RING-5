"""Offline browser contracts for the installed Plotly JavaScript bundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly
import plotly.graph_objects as go
import pytest
from playwright.sync_api import Page
from plotly.offline import get_plotlyjs
from plotly.utils import PlotlyJSONEncoder

from src.web.pages.ui.plotting.types.box_plot import BoxPlot

pytestmark = pytest.mark.requires_browser
_COMPONENT = Path(__file__).parents[2] / "src/web/components/plotting/custom_plotly/index.html"


def _render(page: Page, figure: go.Figure) -> None:
    """Exercise the actual Streamlit component render handler without a server."""
    args = {
        "plotly_js": get_plotlyjs(),
        "plotly_version": plotly.__version__,
        "spec": json.dumps(figure.to_plotly_json(), cls=PlotlyJSONEncoder),
        "config": "{}",
    }
    page.evaluate("args => onRender({data: {args}})", args)


def test_custom_component_renders_binary_arrays_with_no_network(page: Page) -> None:
    requests: list[str] = []
    page.route("**/*", lambda route: (requests.append(route.request.url), route.abort()))
    page.set_content(_COMPONENT.read_text())
    figure = go.Figure(
        go.Scatter(
            x=np.array([1, 2, 3], dtype="int8"), y=np.array([2.0, 4.0, 8.0]), mode="lines+markers"
        )
    )
    _render(page, figure)
    page.wait_for_function('document.getElementById("myDiv").calcdata?.[0]?.length === 3')
    assert page.evaluate('document.getElementById("myDiv").calcdata[0].map(point => point.y)') == [
        2,
        4,
        8,
    ]
    assert page.evaluate("window._ring5_plotly_version") == plotly.__version__
    assert requests == []


@pytest.mark.parametrize("mode", ["tukey", "minmax", "percentile"])
def test_plotly_box_calcdata_uses_precomputed_statistics(page: Page, mode: str) -> None:
    page.set_content(_COMPONENT.read_text())
    data = pd.DataFrame({"x": ["a"] * 5, "y": [0.0, 1.0, 2.0, 3.0, 100.0]})
    config: dict[str, Any] = {
        "x": "x",
        "y": "y",
        "whisker_mode": mode,
        "whisker_percentiles": [20, 80],
    }
    plot = BoxPlot(1, "Distribution")
    trace = plot.create_traces(data, config).traces[0]
    _render(page, plot.create_figure(data, config))
    page.wait_for_function('document.getElementById("myDiv").calcdata?.[0]?.[0]?.q1 !== undefined')
    actual = page.evaluate(
        'Object.fromEntries(["q1", "med", "q3", "lf", "uf"].map(key => '
        '[key, document.getElementById("myDiv").calcdata[0][0][key]]))'
    )
    assert actual == {
        "q1": trace.q1,
        "med": trace.median,
        "q3": trace.q3,
        "lf": trace.lower_whisker,
        "uf": trace.upper_whisker,
    }
