from plots.plotInterface import plotInterface
from stats_analyzer import AnalyzerInfo
import utils.utils as utils
import subprocess
class Barplot(plotInterface):
    def __init__(self, info: AnalyzerInfo, plotJson: dict) -> None:
        super().__init__(info, plotJson)
    
    def checkCorrectness(self) -> None:
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

    def __call__(self) -> None:
        super().__call__()
        subprocess.call(self._RScriptCall)
        
        
