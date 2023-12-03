from argumentParser import AnalyzerInfo
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
        self._filterData()
        self._dataMean()
        self._sortData()
        utils.checkElementExists(plotJson, "normalized")
        if utils.getElementValue(plotJson, "normalized"):
            self._normalizeData()