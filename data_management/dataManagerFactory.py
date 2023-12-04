from argumentParser import AnalyzerInfo
from data_management.dataManagerInterface import DataManagerInterface
from data_management.data_manager_R.dataManagerR import DataManagerR
class DataManagerFactory:
    _managerSingleton = None
    @classmethod
    def getDataManager(self, implName: str, params: AnalyzerInfo) -> DataManagerInterface:
        # Singleton
        if self._managerSingleton is None:
            if (implName == "R"):
                self._managerSingleton = DataManagerR(params)
            else:
                raise ValueError("Invalid parser implementation")
        return self._managerSingleton