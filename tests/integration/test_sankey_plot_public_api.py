"""Public dual-engine Sankey workflow."""

from __future__ import annotations

import matplotlib.figure
import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5

pytestmark = pytest.mark.public_api


def test_public_sankey_renders_validated_labeled_flows_in_both_engines() -> None:
    # [test->req~ring5.plot.sankey~1]
    data = pd.DataFrame(
        {
            "from": ["Input", "Input", "Process", "Process"],
            "to": ["Process", "Loss", "Product", "Product"],
            "amount": [10.0, 2.0, 6.0, 2.0],
            "reason": ["accepted", "rejected", "batch one", "batch two"],
        }
    )
    config = {
        "sankey_source": "from",
        "sankey_target": "to",
        "sankey_value": "amount",
        "sankey_label": "reason",
        "sankey_arrangement": "fixed",
        "sankey_color_mode": "source",
        "sankey_show_link_labels": True,
    }

    with ring5.Session() as session:
        plot = session.create_plot("sankey", data=data, config=config, name="Material flow")
        plotly_figure = session.render(plot, engine="plotly")
        matplotlib_figure = session.render(plot, engine="matplotlib")

        assert len(plotly_figure.data) == 1
        assert isinstance(plotly_figure.data[0], go.Sankey)
        assert list(plotly_figure.data[0].link.value) == [10.0, 2.0, 8.0]
        assert list(plotly_figure.data[0].link.label) == [
            "accepted",
            "rejected",
            "batch one, batch two",
        ]
        assert isinstance(matplotlib_figure, matplotlib.figure.Figure)
        assert len(matplotlib_figure.axes[0].patches) == 7
        assert not matplotlib_figure.axes[0].axison
