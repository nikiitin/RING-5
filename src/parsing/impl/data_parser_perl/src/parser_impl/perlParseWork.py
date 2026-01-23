import os
import subprocess  # nosec

import src.utils.utils as utils
from src.parsing.impl.multiprocessing.parseWork import ParseWork


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
                # Variable not found in file
                # Instead of crashing, fill with default "0" or appropriate empty value
                # This allows parsing files that are missing some variables
                # print(f"Warning: Variable {varID} not found in {self._fileToParse}, using 0")
                itVar.content = "0"

            if type(itVar).__name__ == "Configuration":
                if len(itVar.content) == 0:
                    # If the content is empty, then use the onEmpty value
                    if itVar.onEmpty is None:
                        # Fallback for configuration
                        itVar.content = "None"
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

    def _processVector(self, varID: str, varValue: str) -> None:
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

    def _processDist(self, varID: str, varValue: str) -> None:
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

        # For types with entries (Vector, Distribution, Histogram), extract base ID first
        # and check if it exists before buffering
        if varType == "Vector":
            baseID = varID.split("::")[0]
            # Check if this variable is in our parse list before buffering
            if varsToParse.get(baseID) is None:
                return  # Skip unknown variables
            self._processVector(varID, varValue)
            varID = baseID
        elif varType == "Distribution":
            baseID = varID.split("::")[0]
            # Check if this variable is in our parse list before buffering
            if varsToParse.get(baseID) is None:
                return  # Skip unknown variables
            self._processDist(varID, varValue)
            varID = baseID
        elif varType == "Histogram":
            baseID = varID.split("::")[0]
            targetVar = varsToParse.get(baseID)

            # Skip if not in parse list
            if targetVar is None:
                return

            # Determine handling based on configuration
            if type(targetVar).__name__ == "Vector":
                self._processVector(varID, varValue)
                varType = "Vector"
            else:
                self._processDist(varID, varValue)
                expected_type = type(targetVar).__name__
                if expected_type in ["Distribution", "Histogram"]:
                    varType = expected_type

            varID = baseID
        elif varType == "Scalar" or varType == "Configuration":
            # Check if variable exists before assigning
            if varsToParse.get(varID) is None:
                return  # Skip unknown variables
            varsToParse[varID].content = varValue
        elif varType == "Summary":
            baseID = varID.split("::")[0]
            targetVar = varsToParse.get(baseID)

            handled_as_entry = False
            if targetVar and "::" in varID:
                expected_type = type(targetVar).__name__
                if expected_type == "Vector":
                    self._processVector(varID, varValue)
                    varType = "Vector"
                    varID = baseID
                    handled_as_entry = True
                elif expected_type in ["Distribution", "Histogram"]:
                    self._processDist(varID, varValue)
                    varType = expected_type
                    varID = baseID
                    handled_as_entry = True

            if not handled_as_entry:
                # Summaries need a keyword at the end
                varID = baseID + "__get_summary"
                if varsToParse.get(varID) is None:
                    # Do not parse summary if not asked
                    return
                varsToParse[varID].content = varValue
            # Return to avoid type mismatch
            return
        else:
            # Unknown variable type
            raise RuntimeError("Unknown variable type: " + varType)

        # Final check - should not reach here for unknown variables
        # but keep as safety net
        if varsToParse.get(varID) is None:
            return

        # Check variable type matches the one in the list
        if type(varsToParse.get(varID)).__name__ != varType:
            raise RuntimeError(
                "Variable type does not match the one in the list: "
                + "Expected: "
                + type(varsToParse.get(varID)).__name__
                + " Found: "
                + varType
                + " ID: "
                + varID
            )

    def _processOutput(self, output: str, varsToParse: dict) -> dict:
        # Process the output from the script
        # by lines and return the parsed info
        # Create a dictionary to buffer vector variables
        self._vectorDict = dict()
        self._distDict = dict()
        if len(output) == 0:
            # Output might be empty if no variables matched the filter.
            # We should still return a row with defaults (handled by validateVars)
            # instead of dropping the file completely.
            pass
            # print("Output file: " + self._fileToParse + " is empty! Defaults will be used.")
            # return None
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
            output = subprocess.check_output(scriptCall).decode("utf-8")  # nosec
        except subprocess.CalledProcessError as e:
            print(f"Error while calling script: {scriptCall}")
            print(f"Error message: {e.output}")
            raise
        except Exception:
            print(f"Error while calling script: {scriptCall}")
            raise
        # Return the output
        return output

    def __call__(self) -> dict:
        # Set the script path
        # TODO: Avoid hardcoded path. Ensure this script is accessible.
        scriptPath = os.path.abspath(
            "./src/parsing/impl/data_parser_perl/src/parser_impl/fileParser.pl"
        )

        # Resolve perl executable
        import shutil

        perl_exe = shutil.which("perl")
        if not perl_exe:
            raise RuntimeError("Perl executable not found in PATH")

        # Get a list with a caller for the script
        # and the arguments
        scriptCall = [perl_exe, scriptPath]
        # Add the work to the call
        # The first element is the file to parse
        utils.checkFileExistsOrException(self._fileToParse)
        scriptCall.append(self._fileToParse)
        # In the script, only the IDs are needed
        # Remove directives from the variables
        # at script call
        scriptCall.extend([varID.split("__")[0] for varID in self._varsToParse.keys()])
        # Call the parser script
        output = self._getOutputFromSubprocess(scriptCall)  # nosec
        # print(output)
        # exit(0)
        # Process the output and return the parsed info
        return self._processOutput(output, self._varsToParse)

    def __str__(self) -> str:
        return "File: " + self._fileToParse + " Vars: " + str(self._varsToParse)
