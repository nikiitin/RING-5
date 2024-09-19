from abc import ABC, abstractmethod
import subprocess
import enum

class ConfigurerType(enum.Enum):
    SELECTOR = "selector"
    FILTER = "filter"
    SORT = "sort"
    NORMALIZER = "normalize"
    MEAN = "mean"

class Configurer:
    """! @brief Abstract class for configuring plots.
    """
    @abstractmethod
    def __init__(self, params: dict) -> None:
        """! @brief Configurer constructor
        @param params The parameters to create the configurer.
        @note This method will try to create any subconfigurer
        if there is any. If there is no subconfigurer, it will
        silently continue
        """
        self._configurerComponents: list = []
        self._json = params
        # Preconditions
        self._checkPreconditions()
        pass

    @abstractmethod
    def createConfigurer(self, params: dict) -> None:
        """! @brief Create a configurer.
        @param params The parameters to create the configurer.
        """
        pass

    def addConfigurer(self, configurer) -> None:
        """! @brief Add a configurer to the list of configurers.
        @param configurer The configurer to add.
        """
        self._configurerComponents.append(configurer)

    def configurePlot(self, tmpCsv: str) -> None:
        """! @brief do plot configuration.
        @param plotJson The json for the plot containing the configuration

        """
        self._perform(tmpCsv)
        for configurer in self._configurerComponents:
            configurer.configurePlot(tmpCsv)

    @abstractmethod
    def _checkPreconditions(self) -> None:
        """! @brief Check the preconditions for the configurer."""
        pass
    @abstractmethod
    def _perform(self, tmpCsv: str) -> None:
        """! @brief Perform the specific configuration."""
        subprocess.run(self._RScriptCall)
        pass