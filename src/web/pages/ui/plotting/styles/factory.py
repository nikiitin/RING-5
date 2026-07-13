"""Select series-style controls for a plot type."""

from .bar_ui import BarStyleUI
from .base_ui import BaseStyleUI
from .line_ui import LineStyleUI, ScatterStyleUI


class StyleUIFactory:
    """Create the style editor appropriate for a plot type."""

    @staticmethod
    def get_strategy(plot_id: int, plot_type: str) -> BaseStyleUI:
        """Return a style editor for ``plot_type`` and ``plot_id``."""
        if plot_type == "dual_axis_bar_dot":
            return BaseStyleUI(plot_id, plot_type)
        elif "line" in plot_type:
            return LineStyleUI(plot_id, plot_type)
        elif "scatter" in plot_type:
            return ScatterStyleUI(plot_id, plot_type)
        elif "bar" in plot_type:
            return BarStyleUI(plot_id, plot_type)
        else:
            return BaseStyleUI(plot_id, plot_type)
