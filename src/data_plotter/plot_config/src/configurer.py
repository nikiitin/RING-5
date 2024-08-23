import src.utils.utils as utils
from src.data_plotter.plot_config.src.configurerFactory import ConfigurerFactory
from abc import ABC, abstractmethod
import subprocess
class Configurer:
    _configurerComponents: list = []
    @abstractmethod
    def __init__(self, params: dict) -> None:
        """! @brief Configurer constructor
        @param params The parameters to create the configurer.
        @note This method will try to create any subconfigurer
        if there is any. If there is no subconfigurer, it will
        silently continue
        """
        # Preconditions
        self._checkPreconditions()
        # Check for subconfigurers
        if utils.checkElementExistNoException(params, "subconfigurers"):
            subconfigurers = params["subconfigurers"]
        if len(subconfigurers) > 0:
            # Get both, the name of the configurer
            # and its parameters. Both are required to
            # create a new instance
            for name, params in subconfigurers:
                self._addConfigurer(ConfigurerFactory.getConfigurer(name, params))
            # Extend this method to take the parameters
            # in all the configurers
        pass

    def _addConfigurer(self, configurer) -> None:
        """! @brief Add a configurer to the list of configurers.
        @param configurer The configurer to add.
        """
        self._configurerComponents.append(configurer)

    def configurePlot(self, plotJson: dict, tmpCsv: str) -> None:
        """! @brief do plot configuration.
        @param plotJson The json for the plot containing the configuration

        """
        self._perform(tmpCsv)
        for configurer in self.configurerComponents:
            configurer.configurePlot(plotJson, tmpCsv)

    @abstractmethod
    def _checkPreconditions(self) -> None:
        """! @brief Check the preconditions for the configurer."""
        pass
    @abstractmethod
    def _perform(self, tmpCsv: str) -> None:
        """! @brief Perform the specific configuration."""
        subprocess.run(self._RScriptCall)
        pass