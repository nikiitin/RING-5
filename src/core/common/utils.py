"""
Utility Functions for RING-5

Provides common utility functions for file operations, path validation,
and security-related sanitization used throughout the application.
"""

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def checkFileExistsOrException(filePath: str | Path) -> None:
    """
    Check if a file exists, raise exception if not.

    Args:
        filePath: Path to file

    Raises:
        FileNotFoundError: If file does not exist
    """
    if not os.path.isfile(filePath):
        raise FileNotFoundError(f"File does not exist: {filePath}")


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

    Resolves both ``path`` and ``allowed_base`` to absolute paths,
    normalises them with ``os.path.normpath``, and then uses
    ``os.path.commonpath`` to ensure that the candidate path cannot
    escape the allowed base directory.  This avoids the sibling-path
    bypass that a naive ``str.startswith`` check would allow
    (e.g. ``/allowed/base_evil`` matching ``/allowed/base``).

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
    except ValueError as exc:
        # On Windows, paths on different drives raise ValueError
        raise ValueError(f"Path traversal detected: {resolved} is outside {base}") from exc
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


def allowed_web_stats_roots() -> tuple[Path, ...]:
    """Return administrator-approved roots for web-triggered stats access.

    ``RING5_ALLOWED_STATS_ROOTS`` is an ``os.pathsep``-separated list. When it is
    unset, only the process working directory is allowed. Using the working
    directory keeps repository checkouts and installed-package launches
    predictable without deriving a user-data root from ``site-packages``.

    The environment and working directory are read on every call so tests and
    long-running deployments can update configuration safely.
    """
    configured = os.environ.get("RING5_ALLOWED_STATS_ROOTS", "")
    raw_roots = [part.strip() for part in configured.split(os.pathsep) if part.strip()]
    if not raw_roots:
        return (Path.cwd().resolve(),)
    roots = (Path(root).expanduser().resolve(strict=False) for root in raw_roots)
    return tuple(dict.fromkeys(roots))


def validate_web_stats_path(user_path: str) -> Path:
    """Resolve a web-supplied stats path and confine it to approved roots.

    Symlinks are resolved before containment is checked, preventing an allowed
    directory from linking to arbitrary server-readable locations.

    Args:
        user_path: Path supplied through the Streamlit application.

    Returns:
        The resolved path within an approved root.

    Raises:
        ValueError: If the path is outside every approved root.
    """
    candidate = normalize_user_path(user_path).expanduser().resolve(strict=False)
    for root in allowed_web_stats_roots():
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    allowed = ", ".join(str(root) for root in allowed_web_stats_roots())
    raise ValueError(
        f"Stats path '{candidate}' is outside the allowed web roots: {allowed}. "
        "Set RING5_ALLOWED_STATS_ROOTS on the server to authorize another root."
    )
