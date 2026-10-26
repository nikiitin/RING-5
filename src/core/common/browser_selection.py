"""Select one export browser without launching it or substituting an override."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserSelection:
    """A selected browser literal and its available executable, if any."""

    selected_path: str | None
    executable_path: str | None


def select_browser() -> BrowserSelection:
    """Resolve an explicit browser choice or the pinned provider's discovery.

    Every present BROWSER_PATH value is authoritative, including an empty string.
    Unavailable selections remain visible and never trigger another search.

    Returns:
        Selected literal and its executable path, without running any program.
    """
    # [impl->req~ring5.api.doctor~2]
    selected: str | None
    if "BROWSER_PATH" in os.environ:
        selected = os.environ["BROWSER_PATH"]
    else:
        from choreographer.browsers.chromium import Chromium

        selected = Chromium.find_browser(skip_local=False)
    executable = shutil.which(selected) if selected else None
    return BrowserSelection(selected, executable)
