from plots.plotInterface import PlotInterface
from plots.plot_impl.barplot.barplot import Barplot
class PlotFactory:
    # Any plot instance will be unique,
    # do not use singleton here
    @classmethod
    def plot(self, plotType: str) -> PlotInterface:
        if (plotType == "barplot"):
            return Barplot()
        else:
            raise ValueError("Invalid plot type")