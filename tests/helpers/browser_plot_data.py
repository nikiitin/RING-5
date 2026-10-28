"""Inspect completed native charts and download their actual processed source data."""

from __future__ import annotations

import csv
import json
from io import StringIO
from typing import TYPE_CHECKING, Any

from playwright.sync_api import (
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    expect,
)

if TYPE_CHECKING:
    from tests.visual.pages.manage_plots_page import ManagePlotsPage


_NATIVE_PLOTLY_DIAGNOSTICS = """() => {
    const text = (value, limit = 120) => String(value ?? '').slice(0, limit);
    const scalar = value => typeof value === 'string' ? text(value) :
        typeof value === 'number' && Number.isFinite(value) ? value :
        typeof value === 'boolean' ? value : null;
    const graphState = graph => graph ? {
        title: text(graph._fullLayout?.title?.text),
        traces: graph._fullData?.length ?? null,
        calculatedTraces: graph.calcdata?.length ?? null,
        paper_bgcolor: scalar(graph._fullLayout?.paper_bgcolor),
        plot_bgcolor: scalar(graph._fullLayout?.plot_bgcolor),
        width: scalar(graph._fullLayout?.width),
        height: scalar(graph._fullLayout?.height),
    } : null;
    const app = document.querySelector('[data-testid="stApp"]');
    return {
        scriptState: app?.getAttribute('data-test-script-state') ?? null,
        connectionState: app?.getAttribute('data-test-connection-state') ?? null,
        nativeGraphs: [...document.querySelectorAll('.js-plotly-plot')]
            .slice(0, 8).map(graphState),
        frames: [...document.querySelectorAll('iframe[title$="interactive_plotly"]')]
            .slice(0, 8).map(frame => {
                const rectangle = frame.getBoundingClientRect();
                const state = {
                    title: text(frame.title),
                    width: rectangle.width, height: rectangle.height,
                    top: rectangle.top, left: rectangle.left,
                };
                try {
                    const child = frame.contentWindow;
                    const doc = frame.contentDocument;
                    return {...state,
                        documentReady: doc?.readyState ?? null,
                        plotlyVersion: text(child?.Plotly?.version),
                        bundleVersion: text(child?._ring5_plotly_version),
                        readyTimerActive: child?.readyTimer != null,
                        readyRemainingMs: child?.readyDeadline > 0 ?
                            Math.max(0, child.readyDeadline - child.performance.now()) : 0,
                        graph: graphState(doc?.getElementById('myDiv')),
                    };
                } catch (error) {
                    return {...state, unavailable: text(error.name, 80)};
                }
            }),
        renderedErrors: [...document.querySelectorAll('[data-testid="stException"]')]
            .slice(0, 3).map(element => text(element.innerText, 500)),
    };
}"""


def read_native_plotly(
    page: Page,
    expected_title: str,
    *,
    expected_trace_count: int | None = None,
    expected_layout: dict[str, object] | None = None,
    timeout: int = 60_000,
) -> dict[str, Any]:
    """Read resolved frontend arrays after the requested chart has finished calculating.

    Args:
        page: Live application browser page.
        expected_title: Exact native layout title identifying the requested figure.
        expected_trace_count: Optional additional rerender completion condition.
        expected_layout: Optional native scalar layout values required before capture.
        timeout: Maximum time to wait for this native figure.

    Returns:
        Selected native trace, layout and calculated-point fields with typed arrays
        converted to ordinary JSON lists.
    """
    try:
        result = page.wait_for_function(
            """({title, count, layout}) => {
                const graphs = [...document.querySelectorAll('.js-plotly-plot')];
                for (const frame of document.querySelectorAll(
                    'iframe[title$="interactive_plotly"]')) {
                    const graph = frame.contentDocument?.getElementById('myDiv');
                    if (graph) graphs.push(graph);
                }
                const graph = graphs.find(candidate =>
                    candidate._fullLayout?.title?.text === title &&
                    candidate.calcdata?.length && candidate._fullData?.length &&
                    (count == null || candidate._fullData.length === count) &&
                    Object.entries(layout).every(([key, value]) =>
                        candidate._fullLayout[key] === value));
                if (!graph) return false;
                const plain = value => {
                    if (value === undefined) return null;
                    if (value === null || typeof value !== 'object') return value;
                    if (Array.isArray(value) || ArrayBuffer.isView(value)) {
                        return Array.from(value, plain);
                    }
                    return Object.fromEntries(Object.entries(value)
                        .filter(([key]) => !key.startsWith('_'))
                        .map(([key, item]) => [key, plain(item)]));
                };
                const fields = ['type', 'name', 'legendgroup', 'x', 'y', 'z', 'r', 'theta',
                    'q1', 'median', 'q3', 'mean', 'lowerfence', 'upperfence', 'measure',
                    'text', 'mode', 'line', 'marker', 'error_y', 'xaxis', 'yaxis',
                    'dimensions', 'node', 'link', 'customdata', 'fill',
                    'selectedpoints', 'unselected'];
                const layoutFields = ['title', 'xaxis', 'yaxis', 'yaxis2', 'barmode',
                    'font', 'paper_bgcolor', 'plot_bgcolor', 'width', 'height',
                    'annotations', 'xaxis2'];
                const pointFields = ['x', 'y', 's', 'p', 'v', 'q1', 'med', 'q3', 'lf', 'uf'];
                return {
                    traces: graph._fullData.map(trace => Object.fromEntries(
                        fields.filter(key => trace[key] !== undefined)
                            .map(key => [key, plain(trace[key])]))),
                    layout: Object.fromEntries(layoutFields.filter(key =>
                        graph._fullLayout[key] !== undefined)
                        .map(key => [key, plain(graph._fullLayout[key])])),
                    calculated: graph.calcdata.map(points => points.map(point =>
                        Object.fromEntries(pointFields.filter(key => point[key] !== undefined)
                            .map(key => [key, plain(point[key])])))),
                };
            }""",
            arg={
                "title": expected_title,
                "count": expected_trace_count,
                "layout": expected_layout or {},
            },
            timeout=timeout,
        ).json_value()
    except PlaywrightTimeoutError as exc:
        try:
            diagnostic = page.evaluate(_NATIVE_PLOTLY_DIAGNOSTICS)
        except PlaywrightError as diagnostic_error:
            exc.add_note(
                "Native Plotly diagnostic unavailable: "
                + type(diagnostic_error).__name__
                + ": "
                + str(diagnostic_error)[:300]
            )
        else:
            exc.add_note("Native Plotly diagnostic: " + json.dumps(diagnostic, ensure_ascii=True))
        raise
    assert isinstance(result, dict)
    return result


def download_processed_csv(
    manager: ManagePlotsPage, *, timeout: int = 90_000
) -> tuple[list[str], list[dict[str, str]]]:
    """Download HTML through the app, then use its source-table CSV download.

    The returned rows come from the actual post-pipeline dataframe embedded in
    the browser download, rather than the workspace's unprocessed data manager.
    """
    page = manager.page
    manager.select_engine("plotly")
    manager.open_download_expander("plotly", timeout=timeout)
    html = manager.download_format_pills.get_by_role("radio", name="html", exact=True)
    if not html.is_checked():
        html.click()
        manager.wait_for_streamlit(timeout=timeout, expect_rerun=True)
        manager.open_download_expander("plotly", timeout=timeout)
    with page.expect_download(timeout=timeout) as transfer:
        manager.download_button.click()
    download = transfer.value
    assert download.failure() is None
    document = page.context.new_page()
    try:
        document.set_content(download.path().read_text(encoding="utf-8"), wait_until="load")
        expect(document.get_by_role("region", name="Interactive source dataframe")).to_be_visible(
            timeout=timeout
        )
        with document.expect_download(timeout=timeout) as source_transfer:
            document.get_by_role("button", name="Download source data as CSV", exact=True).click()
        source = source_transfer.value
        assert source.failure() is None
        reader = csv.DictReader(
            StringIO(source.path().read_bytes().decode("utf-8-sig"), newline="")
        )
        rows = list(reader)
        assert reader.fieldnames is not None
        return list(reader.fieldnames), rows
    finally:
        document.close()
