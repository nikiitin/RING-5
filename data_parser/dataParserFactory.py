from data_parser.data_parser_bash.dataParserBash import DataParserBash
from data_parser.dataParserInterface import DataParserInterface
from argumentParser import AnalyzerInfo
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