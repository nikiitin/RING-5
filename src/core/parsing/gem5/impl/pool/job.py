"""
Job - Abstract Base for Parallel Tasks.

Defines the Command pattern interface for all parallelizable work units
in the system. Each job represents an atomic operation that can be executed
independently in the worker pool.

Used by:
- Parsing workers (parse individual variables)
- Scanning workers (scan regex patterns)
- Shaping workers (apply transformations to data)
"""

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
