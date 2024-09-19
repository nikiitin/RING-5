import src.utils.utils as utils
from src.data_plotter.plot_config.src.configurer import Configurer

class SelectorConfigurer(Configurer):
    def __init__(self, params: dict) -> None:
        super().__init__(params)
        # TODO: move paths to configuration file
        self._RScriptCall = ["./src/data_plotter/plot_config/src/configurers/selector/selector.R"]
        # Selector specific parameters
        # selectedCols: The columns that will be selected
        self._selectedCols = utils.jsonToArg(self._json, "selectedCols")

    def _checkPreconditions(self) -> None:
        # Required fields
        utils.checkElementExists(self._json, "selectedCols")

    def _perform(self, tmpCsv: str) -> None:
        # Append the temporary file
        self._RScriptCall.append(tmpCsv)
        # Append the variable to normalize
        self._RScriptCall.extend(self._selectedCols)
        super()._perform(tmpCsv)