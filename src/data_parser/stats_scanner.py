import os
import re
from typing import Any, Dict, List


class StatsScanner:
    """
    Scans gem5 stats files to discover available variables and their types.
    Ports the logic from TypesFormatRegex.pm to Python.
    """

    # Regex patterns
    FLOAT_PATTERN = r"\d+\.\d+"
    VAR_NAME_PATTERN = r"[\d\.\w]+"
    CONF_VALUE_PATTERN = r"[\d\.\w\-\/\(\)\,]+"
    SCALAR_VALUE_PATTERN = f"(?:\\d+|{FLOAT_PATTERN})"
    COMMENT_PATTERN = r"(?:#.*|\(Unspecified\)\s*)"

    # Complex value: 5  32.5%  63.4%
    COMPLEX_VALUE_PATTERN = f"\\d+\\s+{FLOAT_PATTERN}%\\s+{FLOAT_PATTERN}%"

    # Summaries: ::mean, ::total, etc.
    SUMMARIES_ENTRY_PATTERN = r"::(samples|mean|gmean|stdev|total)"

    # Distribution entries: ::5, ::-5, ::overflows
    DIST_ENTRY_NUMERIC_PATTERN = r"::-?\d+"
    DIST_ENTRY_OVERFLOW_PATTERN = r"::overflows"
    DIST_ENTRY_UNDERFLOW_PATTERN = r"::underflows"
    DIST_ENTRY_PATTERN = (
        f"(?:{DIST_ENTRY_NUMERIC_PATTERN}|{DIST_ENTRY_OVERFLOW_PATTERN}|"
        f"{DIST_ENTRY_UNDERFLOW_PATTERN})"
    )

    # Histogram: ::1-5
    HISTOGRAM_ENTRY_RANGE_PATTERN = r"::\d+-\d+"

    # Vector: ::Name (but not summaries)
    VECTOR_ENTRY_PATTERN = r"::([\w\.]+)"  # Capture group for entry name

    # Compiled Regexes
    CONF_REGEX = re.compile(rf"^{VAR_NAME_PATTERN}={CONF_VALUE_PATTERN}$")
    SCALAR_REGEX = re.compile(
        rf"^({VAR_NAME_PATTERN})\s+{SCALAR_VALUE_PATTERN}\s+{COMMENT_PATTERN}?$"
    )

    # Distributions
    DIST_REGEX = re.compile(
        rf"^({VAR_NAME_PATTERN}){DIST_ENTRY_PATTERN}\s+{COMPLEX_VALUE_PATTERN}\s+"
        rf"{COMMENT_PATTERN}?$"
    )
    HISTOGRAM_REGEX = re.compile(
        rf"^({VAR_NAME_PATTERN}){HISTOGRAM_ENTRY_RANGE_PATTERN}\s+{COMPLEX_VALUE_PATTERN}\s+"
        rf"{COMMENT_PATTERN}?$"
    )

    # Summaries (treated as part of vector or distribution usually, but here we want base name)
    SUMMARY_REGEX = re.compile(
        rf"^({VAR_NAME_PATTERN}){SUMMARIES_ENTRY_PATTERN}\s+{SCALAR_VALUE_PATTERN}\s+"
        rf"{COMMENT_PATTERN}?$"
    )

    # Vectors
    # Note: Vector regex in Perl was:
    # ^$varNameRegex$vectorEntryRegex\s+$complexValueRegex\s+$commentRegex?$
    # But vector entries often look like scalars if they don't have percentages.
    # However, gem5 vectors usually print as:
    # name::entry value
    # or
    # name::entry value perc cum_perc
    # Changed \s+ to \s* before comment to handle lines without trailing spaces/comments
    VECTOR_REGEX = re.compile(
        rf"^({VAR_NAME_PATTERN}){VECTOR_ENTRY_PATTERN}\s+(?:{COMPLEX_VALUE_PATTERN}|"
        rf"{SCALAR_VALUE_PATTERN})\s*{COMMENT_PATTERN}?$"
    )

    @staticmethod
    def scan_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Scans a stats file and returns a list of discovered variables.

        Returns:
            List of dicts with 'name', 'type', and 'entries' (for vectors).
        """
        if not os.path.exists(file_path):
            return []

        discovered_vars: Dict[str, Dict[str, Any]] = {}

        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("---"):
                        continue

                    # Check types
                    # Configuration
                    if StatsScanner.CONF_REGEX.match(line):
                        # name=value
                        name = line.split("=")[0]
                        if name not in discovered_vars:
                            discovered_vars[name] = {"type": "configuration", "entries": set()}
                        continue

                    # Scalar
                    match = StatsScanner.SCALAR_REGEX.match(line)
                    if match:
                        name = match.group(1)
                        if name not in discovered_vars:
                            discovered_vars[name] = {"type": "scalar", "entries": set()}
                        continue

                    # Distribution / Histogram
                    match = StatsScanner.DIST_REGEX.match(
                        line
                    ) or StatsScanner.HISTOGRAM_REGEX.match(line)
                    if match:
                        name = match.group(1)
                        if name not in discovered_vars:
                            discovered_vars[name] = {"type": "distribution", "entries": set()}
                        continue

                    # Vector
                    # Check summary first, as it often accompanies vectors/dists
                    match = StatsScanner.SUMMARY_REGEX.match(line)
                    if match:
                        name = match.group(1)
                        entry = match.group(2)

                        if name not in discovered_vars:
                            discovered_vars[name] = {"type": "vector", "entries": {entry}}
                        else:
                            if discovered_vars[name]["type"] == "scalar":
                                discovered_vars[name]["type"] = "vector"
                            discovered_vars[name]["entries"].add(entry)
                        continue

                    match = StatsScanner.VECTOR_REGEX.match(line)
                    if match:
                        name = match.group(1)
                        entry = match.group(2)

                        if name not in discovered_vars:
                            discovered_vars[name] = {"type": "vector", "entries": {entry}}
                        else:
                            if discovered_vars[name]["type"] == "scalar":
                                discovered_vars[name]["type"] = "vector"
                            discovered_vars[name]["entries"].add(entry)
                        continue

        except Exception as e:
            print(f"Error scanning file {file_path}: {e}")
            return []

        # Convert to list
        result = []
        for name, info in sorted(discovered_vars.items()):
            entry = {"name": name, "type": info["type"]}
            if info["entries"]:
                entry["entries"] = sorted(list(info["entries"]))
            result.append(entry)

        return result
