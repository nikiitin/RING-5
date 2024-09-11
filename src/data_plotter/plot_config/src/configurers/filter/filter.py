import src.utils.utils as utils
from src.data_plotter.plot_config.src.configurer import Configurer

class FilterConfigurer(Configurer):
    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self._json = params
        # TODO: move paths to configuration file
        self._RScriptCall = ["./src/data_plotter/plot_config/src/configurers/filter/filter.R"]
        # Filter specific parameters
        # varToFilter: The variable to filter
        # values: The values that will be removed from the data
        self._varToFilter = utils.jsonToArg(self._json, "varToFilter")
        self._valuesToFilter = utils.jsonToArg(self._json, "values")
    
    def _checkPreconditions(self) -> None:
        # Required fields
        utils.checkElementExists(self._json, "varToFilter")
        utils.checkElementExists(self._json, "values")

    def _perform(self, tmpCsv: str) -> None:
        # Append the temporary file
        self._RScriptCall.append(tmpCsv)
        # Append the variable to filter
        self._RScriptCall.extend(self._varToFilter)
        # Append the values to filter
        self._RScriptCall.extend(self._valuesToFilter)
        super()._perform(tmpCsv)