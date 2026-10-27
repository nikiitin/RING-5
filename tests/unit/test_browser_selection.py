"""Browser selection preserves the request without launching or guessing another browser."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from choreographer.browsers.chromium import Chromium
from src.core.common.browser_selection import BrowserSelection, select_browser


def _executable(path: Path) -> str:
    path.write_text("not executed", encoding="utf-8")
    path.chmod(0o700)
    return str(path)


@pytest.mark.parametrize("kind", ["absolute", "relative", "command"])
def test_present_override_resolves_executable_without_vendor_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    browser_name = "chrome"
    executable = _executable(tmp_path / browser_name)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path))
    selected = (
        executable
        if kind == "absolute"
        else f"./{browser_name}" if kind == "relative" else browser_name
    )
    monkeypatch.setenv("BROWSER_PATH", selected)
    discovery = MagicMock(side_effect=AssertionError("Override must not fall back."))
    monkeypatch.setattr(Chromium, "find_browser", discovery)

    result = select_browser()

    assert result.selected_path == selected
    assert result.executable_path is not None
    assert Path(result.executable_path).samefile(executable)
    discovery.assert_not_called()


@pytest.mark.parametrize(
    "kind", ["empty", "whitespace", "missing", "directory", "not-executable", "broken-link"]
)
def test_invalid_override_remains_selected_without_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    path = tmp_path / kind
    if kind == "directory":
        path.mkdir()
    elif kind == "not-executable":
        path.write_text("not executed", encoding="utf-8")
        path.chmod(0o600)
    elif kind == "broken-link":
        path.symlink_to(tmp_path / "absent")
    selected = "" if kind == "empty" else "   " if kind == "whitespace" else str(path)
    monkeypatch.setenv("BROWSER_PATH", selected)
    discovery = MagicMock(side_effect=AssertionError("Invalid override must remain visible."))
    monkeypatch.setattr(Chromium, "find_browser", discovery)

    assert select_browser() == BrowserSelection(selected, None)
    discovery.assert_not_called()


@pytest.mark.parametrize("available", [False, True])
def test_absent_override_uses_exact_required_provider_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, available: bool
) -> None:
    monkeypatch.delenv("BROWSER_PATH", raising=False)
    selected = _executable(tmp_path / "downloaded") if available else None
    discovery = MagicMock(return_value=selected)
    monkeypatch.setattr(Chromium, "find_browser", discovery)

    assert select_browser() == BrowserSelection(selected, selected)
    discovery.assert_called_once_with(skip_local=False)


def test_provider_failure_remains_visible_without_compatibility_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BROWSER_PATH", raising=False)
    error = RuntimeError("required provider failed")
    monkeypatch.setattr(Chromium, "find_browser", MagicMock(side_effect=error))

    with pytest.raises(RuntimeError) as caught:
        select_browser()
    assert caught.value is error


def test_browser_selection_is_immutable() -> None:
    selected: Any = BrowserSelection("chrome", "/tools/chrome")
    with pytest.raises(FrozenInstanceError):
        selected.selected_path = "other"
