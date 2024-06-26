from argumentParser import AnalyzerInfo
from src.data_plotter.plot_config.plotConfigurerInterface import PlotConfigurerInterface
from src.data_plotter.plot_config.plot_config_R.plotConfigurerR import PlotConfigurerR
import threading
class PlotConfigurerFactory:
    # Lock for thread safety
    # Should not be needed, but just in case
    _lock = threading.Lock()
    # Singleton
    _configurerSingleton = None
    @classmethod
    def getConfigurer(cls, implName: str = "R") -> PlotConfigurerInterface:
        # Only one instance of the plot configurer is allowed
        # TODO: Make it configurable
        if cls._configurerSingleton is None:
            # Thread safety
            with cls._lock:
                # Check again if it is None to avoid race conditions
                if cls._configurerSingleton is None:
                    if (implName == "R"):
                        cls._configurerSingleton = PlotConfigurerR()
                    else:
                        raise ValueError("Invalid plot configurer implementation")
        return cls._configurerSingleton