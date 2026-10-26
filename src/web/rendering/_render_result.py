"""Owned source-to-native associations for figure styling and legend projection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    import plotly.graph_objects as go
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.container import Container
    from matplotlib.figure import Figure
    from matplotlib.legend import Legend
    from matplotlib.colorbar import Colorbar
    from matplotlib.gridspec import SubplotSpec
    from matplotlib.layout_engine import LayoutEngine
    from matplotlib.transforms import Bbox
    from plotly.basedatatypes import BaseTraceType
    from src.core.models.visualization.trace_config import TraceType

_ROLE_NAME = re.compile(r"ring5-(?:panel-\d+-)?facet-title-\d+\Z")


def _validate_source(ordinal: int, name: str, role: str, group: str, shown: bool) -> None:
    if (
        type(ordinal) is not int
        or ordinal < 0
        or not isinstance(name, str)
        or not isinstance(role, str)
        or role not in ("primary", "secondary")
        or not isinstance(group, str)
        or type(shown) is not bool
    ):
        raise ValueError("Native source bindings require an ordinal, text identity and typed role.")


@dataclass(frozen=True, slots=True, eq=False)
class PlotlyTraceBinding:
    """An original panel source associated with its actual inserted native trace."""

    source_ordinal: int
    original_name: str
    native_trace: BaseTraceType
    legend_role: Literal["primary", "secondary"]
    legendgroup: str
    show_in_legend: bool

    def __post_init__(self) -> None:
        _validate_source(
            self.source_ordinal,
            self.original_name,
            self.legend_role,
            self.legendgroup,
            self.show_in_legend,
        )


@dataclass(frozen=True, slots=True, eq=False)
class PlotlyLayoutRole:
    """A generated native layout role, associated externally with its source."""

    role_name: str
    source: PlotlyTraceBinding


@dataclass(frozen=True, slots=True, eq=False)
class PlotlyRenderResult:
    """One native root and every original panel's ordered source bindings."""

    figure: go.Figure
    panel_bindings: tuple[tuple[PlotlyTraceBinding, ...], ...]
    layout_roles: tuple[PlotlyLayoutRole, ...] = ()
    shared_legend: bool = False

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Preflight every supplied binding and role before any native mutation.

        Raises:
            ValueError: A source, root, native membership or generated role is inconsistent.
        """
        import plotly.graph_objects as go
        from plotly.basedatatypes import BaseTraceType

        if (
            not isinstance(self.figure, go.Figure)
            or type(self.panel_bindings) is not tuple
            or type(self.shared_legend) is not bool
        ):
            raise ValueError("Plotly bindings require their actual native figure and panel tuples.")
        supplied: list[PlotlyTraceBinding] = []
        for panel in self.panel_bindings:
            if type(panel) is not tuple:
                raise ValueError("Plotly panel bindings must be ordered tuples.")
            for ordinal, binding in enumerate(panel):
                if (
                    not isinstance(binding, PlotlyTraceBinding)
                    or binding.source_ordinal != ordinal
                    or not isinstance(binding.native_trace, BaseTraceType)
                ):
                    raise ValueError("Plotly source ordinals or native trace bindings are invalid.")
                supplied.append(binding)
        owned_ids = [id(binding.native_trace) for binding in supplied]
        if len(set(owned_ids)) != len(owned_ids) or set(owned_ids) != {
            id(trace) for trace in self.figure.data
        }:
            raise ValueError("Plotly native data membership differs from its explicit bindings.")
        if type(self.layout_roles) is not tuple:
            raise ValueError("Generated layout roles must be an ordered tuple.")
        role_names: set[str] = set()
        supplied_ids = {id(binding) for binding in supplied}
        for role in self.layout_roles:
            if (
                not isinstance(role, PlotlyLayoutRole)
                or not isinstance(role.role_name, str)
                or not _ROLE_NAME.fullmatch(role.role_name)
                or role.role_name in role_names
                or id(role.source) not in supplied_ids
                or not isinstance(role.source.native_trace, go.Heatmap)
            ):
                raise ValueError("Generated layout role bindings are invalid or duplicated.")
            role_names.add(role.role_name)
        observed: dict[str, int] = {}
        for annotation in self.figure.layout.annotations or ():
            name = annotation.name
            if isinstance(name, str) and _ROLE_NAME.fullmatch(name):
                observed[name] = observed.get(name, 0) + 1
        if set(observed) != role_names or any(count != 1 for count in observed.values()):
            raise ValueError("Generated layout role membership differs from its explicit bindings.")


@dataclass(frozen=True, slots=True, eq=False)
class MatplotlibTraceBinding:
    """One neutral source and its explicit native data, style and legend subsets."""

    source_ordinal: int
    original_name: str
    axes: Axes
    legend_role: Literal["primary", "secondary"]
    legendgroup: str
    show_in_legend: bool
    family: TraceType
    owned_data: tuple[Artist | Container, ...] = ()
    style_targets: tuple[Artist | Container, ...] = ()
    legend_handle: Artist | Container | None = None

    def __post_init__(self) -> None:
        _validate_source(
            self.source_ordinal,
            self.original_name,
            self.legend_role,
            self.legendgroup,
            self.show_in_legend,
        )


def _native_members(handle: Artist | Container, axes: Axes, attached: set[int]) -> set[int]:
    """Validate a known artist/container and return its physical ownership members."""
    from matplotlib.artist import Artist
    from matplotlib.container import Container

    if isinstance(handle, Container):
        if not any(handle is container for container in axes.containers):
            raise ValueError("A bound native container is no longer attached to its axes.")
        members = {id(handle)}
        for child in handle.get_children():
            members.update(_native_members(child, axes, attached))
        return members
    if (
        not isinstance(handle, Artist)
        or handle.axes is not axes
        or handle.figure is not axes.figure
        or id(handle) not in attached
    ):
        raise ValueError("A bound native artist is no longer attached to its axes.")
    return {id(handle)}


def _validate_mpl_family(binding: MatplotlibTraceBinding) -> None:
    """Check explicit semantic family and eligible native style/legend targets."""
    from matplotlib.collections import PathCollection, PolyCollection, QuadMesh
    from matplotlib.container import BarContainer
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    primary = {
        "bar": (BarContainer,),
        "line": (Line2D,),
        "scatter": (PathCollection,),
        "box": (Patch,),
        "violin": (PolyCollection,),
        "radar": (Line2D,),
        "waterfall": (BarContainer,),
        "sankey": (Patch,),
        "parallel_coordinates": (Line2D,),
        "heatmap": (QuadMesh,),
    }
    if not isinstance(binding.family, str) or binding.family not in primary:
        raise ValueError("A Matplotlib source must declare its supported neutral family.")
    expected = primary[binding.family]
    if binding.owned_data and not any(
        isinstance(handle, expected) for handle in binding.owned_data
    ):
        raise ValueError("Native data does not represent the declared neutral family.")
    targets = (*binding.style_targets, binding.legend_handle)
    if binding.family in ("sankey", "parallel_coordinates", "heatmap"):
        if any(handle is not None for handle in targets):
            raise ValueError("This semantic family has no generic series style or legend target.")
    elif any(handle is not None and not isinstance(handle, expected) for handle in targets):
        raise ValueError("Native style/legend targets do not represent the declared family.")


@dataclass
class MatplotlibRenderResult:
    """One actual native panel, its source bindings and heatmap/category metadata."""

    primary_axes: Axes
    secondary_axes: Axes | None = None
    bindings: tuple[MatplotlibTraceBinding, ...] = ()
    trace_count: int = 0
    heatmap_col_labels: list[str] | None = None
    heatmap_row_labels: list[str] | None = None
    heatmap_image: Any = None
    title_source: MatplotlibTraceBinding | None = None
    x_category_positions: dict[str, float] = field(default_factory=dict)

    def validate(self) -> None:
        """Preflight all source data and subsets, allowing unowned decorations.

        Raises:
            ValueError: A source/axes/artist association is inconsistent or multiply owned.
        """
        from matplotlib.axes import Axes

        axes = (
            (self.primary_axes,)
            if self.secondary_axes is None
            else (self.primary_axes, self.secondary_axes)
        )
        if (
            any(not isinstance(axis, Axes) for axis in axes)
            or len({id(axis) for axis in axes}) != len(axes)
            or any(axis.figure is not self.primary_axes.figure for axis in axes)
            or any(not any(axis is attached for attached in axis.figure.axes) for axis in axes)
            or type(self.bindings) is not tuple
        ):
            raise ValueError("Matplotlib bindings require their actual attached panel axes.")
        all_owned: set[int] = set()
        attached = {id(axis): {id(child) for child in axis.get_children()} for axis in axes}
        for ordinal, binding in enumerate(self.bindings):
            if (
                not isinstance(binding, MatplotlibTraceBinding)
                or binding.source_ordinal != ordinal
                or not any(binding.axes is axis for axis in axes)
                or type(binding.owned_data) is not tuple
                or type(binding.style_targets) is not tuple
                or len({id(handle) for handle in binding.owned_data}) != len(binding.owned_data)
                or len({id(handle) for handle in binding.style_targets})
                != len(binding.style_targets)
            ):
                raise ValueError("Matplotlib source ordinals or native subsets are invalid.")
            owned: set[int] = set()
            _validate_mpl_family(binding)
            for handle in binding.owned_data:
                owned.update(_native_members(handle, binding.axes, attached[id(binding.axes)]))
            if owned & all_owned:
                raise ValueError("A native data artist belongs to more than one source binding.")
            all_owned.update(owned)
            subsets = (*binding.style_targets, binding.legend_handle)
            if any(handle is not None and id(handle) not in owned for handle in subsets):
                raise ValueError("Native style/legend targets must belong to their source data.")
        if self.heatmap_image is not None:
            from matplotlib.collections import QuadMesh

            if not isinstance(self.heatmap_image, QuadMesh) or not any(
                binding.family == "heatmap"
                and any(self.heatmap_image is item for item in binding.owned_data)
                for binding in self.bindings
            ):
                raise ValueError("A heatmap image must be its actual bound source mesh.")
        if self.title_source is not None and (
            not any(self.title_source is binding for binding in self.bindings)
            or self.title_source.family != "heatmap"
        ):
            raise ValueError("A generated facet title requires its actual bound heatmap source.")


@dataclass(frozen=True, slots=True, eq=False)
class _ColorbarAllocation:
    """Exact native layout-space effects of one managed colorbar allocation."""

    axes: Axes
    parent: SubplotSpec | None
    original_box: Bbox
    anchor: Any
    in_layout: bool
    allocated_parent: SubplotSpec | None
    allocated_box: Bbox
    allocated_anchor: Any
    allocated_in_layout: bool


@dataclass(frozen=True, slots=True, eq=False)
class _ColorbarOutput:
    """One physical colorbar and the exact source, callback and layout it owns."""

    colorbar: Colorbar
    source: MatplotlibTraceBinding
    panels: tuple[MatplotlibRenderResult, ...]
    callback_id: int
    allocation: tuple[_ColorbarAllocation, ...]
    layout_engine: LayoutEngine | None
    parent: SubplotSpec | None
    default_box: Bbox
    default_in_layout: bool


@dataclass(slots=True)
class _NativeOutputs:
    """Mutable physical outputs; source associations and composition policy stay frozen."""

    legend: Legend | None = None
    colorbars: tuple[_ColorbarOutput, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class MatplotlibFigureResult:
    """One native figure retaining every real panel's source associations."""

    figure: Figure
    panels: tuple[MatplotlibRenderResult, ...]
    shared_legend: bool = False
    native_outputs: _NativeOutputs = field(default_factory=_NativeOutputs, init=False, repr=False)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate every panel before any figure-wide mutation."""
        from matplotlib.figure import Figure
        from matplotlib.legend import Legend
        from matplotlib.colorbar import Colorbar
        from matplotlib.collections import QuadMesh

        if (
            not isinstance(self.figure, Figure)
            or type(self.panels) is not tuple
            or type(self.shared_legend) is not bool
        ):
            raise ValueError("Matplotlib results require a native figure and panel tuple.")
        owned_axes: set[int] = set()
        native_legend = self.native_outputs.legend
        if native_legend is not None and (
            not isinstance(native_legend, Legend)
            or native_legend.figure is not self.figure
            or not any(native_legend is attached for attached in self.figure.legends)
        ):
            raise ValueError("Generated shared legend membership differs from its native owner.")
        for panel in self.panels:
            if not isinstance(panel, MatplotlibRenderResult):
                raise ValueError("Matplotlib results require actual panel bindings.")
            panel.validate()
            axes = (panel.primary_axes, panel.secondary_axes)
            present = {id(axis) for axis in axes if axis is not None}
            if panel.primary_axes.get_figure(root=True) is not self.figure or owned_axes & present:
                raise ValueError("A native panel belongs to a different or duplicated figure root.")
            owned_axes.update(present)
        if type(self.native_outputs.colorbars) is not tuple:
            raise ValueError("Managed colorbars must be actual native output records.")
        seen: set[int] = set()
        for output in self.native_outputs.colorbars:
            if (
                not isinstance(output, _ColorbarOutput)
                or not isinstance(output.colorbar, Colorbar)
                or not isinstance(output.source, MatplotlibTraceBinding)
                or id(output.colorbar) in seen
                or output.colorbar.ax.get_figure(root=True) is not self.figure
                or not any(output.colorbar.ax is axis for axis in self.figure.axes)
                or not any(
                    output.source is source for panel in self.panels for source in panel.bindings
                )
                or output.source.family != "heatmap"
                or not isinstance(output.colorbar.mappable, QuadMesh)
                or not any(output.colorbar.mappable is item for item in output.source.owned_data)
                or type(output.panels) is not tuple
                or not output.panels
                or type(output.callback_id) is not int
                or any(
                    not any(panel is candidate for candidate in self.panels)
                    for panel in output.panels
                )
                or not any(
                    output.source is source for panel in output.panels for source in panel.bindings
                )
                or output.callback_id
                not in output.colorbar.mappable.callbacks.callbacks.get("changed", {})
            ):
                raise ValueError("Managed colorbar output/source/root membership is inconsistent.")
            seen.add(id(output.colorbar))
            allocation_axes = {
                id(axis)
                for panel in output.panels
                for axis in (panel.primary_axes, panel.secondary_axes)
                if axis is not None
            }
            if (
                type(output.allocation) is not tuple
                or any(not isinstance(item, _ColorbarAllocation) for item in output.allocation)
                or len(output.allocation) != len(allocation_axes)
                or {id(item.axes) for item in output.allocation} != allocation_axes
            ):
                raise ValueError(
                    "Managed colorbar allocation must describe its actual participant axes."
                )


NativeRenderResult = PlotlyRenderResult | MatplotlibFigureResult
