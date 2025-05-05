from src.data_parser.src.impl.data_parser_perl.dataParserPerl import DataParserPerl
from src.data_parser.src.dataParserInterface import DataParserInterface
from argumentParser import AnalyzerInfo
import threading
class DataParserFactory:
    # Lock for thread safety
    # Should not be needed, but just in case
    _lock = threading.Lock()
    # Singleton
    _parserSingleton = None
    @classmethod
    def getDataParser(cls, params: AnalyzerInfo, implName: str = "bash") -> DataParserInterface:
        # Only one instance of the data parser is allowed
        if cls._parserSingleton is None:
            # Thread safety
            with cls._lock:
                # Check again if it is None to avoid race conditions
                if cls._parserSingleton is None:
                    if (implName == "perl"):
                        cls._parserSingleton = DataParserPerl(params)
                    else:
                        raise ValueError("Invalid parser implementation")
        return cls._parserSingleton