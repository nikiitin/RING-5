"""Native secondary-axis labels and legends through the public rendering owner."""

from typing import cast

import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.figure import Figure

import ring5


def test_dual_axis_sets_secondary_ylabel_and_legend(plot_session: ring5.Session) -> None:
    figure = plot_session.plot(
        "grouped_stacked_bar",
        data=ring5.Table(
            pd.DataFrame(
                {
                    "x": ["a", "b"],
                    "cycles": [3.0, 4.0],
                    "IPC": [1.0, 2.0],
                    "group": ["case", "case"],
                }
            )
        ),
        config={
            "x": "x",
            "y_columns": ["cycles"],
            "group": "group",
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "unified_legend": False,
            "ylabel_right": "IPC",
        },
        engine="matplotlib",
    )
    assert isinstance(figure, Figure)
    twin = figure.axes[1]
    assert twin.get_ylabel() == "IPC"
    legend = twin.get_legend()
    assert legend is not None
    assert [entry.get_text() for entry in legend.get_texts()] == ["IPC"]
    assert [cast(Rectangle, patch).get_height() for patch in twin.patches] == [1.0, 2.0]


def test_dual_axis_no_ylabel_right_leaves_label_blank(plot_session: ring5.Session) -> None:
    figure = plot_session.plot(
        "grouped_stacked_bar",
        data=ring5.Table(
            pd.DataFrame(
                {
                    "x": ["a", "b"],
                    "cycles": [3.0, 4.0],
                    "IPC": [1.0, 2.0],
                    "group": ["case", "case"],
                }
            )
        ),
        config={
            "x": "x",
            "y_columns": ["cycles"],
            "group": "group",
            "y_columns_right": ["IPC"],
            "dual_axis": True,
            "unified_legend": False,
        },
        engine="matplotlib",
    )
    assert isinstance(figure, Figure)
    twin = figure.axes[1]
    assert twin.get_ylabel() == ""
    legend = twin.get_legend()
    assert legend is not None
    assert [entry.get_text() for entry in legend.get_texts()] == ["IPC"]
