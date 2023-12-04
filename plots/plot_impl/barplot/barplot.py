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
        self._preparePrefixScriptCall()
        self._RScriptCall.extend(self._prefixScriptCall)
        self._RScriptCall.extend(utils.jsonToArg(self._plotJson, "stats"))
        self._prepareSufixScriptCall()
        self._RScriptCall.extend(self._sufixScriptCall)

    def _preparePrefixScriptCall(self) -> None:
        super()._preparePrefixScriptCall()
    
    def _prepareSufixScriptCall(self) -> None:
        super()._prepareSufixScriptCall()

    def __call__(self) -> None:
        super().__call__()
        subprocess.call(self._RScriptCall)
        
        
