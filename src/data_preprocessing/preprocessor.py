import src.utils.utils as utils
import subprocess

class Preprocessor():
    def __init__(self, csvPath: str, json: dict) -> None:
        self._json = json
        self._csvPath = csvPath

    def __call__(self) -> None:
        RScriptCall = ["./src/data_preprocessing/preprocessors/interface/preprocessor.R"]
        RScriptCall.append(self._csvPath)
        # json is the preprocessor json
        # It exists but we need to know how many preprocessors we have
        # and their type
        RScriptCall.append(str(len(self._json)))
        for preprocessor in self._json:
            # Type
            RScriptCall.extend(utils.jsonToArg(preprocessor, "type"))
            # Args, note that data verification will be done in R
            RScriptCall.extend(utils.jsonToArg(preprocessor, "args"))
        subprocess.call(RScriptCall)

