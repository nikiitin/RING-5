import subprocess
from argumentParser import AnalyzerInfo
from data_management.dataManagerInterface import DataManagerInterface
import utils.utils as utils

class DataManagerR(DataManagerInterface):
    def __init__(self, params: AnalyzerInfo) -> None:
        json = params.getJson()
        self._csvPath = params.getWorkCsv()
        self._configs = json["configs"]
        self._renamingStats = json["renameStats"]
        self._mixingStats = json["mixStats"]
        self._reducingSeeds = utils.jsonToArg(json, "reduceSeeds")
        self._removingOutliers = utils.jsonToArg(json, "removeOutliers")
        self._outlierStat = utils.jsonToArg(json, "outlierStat")
    
    def _renameStats(self) -> None:
        print("Renaming stats")
        RScriptCall = ["./data_management/data_manager_R/dataRenamer.R"]
        RScriptCall.append(self._csvPath)
        RScriptCall.append(str(len(self._renamingStats)))
        for renameInfo in self._renamingStats:
            RScriptCall.extend(utils.jsonToArg(renameInfo, "oldName"))
            RScriptCall.extend(utils.jsonToArg(renameInfo, "newName"))
        subprocess.call(RScriptCall)

    def _mixStats(self) -> None:
        print("Mixing stats onto groups")
        RScriptCall = ["./data_management/data_manager_R/dataMixer.R"]
        RScriptCall.append(self._csvPath)
        RScriptCall.append(str(len(self._mixingStats)))
        for mix in self._mixingStats:
            RScriptCall.extend(utils.jsonToArg(mix, "groupName"))
            RScriptCall.extend(utils.jsonToArg(mix, "mergingStats"))
        subprocess.call(RScriptCall)
        
    def _reduceSeeds(self) -> None:
        print("Reducing seeds and calculating mean and sd")
        RScriptCall = ["./data_management/data_manager_R/reduceSeeds.R"]
        RScriptCall.append(self._csvPath)
        RScriptCall.append(str(len(self._configs) + 1))
        subprocess.call(RScriptCall)
    
    def _removeOutliers(self) -> None:
        print("Removing outliers")
        RScriptCall = ["./data_management/data_manager_R/removeOutliers.R"]
        RScriptCall.append(self._csvPath)
        RScriptCall.extend(self._outlierStat)
        RScriptCall.append(str(len(self._configs)))
        subprocess.call(RScriptCall)

    def manageResults(self) -> None:
        self._renameStats()
        self._mixStats()
        if self._removingOutliers:
            # Remove outliers only if needed
            self._removeOutliers()
        if self._reducingSeeds:
            self._reduceSeeds()
        