"""
Perl Parse Work - Worker unit for parsing a single gem5 stats file.
Executed in parallel across multiple stats files.
"""

import logging
import os
import shutil
import subprocess
from typing import Any, Dict, Optional

import src.utils.utils as utils
from src.parsers.workers.parse_work import ParseWork

logger = logging.getLogger(__name__)


class Gem5ParseWork(ParseWork):
    """
    Worker for parsing a single gem5 stats file using Perl.

    The Perl script outputs lines in format: Type/VarID::Entry/Value
    This class processes those lines and populates the varsToParse objects.
    """

    def __init__(self, fileToParse: str, varsToParse: dict) -> None:
        if not varsToParse:
            raise RuntimeError("Vars to parse is empty!")
        self._fileToParse = fileToParse
        self._varsToParse = varsToParse
        self._entryBuffer: Dict[str, Dict[str, list]] = {}  # Unified buffer for entry-based types
        super().__init__()

    def __str__(self) -> str:
        return f"Gem5ParseWork({self._fileToParse})"

    # ========== Entry Buffering ==========

    def _bufferEntry(self, varID: str, varValue: str) -> None:
        """Buffer an entry-based value (Vector, Distribution, Histogram)."""
        baseID, entryKey = varID.split("::", 1)

        if baseID not in self._entryBuffer:
            self._entryBuffer[baseID] = {}
        if entryKey not in self._entryBuffer[baseID]:
            self._entryBuffer[baseID][entryKey] = []

        self._entryBuffer[baseID][entryKey].append(varValue)

    def _applyBufferedEntries(self, varsToParse: dict) -> None:
        """Apply buffered entries to their corresponding variable objects."""
        for varID, entries in self._entryBuffer.items():
            if varID in varsToParse:
                varsToParse[varID].content = entries

    # ========== Line Processing ==========

    def _parseLine(self, line: str) -> tuple:
        """Parse a line into (varType, varID, varValue)."""
        parts = line.split("/")
        return parts[0], parts[1], parts[2]

    def _getExpectedType(self, var: Any) -> str:
        """Get the type name from a variable object."""
        from src.parsers.type_mapper import TypeMapper

        return TypeMapper.normalize_type(type(var).__name__)

    def _processEntryType(
        self, varType: str, varID: str, varValue: str, varsToParse: dict
    ) -> Optional[str]:
        """
        Process entry-based types (Vector, Distribution, Histogram).
        Returns the resolved varType if successful, None if variable unknown.
        """
        from src.parsers.type_mapper import TypeMapper

        baseID = varID.split("::")[0]
        targetVar = varsToParse.get(baseID)

        if targetVar is None:
            return None  # Unknown variable

        expectedType = self._getExpectedType(targetVar)

        normalizedVarType = TypeMapper.normalize_type(varType)

        # For Histogram, determine handling based on target configuration
        if normalizedVarType == "histogram":
            if expectedType == "vector":
                normalizedVarType = "vector"
            elif expectedType in ("distribution", "histogram"):
                normalizedVarType = expectedType
        elif normalizedVarType == "vector" and expectedType == "distribution":
            normalizedVarType = "distribution"

        self._bufferEntry(varID, varValue)
        return normalizedVarType

    def _processSummary(self, varID: str, varValue: str, varsToParse: dict) -> None:
        """
        Process Summary lines. Summaries can be:
        1. Entry of a Vector/Distribution (e.g., ::total, ::mean)
        2. Standalone summary request (varID__get_summary)
        """
        from src.parsers.type_mapper import TypeMapper

        baseID = varID.split("::")[0]
        targetVar = varsToParse.get(baseID)

        # Check if it's an entry-style summary (::key)
        if targetVar and "::" in varID:
            expectedType = self._getExpectedType(targetVar)
            if TypeMapper.is_entry_type(expectedType):
                self._bufferEntry(varID, varValue)
                return

        # Check if it's a standalone summary request
        summaryID = baseID + "__get_summary"
        if summaryID in varsToParse:
            varsToParse[summaryID].content = varValue

    def _processLine(self, line: str, varsToParse: dict) -> None:
        """Process a single output line from the Perl parser."""
        from src.parsers.type_mapper import TypeMapper

        rawType, varID, varValue = self._parseLine(line)
        normalizedType = TypeMapper.normalize_type(rawType)

        if TypeMapper.is_entry_type(normalizedType):
            resolvedType = self._processEntryType(rawType, varID, varValue, varsToParse)
            if resolvedType is None:
                return  # Unknown variable, skip

            # Validate type consistency
            baseID = varID.split("::")[0]
            expectedType = self._getExpectedType(varsToParse[baseID])
            if expectedType != resolvedType:
                raise RuntimeError(
                    f"Variable type mismatch - Expected: {expectedType} "
                    f"Found: {resolvedType} ID: {baseID}"
                )

        elif normalizedType in ("scalar", "configuration"):
            if varID not in varsToParse:
                return  # Unknown variable, skip
            varsToParse[varID].content = varValue

        elif normalizedType == "summary":
            self._processSummary(varID, varValue, varsToParse)

        else:
            raise RuntimeError(f"Unknown variable type: {rawType}")

    # ========== Validation ==========

    def _validateVars(self, varsToParse: dict) -> dict:
        """Ensure all variables have content, applying defaults where needed."""
        for _varID, var in varsToParse.items():
            if var.content is None:
                var.content = "0"

            if self._getExpectedType(var) == "configuration":
                if not var.content:  # Empty content
                    var.content = var.onEmpty if var.onEmpty else "None"

        return varsToParse

    # ========== Main Processing ==========

    def _processOutput(self, output: str, varsToParse: dict) -> dict:
        """Process the complete Perl script output."""
        self._entryBuffer = {}

        for line in output.splitlines():
            if line:  # Skip empty lines
                self._processLine(line, varsToParse)

        self._applyBufferedEntries(varsToParse)
        return self._validateVars(varsToParse)

    def _runPerlScript(self) -> str:
        """Execute the Perl parser script and return output."""
        scriptPath = os.path.abspath("./src/parsers/perl/fileParser.pl")

        perl_exe = shutil.which("perl")
        if not perl_exe:
            raise RuntimeError("Perl executable not found in PATH")

        # Verify it's a valid executable path
        if not os.path.isfile(perl_exe) or not os.access(perl_exe, os.X_OK):
            raise RuntimeError(f"Perl path is not executable: {perl_exe}")

        utils.checkFileExistsOrException(self._fileToParse)
        if not os.path.isfile(scriptPath):
            raise RuntimeError(f"Script path not found: {scriptPath}")

        # Build keys and validate they are safe (no leading dashes)
        safe_keys = []
        for varID in self._varsToParse.keys():
            key = varID.split("__")[0]
            if key.startswith("-"):
                # Avoid flag injection
                logger.warning("Skipping potentially unsafe key: %s", key)
                continue
            safe_keys.append(key)

        # Build command: perl script.pl <file> <var1> <var2> ...
        cmd = [perl_exe, scriptPath, self._fileToParse]
        cmd.extend(safe_keys)

        try:
            # shell=False is default but explicit is better for security awareness
            # Using subprocess.run for consistency and better error handling
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error("Error calling Perl script: %s", cmd)
            # subprocess.run with text=True ensures e.stdout and e.stderr are strings.
            logger.error("Perl Output: %s", e.stdout)
            logger.error("Perl Error: %s", e.stderr)
            raise

    def __call__(self) -> dict:
        """Execute the parse work and return populated variables."""
        output = self._runPerlScript()
        return self._processOutput(output, self._varsToParse)
