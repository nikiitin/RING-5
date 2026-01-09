import threading

from src.parsing.params import DataParserParams
from src.parsing.interface import DataParserInterface
from src.parsing.impl.data_parser_perl.dataParserPerl import \
    DataParserPerl


class DataParserFactory:
    # Lock for thread safety
    _lock = threading.Lock()
    # Singleton
    _parserSingleton = None

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance."""
        from src.parsing.config_manager import ConfigurationManager
        ConfigurationManager.reset()
        with cls._lock:
            cls._parserSingleton = None

    @classmethod
    def getDataParser(cls, params: DataParserParams, implName: str = "bash") -> DataParserInterface:
        # Only one instance of the data parser is allowed
        if cls._parserSingleton is None:
            # Thread safety
            with cls._lock:
                # Check again if it is None to avoid race conditions
                if cls._parserSingleton is None:
                    if implName == "perl":
                        cls._parserSingleton = DataParserPerl(params)
                    else:
                        raise ValueError("Invalid parser implementation")
        return cls._parserSingleton
