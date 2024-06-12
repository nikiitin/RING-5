import os.path
import subprocess
from argumentParser import AnalyzerInfo
from src.data_parser.src.dataParserInterface import DataParserInterface
import src.utils.utils as utils

# NOTE: Please if you are going to add a new data parser,
#       make it inherit from DataParserInterface
#       and add it to the DataParserFactory
class DataParserBash(DataParserInterface):
    def __init__(self, params: AnalyzerInfo) -> None:
        super().__init__(params)
        
    def _compressData(self):
        print("Compressing data")
        shellScriptCall = ["./data_parser/data_parser_bash/dataCompressor.sh"]
        shellScriptCall.append(self._compressedFilePath)
        shellScriptCall.extend(self._files)
        shellScriptCall.append("*stats.txt")
        shellScriptCall.append(self._finalDirName)
        subprocess.call(shellScriptCall)
        
    def _parseStats(self):
        print("Parsing stats and turning into csv")
        shellScriptCall = ["./data_parser/data_parser_bash/dataParser.sh"]
        shellScriptCall.append(self._csvPath)
        shellScriptCall.append(str(1))
        shellScriptCall.append(self._finalDirName)
        shellScriptCall.extend(self._statsAnalyzed)
        shellScriptCall.extend(self._configs)
        subprocess.call(shellScriptCall)

    def runParse(self):
        super().__call__()
        