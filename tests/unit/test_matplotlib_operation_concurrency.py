"""Public background exports and foreground renders share native global state safely."""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import os
from pathlib import Path
import threading
import time
from typing import Any, Literal

import matplotlib as mpl
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import pytest

import ring5
from src.core.models.visualization.figure_config import FigureConfig
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib


@pytest.mark.public_api
@pytest.mark.parametrize("first_operation", ["render", "export"])
@pytest.mark.parametrize("fails", [False, True])
def test_background_pgf_and_foreground_render_preserve_contexts(
    first_operation: Literal["render", "export"],
    fails: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Overlap real SDK operations at native boundaries without starting TeX."""
    entered_render = threading.Event()
    entered_export = threading.Event()
    requested_second = threading.Event()
    release_first = threading.Event()
    export_finished = threading.Event()
    observed: list[tuple[str, str, str | None]] = []
    original_backgrounds = FigureSpecToMatplotlib._apply_backgrounds
    monkeypatch.setitem(mpl.rcParams, "pgf.texsystem", "xelatex")
    monkeypatch.setitem(mpl.rcParams, "font.family", ["serif"])
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "123")

    def backgrounds(spec: FigureConfig, axes: Axes) -> None:
        entered_render.set()
        if first_operation == "render":
            assert release_first.wait(5)
        assert mpl.rcParams["pgf.texsystem"] == "xelatex"
        assert mpl.rcParams["font.family"] == ["monospace"]
        assert os.environ["SOURCE_DATE_EPOCH"] == "123"
        original_backgrounds(spec, axes)

    def savefig(figure: Figure, target: BytesIO, **kwargs: Any) -> None:
        entered_export.set()
        if first_operation == "export":
            assert release_first.wait(5)
        observed.append(
            (
                mpl.rcParams["pgf.texsystem"],
                mpl.rcParams["font.family"][0],
                os.environ.get("SOURCE_DATE_EPOCH"),
            )
        )
        try:
            if fails:
                raise RuntimeError("Deliberate native export failure")
            target.write(b"controlled native PGF")
        finally:
            export_finished.set()

    with ring5.Session() as session:
        data = ring5.Table.from_rows([{"x": "a", "y": 3.0}, {"x": "b", "y": 5.0}])
        native = session.plot("bar", data=data, config={"x": "x", "y": "y"}, engine="matplotlib")
        other = session.create_plot(
            "bar", data=data, config={"x": "x", "y": "y", "font_family": "monospace"}
        )
        monkeypatch.setattr(FigureSpecToMatplotlib, "_apply_backgrounds", backgrounds)
        monkeypatch.setattr(Figure, "savefig", savefig)

        def render() -> object:
            if first_operation == "export":
                requested_second.set()
            return session.render(other, engine="matplotlib")

        def submit() -> object:
            if first_operation == "render":
                requested_second.set()
            return session.export_submit(
                native, str(tmp_path / "measured.pgf"), tex_system="lualatex", deterministic=True
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            try:
                if first_operation == "render":
                    rendering = executor.submit(render)
                    assert entered_render.wait(5)
                    submitting = executor.submit(submit)
                    assert requested_second.wait(5)
                    assert not entered_export.wait(0.2)
                else:
                    submitting = executor.submit(submit)
                    assert entered_export.wait(5)
                    rendering = executor.submit(render)
                    assert requested_second.wait(5)
                    assert not entered_render.wait(0.2)
            finally:
                release_first.set()
            rendering.result(timeout=5)
            submitting.result(timeout=5)
        assert export_finished.wait(5)
        deadline = time.monotonic() + 5
        while True:
            info = session.background_jobs()[0]
            if info.terminal:
                break
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert info.status == ("failed" if fails else "completed")
        assert observed == [("lualatex", "serif", "0")]
    assert mpl.rcParams["pgf.texsystem"] == "xelatex"
    assert mpl.rcParams["font.family"] == ["serif"]
    assert os.environ["SOURCE_DATE_EPOCH"] == "123"
