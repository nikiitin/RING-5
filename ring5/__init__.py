"""RING-5 public Python API — the full workflow, headless.

Everything the web app does, as plain Python::

    import ring5

    with ring5.Session() as s:
        result = s.parse("/path/to/sims", variables=["simTicks"])
        df = s.load(result.csv_path)
        df = s.reduce_seeds(df, ["config_description_abbrev"], ["simTicks"])
        plot = s.create_plot(
            "bar",
            data=df,
            config={"x": "config_description_abbrev", "y": "simTicks"},
        )
        fig = s.render(plot, engine="matplotlib")
        s.export(fig, "out/simticks.pdf", deterministic=True)
        s.save_portfolio("my_paper")

    # Reproduce every figure from a snapshot — the reproducibility flagship:
    ring5.render_portfolio("my_paper", "figs/", engine="matplotlib", fmt="pdf")

Check external dependencies with ``print(ring5.doctor())`` (perl for
parsing; a Chrome-family browser for plotly image export; xelatex for PGF).
Call ``ring5.shutdown()`` once per process to tear down the worker pools
(they restart transparently on next use).

This package is the headless composition root: like ``app.py`` it wires
``src.core`` and the rendering layer together, so the layer rule
("core never imports web") stays intact underneath it.

Import cost: the heavy workflow names (``Session``, ``render_figure``, the
exporters, ``render_portfolio``, …) are loaded lazily on first access
(PEP 562) — ``import ring5`` and the light surface (``doctor``, the error
types, ``shutdown``) stay fast for CLI startup.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

from ring5._doctor import DependencyStatus, DoctorReport, doctor
from ring5.errors import (
    ColumnNotFoundError,
    DataLoadError,
    DataValidationError,
    DependencyMissingError,
    ExportError,
    MissingStatError,
    ParseError,
    PipelineError,
    PortfolioError,
    PortfolioVersionError,
    RenderError,
    Ring5Error,
    ScanError,
)

# Typed figure config — pure dataclasses (no pandas/matplotlib), so eager:
# build a FigureSpec and pass ``.to_config()`` as the plot config.
from ring5.figure_spec import (
    DualAxisOpts,
    FigureSpec,
    FigureSpecBuilder,
    LegendOpts,
    ReferenceLineOpts,
)

if TYPE_CHECKING:
    # Static names for mypy/IDEs; at runtime these resolve via __getattr__.
    from src.core.models import (
        ColumnContract,
        ColumnSemantics,
        DatasetInfo,
        DatasetLineage,
        DatasetRevision,
        DatasetSnapshotInfo,
        DashboardSpec,
        DrillDownResult,
        DatasetSchemaContract,
        DatasetSemantics,
        JoinCardinality,
        JoinDiagnostics,
        LinkedSelectionSpec,
        ConfigurationDifference,
        PlotConfigurationComparison,
        PlotTransferResult,
        SmallMultiplesSpec,
        RestoreReport,
        ScanResult,
        ScannedVariable,
        SchemaValidationReport,
        SchemaViolation,
        ShaperStepConfig,
    )
    from src.core.models.parsing_models import StatConfig
    from src.core.models.quality_models import ColumnQuality, DataQualityReport

    from ring5._export import export_bytes, export_file
    from ring5._parse import ParseJob, ParseResult
    from ring5._scan import ScanJob
    from ring5._portfolio import render_portfolio
    from ring5._render import render_figure
    from ring5._dashboard import render_dashboard
    from ring5._linked_selection import apply_linked_selection
    from ring5._small_multiples import render_small_multiples
    from ring5._session import PlotType, Session, available_plot_types
    from ring5.shapers import available_shaper_types
    from ring5.coordinates import grouped_bar_coordinates
    from ring5.data import Table, read_table
    from ring5.decorations import FigureDecorations

try:
    __version__ = version("ring5")
except PackageNotFoundError:  # not installed (e.g. vendored checkout)
    __version__ = "0.0.0"


# Heavy exports (they pull pandas/matplotlib/plotly/the web rendering stack)
# resolved lazily: attribute name -> (module, attribute).
_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "Session": ("ring5._session", "Session"),
    "PlotType": ("ring5._session", "PlotType"),
    "available_plot_types": ("ring5._session", "available_plot_types"),
    "ParseJob": ("ring5._parse", "ParseJob"),
    "ParseResult": ("ring5._parse", "ParseResult"),
    "ScanJob": ("ring5._scan", "ScanJob"),
    "ScanResult": ("src.core.models", "ScanResult"),
    "ScannedVariable": ("src.core.models", "ScannedVariable"),
    "render_figure": ("ring5._render", "render_figure"),
    "render_dashboard": ("ring5._dashboard", "render_dashboard"),
    "apply_linked_selection": ("ring5._linked_selection", "apply_linked_selection"),
    "render_small_multiples": ("ring5._small_multiples", "render_small_multiples"),
    "export_bytes": ("ring5._export", "export_bytes"),
    "export_file": ("ring5._export", "export_file"),
    "render_portfolio": ("ring5._portfolio", "render_portfolio"),
    "StatConfig": ("src.core.models.parsing_models", "StatConfig"),
    "RestoreReport": ("src.core.models", "RestoreReport"),
    "ColumnQuality": ("src.core.models", "ColumnQuality"),
    "DataQualityReport": ("src.core.models", "DataQualityReport"),
    "ColumnContract": ("src.core.models", "ColumnContract"),
    "ColumnSemantics": ("src.core.models", "ColumnSemantics"),
    "DatasetInfo": ("src.core.models", "DatasetInfo"),
    "DatasetLineage": ("src.core.models", "DatasetLineage"),
    "DatasetRevision": ("src.core.models", "DatasetRevision"),
    "DatasetSnapshotInfo": ("src.core.models", "DatasetSnapshotInfo"),
    "DashboardSpec": ("src.core.models", "DashboardSpec"),
    "DrillDownResult": ("src.core.models", "DrillDownResult"),
    "DatasetSchemaContract": ("src.core.models", "DatasetSchemaContract"),
    "DatasetSemantics": ("src.core.models", "DatasetSemantics"),
    "JoinCardinality": ("src.core.models", "JoinCardinality"),
    "JoinDiagnostics": ("src.core.models", "JoinDiagnostics"),
    "LinkedSelectionSpec": ("src.core.models", "LinkedSelectionSpec"),
    "ConfigurationDifference": ("src.core.models", "ConfigurationDifference"),
    "PlotConfigurationComparison": ("src.core.models", "PlotConfigurationComparison"),
    "PlotTransferResult": ("src.core.models", "PlotTransferResult"),
    "SmallMultiplesSpec": ("src.core.models", "SmallMultiplesSpec"),
    "SchemaValidationReport": ("src.core.models", "SchemaValidationReport"),
    "SchemaViolation": ("src.core.models", "SchemaViolation"),
    "ShaperStepConfig": ("src.core.models", "ShaperStepConfig"),
    "available_shaper_types": ("ring5.shapers", "available_shaper_types"),
    # Self-contained figure-scripting surface (so scripts import only `ring5`):
    "grouped_bar_coordinates": ("ring5.coordinates", "grouped_bar_coordinates"),
    "FigureDecorations": ("ring5.decorations", "FigureDecorations"),
    "Table": ("ring5.data", "Table"),
    "read_table": ("ring5.data", "read_table"),
}


def __getattr__(name: str) -> Any:
    """PEP 562 lazy resolution of the heavy public names."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    value = getattr(importlib.import_module(target[0]), target[1])
    globals()[name] = value  # cache: subsequent accesses skip __getattr__
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))


def shutdown() -> None:
    # [impl->req~ring5.api.process-lifecycle~1]
    """Tear down the process-wide worker pools (Perl workers + thread pool).

    Safe to call at any time: the pools restart transparently on the next
    parse/scan. Both also register ``atexit`` hooks, so calling this is
    only needed for long-running processes that want to release resources
    early.
    """
    from src.parsing.framework.work_pool import WorkPool
    from src.parsing.gem5.impl.strategies.perl_worker_pool import shutdown_worker_pool

    shutdown_worker_pool()
    WorkPool.get_instance().shutdown()


__all__ = [
    "__version__",
    # workflow
    "Session",
    "PlotType",
    "available_plot_types",
    "available_shaper_types",
    "StatConfig",
    "ParseJob",
    "ParseResult",
    "ScanJob",
    "ScanResult",
    "ScannedVariable",
    "ShaperStepConfig",
    "RestoreReport",
    "ColumnQuality",
    "ColumnContract",
    "ColumnSemantics",
    "DataQualityReport",
    "DatasetInfo",
    "DatasetLineage",
    "DatasetRevision",
    "DatasetSnapshotInfo",
    "DashboardSpec",
    "DrillDownResult",
    "DatasetSchemaContract",
    "DatasetSemantics",
    "JoinCardinality",
    "JoinDiagnostics",
    "LinkedSelectionSpec",
    "ConfigurationDifference",
    "PlotConfigurationComparison",
    "PlotTransferResult",
    "SmallMultiplesSpec",
    "SchemaValidationReport",
    "SchemaViolation",
    "render_figure",
    "render_dashboard",
    "apply_linked_selection",
    "render_small_multiples",
    "export_bytes",
    "export_file",
    "render_portfolio",
    # typed figure config
    "FigureSpec",
    "FigureSpecBuilder",
    "DualAxisOpts",
    "LegendOpts",
    "ReferenceLineOpts",
    "grouped_bar_coordinates",
    "FigureDecorations",
    "Table",
    "read_table",
    # process utilities
    "doctor",
    "DoctorReport",
    "DependencyStatus",
    "shutdown",
    # errors
    "Ring5Error",
    "ScanError",
    "ParseError",
    "MissingStatError",
    "PipelineError",
    "ColumnNotFoundError",
    "DataLoadError",
    "DataValidationError",
    "RenderError",
    "PortfolioError",
    "PortfolioVersionError",
    "ExportError",
    "DependencyMissingError",
]
