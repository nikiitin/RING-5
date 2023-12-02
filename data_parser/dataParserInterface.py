from stats_analyzer import AnalyzerInfo
from data_parser.data_parser_bash.dataParserBash import DataParserBash
class DataParserInterface:
    def __init__(self, params: AnalyzerInfo) -> None:
        pass
    # At least runParse method should be implemented
    def runParse(self) -> None:
        pass

class DataParserFactory:
    _parserSingleton = None
    @classmethod
    def getDataParser(self, implName: str, params: AnalyzerInfo) -> DataParserInterface:
        # Singleton
        if self._parserSingleton is None:
            if (implName == "bash"):
                self._parserSingleton = DataParserBash(params)
            else:
                raise ValueError("Invalid parser implementation")
        return self._parserSingleton