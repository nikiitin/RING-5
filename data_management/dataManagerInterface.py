from stats_analyzer import AnalyzerInfo
from data_management.csv_data_manager.dataManagerCsv import DataManagerCsv
class DataManagerInterface:
    def __init__(self, params: AnalyzerInfo) -> None:
        pass
    # It is desirable to implement this method
    def _reduceSeeds(self) -> None:
        pass
    # At least manageResults method should be implemented
    def manageResults(self) -> None:
        pass

class DataParserFactory:
    _managerSingleton = None
    @classmethod
    def getDataManager(self, implName: str, params: AnalyzerInfo) -> DataManagerInterface:
        # Singleton
        if self._managerSingleton is None:
            if (implName == "csv"):
                self._managerSingleton = DataManagerCsv(params)
            else:
                raise ValueError("Invalid parser implementation")
        return self._managerSingleton