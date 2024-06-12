import os
import subprocess
import src.utils.utils as utils
from src.data_parser.src.impl.multiprocessing.parseWork import ParseWork

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

    def _validateVars(self, varsToParse: dict) -> dict:
        # Check all the variables have content
        for varID in varsToParse.keys():
            itVar = varsToParse[varID]
            if itVar.content is None:
                # This should not happen...
                raise RuntimeError("Variable content none: " + varID)
            if type(itVar).__name__ == "Configuration":
                if len(itVar.content) == 0:
                    # If the content is empty, then use the onEmpty value
                    if itVar.onEmpty is None:
                        # If the onEmpty value is None, then raise error
                        # Should not happen...
                        raise RuntimeError("Configuration variable empty: " +
                                       varID +
                                       "No default value... Stoping...")
                    else:
                        # Use the onEmpty (default) value
                        itVar.content = itVar.onEmpty
        return varsToParse

    def _addBufferedVars(self, varsToParse: dict) -> dict:
        # Add the buffered variables to the dictionary
        for varID in self._vectorDict.keys():
            # Get the vector variable
            varsToParse[varID].content = self._vectorDict.get(varID)
        for varID in self._distDict.keys():
            # Get the vector variable
            varsToParse[varID].content = self._distDict.get(varID)
        # Return the parsed info
        return varsToParse

    def _processVector(self, varID:str, varValue:str) -> None:
        splittedVarID = varID.split("::")
        varID = splittedVarID[0]
        varKey = splittedVarID[1]
        if self._vectorDict.get(varID) is None:
            self._vectorDict.update({varID: dict()})
        # Check if the key is already in the dictionary
        if self._vectorDict[varID].get(varKey) is None:
            self._vectorDict[varID].update({varKey: []})
        # Buffer the value with the key (entry)
        self._vectorDict[varID][varKey].append(varValue)
    
    def _processDist(self, varID:str, varValue:str) -> None:
        splittedVarID = varID.split("::")
        varID = splittedVarID[0]
        # Distribution also has key
        varKey = splittedVarID[1]
        # Check if the variable ID is already in the dictionary
        if self._distDict.get(varID) is None:
            self._distDict.update({varID: dict()})
        # Check if the key is already in the dictionary
        if self._distDict[varID].get(varKey) is None:
            self._distDict[varID].update({varKey: []})
        # Buffer the value with the key (entry)
        self._distDict[varID][varKey].append(varValue)

    def _processLine(self, line: str, varsToParse: dict) -> str:
        # Split the line by slashes
            lineElements = line.split("/")
            # Get the type of the variable
            varType = lineElements[0]
            # Get the ID of the variable
            varID = lineElements[1]
            varValue = lineElements[2]
            # If the variable is a vector, then the ID
            # will be in the format: ID::key
            # So, we need to split it again
            if varType == "Vector":
                self._processVector(varID, varValue)
                # Remove the key from the ID
                varID = varID.split("::")[0]
            elif varType == "Distribution":
                self._processDist(varID, varValue)
                # Remove the key from the ID
                varID = varID.split("::")[0]
            elif varType == "Scalar" or varType == "Configuration":
                varsToParse[varID].content = varValue
            elif varType == "Summary":
                # Summaries need a keyword at the end
                varID = varID + "__get_summary"
                if varsToParse.get(varID) is None:
                    # Do not parse summary if not asked
                    return
                varsToParse[varID].content = varValue
                # Return to avoid type mismatch
                return
            else:
                # Unknown variable type
                raise RuntimeError("Unknown variable type: " + varType)
            # Post check but it is ok, an error will raise            
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

    def _processOutput(self, output: str, varsToParse: dict) -> dict:
        # Process the output from the script
        # by lines and return the parsed info
        # Create a dictionary to buffer vector variables
        self._vectorDict = dict()
        self._distDict = dict()
        if len(output) == 0:
            print("Output file: " + self._fileToParse + " is empty! Skipping...")
            return None
        for line in output.splitlines():
            self._processLine(line, varsToParse)
        # Update all the buffered variables
        varsToParse = self._addBufferedVars(varsToParse)
        varsToParse = self._validateVars(varsToParse)
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
        scriptPath = os.path.join("./src/data_parser/src/impl/data_parser_perl/src/parser_impl/fileParser.pl")
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
        # print(output)
        # exit(0)
        # Process the output and return the parsed info
        return self._processOutput(output, self._varsToParse)

    def __str__(self) -> str:
        return "File: " + self._fileToParse + " Vars: " + str(self._varsToParse)