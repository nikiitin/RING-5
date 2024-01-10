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
        # Preconditions
        utils.checkElementExists(plotJson, "dataConfig")
        utils.checkFileExistsOrException(tmpCsv)
        # Let the user know what is going on
        print("Configuring plot data")
        self._command = ["./plots/plot_config/plot_config_R/dataConfigurer.R"]
        # Inheriting classes have to implement
        # the way to perform the actions
        # Actions
        pass