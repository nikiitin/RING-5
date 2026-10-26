"""Explicit source-owned color channels and finite opacity projection.

Builders declare intrinsic channels before attenuation. Connectors preflight all
affected channels, then apply plans in their existing series-styling phase.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Literal, NoReturn, cast

import numpy as np
from matplotlib.artist import Artist
from matplotlib.collections import Collection, QuadMesh
from matplotlib.colors import Colormap, to_rgba, to_rgba_array
from matplotlib.container import Container
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.text import Text

from src.core.common.opacity import require_opacity
from src.web.rendering._color_utils import color_with_alpha, css_color_to_matplotlib

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from plotly.basedatatypes import BaseTraceType
    from src.core.models.visualization.figure_config import FigureConfig
    from src.web.rendering._render_result import (
        MatplotlibRenderResult,
        MatplotlibTraceBinding,
        PlotlyRenderResult,
    )

_Kind = Literal["line", "marker_face", "marker_edge", "face", "edge", "hatch", "text", "cmap"]
_SEMANTIC_FAMILIES = frozenset({"waterfall", "sankey", "parallel_coordinates", "heatmap"})


def _selected_opacity(spec: FigureConfig, ordinal: int, name: str) -> float | None:
    positional = (
        spec.series_styles[ordinal % len(spec.series_styles)] if spec.series_styles else None
    )
    named = spec.trace_overrides.get(name)
    for style in (named, positional):
        if style is not None and style.opacity is not None:
            return require_opacity(style.opacity)
    return None


def _css_alpha(color: str) -> float:
    if not isinstance(color, str):
        raise ValueError("Owned source colors must be concrete CSS text.")
    try:
        return float(to_rgba(css_color_to_matplotlib(color))[3])
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Opacity requires a concrete RGB, HSL, hexadecimal or named color; "
            "convert unresolved colors before rendering."
        ) from exc


def _css_project(color: str, factor: float) -> str:
    return color_with_alpha(color, _css_alpha(color) * factor)


def validate_parallel_appearance(opacity: object, color: object, colorscale: object) -> None:
    """Reject selected-path transparency unavailable in native Plotly Parcoords.

    Args:
        opacity: Concrete effective source opacity.
        color: Selected-path static color, or numeric values owned by the native trace.
        colorscale: Selected-path colorscale when numeric colors are used.

    Raises:
        ValueError: Selected opacity or embedded alpha cannot be represented by both engines.
    """
    # [impl->req~ring5.figure.series-styling~2]
    if require_opacity(opacity) != 1.0:
        raise ValueError("Parallel coordinates require selected source opacity 1 in both engines.")
    colors: tuple[str, ...]
    if isinstance(color, str):
        colors = (color,)
    elif colorscale is not None and not isinstance(colorscale, str):
        if not isinstance(colorscale, (list, tuple)) or any(
            not isinstance(stop, (list, tuple)) or len(stop) != 2 or not isinstance(stop[1], str)
            for stop in colorscale
        ):
            raise ValueError("Parallel coordinates require concrete positioned colorscale stops.")
        colors = tuple(stop[1] for stop in colorscale)
    else:
        # Named native scales and an omitted native color use opaque selected palettes.
        colors = ()
    if any(_css_alpha(value) != 1.0 for value in colors):
        raise ValueError(
            "Parallel coordinates require opaque selected colors and colorscale stops "
            "because native Plotly discards their alpha."
        )


class _OpacityColormap(Colormap):
    """An exact owned map with source attenuation applied only to returned alpha."""

    def __init__(self, intrinsic: Colormap, opacity: float) -> None:
        super().__init__(f"ring5_opacity_{intrinsic.name}", intrinsic.N)
        self.intrinsic = intrinsic
        self.opacity = opacity
        self.colorbar_extend = intrinsic.colorbar_extend

    def __call__(self, values: Any, alpha: Any = None, bytes: bool = False) -> Any:
        rgba = np.array(self.intrinsic(values, alpha=alpha, bytes=False), copy=True)
        rgba[..., 3] *= self.opacity
        if bytes:
            rgba = (rgba * 255).astype(np.uint8)
        return tuple(rgba) if rgba.ndim == 1 else rgba

    def __copy__(self) -> _OpacityColormap:
        copied = _OpacityColormap(self.intrinsic.copy(), self.opacity)
        copied.colorbar_extend = self.colorbar_extend
        return copied

    def __eq__(self, other: object) -> bool:
        # Delegation has no sampled LUT; compare its declared mapping and factor.
        return (
            isinstance(other, _OpacityColormap)
            and self.opacity == other.opacity
            and self.colorbar_extend == other.colorbar_extend
            and self.intrinsic == other.intrinsic
        )

    def copy(self) -> _OpacityColormap:
        """Copy the intrinsic map and source attenuation independently.

        Returns:
            An independent native map with identical actual color mapping.
        """
        return self.__copy__()

    def get_bad(self) -> Any:
        """Return the masked color with source attenuation.

        Returns:
            Independent RGBA values preserving intrinsic color components.
        """
        return self._special("bad")

    def get_under(self) -> Any:
        """Return the below-range color with source attenuation.

        Returns:
            Independent RGBA values preserving intrinsic color components.
        """
        return self._special("under")

    def get_over(self) -> Any:
        """Return the above-range color with source attenuation.

        Returns:
            Independent RGBA values preserving intrinsic color components.
        """
        return self._special("over")

    def _special(self, name: str) -> Any:
        value = np.array(getattr(self.intrinsic, f"get_{name}")(), copy=True)
        value[3] *= self.opacity
        return value

    def is_gray(self) -> bool:
        """Report whether the intrinsic map has equal RGB components.

        Returns:
            Whether every intrinsic color is grayscale.
        """
        return bool(self.intrinsic.is_gray())

    def _reject_edit(self) -> NoReturn:
        raise ValueError(
            "Replace the native colormap or declare a new intrinsic context "
            "before editing mapped colors."
        )

    def set_bad(self, color: Any = "k", alpha: Any = None) -> None:
        """Reject an undeclared change to the masked intrinsic channel.

        Args:
            color: Requested native color.
            alpha: Requested replacement alpha.

        Raises:
            ValueError: A new intrinsic context is required before changing mapped colors.
        """
        self._reject_edit()

    def set_under(self, color: Any = "k", alpha: Any = None) -> None:
        """Reject an undeclared change to the below-range intrinsic channel.

        Args:
            color: Requested native color.
            alpha: Requested replacement alpha.

        Raises:
            ValueError: A new intrinsic context is required before changing mapped colors.
        """
        self._reject_edit()

    def set_over(self, color: Any = "k", alpha: Any = None) -> None:
        """Reject an undeclared change to the above-range intrinsic channel.

        Args:
            color: Requested native color.
            alpha: Requested replacement alpha.

        Raises:
            ValueError: A new intrinsic context is required before changing mapped colors.
        """
        self._reject_edit()

    def set_extremes(self, *, bad: Any = None, under: Any = None, over: Any = None) -> None:
        """Reject undeclared replacements of intrinsic exceptional colors.

        Args:
            bad: Requested masked-data color, or None to retain it.
            under: Requested below-range color, or None to retain it.
            over: Requested above-range color, or None to retain it.

        Raises:
            ValueError: A requested color requires a new intrinsic context.
        """
        if any(value is not None for value in (bad, under, over)):
            self._reject_edit()

    def with_extremes(self, *, bad: Any = None, under: Any = None, over: Any = None) -> Colormap:
        """Reject undeclared replacements of intrinsic exceptional colors.

        Args:
            bad: Requested masked-data color, or None to retain it.
            under: Requested below-range color, or None to retain it.
            over: Requested above-range color, or None to retain it.

        Returns:
            An independent unchanged map when no replacement colors are requested.

        Raises:
            ValueError: A requested color requires a new intrinsic context.
        """
        if any(value is not None for value in (bad, under, over)):
            self._reject_edit()
        return self.copy()

    def with_alpha(self, alpha: Any) -> Colormap:
        """Reject replacement of source-owned mapped alpha.

        Args:
            alpha: Requested native alpha.

        Raises:
            ValueError: Alpha changes require an explicit source opacity or intrinsic context.
        """
        self._reject_edit()

    def resampled(self, lutsize: int) -> Colormap:
        """Resample the intrinsic map while retaining source attenuation.

        Args:
            lutsize: Requested number of intrinsic color entries.

        Returns:
            An independently resampled map with the same source opacity.
        """
        return _OpacityColormap(self.intrinsic.resampled(lutsize), self.opacity)

    def reversed(self, name: str | None = None) -> Colormap:
        """Reverse the intrinsic map while retaining source attenuation.

        Args:
            name: Optional name for the reversed intrinsic map.

        Returns:
            An independently reversed map with the same source opacity.
        """
        return _OpacityColormap(self.intrinsic.reversed(name), self.opacity)


@dataclass(frozen=True, slots=True, eq=False)
class _MplChannel:
    artist: Artist
    kind: _Kind
    intrinsic: Any
    factor: float = 1.0
    series_color: bool = False


@dataclass(frozen=True, slots=True, eq=False)
class _MplSnapshot:
    opacity: float | None
    channels: tuple[_MplChannel, ...]


@dataclass(slots=True, eq=False)
class MatplotlibAppearance:
    """One source's known intrinsic channels and mutable native output snapshot."""

    snapshot: _MplSnapshot
    labels: tuple[Text, ...] = ()
    label_spec: tuple[Any, ...] | None = None

    @classmethod
    def unmanaged(cls) -> MatplotlibAppearance:
        """Declare unknown native appearance for nonappearance operations only.

        Returns:
            An explicit capability declaration that preserves existing native colors.
        """
        return cls(_MplSnapshot(None, ()))

    def validate(self, axes: Axes, owned: set[int]) -> set[int]:
        """Validate channel surfaces and declared generated text against native ownership."""
        label_ids = {id(label) for label in self.labels}
        attached = {id(item) for item in axes.get_children()}
        seen: set[tuple[int, str]] = set()
        for channel in self.snapshot.channels:
            key = (id(channel.artist), channel.kind)
            if (
                key in seen
                or id(channel.artist) not in owned | label_ids
                or channel.artist.axes is not axes
                or channel.artist.figure is not axes.figure
                or id(channel.artist) not in attached
            ):
                raise ValueError(
                    "Source appearance channels require their actual uniquely owned artists."
                )
            allowed: dict[str, type[Artist] | tuple[type[Artist], ...]] = {
                "line": Line2D,
                "marker_face": Line2D,
                "marker_edge": Line2D,
                "face": (Patch, Collection),
                "edge": (Patch, Collection),
                "hatch": Patch,
                "text": Text,
                "cmap": QuadMesh,
            }
            if channel.kind not in allowed or not isinstance(channel.artist, allowed[channel.kind]):
                raise ValueError(
                    "An appearance channel requires its declared supported native surface."
                )
            if channel.kind == "cmap":
                if not isinstance(channel.intrinsic, Colormap):
                    raise ValueError(
                        "A mapped appearance channel requires its known intrinsic colormap."
                    )
            else:
                rgba = np.asarray(channel.intrinsic, dtype=float)
                valid_shape = rgba.shape == (4,) or (
                    isinstance(channel.artist, Collection)
                    and (rgba.shape == (0,) or (rgba.ndim == 2 and rgba.shape[1] == 4))
                )
                if (
                    not valid_shape
                    or not np.isfinite(rgba).all()
                    or np.any((rgba < 0) | (rgba > 1))
                ):
                    raise ValueError(
                        "Intrinsic appearance channels require finite RGBA values in [0, 1]."
                    )
            seen.add(key)
            require_opacity(channel.factor, field="appearance factor")
        if len(label_ids) != len(self.labels) or any(
            not isinstance(label, Text) or id(label) in owned for label in self.labels
        ):
            raise ValueError("Generated data labels require unique declared source ownership.")
        if self.snapshot.opacity is None:
            if self.snapshot.channels or self.labels:
                raise ValueError("Unmanaged appearance cannot claim known intrinsic channels.")
        else:
            require_opacity(self.snapshot.opacity)
        return label_ids


def _members(owned: Sequence[Artist | Container]) -> tuple[Artist, ...]:
    result: list[Artist] = []
    seen: set[int] = set()

    def visit(value: Artist | Container) -> None:
        if id(value) in seen:
            return
        seen.add(id(value))
        if isinstance(value, Container):
            for child in value.get_children():
                visit(child)
        elif isinstance(value, Artist):
            result.append(value)
        else:
            raise ValueError("Appearance targets must be declared native artists or containers.")

    for value in owned:
        visit(value)
    return tuple(result)


def _read(channel: _MplChannel) -> Any:
    artist = channel.artist
    if channel.kind == "cmap":
        return artist.get_cmap()  # type: ignore[attr-defined]
    getter = {
        "line": "get_color",
        "marker_face": "get_markerfacecolor",
        "marker_edge": "get_markeredgecolor",
        "face": "get_facecolor",
        "edge": "get_edgecolor",
        "hatch": "get_hatchcolor",
        "text": "get_color",
    }[channel.kind]
    value = getattr(artist, getter)()
    if isinstance(artist, Collection):
        return to_rgba_array(value)
    return to_rgba(value)


def _intrinsic(channel: _MplChannel) -> Any:
    value = _read(channel)
    if channel.kind == "cmap":
        return value.copy()
    array = np.asarray(value, dtype=float)
    if array.ndim == 1:
        return tuple(float(item) for item in array)
    return tuple(tuple(float(item) for item in row) for row in array)


def _project(channel: _MplChannel, opacity: float) -> Any:
    factor = opacity * channel.factor
    if channel.kind == "cmap":
        return _OpacityColormap(channel.intrinsic, factor)
    rgba = np.array(channel.intrinsic, dtype=float, copy=True)
    if isinstance(channel.artist, Collection) and not rgba.size:
        return np.empty((0, 4), dtype=float)
    if rgba.size:
        rgba[..., 3] *= factor
    return tuple(rgba) if rgba.ndim == 1 else rgba.reshape((-1, 4))


def _supports_projection(channel: _MplChannel) -> bool:
    return channel.artist.get_alpha() is None and not (
        channel.kind != "cmap"
        and isinstance(channel.artist, Collection)
        and channel.artist.get_array() is not None
    )


def _matches(channel: _MplChannel, opacity: float) -> bool:
    if not _supports_projection(channel):
        return False
    current = _read(channel)
    if channel.kind == "cmap":
        return (
            isinstance(current, _OpacityColormap)
            and current.intrinsic is channel.intrinsic
            and current.opacity == opacity * channel.factor
        )
    return bool(np.array_equal(np.asarray(current), np.asarray(_project(channel, opacity))))


def _write(channel: _MplChannel, value: Any) -> None:
    artist = channel.artist
    artist.set_alpha(None)
    setter = {
        "line": "set_color",
        "marker_face": "set_markerfacecolor",
        "marker_edge": "set_markeredgecolor",
        "face": "set_facecolor",
        "edge": "set_edgecolor",
        "hatch": "set_hatchcolor",
        "text": "set_color",
        "cmap": "set_cmap",
    }[channel.kind]
    getattr(artist, setter)(value)


def seed_matplotlib_appearance(
    owned: Sequence[Artist | Container],
    *,
    opacity: float,
    series_channels: Sequence[tuple[Artist, str]] = (),
    factors: Sequence[tuple[Artist, float]] = (),
) -> MatplotlibAppearance:
    """Declare creation-time intrinsic colors and project one source opacity.

    Args:
        owned: Actual source emissions constructed without scalar native alpha.
        opacity: Concrete initial source opacity.
        series_channels: Exact channels an explicit main-series color may replace.
        factors: Explicit family-local factors for particular owned artists.

    Returns:
        Independently owned appearance output for an explicit native binding.

    Raises:
        ValueError: An intrinsic channel, scalar alpha or family factor is unsupported.
    """
    value = require_opacity(opacity)
    roles = {(id(artist), kind) for artist, kind in series_channels}
    local = {
        id(artist): require_opacity(factor, field="appearance factor") for artist, factor in factors
    }
    channels: list[_MplChannel] = []
    for artist in _members(owned):
        if artist.get_alpha() is not None:
            raise ValueError("Declare intrinsic source colors before applying native scalar alpha.")
        if isinstance(artist, QuadMesh):
            kinds: tuple[_Kind, ...] = ("cmap",)
        elif isinstance(artist, Line2D):
            kinds = ("line", "marker_face", "marker_edge")
        elif isinstance(artist, Patch):
            kinds = ("face", "edge", "hatch")
        elif isinstance(artist, Collection):
            if artist.get_array() is not None:
                raise ValueError(
                    "Data-mapped collections require explicit unmanaged appearance "
                    "or a new supported intrinsic context."
                )
            kinds = ("face", "edge")
        elif isinstance(artist, Text):
            kinds = ("text",)
        else:
            raise ValueError(f"Unsupported owned appearance artist: {type(artist).__name__}.")
        for kind in kinds:
            channel = _MplChannel(
                artist, kind, None, local.get(id(artist), 1.0), (id(artist), kind) in roles
            )
            channels.append(replace(channel, intrinsic=_intrinsic(channel)))
    output = MatplotlibAppearance(_MplSnapshot(value, tuple(channels)))
    for channel in channels:
        _write(channel, _project(channel, value))
    return output


@dataclass(frozen=True, slots=True, eq=False)
class MatplotlibAppearancePlan:
    """One completely preflighted source appearance update."""

    output: MatplotlibAppearance
    snapshot: _MplSnapshot
    writes: tuple[tuple[_MplChannel, Any], ...]


def prepare_matplotlib_appearance(
    spec: FigureConfig, panels: Sequence[MatplotlibRenderResult]
) -> tuple[MatplotlibAppearancePlan, ...]:
    """Preflight every affected channel before any connector mutates a native panel."""
    # [impl->req~ring5.figure.series-styling~2]
    plans: list[MatplotlibAppearancePlan] = []
    for panel in panels:
        for binding in panel.bindings:
            output = binding.appearance
            current = output.snapshot
            opacity = _selected_opacity(spec, binding.source_ordinal, binding.original_name)
            named = spec.trace_overrides.get(binding.original_name)
            color = (
                named.color
                if named is not None and binding.family not in _SEMANTIC_FAMILIES
                else ""
            )
            positional = (
                spec.series_styles[binding.source_ordinal % len(spec.series_styles)]
                if spec.series_styles
                else None
            )
            edge = (
                (positional.bar_border_color or "#000")
                if positional is not None and positional.bar_border_width > 0
                else ""
            )
            if current.opacity is None:
                if (
                    opacity is not None
                    or (named is not None and named.color)
                    or edge
                    or (spec.data_labels is not None and spec.data_labels.enabled)
                ):
                    raise ValueError(
                        "This native source has explicitly unmanaged appearance; provide a known "
                        "intrinsic context before changing color, opacity or source labels."
                    )
                continue
            if binding.family == "parallel_coordinates" and opacity is not None:
                validate_parallel_appearance(opacity, None, None)
            labels = spec.data_labels
            label_change = (
                bool(output.labels)
                and labels is not None
                and labels.enabled
                and (tuple(labels.to_dict().items()) != output.label_spec)
            )
            if opacity is None and not color and not edge and not label_change:
                continue
            selected = current.opacity if opacity is None else opacity
            channels: list[_MplChannel] = []
            writes: list[tuple[_MplChannel, Any]] = []
            for channel in current.channels:
                replacement = color if color and channel.series_color else ""
                label_affected = (
                    label_change
                    and channel.kind == "text"
                    and any(channel.artist is label for label in output.labels)
                )
                if label_affected and labels is not None and labels.color_mode == "custom":
                    replacement = labels.custom_color
                if (
                    edge
                    and channel.kind == "edge"
                    and any(channel.artist is item for item in _members(binding.style_targets))
                ):
                    replacement = edge
                if opacity is None and not replacement and not label_affected:
                    channels.append(channel)
                    continue
                if not _supports_projection(channel) or (
                    not replacement and not _matches(channel, current.opacity)
                ):
                    raise ValueError(
                        "A source appearance was edited outside its declared intrinsic context; "
                        "provide a new explicit color/context before changing opacity."
                    )
                updated = channel
                if replacement:
                    rgba = to_rgba(css_color_to_matplotlib(replacement))
                    intrinsic = (rgba,) if isinstance(channel.artist, Collection) else rgba
                    updated = replace(channel, intrinsic=intrinsic)
                channels.append(updated)
                writes.append((updated, _project(updated, selected)))
            plans.append(
                MatplotlibAppearancePlan(
                    output, _MplSnapshot(selected, tuple(channels)), tuple(writes)
                )
            )
    return tuple(plans)


def apply_matplotlib_appearance(plans: Sequence[MatplotlibAppearancePlan]) -> None:
    """Write already validated channels, then publish their new snapshots together."""
    for plan in plans:
        for channel, value in plan.writes:
            _write(channel, value)
    for plan in plans:
        plan.output.snapshot = plan.snapshot


def intrinsic_colormap(binding: MatplotlibTraceBinding) -> Colormap:
    """Return the declared intrinsic map of a source-owned heatmap."""
    channels = [
        channel for channel in binding.appearance.snapshot.channels if channel.kind == "cmap"
    ]
    if len(channels) != 1 or not isinstance(channels[0].intrinsic, Colormap):
        raise ValueError("A heatmap source requires exactly one intrinsic color mapping.")
    return channels[0].intrinsic


def replace_generated_labels(
    binding: MatplotlibTraceBinding, labels: Sequence[Text], signature: tuple[Any, ...]
) -> None:
    """Own freshly emitted source labels without recapturing existing native channels."""
    output = binding.appearance
    previous = {id(label) for label in output.labels}
    retained = tuple(
        channel for channel in output.snapshot.channels if id(channel.artist) not in previous
    )
    new = tuple(_MplChannel(label, "text", to_rgba(label.get_color())) for label in labels)
    if new and output.snapshot.opacity is None:
        raise ValueError("Source data labels require a known intrinsic appearance context.")
    for channel in new:
        _write(channel, _project(channel, require_opacity(output.snapshot.opacity)))
    output.snapshot = replace(output.snapshot, channels=retained + new)
    output.labels = tuple(labels)
    output.label_spec = signature


@dataclass(frozen=True, slots=True)
class _PlotlyChannel:
    path: tuple[str, ...]
    intrinsic: str | tuple[str, ...]
    factor: float = 1.0


@dataclass(frozen=True, slots=True)
class _PlotlySnapshot:
    opacity: float | None
    channels: tuple[_PlotlyChannel, ...]


@dataclass(slots=True, eq=False)
class PlotlyAppearance:
    """Known intrinsic colors for a native family that requires alpha baking."""

    snapshot: _PlotlySnapshot

    def validate(self) -> None:
        """Validate declared intrinsic channels without adopting actual native edits.

        Raises:
            ValueError: The known or unmanaged appearance capability is inconsistent.
        """
        snapshot = self.snapshot
        if type(snapshot.channels) is not tuple:
            raise ValueError("Intrinsic Sankey channels must be an ordered immutable tuple.")
        if snapshot.opacity is None:
            if snapshot.channels:
                raise ValueError("Unmanaged Sankey appearance cannot claim intrinsic channels.")
            return
        require_opacity(snapshot.opacity)
        expected = {
            ("node", "color"),
            ("node", "line", "color"),
            ("link", "color"),
            ("link", "hovercolor"),
            ("link", "line", "color"),
            ("textfont", "color"),
        }
        if (
            len(snapshot.channels) != len(expected)
            or {channel.path for channel in snapshot.channels} != expected
        ):
            raise ValueError(
                "Known Sankey appearance requires every declared normal, hover and text channel."
            )
        for channel in snapshot.channels:
            require_opacity(channel.factor, field="appearance factor")
            colors = (
                (channel.intrinsic,) if isinstance(channel.intrinsic, str) else channel.intrinsic
            )
            if type(colors) is not tuple:
                raise ValueError("Intrinsic Sankey colors must be static text or immutable tuples.")
            for color in colors:
                _css_alpha(color)

    @classmethod
    def unmanaged(cls) -> PlotlyAppearance:
        """Declare unknown baked native colors without enabling appearance writes.

        Returns:
            An explicit capability declaration for layout and legend operations.
        """
        return cls(_PlotlySnapshot(None, ()))


@dataclass(slots=True, eq=False)
class PlotlyTextAppearance:
    """A declared layout data label's intrinsic font color and projected opacity."""

    intrinsic: str
    opacity: float
    row: int
    column: int
    contrast: bool


def _plotly_get(trace: BaseTraceType, path: tuple[str, ...]) -> Any:
    value: Any = trace
    for name in path:
        value = value[name]
    return value


def _plotly_project(channel: _PlotlyChannel, opacity: float) -> str | tuple[str, ...]:
    factor = opacity * channel.factor
    if isinstance(channel.intrinsic, str):
        return _css_project(channel.intrinsic, factor)
    return tuple(_css_project(color, factor) for color in channel.intrinsic)


def seed_sankey_appearance(
    trace: BaseTraceType,
    *,
    opacity: float,
    node_colors: Sequence[str],
    node_line: str,
    link_colors: Sequence[str],
    link_factor: float,
    link_line: str = "#444444",
    text_color: str = "#000000",
    hover_colors: Sequence[str] | None = None,
) -> PlotlyAppearance:
    """Declare and project concrete Sankey colors, including explicit hover colors.

    Args:
        trace: Actual inserted native Sankey trace.
        opacity: Concrete initial source opacity.
        node_colors: Intrinsic colors for every node.
        node_line: Intrinsic node outline color.
        link_colors: Intrinsic colors for every link.
        link_factor: Explicit link-local opacity factor.
        link_line: Intrinsic link outline color.
        text_color: Intrinsic source text color.
        hover_colors: Explicit intrinsic hover colors, defaulting to normal link colors.

    Returns:
        Independent creation-time native appearance output.

    Raises:
        ValueError: A color or opacity has no concrete supported projection.
    """
    channels = (
        _PlotlyChannel(("node", "color"), tuple(node_colors)),
        _PlotlyChannel(("node", "line", "color"), node_line),
        _PlotlyChannel(("link", "color"), tuple(link_colors), require_opacity(link_factor)),
        _PlotlyChannel(
            ("link", "hovercolor"),
            tuple(link_colors if hover_colors is None else hover_colors),
            require_opacity(link_factor),
        ),
        _PlotlyChannel(("link", "line", "color"), link_line, require_opacity(link_factor)),
        _PlotlyChannel(("textfont", "color"), text_color),
    )
    opacity_value = require_opacity(opacity)
    output = PlotlyAppearance(_PlotlySnapshot(opacity_value, channels))
    projected = tuple((channel, _plotly_project(channel, opacity_value)) for channel in channels)
    for channel, value in projected:
        owner = _plotly_get(trace, channel.path[:-1])
        owner[channel.path[-1]] = value
    return output


@dataclass(frozen=True, slots=True, eq=False)
class PlotlyAppearancePlan:
    """Preflighted native opacity or baked-color writes and retained output state."""

    trace: BaseTraceType
    opacity: float
    set_opacity: bool = True
    baked: PlotlyAppearance | None = None
    writes: tuple[tuple[_PlotlyChannel, Any], ...] = ()
    labels: tuple[tuple[Any, PlotlyTextAppearance, str, str], ...] = ()


def prepare_plotly_appearance(
    spec: FigureConfig, rendered: PlotlyRenderResult
) -> tuple[PlotlyAppearancePlan, ...]:
    """Preflight owned Plotly source opacity and separately baked layout labels."""
    # [impl->req~ring5.figure.series-styling~2]
    import plotly.graph_objects as go
    from src.web.rendering._heatmap_utils import heatmap_ranges, heatmap_text_colors

    annotations = {
        annotation.name: annotation for annotation in rendered.figure.layout.annotations or ()
    }
    heatmaps = [trace for trace in rendered.figure.data if isinstance(trace, go.Heatmap)]
    ranges = (
        heatmap_ranges(heatmaps, spec.legends[0].colorbar)
        if spec.legends
        else tuple((trace.zmin, trace.zmax) for trace in heatmaps)
    )
    text_colors: dict[int, list[list[str]]] = {}
    contrast_sources = {
        id(role.source.native_trace)
        for role in rendered.layout_roles
        if role.appearance is not None and role.appearance.contrast
    }
    for heatmap, (lower, upper) in zip(heatmaps, ranges, strict=True):
        if id(heatmap) not in contrast_sources:
            continue
        # Plotly's stubs flatten matrix/positioned-scale shapes; native bindings
        # retain the validated two-dimensional source and concrete scale stops.
        scale = cast(Sequence[tuple[float, str]], heatmap.colorscale)
        if heatmap.reversescale:
            scale = [(1 - position, color) for position, color in reversed(scale)]
        matrix = cast(Sequence[Sequence[float | None]], heatmap.z)
        text_colors[id(heatmap)] = heatmap_text_colors(matrix, scale, lower, upper)
    plans: list[PlotlyAppearancePlan] = []
    for binding in (source for panel in rendered.panel_bindings for source in panel):
        trace = binding.native_trace
        opacity = _selected_opacity(spec, binding.source_ordinal, binding.original_name)
        if isinstance(trace, go.Parcoords):
            validate_parallel_appearance(
                1.0 if opacity is None else opacity, trace.line.color, trace.line.colorscale
            )
            continue
        baked = binding.appearance
        current = (
            baked.snapshot.opacity
            if baked is not None
            else require_opacity(trace["opacity"] if trace["opacity"] is not None else 1.0)
        )
        named = spec.trace_overrides.get(binding.original_name)
        color = (
            named.color
            if named is not None
            and trace["type"] not in ("heatmap", "waterfall", "sankey", "parcoords")
            else ""
        )
        positional = (
            spec.series_styles[binding.source_ordinal % len(spec.series_styles)]
            if spec.series_styles
            else None
        )
        edge = (
            positional.bar_border_color or "#000"
            if positional is not None
            and positional.bar_border_width > 0
            and hasattr(trace, "marker")
            else ""
        )
        if current is None:
            if opacity is not None or (named is not None and named.color) or edge:
                raise ValueError(
                    "This native source has explicitly unmanaged appearance; provide a known "
                    "intrinsic context before changing color or opacity."
                )
            continue
        selected = current if opacity is None else opacity
        labels: list[tuple[Any, PlotlyTextAppearance, str, str]] = []
        for role in rendered.layout_roles:
            if role.source is not binding or role.appearance is None:
                continue
            annotation = annotations[role.role_name]
            appearance = role.appearance
            intrinsic = (
                text_colors[id(trace)][appearance.row][appearance.column]
                if appearance.contrast
                else appearance.intrinsic
            )
            if opacity is None and intrinsic == appearance.intrinsic:
                continue
            if annotation.font.color != _css_project(appearance.intrinsic, appearance.opacity):
                raise ValueError(
                    "A source data label has unknown native appearance; "
                    "provide a new explicit context."
                )
            labels.append((annotation, appearance, intrinsic, _css_project(intrinsic, selected)))
        if opacity is None and not color and not edge and not labels:
            continue
        writes: list[tuple[_PlotlyChannel, Any]] = []
        if isinstance(trace, go.Sankey):
            if baked is None:
                raise ValueError("A native Sankey requires declared intrinsic appearance colors.")
            for channel in baked.snapshot.channels:
                if _plotly_get(trace, channel.path) != _plotly_project(channel, current):
                    raise ValueError(
                        "A Sankey channel has unknown native appearance; "
                        "provide a new explicit context."
                    )
                writes.append((channel, _plotly_project(channel, selected)))
        elif color:
            # A public inert constructor validates the scalar before any live native mutation.
            go.Scatter(marker={"color": color})
            channels = [_PlotlyChannel(("marker", "color"), color)]
            if isinstance(trace, (go.Scatter, go.Scattergl, go.Scatterpolar, go.Box, go.Violin)):
                channels.append(_PlotlyChannel(("line", "color"), color))
            if isinstance(trace, (go.Box, go.Violin)):
                channels.append(_PlotlyChannel(("fillcolor",), color))
            if isinstance(
                trace, (go.Scatter, go.Scattergl, go.Scatterpolar)
            ) and trace.fill not in (None, "none"):
                channels.append(
                    _PlotlyChannel(
                        ("fillcolor",), color, 0.45 if isinstance(trace, go.Scatterpolar) else 1.0
                    )
                )
            if isinstance(trace, go.Violin):
                channels.append(_PlotlyChannel(("box", "line", "color"), color, 0.8))
            writes.extend(
                (
                    channel,
                    channel.intrinsic if channel.factor == 1.0 else _plotly_project(channel, 1.0),
                )
                for channel in channels
            )
        if edge:
            go.Scatter(marker={"line": {"color": edge}})
            writes.append((_PlotlyChannel(("marker", "line", "color"), edge), edge))
        plans.append(
            PlotlyAppearancePlan(
                trace, selected, opacity is not None, baked, tuple(writes), tuple(labels)
            )
        )
    return tuple(plans)


def apply_plotly_appearance(plans: Sequence[PlotlyAppearancePlan]) -> None:
    """Apply preflighted opacity/owned color plans, then publish baked snapshots."""
    for plan in plans:
        if plan.baked is None and plan.set_opacity:
            plan.trace["opacity"] = plan.opacity
        for channel, value in plan.writes:
            _plotly_get(plan.trace, channel.path[:-1])[channel.path[-1]] = value
        for annotation, _, _, color in plan.labels:
            annotation.font.color = color
    for plan in plans:
        if plan.baked is not None:
            plan.baked.snapshot = replace(plan.baked.snapshot, opacity=plan.opacity)
        for _, output, intrinsic, _ in plan.labels:
            output.intrinsic = intrinsic
            output.opacity = plan.opacity
