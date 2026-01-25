"""Base class for parsing work units."""

from typing import Any

from src.core.multiprocessing.job import Job


class ParseWork(Job):
    """Base class for parallel parsing work units."""

    def __init__(self, **kwargs) -> None:
        pass

    def __call__(self) -> Any:
        raise NotImplementedError("Subclass must implement __call__")

    def __str__(self) -> str:
        return self.__class__.__name__
