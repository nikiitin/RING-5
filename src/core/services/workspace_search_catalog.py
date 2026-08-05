"""Stable command and documentation documents for workspace search."""

from src.core.models.workspace_search_models import WorkspaceSearchEntry
from src.core.services.workspace_command_catalog import (
    DOCUMENTATION_URL,
    WORKSPACE_COMMANDS as REGISTERED_WORKSPACE_COMMANDS,
)

_DOCS_BASE_URL = DOCUMENTATION_URL.rstrip("/")


def _documentation(
    title: str,
    description: str,
    route: str,
    *keywords: str,
) -> WorkspaceSearchEntry:
    """Build one canonical published-documentation search entry."""
    return WorkspaceSearchEntry(
        kind="documentation",
        title=title,
        description=description,
        location=f"{_DOCS_BASE_URL}/{route.strip('/')}/",
        identifier=route.strip("/"),
        keywords=keywords,
    )


WORKSPACE_COMMANDS = tuple(
    WorkspaceSearchEntry(
        kind="documentation" if command.action == "open_external" else "command",
        title=command.title,
        description=command.description,
        location=command.destination,
        identifier=command.command_id,
        keywords=(*command.keywords, *command.shortcuts),
    )
    for command in REGISTERED_WORKSPACE_COMMANDS
)


WORKSPACE_DOCUMENTATION = (
    _documentation(
        "Install RING-5",
        "Set up the repository, optional export tools, and the web application.",
        "user-guide/getting-started/installation",
        "setup",
        "dependencies",
    ),
    _documentation(
        "First analysis",
        "Parse a gem5 statistic, create a plot, and export the result.",
        "user-guide/getting-started/first-analysis",
        "tutorial",
    ),
    _documentation(
        "Core concepts",
        "Understand workspace data, plot pipelines, rendering, and portfolios.",
        "user-guide/getting-started/concepts",
    ),
    _documentation(
        "Troubleshooting",
        "Resolve installation, parsing, plotting, export, and portfolio failures.",
        "user-guide/reference/troubleshooting",
        "errors",
        "problems",
    ),
    _documentation(
        "Load and parse data",
        "Parse a gem5 results tree or load an existing CSV.",
        "user-guide/workflows/loading-data",
        "scan",
        "variables",
    ),
    _documentation(
        "Manage datasets",
        "Reduce repeated runs, remove outliers, and derive shared columns.",
        "user-guide/workflows/managing-datasets",
        "transform",
        "join",
        "compare",
    ),
    _documentation(
        "Dataset snapshots",
        "Save, verify, and reload reusable dataset snapshots.",
        "user-guide/workflows/dataset-snapshots",
        "reuse",
    ),
    _documentation(
        "Background jobs",
        "Monitor progress, cancellation, retries, and bounded errors.",
        "user-guide/workflows/background-jobs",
        "async",
    ),
    _documentation(
        "Create plots",
        "Build a per-plot pipeline, map columns, render, and export.",
        "user-guide/workflows/plotting",
        "figure",
        "shaper",
    ),
    _documentation(
        "Manage portfolios",
        "Save, restore, migrate, and batch-render workspace snapshots.",
        "user-guide/workflows/portfolios",
        "history",
    ),
    _documentation(
        "Python and CLI",
        "Automate parsing, transformations, rendering, and portfolio replay.",
        "user-guide/workflows/scripting",
        "automation",
    ),
    _documentation(
        "Compare configurations",
        "Reduce seeds, normalize to a baseline, and render a grouped comparison.",
        "user-guide/guides/compare-configurations",
        "regression",
    ),
    _documentation(
        "Plot types",
        "Choose a registered plot type for the relationship in the data.",
        "user-guide/reference/plot-types",
        "chart",
        "visualization",
    ),
    _documentation(
        "Shapers",
        "Configure and verify ordered per-plot transformations.",
        "user-guide/reference/shapers",
        "pipeline",
    ),
    _documentation(
        "Figure settings",
        "Find layout, typography, axes, legend, label, and color controls.",
        "user-guide/reference/settings",
        "style",
    ),
    _documentation(
        "Rendering and export",
        "Check engine-format combinations and optional dependencies.",
        "user-guide/reference/rendering-export",
        "plotly",
        "matplotlib",
    ),
    _documentation(
        "Publication output",
        "Size, inspect, and export a figure for a target document.",
        "user-guide/guides/publication-export",
        "paper",
    ),
    _documentation(
        "Architecture",
        "Locate composition roots, dependency direction, and data flow.",
        "developer-guide/architecture",
        "developer",
    ),
    _documentation(
        "Contributor workflow",
        "Set up, implement, test, and review a repository change.",
        "developer-guide/development/workflow",
        "developer",
        "testing",
    ),
    _documentation(
        "Subsystems",
        "Find parsing, core, visualization, web, and portfolio ownership.",
        "developer-guide/subsystems",
        "developer",
    ),
    _documentation(
        "Extension guides",
        "Add a parser, plot, shaper, renderer, manager, or settings panel.",
        "developer-guide/extension-guides",
        "developer",
        "plugin",
    ),
)
