"""Native exports own temporary figure edits and leave submission responsive."""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import threading
import time
from typing import Any, cast

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from numpy.testing import assert_array_equal
import numpy as np
import pytest

import ring5
from src.web.rendering._matplotlib_copy import copy_matplotlib_figure
from src.web.rendering.figure_export import MatplotlibFormat, matplotlib_download_bytes
from src.web.rendering.latex_security import escape_latex_text


@pytest.mark.parametrize("registered", [False, True])
def test_native_snapshot_preserves_artist_ownership_without_registering_managers(
    registered: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = plt.figure() if registered else Figure()
    try:
        axis = original.subplots()
        axis.bar([0, 1], [3.0, 5.0])
        axis.set_title("Measured")
        managers = plt.get_fignums()
        monkeypatch.setattr(
            plt._get_backend_mod(),
            "new_figure_manager_given_figure",
            lambda *args, **kwargs: pytest.fail("Snapshot registered a pyplot manager"),
        )
        owned = copy_matplotlib_figure(original)
        assert owned is not original and owned.axes[0] is not axis
        assert owned.axes[0].figure is owned
        assert all(patch.figure is owned for patch in owned.axes[0].patches)
        assert [cast(Rectangle, patch).get_height() for patch in owned.axes[0].patches] == [
            3.0,
            5.0,
        ]
        owned.axes[0].set_title("Detached edit")
        assert axis.get_title() == "Measured"
        assert plt.get_fignums() == managers
    finally:
        plt.close(original)


@pytest.mark.parametrize("fmt", ["pgf", "pdf", "png", "svg"])
@pytest.mark.parametrize("fails", [False, True])
def test_byte_producer_mutates_only_a_private_native_copy(
    fmt: MatplotlibFormat, fails: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = plt.figure()
    try:
        axis = original.subplots()
        axis.bar([0, 1], [3.0, 5.0])
        title = r"literal $metric_1$ & 50%"
        axis.set_title(title)
        axis.title.set_usetex(True)
        managers = plt.get_fignums()

        def savefig(owned: Figure, target: BytesIO, **kwargs: Any) -> None:
            assert owned is not original
            assert owned.axes[0].get_title() == (
                escape_latex_text(title) if fmt == "pgf" else title
            )
            if fmt != "pgf":
                assert not owned.axes[0].title.get_usetex()
            assert axis.get_title() == title and axis.title.get_usetex()
            assert [cast(Rectangle, patch).get_height() for patch in owned.axes[0].patches] == [
                3.0,
                5.0,
            ]
            assert plt.get_fignums() == managers
            if fails:
                raise RuntimeError("Controlled native writer failure")
            target.write(b"owned native export")

        monkeypatch.setattr(Figure, "savefig", savefig)
        if fails:
            with pytest.raises(RuntimeError, match="Controlled native writer failure"):
                matplotlib_download_bytes(original, fmt)
        else:
            assert matplotlib_download_bytes(original, fmt) == b"owned native export"
        assert axis.get_title() == title and axis.title.get_usetex()
        assert [cast(Rectangle, patch).get_height() for patch in axis.patches] == [3.0, 5.0]
        assert plt.get_fignums() == managers
    finally:
        plt.close(original)


@pytest.mark.public_api
@pytest.mark.parametrize("fails", [False, True])
def test_export_submission_returns_while_another_native_export_is_held(
    fails: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered_export = threading.Event()
    release_export = threading.Event()
    titles: list[str] = []
    original = Figure()
    axis = original.subplots()
    title = r"literal $metric_1$ & 50%"
    axis.bar([0, 1], [3.0, 5.0])
    axis.set_title(title)

    def savefig(owned: Figure, target: BytesIO, **kwargs: Any) -> None:
        titles.append(owned.axes[0].get_title())
        first = len(titles) == 1
        if first:
            entered_export.set()
            assert release_export.wait(5)
        assert owned is not original
        assert [cast(Rectangle, patch).get_height() for patch in owned.axes[0].patches] == [
            3.0,
            5.0,
        ]
        if first and fails:
            raise RuntimeError("Controlled first native export failure")
        target.write(b"owned queued PGF")

    monkeypatch.setattr(Figure, "savefig", savefig)
    with ring5.Session() as session, ThreadPoolExecutor(max_workers=2) as executor:
        active = executor.submit(session.export_bytes, original, "pgf")
        try:
            assert entered_export.wait(5)
            assert axis.get_title() == title
            queued = executor.submit(session.export_submit, original, str(tmp_path / "queued.pgf"))
            info = queued.result(timeout=1)
            assert info.job_id and not release_export.is_set()
            axis.set_title("Changed after submission")
        finally:
            release_export.set()
        if fails:
            with pytest.raises(ring5.ExportError, match="Controlled first native export failure"):
                active.result(timeout=5)
        else:
            assert active.result(timeout=5) == b"owned queued PGF"
        deadline = time.monotonic() + 5
        while True:
            settled = next(job for job in session.background_jobs() if job.job_id == info.job_id)
            if settled.terminal:
                break
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert settled.status == "completed"
        assert (tmp_path / "queued.pgf").read_bytes() == b"owned queued PGF"
        assert titles == [escape_latex_text(title), escape_latex_text(title)]
        assert axis.get_title() == "Changed after submission"


class _MeasuredFigure(Figure):
    """A normal native subclass whose constructor requires domain metadata."""

    def __new__(cls, measurement: str) -> "_MeasuredFigure":
        return super().__new__(cls)

    def __init__(self, measurement: str) -> None:
        super().__init__()
        self.measurement = measurement


def test_native_snapshot_preserves_a_normal_figure_subclass() -> None:
    original = _MeasuredFigure("ipc")
    original.subplots().plot([1, 2], [3.0, 5.0])
    owned = copy_matplotlib_figure(original)
    assert type(owned) is _MeasuredFigure
    assert owned.measurement == "ipc"
    assert owned.axes[0].figure is owned
    assert_array_equal(owned.axes[0].lines[0].get_ydata(), [3.0, 5.0])


class _Noncopyable:
    def __deepcopy__(self, memo: dict[int, object]) -> object:
        raise TypeError("Controlled unsupported native state")


@pytest.mark.public_api
@pytest.mark.parametrize("invalid_mapping", [False, True])
def test_native_snapshot_failures_use_typed_errors_before_job_submission(
    invalid_mapping: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Figure()
    if invalid_mapping:
        monkeypatch.setattr(original, "__getstate__", lambda: [])
        error_type: type[Exception] = ValueError
        message = "state mapping"
    else:
        setattr(original, "unowned_state", _Noncopyable())
        error_type = TypeError
        message = "unsupported native state"
    with ring5.Session() as session:
        with pytest.raises(ring5.ExportError, match=message) as export_error:
            session.export_bytes(original, "png")
        assert isinstance(export_error.value.__cause__, error_type)
        with pytest.raises(ring5.JobError, match=message) as job_error:
            session.export_submit(original, str(tmp_path / "rejected.png"))
        assert isinstance(job_error.value.__cause__, error_type)
        assert session.background_jobs() == ()
        assert not (tmp_path / "rejected.png").exists()


@pytest.mark.parametrize("shared", [False, True])
@pytest.mark.parametrize("coordinate", ["x", "y"])
def test_native_snapshot_owns_categorical_unit_maps_and_shared_axis_identity(
    shared: bool, coordinate: str
) -> None:
    original, axes = plt.subplots(
        1, 2, sharex=shared and coordinate == "x", sharey=shared and coordinate == "y"
    )
    try:
        if coordinate == "x":
            axes[0].plot(["001", "NA"], [3.0, 5.0])
            axes[1].scatter(["NA", "nan"], [7.0, 11.0])
        else:
            axes[0].plot([3.0, 5.0], ["001", "NA"])
            axes[1].scatter([7.0, 11.0], ["NA", "nan"])
        owned = copy_matplotlib_figure(original)
        original_units = [getattr(axis, coordinate + "axis").get_units() for axis in axes]
        copied_units = [getattr(axis, coordinate + "axis").get_units() for axis in owned.axes]
        assert all(new is not old for new, old in zip(copied_units, original_units, strict=True))
        assert (copied_units[0] is copied_units[1]) is shared
        assert [dict(unit._mapping) for unit in copied_units] == [
            dict(unit._mapping) for unit in original_units
        ]
        measured_line = (
            owned.axes[0].lines[0].get_ydata()
            if coordinate == "x"
            else owned.axes[0].lines[0].get_xdata()
        )
        assert_array_equal(measured_line, [3.0, 5.0])
        numeric_index = 1 if coordinate == "x" else 0
        assert_array_equal(
            np.asarray(owned.axes[1].collections[0].get_offsets())[:, numeric_index], [7.0, 11.0]
        )
        before = dict(original_units[0]._mapping)
        copied_units[0].update(["owned-only"])
        assert "owned-only" not in original_units[0]._mapping
        assert "owned-only" not in original_units[1]._mapping
        original_units[0].update(["original-only"])
        assert original_units[0]._mapping["original-only"] == len(before)
        assert "original-only" not in copied_units[0]._mapping
    finally:
        plt.close(original)


@pytest.mark.public_api
def test_native_snapshot_includes_categorical_inset_axes() -> None:
    original = Figure()
    parent = original.subplots()
    inset = parent.inset_axes((0.5, 0.5, 0.4, 0.4))
    inset.plot(["001", "NA"], [3.0, 5.0])
    owned = copy_matplotlib_figure(original)
    copied_inset = owned.axes[0].child_axes[0]
    assert copied_inset.figure is owned
    assert copied_inset.xaxis.get_units() is not inset.xaxis.get_units()
    assert dict(copied_inset.xaxis.get_units()._mapping) == dict(inset.xaxis.get_units()._mapping)
    assert_array_equal(copied_inset.lines[0].get_ydata(), [3.0, 5.0])
    copied_inset.xaxis.get_units().update(["owned-only"])
    assert "owned-only" not in inset.xaxis.get_units()._mapping
    with ring5.Session() as session:
        assert session.export_bytes(original, "png").startswith(b"\x89PNG\r\n\x1a\n")
