from argumentParser import AnalyzerInfo
from plots.configurationManager import ConfigurationManager
import utils.utils as utils
class PlotConfigurerInterface:
    _params: AnalyzerInfo = None
    def __init__(self, params: AnalyzerInfo):
        self._params = params
    def _filterData(self) -> None:
        pass
    def _dataMean(self) -> None:
        pass
    def _sortData(self) -> None:
        pass
    def _normalizeData(self) -> None:
        pass
    def configurePlot(self, plotJson: dict, tmpCsv: str) -> None:
        self._plotJson = plotJson
        # Preconditions
        utils.checkElementExists(plotJson, "dataConfig")
        self._jsonDataConfig = ConfigurationManager.getPlotConfiguration(plotJson)
        self._tmpCsv = tmpCsv
        utils.checkFileExistsOrException(self._tmpCsv)
        # Let the user know what is going on
        print("Configuring plot data")
        # Inheriting classes have to implement
        # the way to perform the actions
        # Actions
        pass