from src.plots.src.plot_config.plotConfigurerInterface import PlotConfigurerInterface
from src.plots.src.configurationManager import ConfigurationManager
from argumentParser import AnalyzerInfo
import src.utils.utils as utils
import subprocess
class PlotConfigurerR(PlotConfigurerInterface):
    def __init__(self, params: AnalyzerInfo):
        super().__init__(params)
        
    
    # Private method to calculate the number of actions
    # to be performed on the data. Used as parameter
    # for dataConfigurer.R
    def _addActionsToCommand(self, jsonDataConfig: dict) -> None:
        nActions = 0
        actions = []
        # Actions
        # Should be in the same order as in dataConfigurer.R
        if utils.checkElementExistNoException(jsonDataConfig, "filter"):
            nActions += 1
            actions.append("Filter")
        if utils.checkElementExistNoException(jsonDataConfig, "mean"):
            nActions += 1
            actions.append("Mean")
        if utils.checkElementExistNoException(jsonDataConfig, "sort"):
            nActions += 1
            actions.append("Sort")
        if utils.checkElementExistNoException(jsonDataConfig, "normalize"):
            nActions += 1
            actions.append("Normalize")
        self._command.append(str(nActions))
        self._command.extend(actions)

    # This implementation builds the command for filtering
    # data action. This command can be built several times
    # depending on the number of filters defined in the
    # plot configuration.
    def _filterData(self) -> None:
        print("Filtering data")
        RScriptCall = []
        # Append the number of filters
        RScriptCall.append(str(len(self._filterJson)))
        for filt in self._filterJson:
            # Preconditions
            # If filter is defined, varToFilter and values
            # must be defined too
            utils.checkElementExists(filt, "varToFilter")
            utils.checkElementExists(filt, "values")
            varToFilter = utils.jsonToArg(filt, "varToFilter")
            varToFilterValues = utils.jsonToArg(filt, "values")
            print("Will filter: " + str(varToFilter) +
                "; values:[" + str(varToFilterValues[1:]) + "]")
            RScriptCall.extend(varToFilter)
            RScriptCall.extend(varToFilterValues)
        self._command.extend(RScriptCall)

    def _dataMean(self) -> None:
        RScriptCall = []
        # Preconditions
        # If mean is defined, meanAlgorithm must be defined too
        utils.checkElementExists(self._meanJson, "meanAlgorithm")
        RScriptCall.extend(utils.jsonToArg(self._meanJson, "meanAlgorithm"))
        self._command.extend(RScriptCall)

    def _sortData(self) -> None:
        RScriptCall = []
        # Append the number of sorts
        RScriptCall.append(str(len(self._sortJson)))
        for sort in self._sortJson:
            # Preconditions
            # If sort is defined, varToSort and values must be defined too
            utils.checkElementExists(sort, "varToSort")
            utils.checkElementExists(sort, "order")
            varToSort = utils.jsonToArg(sort, "varToSort")
            order = utils.jsonToArg(sort, "order")
            print("Will sort: " + str(varToSort) + "; order: " + str(order))
            RScriptCall.extend(varToSort)
            RScriptCall.extend(order)
        self._command.extend(RScriptCall)

    def _normalizeData(self) -> None:
        RScriptCall = []
        # Preconditions
        # If normalize is defined, normalizerIndex must be defined too
        utils.checkElementExists(self._normalizeJson, "normalizerIndex")
        RScriptCall.extend(utils.jsonToArg(self._normalizeJson, "normalizerIndex"))
        self._command.extend(RScriptCall)
    
    def configurePlot(self, plotJson, tmpCsv):
        # Dynamic call to configure on interface class
        super().configurePlot(plotJson, tmpCsv)
        self._command = ["./src/plots/src/plot_config/plot_config_R/dataConfigurer.R"]
        self._command.append(tmpCsv)
        jsonDataConfig = ConfigurationManager.getPlotConfiguration(plotJson)
        self._addActionsToCommand(jsonDataConfig)
        # Preconditions
        utils.checkElementExists(plotJson, "y")
        utils.checkElementExists(plotJson, "x")
        utils.checkElementExists(plotJson, "conf_z")
        self._command.extend(utils.jsonToArg(plotJson, "y"))
        self._command.extend(utils.jsonToArg(plotJson, "x"))
        self._command.extend(utils.jsonToArg(plotJson, "conf_z"))
        
        if utils.checkElementExistNoException(jsonDataConfig, "filter"):
            self._filterJson = jsonDataConfig["filter"]
            self._filterData()
        if utils.checkElementExistNoException(jsonDataConfig, "mean"):
            self._meanJson = jsonDataConfig["mean"]
            self._dataMean()
        if utils.checkElementExistNoException(jsonDataConfig, "sort"):
            self._sortJson = jsonDataConfig["sort"]
            self._sortData()
        if utils.checkElementExistNoException(jsonDataConfig, "normalize"):
            self._normalizeJson = jsonDataConfig["normalize"]
            self._normalizeData()
        # Call the R script
        # print("Calling R script")
        # print(" ".join(self._command))
        # print(self._command)
        subprocess.call(self._command)
        
        
        




