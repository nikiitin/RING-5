from argumentParser import AnalyzerInfo
import src.utils.utils as utils
# NOTE: If you are going to add a new data manager, please
#       make it inherit from DataManagerInterface and add it
#       to the DataManagerFactory
class DataManagerInterface:
    # Constructor
    def __init__(self, params: AnalyzerInfo) -> None:
        json = params.getJson()
        self._csvPath = params.getWorkCsv()
        if utils.checkElementExistNoException(json, "renameStats"):
            self._renamingStats = json["renameStats"]
        else:
            self._renamingStats = None
        if utils.checkElementExistNoException(json, "mixStats"):
            self._mixingStats = json["mixStats"]
        else:
            self._mixingStats = None
        if utils.checkElementExistNoException(json, "reduceSeeds"):
            self._reducingSeeds = utils.jsonToArg(json, "reduceSeeds")
        else:
            self._reducingSeeds = False
        if utils.checkElementExistNoException(json, "removeOutliers"):
            self._removingOutliers = json["removeOutliers"]
            utils.checkElementExists(json, "outlierStat")
            self._outlierStat = utils.jsonToArg(json, "outlierStat")
        else:
            self._removingOutliers = False

    # Private methods, all must be implemented in child classes
    # all of them must be called in __call__ method
    
    # Reduce seeds in case of multiple seeds
    def _reduceSeeds(self) -> None:
        pass
    # Remove outliers for better visualization
    def _removeOutliers(self) -> None:
        pass
    # Rename stats to a more readable name
    def _renameStats(self) -> None:
        pass
    # Mix several stats into a single group
    def _mixStats(self) -> None:
        pass

    # Public generic definition for data management
    def __call__(self) -> None:
        if self._renamingStats is not None:
            self._renameStats()
        if self._mixingStats is not None:
            self._mixStats()
        if self._removingOutliers:
            # Remove outliers only if needed
            self._removeOutliers()
        if self._reducingSeeds:
            self._reduceSeeds()

