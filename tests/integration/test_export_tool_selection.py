"""Public export, diagnostics and saved version facts share one browser selection."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any
from unittest.mock import MagicMock

import plotly.graph_objects as go
import pytest
from choreographer.browsers.chromium import Chromium

import ring5
from src.core.services import environment_metadata_service as metadata
from src.web.rendering import figure_export

pytestmark = pytest.mark.public_api


@pytest.fixture(autouse=True)
def _no_native_processes(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Tool-selection controls must not start native processes.")

    monkeypatch.setattr(subprocess, "run", fail)
    monkeypatch.setattr(subprocess.Popen, "__init__", fail)


@pytest.mark.parametrize("downloaded", [False, True])
@pytest.mark.parametrize("override", [None, "valid", "missing", "", "   "])
def test_actual_public_routes_agree_without_launching_browser_or_compiler(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    downloaded: bool,
    override: str | None,
) -> None:
    # [test->req~ring5.api.doctor~2]
    # [test->req~ring5.portfolio.environment-metadata~1]
    for name in ("downloaded", "path-browser", "override"):
        path = tmp_path / name
        path.write_text("never executed", encoding="utf-8")
        path.chmod(0o700)
    discovered = str(tmp_path / ("downloaded" if downloaded else "path-browser"))
    discover = MagicMock(return_value=discovered)
    monkeypatch.setattr(Chromium, "find_browser", discover)
    if override is None:
        monkeypatch.delenv("BROWSER_PATH", raising=False)
        selected = discovered
    else:
        selected = str(tmp_path / "override") if override == "valid" else override
        monkeypatch.setenv("BROWSER_PATH", selected)
    available = override in (None, "valid")
    versions: list[str | None] = []

    def version(executable: str | None, arguments: Any) -> str | None:
        versions.append(executable)
        return f"version:{executable}" if executable else None

    monkeypatch.setattr(metadata, "_run_version", version)
    calc = MagicMock(return_value=b"image")
    monkeypatch.setattr(figure_export.kaleido, "calc_fig_sync", calc)
    report = ring5.doctor(tex_system="lualatex")
    assert report.chrome.path == selected
    assert report.chrome.found is available
    assert report.tex_compiler.name == "lualatex"
    assert versions == []  # Presence checks never request a version or native process.
    facts = metadata._external_tool_versions()
    assert facts["chrome"] == (f"version:{selected}" if available else None)
    assert versions[0] == (selected if available else None)
    figure = go.Figure(go.Bar(x=["measured"], y=[3.0]))
    with ring5.Session() as session:
        if available:
            assert session.export_bytes(figure, fmt="png") == b"image"
            assert calc.call_args.kwargs["kopts"]["path"] == selected
            trace = figure.data[0]
            assert isinstance(trace, go.Bar)
            assert list(trace.y) == [3.0]
        else:
            with pytest.raises(ring5.DependencyMissingError) as caught:
                session.export_bytes(figure, fmt="png")
            assert repr(selected) in str(caught.value.__cause__)
            calc.assert_not_called()
    if override is not None:
        discover.assert_not_called()


def test_public_html_export_never_selects_a_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    selection = MagicMock(side_effect=AssertionError("HTML must not resolve a browser."))
    monkeypatch.setattr(figure_export, "select_browser", selection)
    monkeypatch.setenv("BROWSER_PATH", "")
    with ring5.Session() as session:
        data = session.export_bytes(go.Figure(), fmt="html")
    assert b"<html>" in data and b"plotly" in data.lower()
    selection.assert_not_called()
