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


def _observe_ready_announcements(page: Page) -> None:
    """Record transport readiness independently of the component's internal timer."""
    page.evaluate("""() => {
        window.readyAnnouncements = 0;
        window.addEventListener('message', event => {
            if (event.source === window.parent && event.origin === location.origin &&
                event.data?.isStreamlitMessage === true &&
                event.data.type === 'streamlit:componentReady') {
                window.readyAnnouncements += 1;
            }
        });
    }""")


def _ready_count(page: Page) -> int:
    """Drain posted messages before reading the parent's readiness receipt count."""
    return int(page.evaluate("""() => new Promise(resolve => {
        const token = 'ready-barrier-' + Math.random();
        const barrier = event => {
            if (event.source === window && event.data?.ring5ReadyBarrier === token) {
                window.removeEventListener('message', barrier);
                resolve(window.readyAnnouncements);
            }
        };
        window.addEventListener('message', barrier);
        window.postMessage({ring5ReadyBarrier: token}, '*');
    })"""))


def _assert_ready_is_pending(page: Page) -> None:
    """An unacknowledged component announces readiness again without a real-time sleep."""
    previous = _ready_count(page)
    page.clock.fast_forward(1000)
    assert _ready_count(page) > previous


@pytest.mark.parametrize(
    ("source", "origin"),
    [("parent", "https://foreign.example"), ("other", None), ("none", None)],
)
def test_component_rejects_foreign_render_messages(
    page: Page, source: str, origin: str | None
) -> None:
    page.clock.install()
    page.set_content(_COMPONENT.read_text())
    _observe_ready_announcements(page)
    _message(
        page, {"type": "streamlit:render", "args": _protocol_args()}, source=source, origin=origin
    )
    assert page.evaluate("window.bundleRuns || 0") == 0
    assert page.evaluate("window.renderCalls || 0") == 0
    _assert_ready_is_pending(page)


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
    page.clock.install()
    page.set_content(_COMPONENT.read_text())
    _observe_ready_announcements(page)
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
    _assert_ready_is_pending(page)
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


@pytest.mark.parametrize(
    ("capture_click", "point_count"), [(False, 1), (True, 0), (True, 1), (True, 2)]
)
def test_component_emits_only_one_unambiguous_captured_point(
    page: Page, capture_click: bool, point_count: int
) -> None:
    """The actual browser bridge rejects disabled, empty and ambiguous click payloads."""
    page.set_content(_COMPONENT.read_text())
    emitted = page.evaluate(
        """({capture, count}) => {
            const messages = [];
            const original = Streamlit.setComponentValue;
            Streamlit.setComponentValue = value => messages.push(value);
            const point = {
                curveNumber: 2, pointNumber: 0, pointIndex: 0, x: 10, y: 32,
                data: {name: 'Prefetch', meta: {
                    ring5_drilldown: [{configuration: 'Prefetch'}],
                }},
            };
            try {
                handlePlotClick({_streamlit_capture_click: capture}, {
                    points: Array.from({length: count}, () => point),
                });
            } finally {
                Streamlit.setComponentValue = original;
            }
            return messages;
        }""",
        {"capture": capture_click, "count": point_count},
    )
    expected = (
        [
            {
                "kind": "drill_down",
                "curveNumber": 2,
                "pointNumber": 0,
                "pointIndex": 0,
                "x": 10,
                "y": 32,
                "traceName": "Prefetch",
                "filters": {"configuration": "Prefetch"},
            }
        ]
        if capture_click and point_count == 1
        else []
    )
    assert emitted == expected


def test_component_recovers_a_ready_message_dropped_before_parent_registration(page: Page) -> None:
    """A late parent listener receives readiness and renders real native observations."""
    origin = "https://ring5-component.test"
    parent = """<!doctype html><html><body><script>
        window.unregisteredReady = 0;
        window.readyAnnouncements = 0;
        window.componentReadyListener = null;
        window.addEventListener('message', event => {
            const child = document.getElementById('component')?.contentWindow;
            if (event.source !== child || event.origin !== location.origin ||
                event.data?.isStreamlitMessage !== true ||
                event.data.type !== 'streamlit:componentReady') return;
            if (window.componentReadyListener === null) {
                window.unregisteredReady += 1;
                return;
            }
            window.readyAnnouncements += 1;
            window.componentReadyListener(event);
        });
        </script><iframe id="component" src="/chart"></iframe></body></html>"""

    def serve(route: Route) -> None:
        document = _COMPONENT.read_text() if route.request.url.endswith("/chart") else parent
        route.fulfill(status=200, content_type="text/html", body=document)

    page.clock.install()
    page.route(f"{origin}/**", serve)
    page.goto(f"{origin}/parent", wait_until="load")
    page.wait_for_function("window.unregisteredReady > 0")
    assert page.evaluate("typeof document.getElementById('component').contentWindow.Plotly") == (
        "undefined"
    )
    args = {
        "plotly_js": get_plotlyjs(),
        "plotly_version": _PLOTLY_VERSION,
        "spec": json.dumps(
            {"data": [{"type": "scatter", "x": [1, 2, 3], "y": [2, 4, 8]}], "layout": {}}
        ),
        "config": "{}",
    }
    page.evaluate(
        """args => {
            window.componentReadyListener = () => {
                document.getElementById('component').contentWindow.postMessage(
                    {type: 'streamlit:render', args}, location.origin);
            };
        }""",
        args,
    )
    page.clock.fast_forward(1000)
    native = page.wait_for_function("""() => {
        const graph = document.getElementById('component').contentDocument.getElementById('myDiv');
        return graph.calcdata?.[0]?.length === 3 && graph.calcdata[0].map(point => point.y);
    }""").json_value()
    assert native == [2, 4, 8]
    received = _ready_count(page)
    assert received > 0
    page.clock.fast_forward(1000)
    assert _ready_count(page) == received


def test_component_stops_unacknowledged_readiness_at_the_parent_deadline(page: Page) -> None:
    """A missing parent cannot leave an unbounded transport timer running."""
    page.clock.install()
    page.set_content(_COMPONENT.read_text())
    _observe_ready_announcements(page)
    _assert_ready_is_pending(page)
    received = _ready_count(page)
    page.clock.fast_forward(60_000)
    assert _ready_count(page) == received
    page.clock.fast_forward(60_000)
    assert _ready_count(page) == received
    assert page.evaluate("typeof window.Plotly") == "undefined"


@pytest.mark.parametrize("event_name", ["pagehide", "unload"])
def test_component_releases_pending_readiness_when_its_document_leaves(
    page: Page, event_name: str
) -> None:
    """Document lifecycle cleanup cancels readiness without accepting a render."""
    page.clock.install()
    page.set_content(_COMPONENT.read_text())
    _observe_ready_announcements(page)
    _assert_ready_is_pending(page)
    page.evaluate("name => window.dispatchEvent(new Event(name))", event_name)
    received = _ready_count(page)
    page.clock.fast_forward(1000)
    assert _ready_count(page) == received
    assert page.evaluate("typeof window.Plotly") == "undefined"


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
