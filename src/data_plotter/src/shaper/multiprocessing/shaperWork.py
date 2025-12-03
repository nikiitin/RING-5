from typing import Any


class ShaperWork:
    """
    Class that represents a work to be done by a shaper worker.
    """
    _deps: list
    def __init__(self, work_id: str, json: dict):
        self._work_id = work_id
        self._json = json
        self._srcCsv = []
        self._dstCsv = ""
        self._deps = []

    @property
    def deps(self) -> list:
        return self._deps
    @deps.setter
    def deps(self, value: Any) -> None:
        if isinstance(value, list):
            self._deps = value
        else:
            raise ValueError("deps must be a list")

    @property
    def work_id(self) -> str:
        return self._work_id
    
    @property
    def json(self) -> dict:
        return self._json
    
    @property
    def srcCsv(self) -> list:
        return self._srcCsv
    
    @srcCsv.setter
    def srcCsv(self, value: Any) -> None:
        if isinstance(value, list):
            self._srcCsv = value
        else:
            raise ValueError("srcCsv must be a list")
    
    @property
    def dstCsv(self) -> str:
        return self._dstCsv
    
    @dstCsv.setter
    def dstCsv(self, value: Any) -> None:
        if isinstance(value, str):
            self._dstCsv = value
        else:
            raise ValueError("dstCsv must be a string")