import subprocess
from argumentParser import AnalyzerInfo
from data_management.dataManagerInterface import DataManagerInterface
import utils.utils as utils

class DataManagerR(DataManagerInterface):
    def __init__(self, params: AnalyzerInfo) -> None:
        json = params.getJson()
        self._csvPath = params.getWorkCsv()
        self._configs = json["configs"]
        self._renameStats = self._json["renameStats"]
        self._mixStats = self._json["mixStats"]
        self._reduceSeeds = utils.jsonToArg(json, "reduceSeeds")
        self._removeOutliers = utils.jsonToArg(json, "removeOutliers")
        self._outlierStat = utils.jsonToArg(json, "outlierStat")
    
    def _renameStats(self) -> None:
        print("Renaming stats")
        RScriptCall = ["./dataRenamer.R"]
        RScriptCall.append(self._csvPath)
        RScriptCall.append(str(len(self._renameStats)))
        for renameInfo in self._renameStats:
            RScriptCall.append(utils.jsonToArg(renameInfo, "oldName"))
            RScriptCall.append(utils.jsonToArg(renameInfo, "newName"))
        subprocess.call(RScriptCall)

    def _mixStats(self) -> None:
        print("Mixing stats onto groups")
        RScriptCall = ["./dataMixer.R"]
        RScriptCall.append(self._csvPath)
        RScriptCall.append(str(len(self._mixStats)))
        for mix in self._mixStats:
            RScriptCall.append(utils.jsonToArg(mix, "groupName"))
            RScriptCall.append(str(len(utils.jsonToArg(mix, "mergingStats"))))
            RScriptCall.extend(utils.jsonToArg(mix, "mergingStats"))
        subprocess.call(RScriptCall)
        
    def _reduceSeeds(self) -> None:
        print("Reducing seeds and calculating mean and sd")
        RScriptCall = ["./reduceSeeds.R"]
        RScriptCall.append(self._csvPath)
        RScriptCall.append(str(len(self._configs) + 1))
        subprocess.call(RScriptCall)
    
    def _removeOutliers(self) -> None:
        print("Removing outliers")
        RScriptCall = ["./removeOutliers.R"]
        RScriptCall.append(self._csvPath)
        RScriptCall.append(self._outlierStat)
        RScriptCall.append(str(len(self._configs)))
        subprocess.call(RScriptCall)

    def manageResults(self) -> None:
        self._renameStats()
        self._mixStats()
        self._reduceSeeds()
        if self._removeOutliers:
            # Remove outliers only if needed
            self._removeOutliers()