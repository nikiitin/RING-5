"""PGF requests honor compiler choices without accepting executable TeX input."""

from io import BytesIO
import os
from pathlib import Path
from typing import Any, cast

import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import pytest

import ring5
from src.core.models.visualization.export_options import TEX_SYSTEMS, TexSystem, validate_tex_system
from src.core.models.visualization.figure_config import FigureConfig
from src.web.rendering.figure_export import matplotlib_download_bytes
from src.web.rendering.latex_security import escape_latex_text


@pytest.mark.parametrize("field", ["latex_extra_preamble", "download_format", "enable_editable"])
@pytest.mark.public_api
def test_inert_settings_reject_before_plot_registration(field: str) -> None:
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="Unsupported plot configuration keys"):
            session.create_plot(
                "bar",
                data=ring5.Table.from_rows([{"x": "a", "y": 3.0}]),
                config={"x": "x", "y": "y", field: "unused"},
            )
        assert session.api.state_manager.get_plots() == []


@pytest.mark.parametrize("field", ["latex_extra_preamble", "unknown_figure_field"])
def test_serialized_figure_spec_rejects_unsupported_fields(field: str) -> None:
    original = FigureConfig(title="Measured").to_dict()
    changed = {**original, field: "unsupported"}
    with pytest.raises(TypeError, match="Unsupported figure configuration fields"):
        FigureConfig.from_dict(changed)
    assert FigureConfig.from_dict(original).to_dict() == original


@pytest.mark.parametrize("compiler", TEX_SYSTEMS)
@pytest.mark.parametrize("deterministic", [False, True])
@pytest.mark.parametrize("fails", [False, True])
def test_pgf_savefig_receives_safe_request_and_restores_state(
    compiler: TexSystem, deterministic: bool, fails: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    # [test->req~ring5.figure.matplotlib-tex-system~1]
    # [test->req~ring5.quality.safe-output-formatting~1]
    figure = Figure()
    axis = figure.subplots()
    axis.bar([0, 1], [3.0, 4.0])
    monkeypatch.setitem(mpl.rcParams, "pgf.preamble", r"\input{untrusted-global-preamble}")
    original_title = r"\input{private} $value_1$ & 50%"
    axis.set_title(original_title)
    texts_before = [(text, text.get_text()) for text in figure.findobj(mpl.text.Text)]
    rc_before = (mpl.rcParams["pgf.texsystem"], mpl.rcParams["pgf.preamble"])
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "123")
    calls: list[dict[str, Any]] = []

    def savefig(owned: Figure, buffer: BytesIO, **kwargs: Any) -> None:
        calls.append(kwargs)
        assert owned is not figure
        assert mpl.rcParams["pgf.texsystem"] == compiler
        assert mpl.rcParams["pgf.preamble"] == ""
        assert owned.axes[0].get_title() == escape_latex_text(original_title)
        assert axis.get_title() == original_title
        assert [(text, text.get_text()) for text in figure.findobj(mpl.text.Text)] == texts_before
        assert os.environ["SOURCE_DATE_EPOCH"] == ("0" if deterministic else "123")
        assert [cast(Rectangle, bar).get_height() for bar in owned.axes[0].patches] == [3.0, 4.0]
        if fails:
            raise RuntimeError("Deliberate savefig failure")
        buffer.write(b"PGF policy verified without TeX execution")

    monkeypatch.setattr(Figure, "savefig", savefig)
    if fails:
        with pytest.raises(RuntimeError, match="Deliberate savefig failure"):
            matplotlib_download_bytes(
                figure, "pgf", tex_system=validate_tex_system(compiler), deterministic=deterministic
            )
    else:
        assert (
            matplotlib_download_bytes(
                figure, "pgf", tex_system=validate_tex_system(compiler), deterministic=deterministic
            )
            == b"PGF policy verified without TeX execution"
        )
    assert calls == [{"format": "pgf", "backend": "pgf"}]
    assert [(text, text.get_text()) for text in figure.findobj(mpl.text.Text)] == texts_before
    assert (mpl.rcParams["pgf.texsystem"], mpl.rcParams["pgf.preamble"]) == rc_before
    assert os.environ["SOURCE_DATE_EPOCH"] == "123"


@pytest.mark.parametrize(
    "compiler", ["", "XeLaTeX", "/usr/bin/xelatex", "xelatex --shell-escape", None, 1]
)
@pytest.mark.public_api
def test_invalid_compiler_rejects_before_native_export(
    compiler: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    figure = Figure()
    monkeypatch.setattr(figure, "savefig", lambda *args, **kwargs: pytest.fail("Unexpected export"))
    with pytest.raises(ValueError, match="TeX system must be one of"):
        matplotlib_download_bytes(figure, "pgf", tex_system=compiler)  # type: ignore[arg-type]
    with ring5.Session() as session:
        with pytest.raises(ring5.ExportError, match="TeX system must be one of"):
            session.export_bytes(figure, "pgf", tex_system=compiler)  # type: ignore[arg-type]


@pytest.mark.parametrize("compiler", TEX_SYSTEMS)
@pytest.mark.public_api
def test_public_export_bytes_and_file_use_the_same_compiler_policy(
    compiler: TexSystem, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    figure = Figure()
    axis = figure.subplots()
    axis.plot([0, 1], [3.0, 4.0])
    calls: list[str] = []

    def savefig(buffer: BytesIO, **kwargs: Any) -> None:
        calls.append(mpl.rcParams["pgf.texsystem"])
        assert mpl.rcParams["pgf.preamble"] == ""
        assert kwargs == {"format": "pgf", "backend": "pgf"}
        buffer.write(b"safe compiler request")

    monkeypatch.setattr(figure, "savefig", savefig)
    with ring5.Session() as session:
        assert session.export_bytes(figure, "pgf", tex_system=compiler) == b"safe compiler request"
        target = tmp_path / "measured.pgf"
        assert session.export(figure, str(target), tex_system=compiler) == str(target)
        assert target.read_bytes() == b"safe compiler request"
    assert calls == [compiler, compiler]


@pytest.mark.parametrize("compiler", TEX_SYSTEMS)
@pytest.mark.public_api
def test_public_dependency_error_names_the_selected_compiler(
    compiler: TexSystem, monkeypatch: pytest.MonkeyPatch
) -> None:
    figure = Figure()

    def savefig(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError(f"'{compiler}' not found; install it")

    monkeypatch.setattr(figure, "savefig", savefig)
    with ring5.Session() as session:
        with pytest.raises(ring5.DependencyMissingError, match=compiler):
            session.export_bytes(figure, "pgf", tex_system=compiler)


@pytest.mark.parametrize("compiler", TEX_SYSTEMS)
@pytest.mark.public_api
def test_named_compiler_in_unrelated_failure_is_an_export_error(
    compiler: TexSystem, monkeypatch: pytest.MonkeyPatch
) -> None:
    figure = Figure()

    def savefig(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError(f"Cannot render figure titled {compiler}")

    monkeypatch.setattr(figure, "savefig", savefig)
    with ring5.Session() as session:
        with pytest.raises(ring5.ExportError, match="Cannot render figure"):
            session.export_bytes(figure, "pgf", tex_system=compiler)


@pytest.mark.parametrize("compiler", TEX_SYSTEMS)
@pytest.mark.public_api
def test_structured_missing_compiler_is_a_dependency_error(
    compiler: TexSystem, monkeypatch: pytest.MonkeyPatch
) -> None:
    figure = Figure()

    def savefig(*args: Any, **kwargs: Any) -> None:
        raise FileNotFoundError(2, "No such file or directory", compiler)

    monkeypatch.setattr(figure, "savefig", savefig)
    with ring5.Session() as session:
        with pytest.raises(ring5.DependencyMissingError, match=compiler):
            session.export_bytes(figure, "pgf", tex_system=compiler)


@pytest.mark.public_api
def test_missing_other_file_is_an_export_error(monkeypatch: pytest.MonkeyPatch) -> None:
    figure = Figure()

    def savefig(*args: Any, **kwargs: Any) -> None:
        raise FileNotFoundError(2, "No such file or directory", "measurement-data")

    monkeypatch.setattr(figure, "savefig", savefig)
    with ring5.Session() as session:
        with pytest.raises(ring5.ExportError, match="measurement-data"):
            session.export_bytes(figure, "pgf")
