from stats_analyzer import AnalyzerInfo
from plots.plot_config.plot_config_R.plotConfigurerR import PlotConfigurerR
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
        
        

class PlotConfigurerFactory:
    __impl = None
    @classmethod
    def getConfigurer(self, implName: str, params: AnalyzerInfo) -> PlotConfigurerInterface:
        if self.__impl is None:
            if (implName == "R"):
                self.__impl = PlotConfigurerR(params)
            else:
                raise ValueError("Invalid plot configurer implementation")