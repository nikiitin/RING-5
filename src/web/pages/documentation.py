"""
Documentation page — lightweight hub linking to detailed docs pages.

Points users to the multi-page documentation in ``docs/`` rather than
embedding content inline.  Each card links to the relevant docs page
for comprehensive guides on each topic.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

# Root of the docs tree (for link construction)
_DOCS_ROOT: Path = Path(__file__).parents[3] / "docs"


def _link_card(icon: str, title: str, description: str, doc_path: str) -> None:
    """Render a documentation link card.

    Parameters
    ----------
    icon:
        Emoji icon for the card header.
    title:
        Card title.
    description:
        Brief description of what the linked page covers.
    doc_path:
        Relative path from the docs root to the Markdown file.
    """
    resolved: Path = _DOCS_ROOT / doc_path
    exists: bool = resolved.exists()
    status: str = "" if exists else " *(coming soon)*"
    st.markdown(f"#### {icon} {title}{status}\n\n{description}\n\n" f"📄 `docs/{doc_path}`")


def show_documentation_page() -> None:
    """Render the Documentation hub page."""
    st.markdown("## 📚 Documentation")
    st.markdown(
        "Welcome to the RING-5 documentation. Browse the sections below "
        "to find guides for the web application, the programmatic API, "
        "and developer resources."
    )

    st.markdown("---")

    # ── WebApp Guide ─────────────────────────────────────────────
    st.markdown("### 🌐 WebApp Guide")
    st.markdown("Step-by-step guides for every page in the RING-5 web application.")

    col1, col2 = st.columns(2)
    with col1:
        _link_card(
            "🚀",
            "Quick Start",
            "Get up and running in under 5 minutes.",
            "webapp/Quick-Start.md",
        )
        _link_card(
            "📂",
            "Data Source",
            "Load simulation data — parse gem5 stats, upload CSV, " "or reload recent files.",
            "webapp/pages/Data-Source.md",
        )
        _link_card(
            "📊",
            "Manage Plots",
            "Create plots, build shaper pipelines, and configure " "rendering engines.",
            "webapp/pages/Manage-Plots.md",
        )
    with col2:
        _link_card(
            "🎯",
            "First Analysis",
            "End-to-end walkthrough from raw stats to a published figure.",
            "webapp/First-Analysis.md",
        )
        _link_card(
            "🔧",
            "Data Managers",
            "Clean and transform data — preprocessing, outlier removal, " "seed reduction, mixing.",
            "webapp/pages/Data-Managers.md",
        )
        _link_card(
            "🎨",
            "Plot Settings",
            "Reference for every settings pill — layout, typography, "
            "legends, axes, colors, and more.",
            "webapp/pages/Plot-Settings.md",
        )

    col1, col2 = st.columns(2)
    with col1:
        _link_card(
            "📥",
            "Export & Download",
            "Export figures as PNG, SVG, PDF, HTML, or PGF for LaTeX.",
            "webapp/pages/Export-Download.md",
        )
    with col2:
        _link_card(
            "💾",
            "Portfolios",
            "Save and reload entire analysis sessions.",
            "webapp/Portfolios.md",
        )

    st.markdown("---")

    # ── API Reference ────────────────────────────────────────────
    st.markdown("### 🔌 API Reference")
    st.markdown("Programmatic access to scanning, parsing, shaping, and plotting.")

    col1, col2 = st.columns(2)
    with col1:
        _link_card(
            "🏗️",
            "Backend Facade",
            "ApplicationAPI — the single entry point to all operations.",
            "api/Backend-Facade.md",
        )
        _link_card(
            "📈",
            "Plotting API",
            "FigureConfig, rendering connectors, and engine-agnostic " "visualization.",
            "api/Plotting-API.md",
        )
    with col2:
        _link_card(
            "⚙️",
            "Parsing API",
            "SimulationParser protocol, SimulatorRegistry, and gem5 " "backend.",
            "api/Parsing-API.md",
        )
        _link_card(
            "🔀",
            "Shaper API",
            "Data transformation pipeline — ShaperFactory and available " "shapers.",
            "api/Shaper-API.md",
        )

    st.markdown("---")

    # ── Developer Guides ─────────────────────────────────────────
    st.markdown("### 🛠️ Developer Guides")

    col1, col2 = st.columns(2)
    with col1:
        _link_card(
            "🏛️",
            "Architecture",
            "3-layer architecture, design patterns, and module " "boundaries.",
            "developer/Architecture.md",
        )
        _link_card(
            "🧪",
            "Testing Guide",
            "Test organization, coverage requirements, and how to " "write tests.",
            "developer/Testing-Guide.md",
        )
    with col2:
        _link_card(
            "💻",
            "Development Setup",
            "Environment setup, dependencies, and development workflow.",
            "developer/Development-Setup.md",
        )
        _link_card(
            "📊",
            "Adding Plot Types",
            "How to register new plot types with the PlotFactory.",
            "developer/Adding-Plot-Types.md",
        )
