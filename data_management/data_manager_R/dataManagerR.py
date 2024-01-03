import subprocess
from argumentParser import AnalyzerInfo
from data_management.dataManagerInterface import DataManagerInterface
import utils.utils as utils

class DataManagerR(DataManagerInterface):
    def __init__(self, params: AnalyzerInfo) -> None:
        super().__init__(params)
        # Add here any pre-processing that needs to be done
        # or any other initialization
    
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
        subprocess.call(RScriptCall)
    
    def _removeOutliers(self) -> None:
        print("Removing outliers")
        RScriptCall = ["./data_management/data_manager_R/removeOutliers.R"]
        RScriptCall.append(self._csvPath)
        RScriptCall.extend(self._outlierStat)
        subprocess.call(RScriptCall)

    def _assignConfKeys(self) -> None:
        print("Assigning configuration keys")
        RScriptCall = ["./data_management/data_manager_R/assignConfKeys.R"]
        RScriptCall.append(self._csvPath)
        subprocess.call(RScriptCall)

    def __call__(self) -> None:
        # Pre-processing...
        # Add configuration keys to csv
        self._assignConfKeys()
        super().__call__()
        # Add here any post-processing that needs to be done
        