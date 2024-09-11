import src.utils.utils as utils
from src.data_plotter.plot_config.src.configurer import Configurer

class MeanConfigurer(Configurer):
    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self._json = params
        # TODO: move paths to configuration file
        self._RScriptCall = ["./src/data_plotter/plot_config/src/configurers/mean/mean.R"]
        # Mean specific parameters
        # meanAlgorithm: The algorithm to calculate the mean
        # meanVar: The variable to group when calculating the mean
        # skipMean: Elements to skip from the variable to calculate the mean
        self._meanAlgorithm = utils.jsonToArg(self._json, "meanAlgorithm")
        self._meanVar = utils.jsonToArg(self._json, "meanVar")
        self._reducedColumn = utils.jsonToArg(self._json, "reducedColumn")
        if (utils.checkElementExistNoException(self._json, "skipMean")):
            self._skipMean = utils.jsonToArg(self._json, "skipMean")
        else:
            # If skipMean is not defined, specify 0 length
            self._skipMean = [0]
        if (utils.checkElementExistNoException(self._json, "newVarName")):
            self._newVarName = utils.jsonToArg(self._json, "newVarName")
        else:
            # If newVarName is not defined, use the mean algorithm
            self._newVarName = [self._meanAlgorithm[1]]
    
    def _checkPreconditions(self) -> None:
        # Required fields
        utils.checkElementExists(self._json, "meanAlgorithm")
        utils.checkElementExists(self._json, "meanVar")
        utils.checkElementExists(self._json, "reducedColumn")

    def _perform(self, tmpCsv: str) -> None:
        # Append the temporary file
        self._RScriptCall.append(tmpCsv)
        # Append the mean algorithm
        self._RScriptCall.extend(self._meanAlgorithm)
        # Append the variable to calculate the mean
        self._RScriptCall.extend(self._meanVar)
        # Append the variable to reduce
        self._RScriptCall.extend(self._reducedColumn)
        # Append the elements to skip
        self._RScriptCall.extend(self._skipMean)
        # Append the new variable name
        self._RScriptCall.extend(self._newVarName)
        super()._perform(tmpCsv)