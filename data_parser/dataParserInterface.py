from stats_analyzer import AnalyzerInfo
from data_parser.jsonParser.dataParserJson import DataParserJson
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
            if (implName == "json"):
                self._parserSingleton = DataParserJson(params)
            else:
                raise ValueError("Invalid parser implementation")
        return self._parserSingleton