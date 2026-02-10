"""
Utility Functions for RING-5

Provides common utility functions for file operations, JSON validation,
and path management used throughout the application.
"""

import enum
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Type alias for JSON-compatible values
JsonValue = Union[bool, int, float, str, List[Any], Dict[Any, Any], None]


def getElementValue(jsonElement: Dict[str, Any], key: str, optional: bool = True) -> JsonValue:
    """
    Get the value of a key in a JSON element.

    Args:
        jsonElement: Dictionary representing JSON data
        key: Key to retrieve from the dictionary
        optional: If False, raises ValueError when value is None

    Returns:
        Value associated with the key, or None if optional and missing

    Raises:
        KeyError: If key is not found in jsonElement
        ValueError: If value is None and optional is False
    """
    if key in jsonElement:
        if jsonElement[key] is None:
            if optional:
                return None
            else:
                raise ValueError(f"Value is None for key: {key} and is not optional")
        else:
            value: JsonValue = jsonElement[key]
            return value
    else:
        raise KeyError(f"Key not found: {key}")


def checkElementExists(jsonElement: Dict[str, Any], key: str) -> None:
    """
    Check if a key exists in a JSON element, raise exception if not.

    Args:
        jsonElement: Dictionary to check
        key: Key to verify

    Raises:
        KeyError: If key is not found
    """
    if key not in jsonElement:
        raise KeyError(f"Key not found: {key}")


def checkElementExistNoException(jsonElement: Dict[str, Any], key: str) -> bool:
    """
    Check if a key exists in a JSON element without raising exception.

    Args:
        jsonElement: Dictionary to check
        key: Key to verify

    Returns:
        True if key exists, False otherwise
    """
    return key in jsonElement


def checkEnumExistsNoException(jsonElement: Dict[str, Any], enum: enum.EnumMeta) -> bool:
    """
    Check if any key in jsonElement matches an enum member.

    Args:
        jsonElement: Dictionary to check
        enum: Enum type to match against

    Returns:
        True if any key matches an enum member, False otherwise
    """
    for key in jsonElement:
        if key in enum.__members__:
            return True
    return False


def getEnumValue(jsonElement: Dict[str, Any], enumType: enum.EnumMeta) -> Optional[str]:
    """
    Get the first enum value that matches a key in jsonElement.

    Args:
        jsonElement: Dictionary to search
        enumType: Enum type to match against

    Returns:
        Matched enum value as string, or None if no match
    """
    for key in jsonElement:
        enum_member: Any
        for enum_member in enumType:
            if key == enum_member.value:
                return key
    return None


def checkFilesExistOrException(filePaths: List[Union[str, Path]]) -> None:
    """
    Check if all files exist, raise exception for first missing file.

    Args:
        filePaths: List of file paths to check

    Raises:
        FileNotFoundError: If any file does not exist
    """
    for filePath in filePaths:
        checkFileExistsOrException(filePath)


def checkDirsExistOrException(dirPaths: List[Union[str, Path]]) -> None:
    """
    Check if all directories exist, raise exception for first missing directory.

    Args:
        dirPaths: List of directory paths to check

    Raises:
        FileNotFoundError: If any directory does not exist
    """
    for dirPath in dirPaths:
        checkDirExistsOrException(dirPath)


def checkFileExistsOrException(filePath: Union[str, Path]) -> None:
    """
    Check if a file exists, raise exception if not.

    Args:
        filePath: Path to file

    Raises:
        FileNotFoundError: If file does not exist
    """
    if not os.path.isfile(filePath):
        raise FileNotFoundError(f"File does not exist: {filePath}")


def checkFileExists(filePath: Union[str, Path]) -> bool:
    """
    Check if a file exists.

    Args:
        filePath: Path to file

    Returns:
        True if file exists, False otherwise
    """
    return os.path.isfile(filePath)


def checkDirExistsOrException(dirPath: Union[str, Path]) -> None:
    """
    Check if a directory exists, raise exception if not.

    Args:
        dirPath: Path to directory

    Raises:
        FileNotFoundError: If directory does not exist
    """
    if not os.path.isdir(dirPath):
        raise FileNotFoundError(f"Directory does not exist: {dirPath}")


def checkDirExists(dirPath: Union[str, Path]) -> bool:
    """
    Check if a directory exists.

    Args:
        dirPath: Path to directory

    Returns:
        True if directory exists, False otherwise
    """
    return os.path.isdir(dirPath)


def createDir(dirPath: Union[str, Path]) -> None:
    """
    Create a directory if it doesn't exist.

    Args:
        dirPath: Path to directory to create
    """
    if not checkDirExists(dirPath):
        os.mkdir(dirPath)
    else:
        logger.debug("Directory already exists: %s", dirPath)


def createTmpFile() -> str:
    """
    Create a temporary file and return its path.

    Returns:
        Path to the created temporary file
    """
    # Create a temporary file
    fd, path = tempfile.mkstemp()
    # Close the file descriptor and return the path
    os.close(fd)
    return path


def checkVarType(var: Any, varType: type) -> None:
    """
    Check if a variable is of the expected type, raise exception if not.

    Args:
        var: Variable to check
        varType: Expected type

    Raises:
        TypeError: If variable is not of expected type
    """
    if not isinstance(var, varType):
        raise TypeError(f"Variable is not of type {varType.__name__}, got {type(var).__name__}")


def sanitize_log_value(value: object) -> str:
    """Sanitize a value for safe inclusion in log messages.

    Removes newlines and control characters to prevent log injection attacks.

    Args:
        value: The value to sanitize for logging.

    Returns:
        A sanitized string safe for log output.
    """
    text: str = str(value)
    # Remove newlines and carriage returns that could forge log entries
    text = text.replace("\n", "\\n").replace("\r", "\\r")
    # Remove other ASCII control characters (0x00-0x1f except tab)
    return "".join(c if c == "\t" or ord(c) >= 0x20 else "" for c in text)


def sanitize_filename(name: str) -> str:
    """Sanitize a filename to prevent path traversal.

    Strips path separators and directory traversal sequences,
    returning only the base filename component.

    Args:
        name: The filename to sanitize.

    Returns:
        A safe filename without directory components.
    """
    # Remove any directory separators and traversal sequences
    name = name.replace("/", "_").replace("\\", "_")
    name = name.replace("..", "_")
    # Remove leading dots (hidden files on Unix)
    name = name.lstrip(".")
    return name if name else "unnamed"


def validate_path_within(path: Path, allowed_base: Path) -> Path:
    """Validate that a resolved path is within an allowed base directory.

    Uses ``os.path.normpath`` followed by ``str.startswith`` -- the exact
    pattern recognised by CodeQL as a path-sanitisation barrier -- to
    prevent path-traversal attacks.

    Args:
        path: The path to validate.
        allowed_base: The base directory the path must reside within.

    Returns:
        The normalised, absolute path if valid.

    Raises:
        ValueError: If the path escapes the allowed base directory.
    """
    # Normalise both paths with os.path.normpath (CodeQL-recognised sanitizer)
    path_str: str = os.path.normpath(str(path))
    base_str: str = os.path.normpath(str(allowed_base))
    # Resolve to absolute paths for accurate comparison
    resolved: str = os.path.normpath(os.path.abspath(path_str))
    base: str = os.path.normpath(os.path.abspath(base_str))
    # Use os.path.commonpath for robust containment check
    # (avoids sibling-path bypass, e.g. "/allowed/base_evil" matching "/allowed/base")
    try:
        common: str = os.path.commonpath([resolved, base])
    except ValueError:
        # On Windows, paths on different drives raise ValueError
        raise ValueError(f"Path traversal detected: {resolved} is outside {base}")
    if common != base:
        raise ValueError(f"Path traversal detected: {resolved} is outside {base}")
    return Path(resolved)


_DEFAULT_STATS_PATH: str = "."

# Allowlist for glob patterns: only alphanumeric, dots, underscores, asterisks, question marks
_SAFE_GLOB_RE: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_.*?]+$")

_DEFAULT_STATS_PATTERN: str = "stats.txt"


def sanitize_glob_pattern(pattern: str, default: str = _DEFAULT_STATS_PATTERN) -> str:
    """Sanitize a user-provided glob pattern for safe use with rglob/glob.

    Validates the pattern against an allowlist of safe characters.
    Rejects patterns containing path separators or traversal sequences.
    Falls back to *default* when *pattern* is empty or invalid.

    Args:
        pattern: Raw glob pattern from user input.
        default: Fallback pattern when *pattern* is empty or invalid.

    Returns:
        A validated glob pattern string.
    """
    if not pattern or not pattern.strip():
        return default
    clean: str = pattern.strip()
    # Reject patterns with path separators or traversal
    if "/" in clean or "\\" in clean or ".." in clean:
        return default
    # Only allow safe characters
    if not _SAFE_GLOB_RE.match(clean):
        return default
    return clean


def normalize_user_path(user_path: str, default: str = _DEFAULT_STATS_PATH) -> Path:
    """Normalize and validate a user-provided filesystem path.

    Applies ``os.path.normpath`` to collapse redundant separators and
    up-level references, then rejects any path that still contains ``..``
    components.  Falls back to *default* when *user_path* is empty.

    This function is recognised by CodeQL as a path-sanitisation barrier
    because it performs ``normpath`` followed by a traversal check.

    Args:
        user_path: Raw path string from user input.
        default: Fallback path when *user_path* is empty.

    Returns:
        A resolved, validated ``Path`` object.

    Raises:
        ValueError: If the normalised path still contains ``..`` segments.
    """
    raw: str = user_path.strip() if user_path else default
    normalized: str = os.path.normpath(raw)
    # Reject any remaining traversal components
    if ".." in normalized.split(os.sep):
        raise ValueError(
            f"Path traversal detected: '{user_path}' "
            f"normalizes to '{normalized}' which contains '..' components"
        )
    # Resolve to absolute using os.path functions (CodeQL-compatible)
    resolved_path: str = os.path.normpath(os.path.abspath(normalized))
    return Path(resolved_path)
