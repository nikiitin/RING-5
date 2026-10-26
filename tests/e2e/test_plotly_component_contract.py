"""Offline rendering and parent-message contracts for the Plotly component."""

from __future__ import annotations

from ring5 import Session
from typing import cast

import json
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from playwright.sync_api import Page, Route
from plotly.offline import get_plotlyjs
from plotly.utils import PlotlyJSONEncoder

from src.core.models.visualization.trace_config import BoxTraceConfig
from src.web.pages.ui.plotting.types.box_plot import BoxPlot
from tests.helpers.streamlit_server import free_loopback_port, running_streamlit

pytestmark = pytest.mark.requires_browser
_PLOTLY_VERSION = version("plotly")
_REPOSITORY = Path(__file__).parents[2]
_COMPONENT = _REPOSITORY / "src/web/components/plotting/custom_plotly/index.html"


def _message(
    page: Page,
    payload: Any,
    *,
    source: str = "parent",
    origin: str | None = None,
) -> None:
    """Dispatch a parent, unrelated-frame, or source-less protocol message."""
    page.evaluate(
        """({payload, source, origin}) => {
            let sender = window.parent;
            if (source === "other") {
                const frame = document.createElement("iframe");
                document.body.appendChild(frame);
                sender = frame.contentWindow;
            } else if (source === "none") {
                sender = null;
            }
            window.dispatchEvent(new MessageEvent("message", {
                source: sender,
                origin: origin ?? window.location.origin,
                data: payload,
            }));
        }""",
        {"payload": payload, "source": source, "origin": origin},
    )


def _render(page: Page, figure: go.Figure) -> None:
    """Exercise the actual Streamlit component render handler without a server."""
    args = {
        "plotly_js": get_plotlyjs(),
        "plotly_version": _PLOTLY_VERSION,
        "spec": json.dumps(figure.to_plotly_json(), cls=PlotlyJSONEncoder),
        "config": "{}",
    }
    _message(page, {"type": "streamlit:render", "args": args})


def _protocol_args() -> dict[str, str]:
    """Make bundle execution and render calls observable without loading Plotly."""
    return {
        "spec": '{"data": [], "layout": {}}',
        "config": "{}",
        "plotly_version": "test",
        "plotly_js": (
            "window.bundleRuns = (window.bundleRuns || 0) + 1;"
            "window.Plotly = {react: () => {"
            "window.renderCalls = (window.renderCalls || 0) + 1;"
            "return {then: () => {}};}};"
        ),
    }


@pytest.mark.parametrize(
    ("source", "origin"),
    [("parent", "https://foreign.example"), ("other", None), ("none", None)],
)
def test_component_rejects_foreign_render_messages(
    page: Page, source: str, origin: str | None
) -> None:
    page.set_content(_COMPONENT.read_text())
    _message(
        page, {"type": "streamlit:render", "args": _protocol_args()}, source=source, origin=origin
    )
    assert page.evaluate("window.bundleRuns || 0") == 0
    assert page.evaluate("window.renderCalls || 0") == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("message", None),
        ("message", []),
        ("message", 42),
        ("message", {}),
        ("message", {"type": "unrelated"}),
        ("args", None),
        ("args", []),
        ("spec", {}),
        ("spec", "{"),
        ("spec", "null"),
        ("spec", '{"data": {}}'),
        ("spec", '{"data": [], "layout": []}'),
        ("config", {}),
        ("config", "{"),
        ("config", "[]"),
        ("config", "null"),
        ("plotly_js", None),
        ("plotly_version", None),
    ],
)
def test_component_ignores_invalid_payloads_before_loading_a_bundle(
    page: Page, field: str, value: Any
) -> None:
    errors: list[str] = []

    def record_error(error: Any) -> None:
        errors.append(str(error))

    page.on("pageerror", record_error)
    page.set_content(_COMPONENT.read_text())
    payload: Any = {"type": "streamlit:render", "args": _protocol_args()}
    if field == "message":
        payload = value
    elif field == "args":
        payload["args"] = value
    else:
        payload["args"][field] = value
    _message(page, payload)
    assert page.evaluate("window.bundleRuns || 0") == 0
    assert page.evaluate("window.renderCalls || 0") == 0
    assert errors == []


def test_component_accepts_parent_rerenders_and_loads_each_bundle_version_once(page: Page) -> None:
    page.set_content(_COMPONENT.read_text())
    args = _protocol_args()
    _message(page, {"type": "streamlit:render", "args": args})
    _message(page, {"type": "streamlit:render", "args": args})
    assert page.evaluate("window.bundleRuns") == 1
    assert page.evaluate("window.renderCalls") == 2
    args["plotly_version"] = "next"
    _message(page, {"type": "streamlit:render", "args": args})
    assert page.evaluate("window.bundleRuns") == 2
    assert page.evaluate("window.renderCalls") == 3


def test_installed_component_accepts_the_actual_streamlit_parent(
    page: Page, tmp_path: Path
) -> None:
    script = tmp_path / "component_app.py"
    script.write_text(
        "import numpy as np\n"
        "import plotly.graph_objects as go\n"
        "from src.web.components.plotting.interactive_plot import interactive_plotly_chart\n"
        "figure = go.Figure(go.Scatter(x=np.array([1, 2, 3]), y=np.array([2, 4, 8])))\n"
        "interactive_plotly_chart(figure, key='parent-contract')\n",
        encoding="utf-8",
    )
    with running_streamlit(
        script,
        port=free_loopback_port(),
        environment={"PYTHONPATH": str(_REPOSITORY)},
    ) as url:
        page.goto(url)
        page.wait_for_function(
            """() => document.querySelector('iframe[title$="interactive_plotly"]')
                ?.contentDocument?.getElementById("myDiv")?.calcdata?.[0]?.length === 3""",
            timeout=30_000,
        )
        chart = page.frame_locator('iframe[title$="interactive_plotly"]').locator("#myDiv")
        assert chart.evaluate("node => node.calcdata[0].map(point => point.y)") == [2, 4, 8]
        assert chart.evaluate("() => window.location.origin") == page.evaluate(
            "window.location.origin"
        )


def test_custom_component_renders_binary_arrays_with_no_network(page: Page) -> None:
    requests: list[str] = []

    def block_request(route: Route) -> None:
        requests.append(route.request.url)
        route.abort()

    page.route("**/*", block_request)
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
    assert page.evaluate("window._ring5_plotly_version") == _PLOTLY_VERSION
    assert requests == []


@pytest.mark.parametrize("mode", ["tukey", "minmax", "percentile"])
def test_plotly_box_calcdata_uses_precomputed_statistics(
    page: Page, mode: str, plot_session: Session
) -> None:
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
    assert isinstance(trace, BoxTraceConfig)
    plot.processed_data = data
    plot.config = config
    _render(page, cast(go.Figure, plot_session.render(plot)))
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
