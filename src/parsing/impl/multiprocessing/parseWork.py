from typing import Any

from src.core.multiprocessing.job import Job


class ParseWork(Job):
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __call__(self) -> Any:
        raise NotImplementedError("This method must be implemented by the child class")

    def __str__(self) -> str:
        return self.__class__.__name__
