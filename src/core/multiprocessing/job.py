from abc import ABC, abstractmethod
from typing import Any


class Job(ABC):
    """
    Base interface for all parallel tasks in the system.
    Follows the Command pattern.
    """

    @abstractmethod
    def __call__(self) -> Any:
        """Execute the job logic."""
        pass

    def __str__(self) -> str:
        return self.__class__.__name__
