from typing import Any, List, Optional
import pandas as pd
from src.core.multiprocessing.job import Job
from src.web.services.shapers.factory import ShaperFactory
from src.web.services.shapers.uni_df_shaper import UniDfShaper
from src.web.services.shapers.multi_df_shaper import MultiDfShaper
import src.utils.utils as utils


class ShaperWork(Job):
    """
    Class that represents a shaper task to be executed in the WorkPool.
    Follows the Command pattern via the Job interface.
    """

    def __init__(self, work_id: str, json_config: dict):
        self._work_id = work_id
        self._json = json_config
        self._srcCsv = []
        self._dstCsv = ""
        self._deps = []

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
    def json(self) -> dict:
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
            print(f"Error: No source CSV files found for work {self._work_id}")
            return False

        utils.checkFilesExistOrException(self._srcCsv)
        
        task_type = utils.getElementValue(self._json, "type")
        task_params = utils.getElementValue(self._json, "params")
        
        # Create the shaper using the factory
        shaper = ShaperFactory.createShaper(task_type, task_params)
        if shaper is None:
            raise Exception(f"Error: Shaper not created for work {self._work_id}")
            
        # Perform the shaper operation
        if isinstance(shaper, UniDfShaper):
            # UniDfShaper usually takes the first (or relevant) CSV
            # Original code used srcCsv[1] which might be a bug or specific to its logic
            # Let's check original: df = cls.getDataFrame(work.srcCsv[1])
            # Wait, if it has one source, it's index 0. If it has dependencies, maybe index 1?
            # Looking at ShaperWorkManager, it appends to srcCsv.
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
