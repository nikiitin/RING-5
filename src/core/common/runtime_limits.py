"""Early process defaults for native numerical runtimes."""

from __future__ import annotations

import os

DEFAULT_NATIVE_THREADS = 2
NATIVE_THREAD_ENV_VARS = (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)


def configure_native_thread_limits(default: int = DEFAULT_NATIVE_THREADS) -> None:
    """Set bounded thread defaults without replacing deployment overrides.

    Args:
        default: Positive thread count used only for variables that are unset.

    Raises:
        ValueError: If ``default`` is less than one.
    """
    if default < 1:
        raise ValueError("Native thread limit must be at least one")
    for variable in NATIVE_THREAD_ENV_VARS:
        os.environ.setdefault(variable, str(default))
