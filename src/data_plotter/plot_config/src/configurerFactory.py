from src.data_plotter.plot_config.src.configurers.filter import FilterConfigurer
from src.data_plotter.plot_config.src.configurers.mean import MeanConfigurer
from src.data_plotter.plot_config.src.configurers.normalize import NormalizeConfigurer
from src.data_plotter.plot_config.src.configurers.sort import SortConfigurer
from src.data_plotter.plot_config.src.configurers.selector import SelectorConfigurer

class ConfigurerFactory:
    """! @brief Factory class for creating configurer objects.
    """
    @classmethod
    def getConfigurer(cls, implName: str, params: dict):
        """! @brief Get a configurer object.
        @param implName The name of the configurer to create.
        @return The configurer object.
        @note The implementation name must be one of the following:
        - filter
        - mean
        - normalize
        - sort
        @note everytime this method is called a new configurator instance
        is created.
        """
        if (implName == "filter"):
            return FilterConfigurer(params)
        elif (implName == "mean"):
            return MeanConfigurer(params)
        elif (implName == "normalize"):
            return NormalizeConfigurer(params)
        elif (implName == "sort"):
            return SortConfigurer(params)
        elif (implName == "selector"):
            return SelectorConfigurer(params)
        else:
            raise ValueError("Invalid configurer implementation")