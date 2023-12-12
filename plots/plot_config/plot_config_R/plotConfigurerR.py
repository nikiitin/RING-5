from plots.plot_config.plotConfigurerInterface import PlotConfigurerInterface
from argumentParser import AnalyzerInfo
import utils.utils as utils
import subprocess
class PlotConfigurerR(PlotConfigurerInterface):
    def __init__(self, params: AnalyzerInfo):
        super().__init__(params)

    def _filterData(self) -> None:
        print("Filtering data")

        RScriptCall = ["./plots/plot_config/plot_config_R/dataFilter.R"]
        RScriptCall.append(self._tmpCsv)
        RScriptCall.extend(utils.jsonToArg(self._filterJson, "benchmarksFiltered"))
        RScriptCall.extend(utils.jsonToArg(self._filterJson, "configsFiltered"))
        subprocess.call(RScriptCall)

    def _dataMean(self) -> None:
        print("Calculating means")
        print("Algorithm: " + utils.getElementValue(self._meanJson, "meanAlgorithm"))
        RScriptCall = ["./plots/plot_config/plot_config_R/dataMeanCalculator.R"]
        RScriptCall.append(self._tmpCsv)
        RScriptCall.extend(utils.jsonToArg(self._meanJson, "meanAlgorithm"))
        subprocess.call(RScriptCall)

    def _sortData(self) -> None:
        print("Ordering data")
        RScriptCall = ["./plots/plot_config/plot_config_R/ordering.R"]
        RScriptCall.append(self._tmpCsv)
        RScriptCall.extend(utils.jsonToArg(self._meanJson, "meanAlgorithm"))
        RScriptCall.extend(utils.jsonToArg(self._sortJson, "orderingType"))
        RScriptCall.extend(utils.jsonToArg(self._sortJson, "configsOrdering"))
        RScriptCall.extend(utils.jsonToArg(self._sortJson, "benchmarksOrdering"))
        subprocess.call(RScriptCall)

    def _normalizeData(self) -> None:
        print("Normalize data")
        RScriptCall = ["./plots/plot_config/plot_config_R/normalize.R"]
        RScriptCall.append(self._tmpCsv)
        RScriptCall.extend(utils.jsonToArg(self._normalizeJson, "normalized"))
        # TODO: remove this
        RScriptCall.append(str(True))
        RScriptCall.extend(utils.jsonToArg(self._normalizeJson, "normalizer"))
        RScriptCall.extend(utils.jsonToArg(self._plotJson, "stats"))
        subprocess.call(RScriptCall)
    
    def configurePlot(self, plotJson, tmpCsv):
        # Dynamic call to configure on interface class
        # will call all overriden methods
        super().configurePlot(plotJson, tmpCsv)



