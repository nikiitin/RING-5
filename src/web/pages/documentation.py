"""Documentation hub linking to the published RING-5 guides."""

from __future__ import annotations

from collections.abc import Sequence

import streamlit as st

_DOCS_BASE_URL = "https://nikiitin.github.io/RING-5"
_Card = tuple[str, str, str]


def _published_url(route: str) -> str:
    """Return the published URL for a documentation route."""
    return f"{_DOCS_BASE_URL}/{route.strip('/')}/"


def _link_card(title: str, description: str, route: str) -> None:
    """Render a card with a direct link to a published documentation page.

    Args:
        title: Card title.
        description: Short description of the linked task.
        route: Published route relative to the documentation root.
    """
    st.markdown(
        f"#### {title}\n\n{description}\n\n" f"[Open documentation]({_published_url(route)})"
    )


def _card_grid(cards: Sequence[_Card]) -> None:
    """Render documentation cards in two columns."""
    columns = st.columns(2)
    for index, (title, description, route) in enumerate(cards):
        with columns[index % len(columns)]:
            _link_card(title, description, route)


def show_documentation_page() -> None:
    """Render the Documentation hub page."""
    st.markdown("## Documentation")
    st.markdown(
        "Open the published User Guide for analysis tasks or the Developer Guide "
        "for architecture and contribution work."
    )

    st.markdown("### Getting started")
    _card_grid(
        (
            (
                "Install RING-5",
                "Set up the repository, optional export tools, and the web application.",
                "user-guide/getting-started/installation",
            ),
            (
                "First analysis",
                "Parse a gem5 statistic, create a plot, and export the result.",
                "user-guide/getting-started/first-analysis",
            ),
            (
                "Core concepts",
                "Understand workspace data, plot pipelines, rendering, and portfolios.",
                "user-guide/getting-started/concepts",
            ),
            (
                "Troubleshooting",
                "Resolve installation, parsing, plotting, export, and portfolio failures.",
                "user-guide/reference/troubleshooting",
            ),
        )
    )

    st.markdown("### Analysis workflows")
    _card_grid(
        (
            (
                "Load and parse data",
                "Parse a gem5 results tree or load an existing CSV in Python.",
                "user-guide/workflows/loading-data",
            ),
            (
                "Manage datasets",
                "Reduce repeated runs, remove outliers, and derive shared columns.",
                "user-guide/workflows/managing-datasets",
            ),
            (
                "Create plots",
                "Build a per-plot pipeline, map columns, render, and export.",
                "user-guide/workflows/plotting",
            ),
            (
                "Manage portfolios",
                "Save, restore, migrate, and batch-render workspace snapshots.",
                "user-guide/workflows/portfolios",
            ),
            (
                "Python and CLI",
                "Automate parsing, transformations, rendering, and portfolio replay.",
                "user-guide/workflows/scripting",
            ),
            (
                "Compare configurations",
                "Reduce seeds, normalize to a baseline, and render a grouped comparison.",
                "user-guide/guides/compare-configurations",
            ),
        )
    )

    st.markdown("### Figure reference")
    _card_grid(
        (
            (
                "Plot types",
                "Choose a registered plot type from the relationship in the data.",
                "user-guide/reference/plot-types",
            ),
            (
                "Shapers",
                "Configure and verify ordered per-plot transformations.",
                "user-guide/reference/shapers",
            ),
            (
                "Figure settings",
                "Find layout, typography, axes, legend, label, and color controls.",
                "user-guide/reference/settings",
            ),
            (
                "Rendering and export",
                "Check engine-format combinations and optional dependencies.",
                "user-guide/reference/rendering-export",
            ),
            (
                "Publication output",
                "Size, inspect, and export a figure for a target document.",
                "user-guide/guides/publication-export",
            ),
        )
    )

    st.markdown("### Developer Guide")
    _card_grid(
        (
            (
                "Architecture",
                "Locate composition roots, dependency direction, and data flow.",
                "developer-guide/architecture",
            ),
            (
                "Contributor workflow",
                "Set up, implement, test, and review a repository change.",
                "developer-guide/development/workflow",
            ),
            (
                "Subsystems",
                "Find parsing, core, visualization, web, and portfolio ownership.",
                "developer-guide/subsystems",
            ),
            (
                "Extension guides",
                "Add a parser, plot, shaper, renderer, manager, or settings panel.",
                "developer-guide/extension-guides",
            ),
        )
    )
