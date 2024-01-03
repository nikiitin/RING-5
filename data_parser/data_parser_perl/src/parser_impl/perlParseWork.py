import os
import subprocess
import utils.utils as utils
from data_parser.multiprocessing.parseWork import ParseWork

class PerlParseWork(ParseWork):
    def __init__(self, fileToParse: str, varsToParse: dict) -> None:
        # File to parse
        self._fileToParse = fileToParse
        # Variables to parse
        # It is a dictionary with the following format:
        # { "id" : {"varType": Scalar, content:[]} }
        self._varsToParse = varsToParse
        if len(varsToParse) == 0:
            raise RuntimeError("Vars to parse is empty!")
        super().__init__()
    
    def _processOutput(self, output: str, varsToParse: dict) -> dict:
        # Process the output from the script
        # by lines and return the parsed info
        # Create a dictionary to buffer vector variables
        vectorDict = dict()
        if len(output) == 0:
            print("Output file: " + self._fileToParse + " is empty! Skipping...")
            return None
        for line in output.splitlines():
            # Split the line by slashes
            lineElements = line.split("/")
            # Get the type of the variable
            varType = lineElements[0]
            # Get the ID of the variable
            varID = lineElements[1]
            # If the variable is a vector, then the ID
            # will be in the format: ID::key
            # So, we need to split it again
            varKey = None
            if varType == "Vector":
                splittedVarID = varID.split("::")
                varID = splittedVarID[0]
                varKey = splittedVarID[1]
                if vectorDict.get(varID) is None:
                    vectorDict.update({varID: dict()})
            # Check if the variable is in the list of variables to parse
            if varsToParse.get(varID) is None:
                # Variable not in the list, raise error
                raise RuntimeError("Variable not in the list of variables to parse: " + varID)
            # Check variable type matches the one in the list
            if type(varsToParse.get(varID)).__name__ != varType:
                raise RuntimeError("Variable type does not match the one in the list: " +
                    "Expected: " + type(varsToParse.get(varID)).__name__ +
                    " Found: " + varType + " ID: " +
                    varID)
            varValue = lineElements[2]
            # If variable is a vector, create a new dictionary with the key and value
            if varType == "Vector":
                # Check if the key is already in the dictionary
                if vectorDict[varID].get(varKey) is None:
                    vectorDict[varID].update({varKey: []})
                # Buffer the value with the key (entry)
                vectorDict[varID][varKey].append(varValue)
            else:
                varsToParse[varID].content = varValue
        # Update all the vector variables
        for varID in vectorDict.keys():
            # Get the vector variable
            varsToParse[varID].content = vectorDict.get(varID)
        # Return the parsed info
        return varsToParse

    def _getOutputFromSubprocess(self, scriptCall: list) -> str:
        # Call the script and get the output
        output = ""
        try:
            output = subprocess.check_output(scriptCall).decode("utf-8")
        except subprocess.CalledProcessError as e:
            print("Error while calling script: " + scriptCall)
            print("Error message: " + str(e.output))
            raise
        except Exception:
            print("Error while calling script: " + scriptCall)
            raise
        # Return the output
        return output

    def __call__(self) -> dict:
        # Set the script path
        # FIXME: MAGIC!
        scriptPath = os.path.join("./data_parser/data_parser_perl/src/parser_impl/fileParser.pl")
        # Get a list with a caller for the script
        # and the arguments
        scriptCall = ["perl",
            scriptPath]
        # Add the work to the call
        # The first element is the file to parse
        utils.checkFileExistsOrException(self._fileToParse)
        scriptCall.append(self._fileToParse)
        # In the script, only the IDs are needed
        scriptCall.extend(self._varsToParse.keys())
        # Call the parser script
        output = self._getOutputFromSubprocess(scriptCall)
        # Process the output and return the parsed info
        return self._processOutput(output, self._varsToParse)

    def __str__(self) -> str:
        return "File: " + self._fileToParse + " Vars: " + str(self._varsToParse)