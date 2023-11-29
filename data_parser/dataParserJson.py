import os.path
import subprocess
from data_parser.dataParserInterface import DataParserInterface
import utils.utils as utils

class DataParserJson(DataParserInterface):
    def __init__(self, json, csvPath):
        outDir = json["outputPath"]
        self._compressedFilePath = os.path.join(outDir, "stats.tar")
        self._files = utils.jsonToArg(json, "filesPaths")
        utils.checkFilesExistOrException(self._files[1:])
        self._finalDirName = os.path.join(outDir, "stats")
        self._csvPath = csvPath
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
        