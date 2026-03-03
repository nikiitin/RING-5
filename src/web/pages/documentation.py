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
        "to find guides for the web application, tutorials, feature "
        "references, and developer resources."
    )

    st.markdown("---")

    # ── User Guide — Getting Started ─────────────────────────────
    st.markdown("### 🚀 Getting Started")
    st.markdown(
        "New to RING-5? Start here to install, learn key concepts, "
        "and create your first analysis."
    )

    col1, col2 = st.columns(2)
    with col1:
        _link_card(
            "📦",
            "Installation",
            "Python prerequisites, virtual environment setup, " "and launching the app.",
            "user-guide/getting-started/installation.md",
        )
        _link_card(
            "💡",
            "Key Concepts",
            "Variables, entries, data managers, shapers, settings " "pills, and export presets.",
            "user-guide/getting-started/concepts.md",
        )
    with col2:
        _link_card(
            "🎯",
            "First Steps",
            "Load data, create a bar chart, customize it, and " "export — in 7 steps.",
            "user-guide/getting-started/first-steps.md",
        )
        _link_card(
            "❓",
            "FAQ",
            "Answers to common questions about data loading, " "plotting, and exports.",
            "user-guide/reference/faq.md",
        )

    st.markdown("---")

    # ── User Guide — Page Guides ─────────────────────────────────
    st.markdown("### 🌐 Page Guides")
    st.markdown("Detailed walkthrough of every page in the RING-5 web application.")

    col1, col2 = st.columns(2)
    with col1:
        _link_card(
            "📂",
            "Data Source",
            "Load simulation data — parse gem5 stats, upload CSV, " "or reload recent files.",
            "user-guide/pages/data-source.md",
        )
        _link_card(
            "📊",
            "Manage Plots",
            "Create plots, build shaper pipelines, configure " "settings, and export figures.",
            "user-guide/pages/manage-plots.md",
        )
    with col2:
        _link_card(
            "🔧",
            "Data Managers",
            "Clean and transform data — preprocessing, outlier " "removal, seed reduction, mixing.",
            "user-guide/pages/data-managers.md",
        )
        _link_card(
            "💾",
            "Portfolio",
            "Save and reload entire analysis sessions as " "portable JSON snapshots.",
            "user-guide/pages/portfolio.md",
        )

    st.markdown("---")

    # ── User Guide — Features ────────────────────────────────────
    st.markdown("### 🔍 Features Reference")
    st.markdown(
        "In-depth reference for every feature — plot types, shapers, "
        "settings, export presets, and rendering engines."
    )

    col1, col2 = st.columns(2)
    with col1:
        _link_card(
            "📈",
            "Plot Types",
            "All 9 plot types with column requirements, use cases, " "and configuration options.",
            "user-guide/features/plot-types.md",
        )
        _link_card(
            "🎨",
            "Settings Pills",
            "11 settings pills — layout, typography, axes, legend, "
            "colors, data labels, and more.",
            "user-guide/features/settings.md",
        )
        _link_card(
            "⚡",
            "Dual Engine",
            "When to use Plotly (interactive) vs Matplotlib " "(publication-quality).",
            "user-guide/features/dual-engine.md",
        )
    with col2:
        _link_card(
            "🔀",
            "Shapers",
            "10 shaper types for filtering, sorting, normalizing, "
            "pivoting, and transforming data.",
            "user-guide/features/shapers.md",
        )
        _link_card(
            "📥",
            "Export Presets",
            "13 venue-specific presets (ISCA, MICRO, ASPLOS, …) "
            "with dimensions and format details.",
            "user-guide/features/export-presets.md",
        )
        _link_card(
            "🗂️",
            "Portfolios",
            "How portfolios capture and restore complete workspace " "state across sessions.",
            "user-guide/features/portfolios.md",
        )

    st.markdown("---")

    # ── User Guide — Tutorials ───────────────────────────────────
    st.markdown("### 📝 Tutorials")
    st.markdown("Hands-on, step-by-step guides that walk you through " "common analysis workflows.")

    col1, col2 = st.columns(2)
    with col1:
        _link_card(
            "📂",
            "Load & Explore Data",
            "Import CSV or parse gem5 stats, then inspect and " "clean your dataset.",
            "user-guide/tutorials/load-and-explore.md",
        )
        _link_card(
            "📐",
            "Normalize Data",
            "Use the shaper pipeline to normalize metrics against " "a baseline configuration.",
            "user-guide/tutorials/normalize-data.md",
        )
        _link_card(
            "🔬",
            "Compare Simulations",
            "Multi-seed analysis with grouped bars and error bars.",
            "user-guide/tutorials/compare-simulations.md",
        )
    with col2:
        _link_card(
            "📊",
            "Create a Bar Chart",
            "Build a grouped bar chart comparing performance " "across benchmarks.",
            "user-guide/tutorials/create-bar-chart.md",
        )
        _link_card(
            "📄",
            "Publication-Ready Export",
            "Apply an ISCA preset and export PDF/PGF figures " "for LaTeX papers.",
            "user-guide/tutorials/publication-ready.md",
        )
        _link_card(
            "🎨",
            "Custom Styling",
            "Fine-tune typography, colors, legends, axes, " "and reference lines.",
            "user-guide/tutorials/custom-styling.md",
        )

    st.markdown("---")

    # ── Developer Guide ──────────────────────────────────────────
    st.markdown("### 🛠️ Developer Guide")
    st.markdown(
        "Architecture, API reference, extension guides, and "
        "development workflow for contributors."
    )

    col1, col2 = st.columns(2)
    with col1:
        _link_card(
            "🏛️",
            "Architecture Overview",
            "3-layer architecture, design patterns, and module " "boundaries.",
            "developer-guide/architecture/overview.md",
        )
        _link_card(
            "🏗️",
            "Application API",
            "ApplicationAPI — the single entry point to all " "backend operations.",
            "developer-guide/api-reference/application-api.md",
        )
        _link_card(
            "🔌",
            "Extension Guides",
            "How to add new plot types, shapers, data managers, " "renderers, and settings panels.",
            "developer-guide/extension-guides/adding-a-plot-type.md",
        )
        _link_card(
            "📈",
            "Plotting System",
            "FigureConfig, PlotFactory, rendering connectors, "
            "and engine-agnostic visualization.",
            "developer-guide/visualization/plotting-system.md",
        )
    with col2:
        _link_card(
            "🧱",
            "Layer Boundaries",
            "Import rules, dependency flow, and the " "Core ← Parsing / Web → Core contract.",
            "developer-guide/architecture/layer-boundaries.md",
        )
        _link_card(
            "⚙️",
            "Parsing System",
            "SimulationParser protocol, SimulatorRegistry, " "and the gem5 backend.",
            "developer-guide/parsing/parsing-architecture.md",
        )
        _link_card(
            "🧪",
            "Testing Guide",
            "Test organization, coverage requirements, and " "how to write tests.",
            "developer-guide/development/testing.md",
        )
        _link_card(
            "💻",
            "Development Setup",
            "Environment setup, dependencies, and development " "workflow.",
            "developer-guide/development/setup.md",
        )

    st.markdown("---")

    # ── Quick Reference ──────────────────────────────────────────
    st.markdown("### 📋 Quick Reference")

    col1, col2 = st.columns(2)
    with col1:
        _link_card(
            "📁",
            "Supported Formats",
            "Input formats (CSV, gem5 stats) and export formats " "(PNG, SVG, PDF, HTML, PGF).",
            "user-guide/reference/supported-formats.md",
        )
    with col2:
        _link_card(
            "⌨️",
            "Keyboard Shortcuts",
            "Streamlit and Plotly keyboard shortcuts for " "faster navigation.",
            "user-guide/reference/keyboard-shortcuts.md",
        )
