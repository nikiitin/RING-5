from argumentParser import AnalyzerInfo
from plots.plot_config.plotConfigurerInterface import PlotConfigurerInterface
from plots.plot_config.plot_config_R.plotConfigurerR import PlotConfigurerR
class PlotConfigurerFactory:
    __impl = None
    @classmethod
    def getConfigurer(self, params: AnalyzerInfo, implName: str = "R") -> PlotConfigurerInterface:
        if self.__impl is None:
            if (implName == "R"):
                self.__impl = PlotConfigurerR(params)
            else:
                raise ValueError("Invalid plot configurer implementation")
        return self.__impl