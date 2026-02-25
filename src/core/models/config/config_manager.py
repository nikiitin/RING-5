"""
RING-5 Configuration TypedDict Models.

Pure data models for configuration structure.
Business logic (validation, template generation) lives in
src/core/services/config_validation_service.py.
"""

from __future__ import annotations

from typing import Any, TypedDict


class OutputConfig(TypedDict):
    """Type definition for plot output configuration."""

    filename: str
    format: str  # "png", "pdf", "svg"
    dpi: int


class PlotDataConfig(TypedDict, total=False):
    """Type definition for plot data configuration."""

    x: str
    y: str
    hue: str
    filters: dict[str, Any]
    aggregate: str


class PlotStyleConfig(TypedDict, total=False):
    """Type definition for plot style configuration."""

    width: int
    height: int
    theme: str
    title: str
    xlabel: str
    ylabel: str
    ylim: list[float]
    grid: bool
    legend: dict[str, Any]


class PlotConfig(TypedDict):
    """Type definition for complete plot configuration."""

    type: str
    output: OutputConfig
    data: PlotDataConfig
    style: PlotStyleConfig


class VariableConfig(TypedDict, total=False):
    """Type definition for variable parsing configuration."""

    name: str
    type: str  # "scalar", "vector", "distribution", "configuration"
    rename: str


class ParseConfig(TypedDict):
    """Type definition for parsing configuration."""

    parser: str
    statsPath: str
    statsPattern: str
    variables: list[VariableConfig]


class DataManagersConfig(TypedDict, total=False):
    """Type definition for data managers configuration."""

    seedsReducer: bool
    outlierRemover: dict[str, Any]
    normalizer: dict[str, Any]


class RingConfig(TypedDict):
    """Type definition for complete RING-5 configuration."""

    outputPath: str
    parseConfig: ParseConfig
    dataManagers: DataManagersConfig
    plots: list[PlotConfig]
