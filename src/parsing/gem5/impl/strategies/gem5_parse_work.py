"""
Perl Parse Work - Worker unit for parsing a single gem5 stats file.
Executed in parallel across multiple stats files.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.parsing.gem5.types.base import StatType

import src.core.common.utils as utils
from src.core.common.safe_regex import (
    SafeRegexError,
    escape_perl_stat_filter,
    numeric_pattern_id,
)
from src.core.common.security_limits import MAX_PARSE_VARIABLES
from src.parsing.gem5.impl.pool.parse_work import ParsedVarsDict, ParseWork
from src.parsing.gem5.impl.strategies.file_parser_strategy import INTERNAL_SIM_PATH_KEY
from src.parsing.gem5.impl.strategies.perl_worker_pool import get_worker_pool
from src.parsing.gem5.types.type_mapper import TypeMapper

# Type aliases for clarity
# EntryBuffer: baseID -> {entryKey -> [values]}
EntryBufferType = dict[str, dict[str, list[str]]]

# Variable dictionary: varID -> StatType instance
VarsDictType = dict[str, "StatType"]

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

    # ========== Variable-ID helpers ==========

    @staticmethod
    def _base_id(var_id: str) -> str:
        """Base variable id before the ``::`` entry separator (e.g. ``a::b`` -> ``a``)."""
        return var_id.split("::", 1)[0]

    @staticmethod
    def _request_key(var_id: str) -> str:
        """Return the concrete stat name requested from the Perl parser.

        ``__get_summary`` is RING-5's only synthetic suffix.  Gem5 itself
        legitimately uses double underscores in names (for example
        ``MemDepUnit__0``), so splitting at the first ``__`` silently
        truncated pattern-expanded aliases and left their values missing.
        """
        suffix = "__get_summary"
        return var_id[: -len(suffix)] if var_id.endswith(suffix) else var_id

    @staticmethod
    def _numeric_pattern_id(pattern: str, concrete_name: str) -> str | None:
        r"""Return the numeric ID when *concrete_name* matches a ``\d+`` pattern.

        Literal segments are escaped before matching, so this helper never
        evaluates user-controlled regex syntax.
        """
        try:
            return numeric_pattern_id(pattern, concrete_name)
        except SafeRegexError:
            return None

    @classmethod
    def _scalar_pattern_entry(
        cls, var_id: str, target_var: StatType, vars_to_parse: VarsDictType
    ) -> tuple[str, str] | None:
        """Resolve a concrete scalar alias to its logical vector entry."""
        target_content = target_var.content
        target_entries = target_var.entries or []
        for logical_id, logical_var in vars_to_parse.items():
            entry = cls._numeric_pattern_id(logical_id, var_id)
            if entry is None:
                continue
            if logical_var.content is target_content and entry in target_entries:
                return logical_id, entry
        return None

    # ========== Line Processing ==========

    def _parseLine(self, line: str) -> tuple[str, str, str]:
        """
        Parse a Perl output line into its components.

        Args:
            line: Output line in format "Type/VarID/Value"

        Returns:
            Tuple of (varType, varID, varValue)
        """
        # maxsplit=2: the value is everything after the second '/' — configuration values
        # legitimately contain '/' (paths, device strings); an unbounded split would
        # truncate them to the first segment.
        parts: list[str] = line.split("/", 2)
        if len(parts) < 3:
            logger.warning("PARSER: Malformed Perl output line (expected 3+ parts): %s", line[:200])
            return "", "", ""
        return parts[0], parts[1], parts[2]

    def _getExpectedType(self, var: StatType) -> str:
        """
        Get the normalized type name from a StatType variable object.

        Args:
            var: StatType instance.

        Returns:
            Normalized type name (e.g., 'scalar', 'vector', 'distribution')
        """
        return TypeMapper.normalize_type(type(var).__name__)

    def _processEntryType(
        self, varType: str, varID: str, varValue: str, varsToParse: VarsDictType
    ) -> str | None:
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
        baseID: str = self._base_id(varID)
        targetVar: StatType | None = varsToParse.get(baseID)

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
        baseID: str = self._base_id(varID)
        targetVar: StatType | None = varsToParse.get(baseID)

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
        if not rawType:
            return  # Malformed line, skip
        normalizedType: str = TypeMapper.normalize_type(rawType)

        if TypeMapper.is_entry_type(normalizedType):
            resolvedType: str | None = self._processEntryType(rawType, varID, varValue, varsToParse)
            if resolvedType is None:
                return  # Unknown variable, skip

            # Validate type consistency
            baseID: str = self._base_id(varID)
            expectedType: str = self._getExpectedType(varsToParse[baseID])
            if expectedType != resolvedType:
                raise RuntimeError(
                    f"Variable type mismatch - Expected: {expectedType} "
                    f"Found: {resolvedType} ID: {baseID}"
                )

        elif normalizedType in ("scalar", "configuration"):
            if varID not in varsToParse:
                return  # Unknown variable, skip
            target_var = varsToParse[varID]
            expected_type = self._getExpectedType(target_var)
            if normalizedType == "scalar" and expected_type == "vector":
                resolved_entry = self._scalar_pattern_entry(varID, target_var, varsToParse)
                if resolved_entry is None:
                    raise RuntimeError(
                        f"Variable type mismatch - Expected: {expected_type} "
                        f"Found: {normalizedType} ID: {varID}"
                    )
                logical_id, entry = resolved_entry
                self._bufferEntry(f"{logical_id}::{entry}", varValue)
                return
            target_var.content = varValue

        elif normalizedType == "summary":
            self._processSummary(varID, varValue, varsToParse)

        else:
            raise RuntimeError(f"Unknown variable type: {rawType}")

    # ========== Validation ==========

    def _validateVars(self, varsToParse: VarsDictType) -> VarsDictType:
        """
        Validate parsed variables and log absent/incomplete numeric stats.

        Configuration variables fall back to their user-configured ``onEmpty``
        value. Numeric variables are NOT fabricated: an absent or incomplete
        stat is left empty so ``balance_content`` pads it with NaN downstream
        (hard rule 6). Every absent/incomplete numeric stat is logged with the
        source file so missingness is traceable (what + where).

        Args:
            varsToParse: Dictionary of parsed variables

        Returns:
            The same dictionary after validation
        """
        missing: list[str] = []
        for varID, var in varsToParse.items():
            if self._getExpectedType(var) == "configuration":
                if not var.content:  # Empty content
                    var.content = var.onEmpty if var.onEmpty else "None"
                continue

            content = var.content
            if not content or (not isinstance(content, dict) and len(content) < var.repeat):
                missing.append(varID)

        if missing:
            logger.warning(
                "PARSER: %d requested stat(s) absent or incomplete in %s — "
                "recorded as NaN (not 0): %s",
                len(missing),
                self._fileToParse,
                ", ".join(sorted(missing)),
            )

        return varsToParse

    # Output processing
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

        # Convert user-visible names into a deliberately tiny regex grammar:
        # literals plus the scanner-generated \d+ placeholder. The Perl backend
        # never receives arbitrary regex grouping or quantifiers.
        request_keys = list(
            dict.fromkeys(self._request_key(var_id) for var_id in self._varsToParse)
        )
        safe_keys: list[str] = []
        for key in request_keys:
            # Regex-expanded variables also have concrete aliases in the map.
            # Request those anchored literals and omit the broader pattern.
            if r"\d+" in key and any(
                self._numeric_pattern_id(key, candidate) is not None
                for candidate in request_keys
                if candidate != key
            ):
                continue
            try:
                escaped_key = escape_perl_stat_filter(key)
            except SafeRegexError as exc:
                raise RuntimeError(f"Unsafe parser stat filter {key!r}: {exc}") from exc
            if escaped_key not in safe_keys:
                safe_keys.append(escaped_key)

        if not safe_keys:
            raise RuntimeError("No variable filters were provided for parsing.")
        if len(safe_keys) > MAX_PARSE_VARIABLES:
            raise RuntimeError(
                f"Parser request exceeds the {MAX_PARSE_VARIABLES}-variable filter limit."
            )

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
        result: ParsedVarsDict = dict(self._processOutput(output, self._varsToParse))
        result[INTERNAL_SIM_PATH_KEY] = self._fileToParse
        return result
