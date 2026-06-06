"""Matplotlib dual-axis parity (M3): the twin axis gets a Y-title + legend."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.core.services.visualization.config_resolver import resolve_config  # noqa: E402
from src.web.components.common.chart_display import ChartDisplayComponent  # noqa: E402
from src.web.rendering.config_builder import ConfigSpecBuilder  # noqa: E402


def _spec():
    return resolve_config(ConfigSpecBuilder.from_config({}, "grouped_stacked_bar"))


def test_dual_axis_sets_secondary_ylabel_and_legend() -> None:
    fig, ax = plt.subplots()
    twin = ax.twinx()
    twin.plot([0, 1], [1.0, 2.0], label="IPC")

    ChartDisplayComponent._apply_matplotlib_dual_axis(twin, {"ylabel_right": "IPC"}, _spec())

    assert twin.get_ylabel() == "IPC"
    assert twin.get_legend() is not None
    legend_texts = [t.get_text() for t in twin.get_legend().get_texts()]
    assert "IPC" in legend_texts
    plt.close(fig)


def test_dual_axis_no_ylabel_right_leaves_label_blank() -> None:
    fig, ax = plt.subplots()
    twin = ax.twinx()
    twin.plot([0, 1], [1.0, 2.0], label="IPC")

    ChartDisplayComponent._apply_matplotlib_dual_axis(twin, {}, _spec())

    assert twin.get_ylabel() == ""
    # Right-axis series is still legendable even without a secondary title.
    assert twin.get_legend() is not None
    plt.close(fig)
