from argumentParser import AnalyzerInfo
from plots.plot_config.plotConfigurerInterface import PlotConfigurerInterface
from plots.plot_config.plot_config_R.plotConfigurerR import PlotConfigurerR
class PlotConfigurerFactory:
    __impl = None
    @classmethod
    def getConfigurer(self, implName: str, params: AnalyzerInfo) -> PlotConfigurerInterface:
        if self.__impl is None:
            if (implName == "R"):
                self.__impl = PlotConfigurerR(params)
            else:
                raise ValueError("Invalid plot configurer implementation")