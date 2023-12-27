from plots.plotInterface import PlotInterface
from plots.src.plot_impl.barplot.src.barplot import Barplot
from argumentParser import AnalyzerInfo
class PlotFactory:
    # Any plot instance will be unique,
    # do not use singleton here
    @classmethod
    def plot(self, info: AnalyzerInfo, plotJson: dict, plotType: str = "barplot") -> PlotInterface:
        if (plotType == "barplot"):
            return Barplot(info, plotJson)
        else:
            raise ValueError("Invalid plot type")