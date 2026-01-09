import src.utils.utils as utils
from src.parsing.config_manager import ConfigurationManager
from src.parsing.impl.multiprocessing.parseWorkPool import ParseWorkPool
from src.parsing.params import DataParserParams


class DataParserInterface:
    def __init__(self, params: DataParserParams) -> None:
        self._args = params
        self._parseConfig = ConfigurationManager.getParser(params.get_json())
        self._shouldCompress = ConfigurationManager.getCompress(params.get_json())
        self._parseWorkPool = ParseWorkPool.getInstance()
        for parsing in self._parseConfig:
            # Check for the required elements on every parsing
            utils.checkElementExists(parsing, "path")
            utils.checkElementExists(parsing, "files")
            utils.checkElementExists(parsing, "vars")

    # Private methods, all must be implemented in child classes
    # all of them must be called in __call__ method
    def _compressData(self) -> None:
        pass

    def _parseStats(self) -> None:
        pass

    def _turnIntoCsv(self) -> None:
        pass

    # Generic definition for data parsing
    def __call__(self) -> None:
        # Data compression will bring all stats files into a single directory
        if self._shouldCompress == "True":
            self._compressData()
        # Parse stats and turn them into csv
        self._parseStats()
        self._turnIntoCsv()
