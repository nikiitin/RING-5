import os.path
import subprocess
from stats_analyzer import AnalyzerInfo
from data_parser.dataParserInterface import DataParserInterface
import utils.utils as utils

# NOTE: Please if you are going to add a new data parser,
#       make it inherit from DataParserInterface
#       and add it to the DataParserFactory
class DataParserBash(DataParserInterface):
    def __init__(self, analyzerInfo: AnalyzerInfo) -> None:
        json = analyzerInfo.getJson()
        outDir = json["outputPath"]
        self._compressedFilePath = os.path.join(outDir, "stats.tar")
        self._files = utils.jsonToArg(json, "filesPaths")
        utils.checkFilesExistOrException(self._files[1:])
        self._finalDirName = os.path.join(outDir, "stats")
        self._csvPath = analyzerInfo.getCsv()
        self._statsAnalyzed = utils.jsonToArg(json, "statsAnalyzed")
        self._configs = utils.jsonToArg(json, "configs")
        
    def _compressData(self):
        print("Compressing data")
        shellScriptCall = ["./data_parser/dataCompressor.sh"]
        shellScriptCall.append(self._compressedFilePath)
        shellScriptCall.extend(self._files)
        shellScriptCall.append("*stats.txt")
        shellScriptCall.append(self._finalDirName)
        subprocess.call(shellScriptCall)
        
    def _parseStats(self):
        print("Parsing stats and turning into csv")
        shellScriptCall = ["./data_parser/dataParser.sh"]
        shellScriptCall.append(self._csvPath)
        shellScriptCall.append(str(1))
        shellScriptCall.append(self._finalDirName)
        shellScriptCall.extend(self._statsAnalyzed)
        shellScriptCall.extend(self._configs)
        subprocess.call(shellScriptCall)

    def runParse(self):
        self._compressData()
        self._parseStats()
        