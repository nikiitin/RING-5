import src.utils.utils as utils
from src.data_plotter.plot_config.src.configurer import Configurer

class NormalizeConfigurer(Configurer):
    def __init__(self, params: dict) -> None:
        super().__init__(params)
        # TODO: move paths to configuration file
        self._RScriptCall = ["./src/data_plotter/plot_config/src/configurers/normalize/normalize.R"]
        # Normalize specific parameters
        # normalizeVar: The categoric variable to apply normalization
        # normalizeValue: The value from categoric variable to normalize
        # data with
        # groupBy: The categoric variables that group the statistics
        # normalizeStats: If there are several statistics, choose the
        # ones to use to normalize. "all" value add all statistics together
        # to apply normalization
        self._normalizeVars = utils.getElementValue(self._json, "normalizeVars")
        self._groupBy = utils.jsonToArg(self._json, "groupBy")
        self._normalizeStats = utils.jsonToOptionalArg(self._json, "normalizeStats")
        self._skipsNormalize = utils.jsonToOptionalArg(self._json, "skipsNormalize")

    def _checkPreconditions(self) -> None:
        # Required fields
        utils.checkElementExists(self._json, "normalizeVars")
        utils.checkElementExists(self._json, "groupBy")

    def _perform(self, tmpCsv: str) -> None:
        # Append the temporary file
        self._RScriptCall.append(tmpCsv)
        # Append the variables to normalize
        self._RScriptCall.append(str(len(self._normalizeVars)))
        for var in self._normalizeVars:
            for k, v in var.items():
                self._RScriptCall.append(k)
                self._RScriptCall.append(v)
        # Append the grouping variables
        self._RScriptCall.extend(self._groupBy)
        # Append the statistics to normalize
        self._RScriptCall.extend(self._normalizeStats)
        # Append the statistics to skip in normalization
        self._RScriptCall.extend(self._skipsNormalize)
        print(self._RScriptCall)
        super()._perform(tmpCsv)