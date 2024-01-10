from plots.plotInterface import PlotInterface
from plots.src.plot_impl.barplot.src.barplot import Barplot
from plots.src.plot_impl.stackedbarplot.src.stackedBarplot import StackedBarplot
from plots.src.plot_impl.percentagestackedbarplot.src.percentageStackedBarplot import PercentageStackedBarplot
from argumentParser import AnalyzerInfo
class PlotFactory:
    # Any plot instance will be unique,
    # do not use singleton here
    @staticmethod
    def plot(info: AnalyzerInfo, plotJson: dict, plotType: str = "barplot") -> PlotInterface:
        if (plotType == "barplot"):
            return Barplot(info, plotJson)
        elif (plotType == "stackedBarplot"):
            return StackedBarplot(info, plotJson)
        elif (plotType == "percentageStackedBarplot"):
            return PercentageStackedBarplot(info, plotJson)
        else:
            raise ValueError("Invalid plot type")