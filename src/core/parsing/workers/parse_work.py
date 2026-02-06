"""Base class for parsing work units."""

from typing import Any, Dict

from src.core.multiprocessing.job import Job

# Type alias for parsed variable dictionaries
# Key: variable identifier (str)
# Value: StatType instance with parsed content
# Using Any for value since StatType is defined in parsers.types and we want to avoid circular imports  # noqa: E501
ParsedVarsDict = Dict[str, Any]


class ParseWork(Job):
    """
    Base class for parallel parsing work units.

    Subclasses must implement __call__ to return a dictionary mapping
    variable identifiers to their parsed StatType instances.

    The return type uses Any for values to avoid circular imports with StatType.
    In practice, all values are StatType instances from src.core.parsing.types.base.
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize the parse work unit.

        Args:
            **kwargs: Subclass-specific initialization parameters
        """
        pass

    def __call__(self) -> ParsedVarsDict:
        """
        Execute the parsing work.

        Returns:
            Dictionary mapping variable IDs to their populated StatType instances

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """
        raise NotImplementedError("Subclass must implement __call__")

    def __str__(self) -> str:
        """
        Get string representation of the work unit.

        Returns:
            Class name of the work unit
        """
        return self.__class__.__name__
