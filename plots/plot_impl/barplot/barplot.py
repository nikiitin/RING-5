from plots.plotInterface import PlotInterface
from argumentParser import AnalyzerInfo
import utils.utils as utils
import subprocess
class Barplot(PlotInterface):
    def __init__(self, info: AnalyzerInfo, plotJson: dict) -> None:
        super().__init__(info, plotJson)
    
    def _checkCorrectness(self) -> None:
        super()._checkCorrectness()
        # Check plot format info
        utils.checkElementExists(self._plotJson, "legendNames")
        utils.checkElementExists(self._plotJson, "breaks")
        utils.checkElementExists(self._plotJson, "limitTop")
        utils.checkElementExists(self._plotJson, "limitBot")

    def _prepareScriptCall(self) -> None:
        # TODO: description file for locations
        # (Avoid hardcoding paths)
        self._RScriptCall = ["./plots/plot_impl/barplot/barplot.R"]
        self._RScriptCall.extend(self._preparePlotInfo())
        self._RScriptCall.extend(self._preparePlotFormatInfo())

    def _preparePlotInfo(self) -> list:
        plotInfo = super()._preparePlotInfo()
        plotInfo.extend(utils.jsonToArg(self._plotJson, "group"))
    
    def _preparePlotFormatInfo(self) -> list:
        plotFormatInfo = super()._preparePlotFormatInfo()
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "legendNames"))
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "breaks"))
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "limitTop"))
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "limitBot"))
        return plotFormatInfo

    def __call__(self) -> None:
        super().__call__()
        subprocess.call(self._RScriptCall)
        
        
