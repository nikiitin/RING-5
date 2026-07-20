"""Public API coverage for faceting one plot into ordered comparable panels."""

from __future__ import annotations

import copy

import pandas as pd
import pytest

import ring5

pytestmark = pytest.mark.public_api


def _plot(session: ring5.Session) -> object:
    data = pd.DataFrame(
        {
            "benchmark": ["A", "B", "A", "B", "A", "B"],
            "architecture": ["x86", "x86", "arm", "arm", "riscv", "riscv"],
            "mode": ["fast", "fast", "safe", "safe", "fast", "fast"],
            "ipc": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
        }
    )
    return session.create_plot(
        "bar",
        data=data,
        config={
            "x": "benchmark",
            "y": "ipc",
            "title": "IPC by architecture",
            "xlabel": "Benchmark",
            "ylabel": "IPC",
            "color_palette": "wong",
        },
        name="IPC",
    )


def test_small_multiples_render_both_engines_in_order_without_mutation() -> None:
    # [test->req~ring5.plots.small-multiples~1]
    with ring5.Session() as session:
        plot = _plot(session)
        original_data = plot.processed_data.copy(deep=True)
        original_config = copy.deepcopy(plot.config)
        spec = session.create_small_multiples(
            plot,
            by=["architecture", "mode"],
            columns=2,
            order=[("arm", "safe")],
            labels={("arm", "safe"): "ARM safe"},
            width=960,
            panel_height=280,
            shared_xaxes=True,
            shared_yaxes=True,
        )

        assert isinstance(spec, ring5.SmallMultiplesSpec)
        assert [panel.title for panel in spec.panels] == [
            "ARM safe",
            "architecture: x86 · mode: fast",
            "architecture: riscv · mode: fast",
        ]
        assert (spec.rows, spec.columns, spec.width, spec.height) == (2, 2, 960, 560)

        plotly_figure = session.render_small_multiples(spec, engine="plotly")
        assert len(plotly_figure.data) == 3
        assert [annotation.text for annotation in plotly_figure.layout.annotations[:3]] == [
            "ARM safe",
            "architecture: x86 · mode: fast",
            "architecture: riscv · mode: fast",
        ]
        xaxes = list(plotly_figure.select_xaxes())
        yaxes = [axis for axis in plotly_figure.select_yaxes() if not axis.overlaying]
        assert all(axis.matches == "x" for axis in xaxes[1:])
        assert all(axis.matches == "y" for axis in yaxes[1:])
        assert len({trace.marker.color for trace in plotly_figure.data}) == 1
        assert session.export_bytes(plotly_figure, "html").lstrip().startswith(b"<html")

        direct = ring5.render_small_multiples(session.plots, spec, engine="plotly")
        assert len(direct.data) == 3

        matplotlib_figure = session.render_small_multiples(spec, engine="matplotlib")
        assert [axis.get_title() for axis in matplotlib_figure.axes[:3]] == [
            "ARM safe",
            "architecture: x86 · mode: fast",
            "architecture: riscv · mode: fast",
        ]
        assert (
            matplotlib_figure.axes[0]
            .get_shared_y_axes()
            .joined(matplotlib_figure.axes[0], matplotlib_figure.axes[1])
        )
        assert session.export_bytes(matplotlib_figure, "pdf")[:5] == b"%PDF-"

        pd.testing.assert_frame_equal(plot.processed_data, original_data)
        assert plot.config == original_config
        assert plot.last_traces is None


def test_small_multiples_convenience_and_typed_errors() -> None:
    with ring5.Session() as session:
        plot = _plot(session)
        figure = session.small_multiples(plot, by="architecture", columns=3)
        assert len(figure.data) == 3

        with pytest.raises(ring5.DataValidationError, match="categorical"):
            session.create_small_multiples(plot, by="ipc")
        with pytest.raises(ring5.DataValidationError, match="unknown plot ID"):
            session.create_small_multiples(999, by="architecture")

        spec = session.create_small_multiples(plot, by="architecture")
        session.api.state_manager.set_plots([])
        with pytest.raises(ring5.RenderError, match="unknown plot ID"):
            session.render_small_multiples(spec)


def test_small_multiples_match_dual_axes_by_role_without_cycles() -> None:
    with ring5.Session() as session:
        plot = session.create_plot(
            "dual_axis_bar_dot",
            data=pd.DataFrame(
                {
                    "benchmark": ["A", "B", "A", "B"],
                    "architecture": ["x86", "x86", "arm", "arm"],
                    "cycles": [10.0, 20.0, 30.0, 40.0],
                    "ipc": [1.0, 1.5, 2.0, 2.5],
                }
            ),
            config={"x": "benchmark", "y_bar": "cycles", "y_dot": "ipc"},
        )
        spec = session.create_small_multiples(plot, by="architecture", columns=2)

        figure = session.render_small_multiples(spec)
        axes = list(figure.select_yaxes())

        assert [(axis.plotly_name, axis.matches) for axis in axes] == [
            ("yaxis", None),
            ("yaxis2", None),
            ("yaxis3", "y"),
            ("yaxis4", "y2"),
        ]
