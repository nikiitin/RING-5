"""Typed models for reusable parameterized analysis recipes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from src.core.models.data_models import ParseVariableConfig, ScannedVariableDict
from src.core.models.shaper_models import ShaperStepConfig

RecipeParameterType = Literal["string", "integer", "number", "boolean", "path"]
RecipeScalar = str | int | float | bool
RecipeSourceKind = Literal["csv", "parser"]
RecipeEngine = Literal["plotly", "matplotlib"]


@dataclass(frozen=True)
class RecipeParameter:
    """One typed value resolved when an analysis recipe runs.

    Attributes:
        name: Placeholder identifier used as ``{{name}}``.
        type: Runtime value type.
        description: Human-readable purpose.
        required: Whether callers must supply a value when no default exists.
        default: Optional validated fallback value.
        choices: Optional allowed values, all matching ``type``.
    """

    name: str
    type: RecipeParameterType
    description: str = ""
    required: bool = True
    default: RecipeScalar | None = None
    choices: tuple[RecipeScalar, ...] = ()


@dataclass(frozen=True)
class RecipeSource:
    """CSV or simulator-parser input used by an analysis recipe.

    Attributes:
        kind: ``"csv"`` or ``"parser"``.
        path: CSV path or simulator-results root, optionally parameterized.
        pattern: Parser statistics-file pattern.
        strategy: Registered parser strategy.
        variables: Serialized parser-variable configurations.
        scanned_variables: Captured scanner metadata used by parser variables.
        scan_limit: Parser discovery sample limit; zero is exhaustive.
        strict: Whether missing parser statistics fail execution.
    """

    kind: RecipeSourceKind
    path: str
    pattern: str = "stats.txt"
    strategy: str = "simple"
    variables: tuple[ParseVariableConfig, ...] = ()
    scanned_variables: tuple[ScannedVariableDict, ...] = ()
    scan_limit: int = 10
    strict: bool = True


@dataclass(frozen=True)
class RecipePlot:
    """One plot and its independent shaping pipeline.

    Attributes:
        name: Stable recipe-local plot name.
        plot_type: Registered plot identifier.
        config: Flat figure configuration accepted by ``Session.create_plot``.
        pipeline: Ordered shapers applied before the plot is created.
    """

    name: str
    plot_type: str
    config: Mapping[str, Any]
    pipeline: tuple[ShaperStepConfig, ...] = ()


@dataclass(frozen=True)
class RecipeExport:
    """File export produced from one named recipe plot.

    Attributes:
        plot: Recipe-local plot name.
        path: Output path, optionally parameterized.
        engine: Rendering engine.
        format: Explicit engine-supported output format.
        deterministic: Whether to enable byte-stable export settings.
    """

    plot: str
    path: str
    engine: RecipeEngine = "matplotlib"
    format: str = "pdf"
    deterministic: bool = True


@dataclass(frozen=True)
class AnalysisRecipe:
    # [impl->req~ring5.portfolio.analysis-recipes~1]
    """Versioned reusable analysis definition.

    Attributes:
        name: Stable saved recipe name.
        description: Human-readable purpose.
        source: CSV or parser input definition.
        parameters: Typed runtime placeholder declarations.
        transformations: Ordered dataset-wide shapers.
        plots: Plot configurations and per-plot shapers.
        exports: Named-plot output instructions.
        schema_version: Recipe document schema version.
    """

    name: str
    source: RecipeSource
    description: str = ""
    parameters: tuple[RecipeParameter, ...] = ()
    transformations: tuple[ShaperStepConfig, ...] = ()
    plots: tuple[RecipePlot, ...] = ()
    exports: tuple[RecipeExport, ...] = ()
    schema_version: int = 1


@dataclass(frozen=True)
class AnalysisRecipeInfo:
    """Saved recipe catalog entry.

    Attributes:
        name: Saved recipe name.
        description: Human-readable purpose.
        path: Local recipe JSON path.
        modified: File modification time as seconds since the epoch.
        parameters: Number of runtime parameters.
        transformations: Number of dataset-wide shapers.
        plots: Number of plots.
        exports: Number of export instructions.
    """

    name: str
    description: str
    path: str
    modified: float
    parameters: int
    transformations: int
    plots: int
    exports: int


@dataclass(frozen=True)
class AnalysisRecipeRunResult:
    """Outcome of executing one materialized analysis recipe.

    Attributes:
        recipe_name: Executed recipe name.
        parameter_values: Resolved runtime values in declaration order.
        rows: Rows in the transformed dataset.
        columns: Columns in the transformed dataset.
        plot_names: Created plots in recipe order.
        exported_paths: Written output files in recipe order.
    """

    recipe_name: str
    parameter_values: tuple[tuple[str, RecipeScalar], ...]
    rows: int
    columns: tuple[str, ...]
    plot_names: tuple[str, ...] = field(default_factory=tuple)
    exported_paths: tuple[str, ...] = field(default_factory=tuple)
