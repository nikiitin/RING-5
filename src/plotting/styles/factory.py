from .base_ui import BaseStyleUI
from .line_ui import LineStyleUI, ScatterStyleUI
from .bar_ui import BarStyleUI

class StyleUIFactory:
    @staticmethod
    def get_strategy(plot_id: int, plot_type: str) -> BaseStyleUI:
        if "line" in plot_type:
            return LineStyleUI(plot_id, plot_type)
        elif "scatter" in plot_type:
            return ScatterStyleUI(plot_id, plot_type)
        elif "bar" in plot_type:
            return BarStyleUI(plot_id, plot_type)
        else:
            return BaseStyleUI(plot_id, plot_type)
