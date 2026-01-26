import logging
from pathlib import Path
from typing import Any, Dict, List, Union, cast

import pandas as pd

import src.utils.utils as utils
from src.core.multiprocessing.job import Job
from src.web.services.shapers.factory import ShaperFactory
from src.web.services.shapers.multi_df_shaper import MultiDfShaper
from src.web.services.shapers.uni_df_shaper import UniDfShaper

logger = logging.getLogger(__name__)


class ShaperWork(Job):
    """
    Class that represents a shaper task to be executed in the WorkPool.
    Follows the Command pattern via the Job interface.
    """

    def __init__(self, work_id: str, json_config: Dict[str, Any]):
        self._work_id = work_id
        self._json = json_config
        self._srcCsv: List[str] = []
        self._dstCsv = ""
        self._deps: List[str] = []

    @property
    def deps(self) -> List[str]:
        return self._deps

    @deps.setter
    def deps(self, value: List[str]) -> None:
        if isinstance(value, list):
            self._deps = value
        else:
            raise ValueError("deps must be a list")

    @property
    def work_id(self) -> str:
        return self._work_id

    @property
    def json(self) -> Dict[str, Any]:
        return self._json

    @property
    def srcCsv(self) -> List[str]:
        return self._srcCsv

    @srcCsv.setter
    def srcCsv(self, value: List[str]) -> None:
        if isinstance(value, list):
            self._srcCsv = value
        else:
            raise ValueError("srcCsv must be a list")

    @property
    def dstCsv(self) -> str:
        return self._dstCsv

    @dstCsv.setter
    def dstCsv(self, value: str) -> None:
        if isinstance(value, str):
            self._dstCsv = value
        else:
            raise ValueError("dstCsv must be a string")

    def _getDataFrame(self, file: str) -> pd.DataFrame:
        utils.checkFileExistsOrException(file)
        # Assuming tab separator as per original shaperWorker
        return pd.read_csv(file, sep="\t")

    def _persistDf(self, df: pd.DataFrame, file: str) -> None:
        df.to_csv(file, sep="\t", index=False)

    def __call__(self) -> bool:
        """
        Execute the shaper task.
        """
        if len(self._srcCsv) == 0:
            logger.error("No source CSV files found for work %s", self._work_id)
            return False

        utils.checkFilesExistOrException(cast(List[Union[str, Path]], self._srcCsv))

        task_type_raw = utils.getElementValue(self._json, "type")
        task_params_raw = utils.getElementValue(self._json, "params")
        task_type = str(task_type_raw) if task_type_raw is not None else ""
        task_params = cast(Dict[str, Any], task_params_raw) if isinstance(task_params_raw, dict) else {}

        # Create the shaper using the factory
        shaper = ShaperFactory.createShaper(task_type, task_params)
        if shaper is None:
            raise Exception(f"Error: Shaper not created for work {self._work_id}")

        # Perform the shaper operation
        if isinstance(shaper, UniDfShaper):
            # UniDfShaper uses the second source if available (dependency output), otherwise first.
            source_idx = 1 if len(self._srcCsv) > 1 else 0
            df = self._getDataFrame(self._srcCsv[source_idx])
            shaper(df)
            self._persistDf(df, self._dstCsv)
        elif isinstance(shaper, MultiDfShaper):
            dfs = [self._getDataFrame(f) for f in self._srcCsv]
            shaper(dfs)
            # Persist the last dataframe as per original shaperWorker
            self._persistDf(dfs[-1], self._dstCsv)
        else:
            # Fallback for generic shapers that might take a single DF
            df = self._getDataFrame(self._srcCsv[0])
            shaper(df)
            self._persistDf(df, self._dstCsv)

        return True

    def __str__(self) -> str:
        return f"ShaperWork(id={self._work_id}, type={self._json.get('type')})"
