from argumentParser import AnalyzerInfo
class DataManagerInterface:
    def __init__(self, params: AnalyzerInfo) -> None:
        pass
    # It is desirable to implement this method
    def _reduceSeeds(self) -> None:
        pass
    # At least manageResults method should be implemented
    def manageResults(self) -> None:
        pass

