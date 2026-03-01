"""Bar plot configuration component."""

import pandas as pd

from src.web.components.plotting.config.base_plot_config import render_common_with_color
from src.web.models.plot_models import PlotConfig


def render(
    data: pd.DataFrame,
    saved_config: PlotConfig,
    plot_id: int,
) -> PlotConfig:
    """Render configuration UI for a simple bar plot.

    Uses the shared X / Y / title / colour-by layout.

    Args:
        data: DataFrame to plot.
        saved_config: Previously saved configuration.
        plot_id: Unique plot identifier for widget keys.

    Returns:
        Configuration dictionary.
    """
    return render_common_with_color(data, saved_config, plot_id)
