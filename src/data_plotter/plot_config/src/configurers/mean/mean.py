import src.utils.utils as utils
from src.data_plotter.plot_config.src.configurer import Configurer

class MeanConfigurer(Configurer):
    def __init__(self, params: dict) -> None:
        super().__init__(params)
        # TODO: move paths to configuration file
        self._RScriptCall = ["./src/data_plotter/plot_config/src/configurers/mean/mean.R"]
        # Mean specific parameters
        # meanAlgorithm: The algorithm to calculate the mean
        # meanVar: The variable to group when calculating the mean
        # skipMean: Elements to skip from the variable to calculate the mean
        # reducedColumn: The column used to group the mean
        # replacingColumn: The column to replace with the mean label
        self._meanAlgorithm = utils.jsonToArg(self._json, "meanAlgorithm")
        self._meanVars = utils.jsonToArg(self._json, "meanVars")
        self._groupingColumn = utils.jsonToArg(self._json, "groupingColumn")
        self._replacingColumn = utils.jsonToArg(self._json, "replacingColumn")
        self._skipMean = utils.jsonToOptionalArg(self._json, "skipMean")
    
    def _checkPreconditions(self) -> None:
        # Required fields
        utils.checkElementExists(self._json, "meanAlgorithm")
        utils.checkElementExists(self._json, "meanVars")
        utils.checkElementExists(self._json, "groupingColumn")

    def _perform(self, tmpCsv: str) -> None:
        # Append the temporary file
        self._RScriptCall.append(tmpCsv)
        # Append the mean algorithm
        self._RScriptCall.extend(self._meanAlgorithm)
        # Append the variable to calculate the mean
        self._RScriptCall.extend(self._meanVars)
        # Append the variable to reduce
        self._RScriptCall.extend(self._groupingColumn)
        # Append the elements to skip
        self._RScriptCall.extend(self._skipMean)
        # Append the new variable name
        self._RScriptCall.extend(self._replacingColumn)
        super()._perform(tmpCsv)