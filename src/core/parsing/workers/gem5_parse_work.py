"""
Perl Parse Work - Worker unit for parsing a single gem5 stats file.
Executed in parallel across multiple stats files.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import src.core.common.utils as utils
from src.core.parsing.type_mapper import TypeMapper
from src.core.parsing.workers.parse_work import ParsedVarsDict, ParseWork
from src.core.parsing.workers.perl_worker_pool import get_worker_pool

# Type aliases for clarity
# EntryBuffer: baseID -> {entryKey -> [values]}
EntryBufferType = Dict[str, Dict[str, List[str]]]

# Variable dictionary: varID -> StatType instance
# Using Any for StatType to avoid circular import with src.core.parsing.types.base
VarsDictType = Dict[str, Any]

logger = logging.getLogger(__name__)


class Gem5ParseWork(ParseWork):
    """
    Worker for parsing a single gem5 stats file using the Perl worker pool.

    Uses persistent Perl processes from the worker pool to eliminate subprocess
    startup overhead (54x speedup). The Perl output format is: Type/VarID::Entry/Value
    """

    def __init__(self, fileToParse: str, varsToParse: VarsDictType) -> None:
        """
        Initialize the gem5 parse work unit.

        Args:
            fileToParse: Absolute path to the gem5 stats.txt file
            varsToParse: Dictionary mapping variable IDs to StatType instances

        Raises:
            RuntimeError: If varsToParse is empty
        """
        if not varsToParse:
            raise RuntimeError("Vars to parse is empty!")
        self._fileToParse: str = fileToParse
        self._varsToParse: VarsDictType = varsToParse
        self._entryBuffer: EntryBufferType = {}  # Unified buffer for entry-based types
        super().__init__()

    def __str__(self) -> str:
        return f"Gem5ParseWork({self._fileToParse})"

    # ========== Entry Buffering ==========

    def _bufferEntry(self, varID: str, varValue: str) -> None:
        """
        Buffer an entry-based value (Vector, Distribution, Histogram).

        Args:
            varID: Variable identifier with entry key (format: baseID::entryKey)
            varValue: String value to buffer for this entry
        """
        baseID: str
        entryKey: str
        baseID, entryKey = varID.split("::", 1)

        if baseID not in self._entryBuffer:
            self._entryBuffer[baseID] = {}
        if entryKey not in self._entryBuffer[baseID]:
            self._entryBuffer[baseID][entryKey] = []

        self._entryBuffer[baseID][entryKey].append(varValue)

    def _applyBufferedEntries(self, varsToParse: VarsDictType) -> None:
        """
        Apply buffered entries to their corresponding variable objects.

        Args:
            varsToParse: Dictionary of variables to update with buffered content
        """
        for varID, entries in self._entryBuffer.items():
            if varID in varsToParse:
                varsToParse[varID].content = entries

    # ========== Line Processing ==========

    def _parseLine(self, line: str) -> Tuple[str, str, str]:
        """
        Parse a Perl output line into its components.

        Args:
            line: Output line in format "Type/VarID/Value"

        Returns:
            Tuple of (varType, varID, varValue)
        """
        parts: List[str] = line.split("/")
        return parts[0], parts[1], parts[2]

    def _getExpectedType(self, var: Any) -> str:
        """
        Get the normalized type name from a StatType variable object.

        Args:
            var: StatType instance (using Any to avoid circular import
                 with src.core.parsing.types.base)

        Returns:
            Normalized type name (e.g., 'scalar', 'vector', 'distribution')

        Note:
            Uses Any for var parameter because StatType is defined in src.core.parsing.types.base
            and importing it here would create a circular dependency. At runtime, var is
            always a StatType instance.
        """
        return TypeMapper.normalize_type(type(var).__name__)

    def _processEntryType(
        self, varType: str, varID: str, varValue: str, varsToParse: VarsDictType
    ) -> Optional[str]:
        """
        Process entry-based types (Vector, Distribution, Histogram).

        Args:
            varType: Raw type from Perl output
            varID: Variable identifier with entry key
            varValue: String value for this entry
            varsToParse: Dictionary of variables being parsed

        Returns:
            Normalized type name if successful, None if variable is unknown
        """
        baseID: str = varID.split("::")[0]
        targetVar: Optional[Any] = varsToParse.get(baseID)  # Any = StatType instance

        if targetVar is None:
            return None  # Unknown variable

        expectedType: str = self._getExpectedType(targetVar)

        normalizedVarType: str = TypeMapper.normalize_type(varType)

        # For Histogram, determine handling based on target configuration
        if normalizedVarType == "histogram":
            if expectedType == "vector":
                normalizedVarType = "vector"
            elif expectedType in ("distribution", "histogram"):
                normalizedVarType = expectedType
        elif normalizedVarType == "vector" and expectedType == "distribution":
            normalizedVarType = "distribution"
        elif normalizedVarType == "vector" and expectedType == "histogram":
            # Vector statistics (::samples, ::mean, ::total) are part of histogram
            normalizedVarType = "histogram"

        self._bufferEntry(varID, varValue)
        return normalizedVarType

    def _processSummary(self, varID: str, varValue: str, varsToParse: VarsDictType) -> None:
        """
        Process Summary lines from Perl output.

        Summaries can be:
        1. Entry of a Vector/Distribution (e.g., ::total, ::mean)
        2. Standalone summary request (varID__get_summary)

        Args:
            varID: Variable identifier (may include ::entry_key)
            varValue: Summary value as string
            varsToParse: Dictionary of variables being parsed
        """
        baseID: str = varID.split("::")[0]
        targetVar: Optional[Any] = varsToParse.get(baseID)  # Any = StatType instance

        # Check if it's an entry-style summary (::key)
        if targetVar and "::" in varID:
            expectedType: str = self._getExpectedType(targetVar)
            if TypeMapper.is_entry_type(expectedType):
                self._bufferEntry(varID, varValue)
                return

        # Check if it's a standalone summary request
        summaryID: str = baseID + "__get_summary"
        if summaryID in varsToParse:
            varsToParse[summaryID].content = varValue

    def _processLine(self, line: str, varsToParse: VarsDictType) -> None:
        """
        Process a single output line from the Perl parser.

        Args:
            line: Output line in format "Type/VarID/Value"
            varsToParse: Dictionary of variables being parsed

        Raises:
            RuntimeError: If variable type mismatch or unknown type encountered
        """
        rawType: str
        varID: str
        varValue: str
        rawType, varID, varValue = self._parseLine(line)
        normalizedType: str = TypeMapper.normalize_type(rawType)

        if TypeMapper.is_entry_type(normalizedType):
            resolvedType: Optional[str] = self._processEntryType(
                rawType, varID, varValue, varsToParse
            )
            if resolvedType is None:
                return  # Unknown variable, skip

            # Validate type consistency
            baseID: str = varID.split("::")[0]
            expectedType: str = self._getExpectedType(varsToParse[baseID])
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

    def _validateVars(self, varsToParse: VarsDictType) -> VarsDictType:
        """
        Ensure all variables have content, applying defaults where needed.

        Args:
            varsToParse: Dictionary of parsed variables

        Returns:
            The same dictionary after validation and default application
        """
        for _varID, var in varsToParse.items():
            if var.content is None:
                var.content = "0"

            if self._getExpectedType(var) == "configuration":
                if not var.content:  # Empty content
                    var.content = var.onEmpty if var.onEmpty else "None"

        return varsToParse

    # ========== Main Processing ==========

    def _processOutput(self, output: str, varsToParse: VarsDictType) -> VarsDictType:
        """
        Process the complete Perl script output with optimizations.

        Args:
            output: Complete stdout from Perl parser script
            varsToParse: Dictionary of variables to populate

        Returns:
            Dictionary of variables with parsed and validated content
        """
        self._entryBuffer = {}

        # More efficient: splitlines() is faster than split('\n')
        # Strip whitespace and filter empty lines in one pass
        lines = [line for line in output.splitlines() if line.strip()]

        for line in lines:
            self._processLine(line, varsToParse)

        self._applyBufferedEntries(varsToParse)
        return self._validateVars(varsToParse)

    def _runPerlScript(self) -> str:
        """
        Execute parsing using the worker pool (eliminates subprocess startup overhead).

        Returns:
            Complete output from the Perl worker pool

        Raises:
            RuntimeError: If file doesn't exist or worker pool fails
            TimeoutError: If parsing exceeds timeout
        """
        utils.checkFileExistsOrException(self._fileToParse)

        # Build keys and validate they are safe (no leading dashes)
        safe_keys: List[str] = []
        for varID in self._varsToParse.keys():
            key: str = varID.split("__")[0]
            if key.startswith("-"):
                # Avoid flag injection
                logger.warning("Skipping potentially unsafe key: %s", key)
                continue
            safe_keys.append(key)

        # Use worker pool for parsing (54x faster than subprocess)
        logger.debug(f"Parsing {self._fileToParse} with {len(safe_keys)} variables via worker pool")

        try:
            pool = get_worker_pool()
            output_lines = pool.parse_file(
                self._fileToParse, safe_keys, timeout=120.0  # Match previous timeout
            )

            # Convert list of lines back to string to match original interface
            return "\n".join(output_lines)

        except TimeoutError as e:
            logger.error("Worker pool timeout after 120s: %s", self._fileToParse)
            raise RuntimeError(f"Parser timeout: {self._fileToParse}") from e
        except Exception as e:
            logger.error("Worker pool error: %s", e, exc_info=True)
            raise RuntimeError(f"Worker pool parse failed: {self._fileToParse}") from e

    def __call__(self) -> ParsedVarsDict:
        """
        Execute the parse work and return populated variables.

        Returns:
            Dictionary mapping variable IDs to their populated StatType instances

        Raises:
            RuntimeError: If parsing fails or type mismatches occur
            subprocess.CalledProcessError: If Perl script fails
        """
        output: str = self._runPerlScript()
        return self._processOutput(output, self._varsToParse)
