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
        self._plotJson = plotJson
        # Preconditions
        utils.checkElementExists(plotJson, "stats")
        utils.checkElementExists(plotJson, "dataMod")
        self._jsonDataMod = plotJson["dataMod"]
        # Preconditions
        utils.checkElementExists(self._jsonDataMod, "filter")
        utils.checkElementExists(self._jsonDataMod, "mean")
        utils.checkElementExists(self._jsonDataMod, "sort")
        utils.checkElementExists(self._jsonDataMod, "normalize")
        self._filterJson = self._jsonDataMod["filter"]
        self._meanJson = self._jsonDataMod["mean"]
        self._sortJson = self._jsonDataMod["sort"]
        self._normalizeJson = self._jsonDataMod["normalize"]
        self._tmpCsv = tmpCsv
        utils.checkFileExistsOrException(self._tmpCsv)

        self._filterData()
        self._dataMean()
        self._sortData()
        utils.checkElementExists(self._normalizeJson, "normalized")
        if utils.getElementValue(self._normalizeJson, "normalized"):
            self._normalizeData()