from argumentParser import AnalyzerInfo
import utils.utils as utils
# NOTE: If you are going to add a new data manager, please
#       make it inherit from DataManagerInterface and add it
#       to the DataManagerFactory
class DataManagerInterface:
    # Constructor
    def __init__(self, params: AnalyzerInfo) -> None:
        json = params.getJson()
        self._csvPath = params.getWorkCsv()
        self._configs = json["configs"]
        self._renamingStats = json["renameStats"]
        self._mixingStats = json["mixStats"]
        self._reducingSeeds = utils.jsonToArg(json, "reduceSeeds")
        self._removingOutliers = utils.jsonToArg(json, "removeOutliers")
        self._outlierStat = utils.jsonToArg(json, "outlierStat")

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
        self._renameStats()
        self._mixStats()
        if self._removingOutliers:
            # Remove outliers only if needed
            self._removeOutliers()
        if self._reducingSeeds:
            self._reduceSeeds()

