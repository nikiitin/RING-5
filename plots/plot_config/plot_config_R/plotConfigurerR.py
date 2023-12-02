from plotConfigurerInterface import PlotConfigurerInterface
from stats_analyzer import AnalyzerInfo
import utils.utils as utils
import subprocess
class PlotConfigurerR(PlotConfigurerInterface):
    def __init__(self, params: AnalyzerInfo):
        super().__init__(params)

    def _filterData(self) -> None:
        print("Filtering data")

        RScriptCall = ["./dataFilter.R"]
        RScriptCall.append(self._tmpCsv)
        RScriptCall.extend(utils.jsonToArg(self._filterJson, "benchmarksFiltered"))
        RScriptCall.extend(utils.jsonToArg(self._filterJson, "configsFiltered"))
        subprocess.call(RScriptCall)

    def _dataMean(self) -> None:
        print("Calculating means")
        print("Algorithm: " + utils.getElementValue(self._meanJson, "meanAlgorithm"))
        RScriptCall = ["./dataMeanCalculator.R"]
        RScriptCall.append(self._tmpCsv)
        RScriptCall.append(str(utils.jsonToArg(self._params.getJson(), "configs")[0]))
        RScriptCall.extend(utils.jsonToArg(self._meanJson, "meanAlgorithm"))
        subprocess.call(RScriptCall)

    def _sortData(self) -> None:
        print("Ordering data")
        RScriptCall = ["./ordering.R"]
        RScriptCall.append(self._tmpCsv)
        RScriptCall.extend(utils.jsonToArg(self._meanJson, "meanAlgorithm"))
        RScriptCall.extend(utils.jsonToArg(self._sortJson, "orderingType"))
        RScriptCall.extend(utils.jsonToArg(self._sortJson, "configsOrdering"))
        RScriptCall.extend(utils.jsonToArg(self._sortJson, "benchmarksOrdering"))
        subprocess.call(RScriptCall)

    def _normalizeData(self) -> None:
        print("Normalize data")
        RScriptCall = ["./normalize.R"]
        RScriptCall.append(self._tmpCsv)
        RScriptCall.extend(utils.jsonToArg(self._normalizeJson, "normalized"))
        # TODO: remove this
        RScriptCall.append(str(True))
        RScriptCall.append(utils.jsonToArg(self._normalizeJson, "normalizer"))
        RScriptCall.extend(utils.jsonToArg(self._jsonDataMod, "stats"))
        subprocess.call(RScriptCall)

    def configurePlot(self, plotJson, tmpCsv):
        self._plotJson = plotJson
        # Preconditions
        utils.checkElementExists(plotJson, "stats")
        utils.checkElementExists(plotJson, "dataMod")
        self._jsonDataMod = plotJson["dataMod"]
        # Preconditions
        utils.checkElementExists(plotJson, "filter")
        utils.checkElementExists(plotJson, "mean")
        utils.checkElementExists(plotJson, "sort")
        utils.checkElementExists(plotJson, "normalize")
        self._filterJson = plotJson["filter"]
        self._meanJson = plotJson["mean"]
        self._sortJson = plotJson["sort"]
        self._normalizeJson = plotJson["normalize"]
        self._tmpCsv = tmpCsv
        utils.checkFileExistsOrException(self._tmpCsv)
        # Dynamic call to configure on interface class
        # will call all overriden methods
        super().configurePlot()



