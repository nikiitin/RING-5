import src.utils.utils as utils
import subprocess
import abc

from src.data_preprocessing.src.preprocessor import Preprocessor

class Divider(Preprocessor):

    def __init__(self, csvPath: str, json: dict) -> None:
        super().__init__(csvPath, json)

    def _checkPreconditions(self) -> None:
        utils.checkElementExists(self._json, "src1")
        utils.checkElementExists(self._json, "src2")
    
    def _perform(self) -> str:
        self._RScriptCall.append(self._operands["dst"])
        self._RScriptCall.append(self._operands["src1"])
        self._RScriptCall.append(self._operands["src2"])
        subprocess.call(self._RScriptCall)
        return self._operands["dst"]
        
    def _configurePreprocessor(self) -> None:
        super()._configurePreprocessor()
        # Retrieve the operands from the json
        self._RScriptCall = ["./src/data_preprocessing/src/preprocessors/divider/divider.R"]
        self._RScriptCall.append(self._csvPath)