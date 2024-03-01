from src.plots.src.plot_impl.plotInterface import PlotInterface
from argumentParser import AnalyzerInfo
import src.utils.utils as utils
import subprocess
class LinePlot(PlotInterface):
    def __init__(self, info: AnalyzerInfo, plotJson: dict) -> None:
        super().__init__(info, plotJson)
    
    def _checkCorrectness(self) -> None:
        super()._checkCorrectness()
        # Check plot format info
        utils.checkElementExists(self._styleConfigJson, "legendNames")
        utils.checkElementExists(self._styleConfigJson, "breaks")
        utils.checkElementExists(self._styleConfigJson, "limitTop")
        utils.checkElementExists(self._styleConfigJson, "limitBot")
        utils.checkElementExists(self._styleConfigJson, "xSplitPoints")

        # Check plot info
        utils.checkElementExists(self._plotJson, "conf_z")

    def _prepareScriptCall(self) -> None:
        # TODO: description file for locations
        # (Avoid hardcoding paths)
        self._RScriptCall = ["./src/plots/src/plot_impl/lineplot/src/run.R"]
        self._RScriptCall.extend(self._preparePlotInfo())
        self._RScriptCall.extend(self._preparePlotStyleInfo())

    def _preparePlotInfo(self) -> list:
        plotInfo = super()._preparePlotInfo()
        plotInfo.extend(utils.jsonToArg(self._plotJson, "conf_z"))
        if utils.checkElementExistNoException(self._plotJson, "hiddenBars"):
            plotInfo.extend(utils.jsonToArg(self._plotJson, "hiddenBars"))
        else:
            plotInfo.append("0")
        # FIXME
        # All plots that inherit from barplot are faceteables
        # by a variable
        if utils.checkElementExistNoException(self._plotJson, "facet"):
            facet = self._plotJson["facet"]
            utils.checkElementExists(facet, "facetVar")
            utils.checkElementExists(facet, "facetMappings")
            plotInfo.extend(utils.jsonToArg(facet, "facetMappings"))
            plotInfo.extend(utils.jsonToArg(facet, "facetVar"))
        else:
            plotInfo.append("0")
        return plotInfo
    
    def _preparePlotStyleInfo(self) -> list:
        plotFormatInfo = super()._preparePlotStyleInfo()
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "xSplitPoints"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "legendNames"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "breaks"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "limitTop"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "limitBot"))
        return plotFormatInfo

    def __call__(self) -> None:
        super().__call__()
        subprocess.call(self._RScriptCall)
        
        
