from argumentParser import AnalyzerInfo
import utils.utils as utils
import os.path
from data_parser.configurationManager import ConfigurationManager
class DataParserInterface:
    def __init__(self, params: AnalyzerInfo) -> None:
        self._args = params
        self._parseConfig = ConfigurationManager.getParser(params.getJson())
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

    def _parseFile(self, file: str, varsToParse: list) -> None:
        pass

    # Generic definition for data parsing
    def __call__(self) -> None:
        # Data compression will bring all stats files into a single directory
        self._compressData()
        # Parse stats and turn them into csv
        self._parseStats()