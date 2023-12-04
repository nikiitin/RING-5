from argumentParser import AnalyzerInfo
class DataParserInterface:
    def __init__(self, params: AnalyzerInfo) -> None:
        pass
    # At least runParse method should be implemented
    def runParse(self) -> None:
        pass