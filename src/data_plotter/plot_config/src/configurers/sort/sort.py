import src.utils.utils as utils
from src.data_plotter.plot_config.src.configurer import Configurer

class SortConfigurer(Configurer):
    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self._json = params
        # TODO: move paths to configuration file
        self._RScriptCall = ["./src/data_plotter/plot_config/src/configurers/sort/sort.R"]
        # Sort specific parameters
        # 
        self._varToSort = utils.jsonToArg(self._json, "varToSort")
        self._order = utils.jsonToArg(self._json, "order")
            
    def _checkPreconditions(self) -> None:
        # Required fields
        utils.checkElementExists(self._json, "varToSort")
        utils.checkElementExists(self._json, "order")

    def _perform(self, tmpCsv: str) -> None:
        # Append the temporary file
        self._RScriptCall.append(tmpCsv)
        # Append the variable to sort
        self._RScriptCall.extend(self._varToSort)
        # Append the order
        self._RScriptCall.extend(self._order)
        super()._perform(tmpCsv)