"""Engine-agnostic figure → bytes export (no Streamlit).

The byte-producing export path for both rendering engines, plus the
deterministic-output knobs CI regression needs. The download UI
(``src/web/pages/ui/plotting/download_section.py``) and the public
``ring5`` package both build on this module.

**Plotly path**: Kaleido v1 (``kaleido.calc_fig_sync``) for PNG/SVG/PDF,
``fig.to_html()`` for interactive HTML.
**Matplotlib path**: ``savefig`` for PDF/PGF/PNG/SVG.

Determinism notes (byte-identical re-exports of the same figure):
    - plotly PNG and matplotlib PGF are deterministic as-is.
    - plotly HTML embeds a random div uuid → fixed by ``div_id``.
    - plotly SVG embeds one random 6-hex uid in element ids; plotly PDF
      embeds Chrome's CreationDate/ModDate → both normalized when
      ``deterministic=True`` (length-preserving, so PDF xref stays valid).
    - matplotlib SVG/PDF embed dates and salted ids → fixed via
      ``SOURCE_DATE_EPOCH`` + ``svg.hashsalt`` when ``deterministic=True``.
"""

from __future__ import annotations

import io
import logging
import os
import re
import threading
from typing import TYPE_CHECKING, Any, Literal, cast

import kaleido
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from kaleido.errors import ChromeNotFoundError
from matplotlib.figure import Figure as MplFigure

from src.core.models.visualization.figure_config import FigureConfig

if TYPE_CHECKING:
    from matplotlib.typing import RcKeyType

logger = logging.getLogger(__name__)

# ── Type aliases ─────────────────────────────────────────────────

PlotlyFormat = Literal["png", "svg", "pdf", "html"]
MatplotlibFormat = Literal["pdf", "pgf", "png", "svg"]

# Kaleido raster export (png/svg/pdf) drives a headless Chrome subprocess that
# can intermittently stall under load. Plotly's ``fig.to_image()`` hardcodes a
# single 90s-timeout attempt, so a stall blocks for ~90s and then fails. We
# instead drive Kaleido directly with a short per-attempt timeout and retry —
# each attempt is a fresh oneshot Chrome (the app starts no persistent Kaleido
# server), so a retry recovers from a wedged browser.
_KALEIDO_ATTEMPT_TIMEOUT_S: int = 25
_KALEIDO_ATTEMPTS: int = 3

_FORMAT_MIME = {
    "png": "image/png",
    "svg": "image/svg+xml",
    "pdf": "application/pdf",
    "html": "text/html",
}

_FORMAT_EXT = {
    "png": ".png",
    "svg": ".svg",
    "pdf": ".pdf",
    "html": ".html",
}

_MPL_FORMAT_MIME = {
    "pdf": "application/pdf",
    "pgf": "application/x-pgf",
    "png": "image/png",
    "svg": "image/svg+xml",
}

_MPL_FORMAT_EXT = {
    "pdf": ".pdf",
    "pgf": ".pgf",
    "png": ".png",
    "svg": ".svg",
}

#: Stable div id used for deterministic HTML export.
DETERMINISTIC_DIV_ID = "ring5-figure"

#: Stable hash salt for deterministic matplotlib SVG ids.
DETERMINISTIC_SVG_HASHSALT = "ring5"

# Serializes matplotlib exports: savefig is not thread-safe, the rc_context
# blocks mutate process-global rcParams, and deterministic mode round-trips
# the process-global SOURCE_DATE_EPOCH env var — all of which race across
# concurrent exports without this lock.
_MPL_EXPORT_LOCK = threading.Lock()


# ── Deterministic-output normalizers ─────────────────────────────


def _normalize_plotly_svg(data: bytes) -> bytes:
    """Replace plotly.js's per-render random ids with fixed tokens.

    Three sources of nondeterminism:
    - One random 6-hex uid embedded in element ids (``defs-XXXXXX``,
      ``clipXXXXXXxyplot``, ``topdefs-XXXXXX``, gradient ids ``gXXXXXX-…``).
      Replacement is anchored to those id contexts — a bare global replace
      could corrupt coincidental matches inside base64-embedded rasters
      (heatmaps) or hex colors.
    - Colorbar gradients carry a random 8-hex suffix per gradient
      (``g<uid>-<8hex>``), remapped to a stable per-figure index.
    - Colorbars carry a random 6-hex class token (``cb<6hex>`` /
      ``ycb<6hex>tick``), remapped the same way.
    """
    match = re.search(rb"defs-([0-9a-f]{6})\b", data)
    if not match:
        return data
    uid = match.group(1)

    # Anchored uid rewrite: only inside the known id constructs.
    data = re.sub(
        rb"(defs-|clip|topdefs-|\bg)" + re.escape(uid),
        rb"\g<1>000000",
        data,
    )

    # Stable remap of gradient suffixes (order of first appearance). Single-pass callback so
    # a replacement token (also valid hex) can never be re-hit by a later substitution.
    grad_suffixes: list[bytes] = []
    for grad in re.finditer(rb"g000000-([0-9a-f]{8})\b", data):
        if grad.group(1) not in grad_suffixes:
            grad_suffixes.append(grad.group(1))
    grad_index = {s: i for i, s in enumerate(grad_suffixes)}
    data = re.sub(
        rb"g000000-([0-9a-f]{8})\b",
        lambda m: b"g000000-" + b"%08d" % grad_index[m.group(1)],
        data,
    )

    # Stable remap of colorbar class tokens (6-hex, independent of the main uid):
    # `class="cb<tok> colorbar"` and `class="ycb<tok>tick"` — matched only in those two
    # contexts, also single-pass to avoid the same re-hit cascade.
    cb_tokens: list[bytes] = []
    for cb in re.finditer(rb'"cb([0-9a-f]{6}) |ycb([0-9a-f]{6})tick', data):
        token = cb.group(1) or cb.group(2)
        if token not in cb_tokens:
            cb_tokens.append(token)
    cb_index = {tok: i for i, tok in enumerate(cb_tokens)}

    def _cb_sub(m: re.Match[bytes]) -> bytes:
        if m.group(1) is not None:  # "cb<tok>  (space-terminated)
            return b'"cb' + b"%06d" % cb_index[m.group(1)] + b" "
        return b"ycb" + b"%06d" % cb_index[m.group(2)] + b"tick"  # ycb<tok>tick

    data = re.sub(rb'"cb([0-9a-f]{6}) |ycb([0-9a-f]{6})tick', _cb_sub, data)
    return data


def _normalize_plotly_pdf(data: bytes) -> bytes:
    """Zero the digits of Chrome's /CreationDate and /ModDate stamps.

    Length-preserving (digit-for-digit), so the PDF xref offsets stay valid.
    These two fields are the only varying bytes across re-exports.
    """

    def _zero_digits(m: re.Match[bytes]) -> bytes:
        return m.group(1) + re.sub(rb"\d", b"0", m.group(2))

    return re.sub(rb"(/(?:CreationDate|ModDate) \(D:)([^)]*)", _zero_digits, data)


# ── Plotly export (Kaleido v1) ───────────────────────────────────


def plotly_download_bytes(
    fig: go.Figure,
    fmt: PlotlyFormat,
    *,
    width: int = 700,
    height: int = 400,
    scale: int = 2,
    deterministic: bool = False,
    div_id: str | None = None,
) -> bytes:
    """Export a Plotly figure to bytes.

    Args:
        fig: The Plotly figure to export.
        fmt: One of ``"png"``, ``"svg"``, ``"pdf"``, ``"html"``.
        width: Image width in pixels (before scale).  Ignored for HTML.
        height: Image height in pixels (before scale).  Ignored for HTML.
        scale: Resolution multiplier (only affects raster formats).
        deterministic: Make re-exports of the same figure byte-identical
            (fixed HTML div id, normalized SVG uid / PDF dates; PNG is
            deterministic as-is).
        div_id: Explicit div id for HTML export (implies a stable id;
            defaults to a random uuid unless ``deterministic`` is set).

    Returns:
        Raw bytes of the exported content.

    Raises:
        ValueError: If *fmt* is not a supported format.
        kaleido.errors.ChromeNotFoundError: No Chrome-family browser is
            available for raster/vector export (install one with
            ``kaleido_get_chrome`` or point ``BROWSER_PATH`` at one).
    """
    if fmt not in _FORMAT_MIME:
        raise ValueError(
            f"Unsupported format {fmt!r}. " f"Choose from {list(_FORMAT_MIME.keys())}."
        )

    if fmt == "html":
        effective_div_id = div_id or (DETERMINISTIC_DIV_ID if deterministic else None)
        html_str: str = fig.to_html(
            include_plotlyjs=True,
            full_html=True,
            div_id=effective_div_id,
        )
        return html_str.encode("utf-8")

    # Raster/vector via Kaleido — driven directly (not via fig.to_image) so we
    # can bound each attempt and retry with a fresh Chrome on a stall. For
    # vector formats scale has no effect, but the API accepts it.
    fig_dict = fig.to_dict()
    opts = {"format": fmt, "width": width, "height": height, "scale": scale}
    last_exc: Exception | None = None
    for attempt in range(1, _KALEIDO_ATTEMPTS + 1):
        try:
            data = cast(
                bytes,
                kaleido.calc_fig_sync(
                    fig_dict,
                    opts=opts,
                    kopts={"timeout": _KALEIDO_ATTEMPT_TIMEOUT_S},
                ),
            )
            if deterministic:
                if fmt == "svg":
                    data = _normalize_plotly_svg(data)
                elif fmt == "pdf":
                    data = _normalize_plotly_pdf(data)
            return data
        except ChromeNotFoundError:
            # No browser installed — retrying cannot help; propagate the
            # upstream error (its message carries the install instructions).
            raise
        except Exception as exc:  # Kaleido/Chrome stall or transient failure
            last_exc = exc
            logger.warning(
                "Kaleido %s export attempt %d/%d failed (%s); " "retrying with a fresh browser",
                fmt,
                attempt,
                _KALEIDO_ATTEMPTS,
                exc,
            )
    raise RuntimeError(
        f"Kaleido {fmt} export failed after {_KALEIDO_ATTEMPTS} attempts"
    ) from last_exc


def get_plotly_mime(fmt: PlotlyFormat) -> str:
    """Return the MIME type for a Plotly export format."""
    return _FORMAT_MIME[fmt]


def get_plotly_extension(fmt: PlotlyFormat) -> str:
    """Return the file extension (with dot) for a Plotly export format."""
    return _FORMAT_EXT[fmt]


# ── Matplotlib export (savefig + PGF) ────────────────────────────


def matplotlib_download_bytes(
    fig: MplFigure,
    fmt: MatplotlibFormat,
    *,
    dpi: int = 300,
    spec: FigureConfig | None = None,
    deterministic: bool = False,
) -> bytes:
    """Export a matplotlib Figure to image bytes via savefig.

    Args:
        fig: The matplotlib Figure to export.
        fmt: One of ``"pdf"``, ``"pgf"``, ``"png"``, ``"svg"``.
        dpi: Resolution for raster formats (PNG). Ignored by vector formats.
        spec: Optional FigureConfig for PGF preamble extraction.
        deterministic: Make re-exports byte-identical: sets
            ``SOURCE_DATE_EPOCH=0`` around savefig (zeroes the PDF/SVG date
            stamps, which are otherwise timezone-dependent) and a fixed
            ``svg.hashsalt`` (stable SVG clip-path ids). PNG and PGF are
            deterministic as-is.

    Returns:
        Raw bytes of the exported image.

    Raises:
        ValueError: If *fmt* is not a supported format.
    """
    if fmt not in _MPL_FORMAT_MIME:
        raise ValueError(
            f"Unsupported format {fmt!r}. " f"Choose from {list(_MPL_FORMAT_MIME.keys())}."
        )

    # The lock covers the whole export: savefig is not thread-safe, the
    # rc_context blocks mutate process-global rcParams, and the
    # SOURCE_DATE_EPOCH round-trip below would otherwise race a concurrent
    # export (losing determinism, or leaking epoch=0 process-wide).
    with _MPL_EXPORT_LOCK:
        saved_epoch: str | None = None
        if deterministic:
            saved_epoch = os.environ.get("SOURCE_DATE_EPOCH")
            os.environ["SOURCE_DATE_EPOCH"] = "0"

        try:
            buf = io.BytesIO()
            det_rc: dict[RcKeyType, Any] = (
                {"svg.hashsalt": DETERMINISTIC_SVG_HASHSALT} if deterministic else {}
            )

            if fmt == "pgf":
                preamble = spec.latex_extra_preamble if spec else ""
                with plt.rc_context(
                    {
                        "pgf.texsystem": "xelatex",
                        "pgf.preamble": preamble,
                        "pgf.rcfonts": True,
                        **det_rc,
                    }
                ):
                    # NOTE: PGF deliberately omits bbox_inches="tight" — the exported
                    # physical size must equal the matplotlib figsize so a LaTeX \input fills
                    # a known column width. PDF/PNG/SVG below ARE tight-cropped, so the same
                    # figure is a different size across formats by design (see docs).
                    fig.savefig(buf, format="pgf", backend="pgf")
            elif fmt == "pdf":
                with plt.rc_context(det_rc):
                    fig.savefig(buf, format="pdf", dpi=dpi, bbox_inches="tight")
            elif fmt == "png":
                # rc_context ensures usetex is off – dvipng may not be installed
                # and another caller may have turned it on globally.
                with plt.rc_context({"text.usetex": False, **det_rc}):
                    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", backend="agg")
            elif fmt == "svg":
                with plt.rc_context(det_rc):
                    fig.savefig(buf, format="svg", bbox_inches="tight")

            buf.seek(0)
            return buf.read()
        finally:
            if deterministic:
                if saved_epoch is None:
                    os.environ.pop("SOURCE_DATE_EPOCH", None)
                else:
                    os.environ["SOURCE_DATE_EPOCH"] = saved_epoch


def get_matplotlib_mime(fmt: MatplotlibFormat) -> str:
    """Return the MIME type for a matplotlib export format."""
    return _MPL_FORMAT_MIME[fmt]


def get_matplotlib_extension(fmt: MatplotlibFormat) -> str:
    """Return the file extension (with dot) for a matplotlib export format."""
    return _MPL_FORMAT_EXT[fmt]
