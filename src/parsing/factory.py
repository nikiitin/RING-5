import threading
from typing import Dict, Type

from src.parsing.impl.data_parser_perl.dataParserPerl import DataParserPerl
from src.parsing.interface import DataParserInterface
from src.parsing.params import DataParserParams


class DataParserFactory:
    """Factory for creating data parsers using registry pattern with singleton management."""

    # Lock for thread safety
    _lock = threading.Lock()
    # Singleton instance
    _parserSingleton = None

    # Registry of parser implementations
    _registry: Dict[str, Type[DataParserInterface]] = {
        "perl": DataParserPerl,
    }

    @classmethod
    def register(cls, impl_name: str, parser_class: Type[DataParserInterface]) -> None:
        """
        Register a new parser implementation.

        Args:
            impl_name: The identifier for the parser implementation.
            parser_class: The class implementing DataParserInterface.
        """
        cls._registry[impl_name] = parser_class

    @classmethod
    def get_available_implementations(cls) -> list:
        """Get list of registered parser implementation names."""
        return list(cls._registry.keys())

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance."""
        from src.parsing.config_manager import ConfigurationManager
        from src.parsing.impl.multiprocessing.parseWorkPool import ParseWorkPool

        ConfigurationManager.reset()
        ParseWorkPool.reset()
        with cls._lock:
            cls._parserSingleton = None

    @classmethod
    def getDataParser(cls, params: DataParserParams, implName: str = "perl") -> DataParserInterface:
        """
        Get or create a data parser singleton.

        Args:
            params: Parser configuration parameters.
            implName: Implementation name (default: "perl").

        Returns:
            DataParserInterface instance.

        Raises:
            ValueError: If the implementation name is not registered.
        """
        # Only one instance of the data parser is allowed
        if cls._parserSingleton is None:
            # Thread safety
            with cls._lock:
                # Check again if it is None to avoid race conditions
                if cls._parserSingleton is None:
                    if implName not in cls._registry:
                        available = ", ".join(cls._registry.keys())
                        raise ValueError(
                            f"Unknown parser implementation: '{implName}'. Available: {available}"
                        )
                    cls._parserSingleton = cls._registry[implName](params)
        return cls._parserSingleton
