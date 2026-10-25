"""One native figure and the exact inputs and neutral preparation that produced it."""

from copy import deepcopy
from dataclasses import dataclass, field
from uuid import uuid4

import pandas as pd
import plotly.graph_objects as go
from matplotlib.figure import Figure as MplFigure

from src.core.models.plot_config import PlotConfig
from src.core.models.visualization.engine import EngineMode
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.web.rendering.figure_preparation import PreparedDashboard, PreparedFigure


@dataclass(frozen=True, slots=True)
class RenderArtifact:
    """Own one complete native generation or its configuration-only detached state."""

    _config: PlotConfig | None
    figure: go.Figure | MplFigure | None = None
    preparation: PreparedFigure | PreparedDashboard | None = None
    engine: EngineMode | None = None
    cache_key: str | None = None
    source_data: pd.DataFrame | None = None
    generation: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        if self.figure is None:
            if any(
                value is not None
                for value in (self.preparation, self.engine, self.cache_key, self.source_data)
            ):
                raise ValueError("Detached artifacts retain configuration only.")
        else:
            expected_engine = "plotly" if isinstance(self.figure, go.Figure) else "matplotlib"
            if (
                not isinstance(self.figure, (go.Figure, MplFigure))
                or self.engine != expected_engine
            ):
                raise ValueError("A render artifact's engine must match its native figure.")
            if not isinstance(self.preparation, (PreparedFigure, PreparedDashboard)):
                raise ValueError("A native artifact requires its actual neutral preparation.")
        if isinstance(self.preparation, PreparedFigure):
            if self._config is not None:
                raise ValueError("Single-figure configuration belongs to its preparation.")
        elif self._config is None:
            raise ValueError("Detached and composite artifacts require configuration state.")

    @property
    def config(self) -> PlotConfig:
        """Return an owned snapshot of this generation's one configuration authority."""
        if isinstance(self.preparation, PreparedFigure):
            return self.preparation.config
        if self._config is None:
            raise ValueError("Detached and composite artifacts require configuration state.")
        return deepcopy(self._config)

    @property
    def trace_result(self) -> TraceBuildResult | None:
        """Return actual single-figure traces; composite panels retain their own results."""
        return (
            self.preparation.trace_result if isinstance(self.preparation, PreparedFigure) else None
        )

    @property
    def figure_spec(self) -> FigureConfig | PreparedDashboard | None:
        """Return single-figure styling or the complete real panel preparation."""
        if isinstance(self.preparation, PreparedFigure):
            return self.preparation.spec
        return self.preparation

    def detached(self) -> "RenderArtifact":
        """Retain configuration without native, source-row or preparation references."""
        return RenderArtifact(self.config)
