"""
Figure Engine — Streamlit-free figure construction and styling.

Public API:
    FigureEngine: Facade for building styled Plotly figures.
    FigureCreator: Protocol for type-specific figure creation.
    FigureStyler: Protocol for style application.
"""

from src.web.figures.engine import FigureEngine
from src.web.figures.protocols import FigureCreator, FigureStyler

__all__: list[str] = ["FigureEngine", "FigureCreator", "FigureStyler"]
