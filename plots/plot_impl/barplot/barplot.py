from plots.plotInterface import PlotInterface
from argumentParser import AnalyzerInfo
import utils.utils as utils
import subprocess
class Barplot(PlotInterface):
    def __init__(self, info: AnalyzerInfo, plotJson: dict) -> None:
        super().__init__(info, plotJson)
    
    def _checkCorrectness(self) -> None:
        super()._checkCorrectness()
        utils.checkElementExists(self._plotJson, "stats")

    def _prepareScriptCall(self) -> None:
        # TODO: description file for locations
        # (Avoid hardcoding paths)
        self._RScriptCall = ["./plots/plot_impl/barplot/barplot.R"]
        self._RScriptCall.extend(self._preparePlotInfo())
        self._RScriptCall.extend(self._preparePlotFormatInfo())

    def _preparePlotInfo(self) -> list:
        return super()._preparePlotInfo()
    
    def _preparePlotFormatInfo(self) -> list:
        return super()._preparePlotFormatInfo()

    def __call__(self) -> None:
        super().__call__()
        subprocess.call(self._RScriptCall)
        
        
