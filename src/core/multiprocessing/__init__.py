"""
RING-5 Core Multiprocessing Module

Provides unified singleton pool manager for parallel task execution.
Supports both ProcessPool (for CPU-bound tasks) and ThreadPool (for IO-bound).

Exports:
    - WorkPool: Singleton pool manager
    - Job: Abstract base class for parallel tasks
"""

from .job import Job
from .pool import WorkPool

__all__ = ["WorkPool", "Job"]
