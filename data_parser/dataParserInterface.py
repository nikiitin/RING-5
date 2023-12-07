from argumentParser import AnalyzerInfo
import utils.utils as utils
import os.path
class DataParserInterface:
    def __init__(self, params: AnalyzerInfo) -> None:
        json = params.getJson()
        outDir = json["outputPath"]
        self._compressedFilePath = os.path.join(outDir, "stats.tar")
        self._files = utils.jsonToArg(json, "filesPaths")
        utils.checkDirsExistOrException(self._files[1:])
        self._finalDirName = os.path.join(outDir, "stats")
        self._csvPath = params.getCsv()
        self._statsAnalyzed = utils.jsonToArg(json, "statsAnalyzed")
        self._configs = utils.jsonToArg(json, "configs")

    # Private methods, all must be implemented in child classes
    # all of them must be called in __call__ method
    def _compressData(self) -> None:
        pass
    
    def _parseStats(self) -> None:
        pass
    
    # Generic definition for data parsing
    def __call__(self) -> None:
        # Data compression will bring all stats files into a single directory
        self._compressData()
        # Parse stats and turn them into csv
        self._parseStats()