from argumentParser import AnalyzerInfo
from src.data_management.src.dataManagerInterface import DataManagerInterface
from src.data_management.src.impl.data_manager_R.dataManagerR import DataManagerR
import threading
class DataManagerFactory:
    # Lock for thread safety
    # Should not be needed, but just in case
    _lock = threading.Lock()
    # Singleton
    _managerSingleton = None
    @classmethod
    def getDataManager(self, implName: str, params: AnalyzerInfo) -> DataManagerInterface:
        # Only one instance of the data manager is allowed
        # TODO: Make it configurable
        if self._managerSingleton is None:
            # Thread safety
            with self._lock:
                # Check again if it is None
                # This is needed for race conditions
                if self._managerSingleton is None:
                    if (implName == "R"):
                        self._managerSingleton = DataManagerR(params)
                    else:
                        raise ValueError("Invalid parser implementation")
        return self._managerSingleton