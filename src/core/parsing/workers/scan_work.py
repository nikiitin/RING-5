"""
Scan Work - Abstract Base for Variable Discovery Jobs.

Defines the interface for all scanning work units that discover variables
in gem5 statistics files. Used by scanner service for parallel discovery
of scalar, vector, and other statistics.
"""

from typing import Any

from src.core.multiprocessing.job import Job


class ScanWork(Job):
    """
    Abstract base class for scanning work.
    Inherits from the core Job class to be compatible with WorkPool.
    """

    def __init__(self, **kwargs: Any) -> None:
        pass

    def __call__(self) -> Any:
        raise NotImplementedError("This method must be implemented by the child class")

    def __str__(self) -> str:
        return self.__class__.__name__
