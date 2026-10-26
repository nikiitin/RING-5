"""Headless figure export — engine inferred from the figure object.

Thin policy layer over ``src.web.rendering.figure_export`` (the byte
producers shared with the download UI): infers the engine from the figure
type, maps file extensions to formats, writes files, and converts
dependency failures into typed ring5 errors.
"""

from __future__ import annotations

from pathlib import Path
from typing import get_args

import plotly.graph_objects as go
from kaleido.errors import ChromeNotFoundError
from matplotlib.figure import Figure as MplFigure

from src.core.models.visualization.export_options import TexSystem, validate_tex_system
from src.web.rendering.figure_export import (
    MatplotlibFormat,
    PlotlyFormat,
    matplotlib_download_bytes,
    plotly_download_bytes,
)

from ring5.errors import DependencyMissingError, ExportError

# Derived from the canonical Literal types — one source of truth.
_PLOTLY_FORMATS: tuple[str, ...] = get_args(PlotlyFormat)
_MPL_FORMATS: tuple[str, ...] = get_args(MatplotlibFormat)

_CHROME_HINT = (
    "Run `ring5 install-chrome` and set BROWSER_PATH to its printed path, "
    "or export via the matplotlib engine / HTML format instead."
)


def export_bytes(
    fig: go.Figure | MplFigure,
    fmt: str,
    *,
    deterministic: bool = False,
    width: int = 700,
    height: int = 400,
    scale: int = 2,
    dpi: int = 300,
    tex_system: TexSystem = "xelatex",
) -> bytes:
    # [impl->req~ring5.export.public-boundary~1]
    """Export a rendered figure to image/document bytes.

    The engine is inferred from the figure type: ``go.Figure`` → plotly
    (png/svg/pdf/html via Kaleido/to_html), matplotlib ``Figure`` →
    savefig (pdf/pgf/png/svg). PGF uses the requested compiler, an empty
    custom preamble and escaped figure text.

    Args:
        fig: The figure ``Session.render`` returned.
        fmt: Target format (see above per engine).
        deterministic: Byte-identical re-exports (CI regression mode).
        width: Plotly image width in pixels (before scale).
        height: Plotly image height in pixels (before scale).
        scale: Plotly raster resolution multiplier.
        dpi: Matplotlib raster resolution.
        tex_system: PGF compiler: ``xelatex``, ``pdflatex`` or ``lualatex``.

    Raises:
        ExportError: Unsupported format for the figure's engine, or the
            export failed.
        DependencyMissingError: Kaleido found no Chrome-family browser
            (plotly png/svg/pdf), with the install hint.
    """
    try:
        compiler = validate_tex_system(tex_system)
    except ValueError as exc:
        raise ExportError(str(exc)) from exc
    if isinstance(fig, go.Figure):
        if fmt not in _PLOTLY_FORMATS:
            raise ExportError(
                f"Format {fmt!r} is not supported for plotly figures "
                f"(choose from {', '.join(_PLOTLY_FORMATS)}; "
                "pgf needs the matplotlib engine)."
            )
        try:
            return plotly_download_bytes(
                fig,
                # mypy: fmt is validated against _PLOTLY_FORMATS above
                fmt,  # type: ignore[arg-type]
                width=width,
                height=height,
                scale=scale,
                deterministic=deterministic,
            )
        except ChromeNotFoundError as exc:
            raise DependencyMissingError("chrome", _CHROME_HINT) from exc
        except (OSError, RuntimeError, ValueError) as exc:
            raise ExportError(f"Plotly {fmt} export failed: {exc}") from exc

    if isinstance(fig, MplFigure):
        if fmt not in _MPL_FORMATS:
            raise ExportError(
                f"Format {fmt!r} is not supported for matplotlib figures "
                f"(choose from {', '.join(_MPL_FORMATS)}; "
                "html needs the plotly engine)."
            )
        try:
            return matplotlib_download_bytes(
                fig,
                # mypy: fmt is validated against _MPL_FORMATS above
                fmt,  # type: ignore[arg-type]
                dpi=dpi,
                tex_system=compiler,
                deterministic=deterministic,
            )
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            # matplotlib pre-checks the TeX toolchain for PGF and raises a
            # RuntimeError naming the missing executable.
            missing_compiler = (
                isinstance(exc, FileNotFoundError) and exc.filename == compiler
            ) or (isinstance(exc, RuntimeError) and str(exc).startswith(f"{compiler!r} not found;"))
            if fmt == "pgf" and missing_compiler:
                raise DependencyMissingError(
                    compiler,
                    f"Install a TeX distribution providing {compiler} "
                    "(for example, `make install-latex`).",
                ) from exc
            raise ExportError(f"Matplotlib {fmt} export failed: {exc}") from exc

    raise ExportError(
        f"Cannot export object of type {type(fig).__name__} — expected a "
        "plotly go.Figure or a matplotlib Figure from Session.render()."
    )


def export_file(
    fig: go.Figure | MplFigure,
    path: str,
    *,
    fmt: str | None = None,
    deterministic: bool = False,
    width: int = 700,
    height: int = 400,
    scale: int = 2,
    dpi: int = 300,
    tex_system: TexSystem = "xelatex",
) -> str:
    # [impl->req~ring5.export.public-boundary~1]
    """Export a rendered figure to a file; format defaults from the extension.

    Args:
        fig: The figure ``Session.render`` returned.
        path: Output file path; parent directories are created.
        fmt: Explicit format; defaults to the file extension.
        deterministic: Byte-identical re-exports (CI regression mode).
        width: Plotly image width in pixels (before scale).
        height: Plotly image height in pixels (before scale).
        scale: Plotly raster resolution multiplier.
        dpi: Matplotlib raster resolution.
        tex_system: PGF compiler: ``xelatex``, ``pdflatex`` or ``lualatex``.

    Returns:
        The written file path.
    """
    target = Path(path)
    effective_fmt = fmt or target.suffix.lstrip(".").lower()
    if not effective_fmt:
        raise ExportError(f"No format given and no file extension to infer it from: {path!r}")

    data = export_bytes(
        fig,
        effective_fmt,
        deterministic=deterministic,
        width=width,
        height=height,
        scale=scale,
        dpi=dpi,
        tex_system=tex_system,
    )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    except OSError as exc:
        raise ExportError(f"Could not write export to {path!r}: {exc}") from exc
    return str(target)


# Re-exported for callers that want to type against the format unions.
__all__ = [
    "export_bytes",
    "export_file",
    "PlotlyFormat",
    "MatplotlibFormat",
]
