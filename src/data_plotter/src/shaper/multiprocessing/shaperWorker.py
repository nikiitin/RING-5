# from shaperFactory import ShaperFactory
import pandas as pd
from multiDfShaper import MultiDfShaper
from shaperFactory import ShaperFactory
from shaperWork import ShaperWork
from uniDfShaper import UniDfShaper

import utils.utils as utils


class shaperWorker:
    """
    Worker class for the shapers. This class will be used to execute
    the shapers in a separate thread.
    """

    def __init__(self):
        pass

    @classmethod
    def getDataFrame(cls, file: str) -> pd.DataFrame:
        """
        Returns a dataframe from a csv file.
        """
        utils.checkFileExistsOrException(file)
        return pd.read_csv(file, sep="\t")

    @classmethod
    def persistDf(cls, df: pd.DataFrame, file: str) -> None:
        """
        Persists a dataframe to a csv file.
        """
        df.to_csv(file, sep="\t", index=False)

    @classmethod
    def executeWork(cls, work: ShaperWork) -> bool:
        """
        Executes a shaper work. The work is given by the json.
        """
        if len(work.srcCsv) == 0 or len(work.deps) != 0:
            print("Error: No source CSV files or dependencies found for work " + work.work_id)
            return False

        utils.checkFilesExistOrException(work.srcCsv)
        task_type: str = utils.getElementValue(work.json, "type")
        utils.checkVarType(task_type, str)
        task_params: dict = utils.getElementValue(work.json, "params")
        utils.checkVarType(task_params, dict)
        # Create the shaper
        shaper = ShaperFactory.createShaper(task_type, task_params)
        if shaper is None:
            raise Exception("Error: Shaper not created for work " + work.work_id)
        # Perform the shaper operation
        # Check if the last shaper is a UniDfShaper
        if isinstance(shaper, UniDfShaper):
            df = cls.getDataFrame(work.srcCsv[1])
            shaper(df)
            cls.persistDf(df, work.dstCsv)
        elif isinstance(shaper, MultiDfShaper):
            dfs = []
            for srcCsv in work.srcCsv:
                dfs.append(cls.getDataFrame(srcCsv))
            shaper(dfs)
            # Persist the last dataframe
            cls.persistDf(dfs[len(dfs) - 1], work.dstCsv)
        return True
