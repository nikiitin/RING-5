"""Browser actions for figure exchange, dashboard selection and source-row inspection."""

from __future__ import annotations

import csv
from io import StringIO

from playwright.sync_api import Locator, expect

from tests.visual.pages.base_page import BasePage
from tests.visual.pages.data_managers_page import DataManagersPage


class PlotInteractionsPage(BasePage):
    """Drive ordinary browser controls without modifying application state."""

    @property
    def dashboard(self) -> Locator:
        """The composer containing its controls, preview and complete export."""
        return self.page.get_by_test_id("stExpander").filter(has_text="Multi-panel dashboard")

    def open_dashboard(self) -> None:
        """Open the composer without collapsing an already open editor."""
        button = self.dashboard.get_by_role("button", name="Build dashboard")
        if not button.is_visible():
            self.dashboard.locator("summary").first.click()
        expect(button).to_be_visible(timeout=self.RENDER_TIMEOUT)

    def download_workspace_rows(self) -> list[dict[str, str]]:
        """Download the complete active table through Data Managers."""
        manager = DataManagersPage(self.page)
        manager.navigate()
        downloaded = manager.download_current_view()
        return list(csv.DictReader(StringIO(downloaded.path().read_text(encoding="utf-8-sig"))))

    def download_drill_down_rows(self) -> list[dict[str, str]]:
        """Read the displayed source-row table through its CSV toolbar action."""
        table = self.page.get_by_test_id("stDataFrame").last
        expect(table).to_be_visible(timeout=self.RENDER_TIMEOUT)
        table.hover()
        # Exercise the browser download path rather than a native OS save dialog.
        self.page.evaluate(
            "Object.defineProperty(window, 'showSaveFilePicker', "
            "{configurable: true, value: undefined})"
        )
        download = table.get_by_role("button", name="Download as CSV", exact=True)
        expect(download).to_be_visible(timeout=self.RENDER_TIMEOUT)
        with self.page.expect_download(timeout=self.RENDER_TIMEOUT) as downloaded:
            download.press("Enter")
        text = downloaded.value.path().read_text(encoding="utf-8-sig")
        return list(csv.DictReader(StringIO(text)))

    def click_bar_point(self, *, trace: int, point: int) -> None:
        """Click inside a positive bar's value edge through Plotly's pointer surface."""
        frame = self.page.locator('iframe[title$="interactive_plotly"]').first.content_frame
        bar = frame.locator(".barlayer .trace").nth(trace).locator(".point path").nth(point)
        bar.scroll_into_view_if_needed()
        bounds = bar.bounding_box()
        assert (
            bounds is not None and bounds["width"] > 0 and bounds["height"] > 0
        ), "The selected bar must have a visible, nonzero pointer target"
        x = bounds["x"] + bounds["width"] / 2
        y = bounds["y"] + min(8, bounds["height"] / 10)
        # Plotly's transparent drag layer intentionally owns native mouse events.
        self.page.mouse.move(x, y)
        frame.locator("#myDiv").evaluate(
            """(graph, expected) => new Promise((resolve, reject) => {
                const deadline = Date.now() + expected.timeout;
                const check = () => {
                    const points = graph._hoverdata;
                    const hovered = points?.length === 1 ? points[0] : null;
                    const trace = graph._fullData?.[expected.trace];
                    if (hovered && trace && hovered.curveNumber === expected.trace &&
                        hovered.pointNumber === expected.point &&
                        hovered.fullData?.uid === trace.uid) return resolve(true);
                    if (Date.now() >= deadline) {
                        const describe = point => ({
                            curveNumber: point.curveNumber ?? null,
                            pointNumber: Array.isArray(point.pointNumber)
                                ? point.pointNumber.slice(0, 4) : point.pointNumber ?? null,
                            pointIndex: point.pointIndex ?? null,
                            uid: String(point.fullData?.uid ?? '').slice(0, 64),
                            name: String(point.fullData?.name ?? '').slice(0, 80),
                        });
                        const diagnostic = {
                            hovermode: graph._fullLayout?.hovermode ?? null,
                            captureClick: graph._streamlit_capture_click ?? null,
                            requested: {
                                curveNumber: expected.trace, pointNumber: expected.point,
                                uid: String(trace?.uid ?? '').slice(0, 64),
                                name: String(trace?.name ?? '').slice(0, 80),
                            },
                            hoverCount: points?.length ?? 0,
                            hovered: Array.isArray(points) ? points.slice(0, 4).map(describe) : [],
                            pointer: {x: expected.x, y: expected.y},
                        };
                        return reject(new Error(
                            'Native bar hover did not identify the requested point: ' +
                            JSON.stringify(diagnostic)));
                    }
                    requestAnimationFrame(check);
                };
                check();
            })""",
            {"trace": trace, "point": point, "timeout": self.RENDER_TIMEOUT, "x": x, "y": y},
        )
        self.page.mouse.click(x, y)
        self.wait_for_streamlit(expect_rerun=True)

    def click_heatmap_cell(self, *, trace: int, row: int, column: int) -> None:
        """Click a rendered heatmap cell using its actual native axis coordinates."""
        frame = self.page.locator('iframe[title$="interactive_plotly"]').first.content_frame
        graph = frame.locator("#myDiv")
        position = graph.evaluate(
            """(graph, location) => {
                const trace = graph._fullData[location.trace];
                const axis = name => name[0] + 'axis' + name.slice(1);
                const xaxis = graph._fullLayout[axis(trace.xaxis)];
                const yaxis = graph._fullLayout[axis(trace.yaxis)];
                return {
                    x: xaxis._offset + xaxis.d2p(trace.x[location.column]),
                    y: yaxis._offset + yaxis.d2p(trace.y[location.row]),
                };
            }""",
            {"trace": trace, "row": row, "column": column},
        )
        graph.click(position=position)
        self.wait_for_streamlit(expect_rerun=True)

    def select_dashboard_category(self, category: str) -> None:
        """Drag a real box around one category in the first dashboard panel."""
        frame = self.dashboard.locator('iframe[title$="interactive_plotly"]').content_frame
        graph = frame.locator("#myDiv")
        graph.scroll_into_view_if_needed()
        rectangle = graph.evaluate(
            """(graph, category) => {
                const axis = graph._fullLayout.xaxis;
                const yaxis = graph._fullLayout.yaxis;
                const center = axis._offset + axis.d2p(category);
                const halfWidth = Math.abs(axis.l2p(1) - axis.l2p(0)) / 3;
                return {
                    left: center - halfWidth,
                    right: center + halfWidth,
                    top: yaxis._offset + 2,
                    bottom: yaxis._offset + yaxis._length - 2,
                };
            }""",
            category,
        )
        bounds = graph.bounding_box()
        assert bounds is not None, "The dashboard graph must have a visible pointer target"
        self.page.mouse.move(bounds["x"] + rectangle["left"], bounds["y"] + rectangle["top"])
        self.page.mouse.down()
        self.page.mouse.move(
            bounds["x"] + rectangle["right"], bounds["y"] + rectangle["bottom"], steps=12
        )
        self.page.mouse.up()
        self.wait_for_streamlit(expect_rerun=True)

    def wait_for_dashboard_selection(
        self, category: str, *, mode: str, selected: bool, point_count: int
    ) -> None:
        """Wait for the native panels to reflect a real selection or clear action."""
        graph = self.dashboard.locator('iframe[title$="interactive_plotly"]').content_frame.locator(
            "#myDiv"
        )
        graph.evaluate(
            """(graph, expected) => new Promise((resolve, reject) => {
                const deadline = Date.now() + expected.timeout;
                const ready = () => {
                    const traces = graph._fullData;
                    if (!traces || traces.length !== 2 || !graph.calcdata) return false;
                    return traces.every((trace, index) => {
                        if (graph.calcdata[index].length !== expected.pointCount) return false;
                        const points = Array.from(trace.selectedpoints ?? []);
                        if (!expected.selected) return points.length === 0;
                        if (expected.mode === 'filter') {
                            return Array.from(trace.x).every(value => value === expected.category);
                        }
                        const wanted = Array.from(trace.x).flatMap((value, index) =>
                            value === expected.category ? [index] : []);
                        return points.length === wanted.length &&
                            points.every((value, index) => value === wanted[index]);
                    });
                };
                const check = () => {
                    if (ready()) return resolve(true);
                    if (Date.now() >= deadline) return reject(
                        new Error('Native dashboard did not apply the selection'));
                    requestAnimationFrame(check);
                };
                check();
            })""",
            {
                "category": category,
                "mode": mode,
                "selected": selected,
                "pointCount": point_count,
                "timeout": self.RENDER_TIMEOUT,
            },
        )
