"""
RING-5 Services Module -- Business logic and data operations.

Public API:
    - DefaultServicesAPI:  Default implementation composing all services

Sub-APIs composed by DefaultServicesAPI:
    - managers:       ManagersAPI (arithmetic, outlier, reduction)
    - data_services:  DataServicesAPI (CSV pool, config, variables, portfolios)
    - shapers:        ShapersAPI (pipeline CRUD + shaper execution)

Submodules:
    - managers/       Stateless data transformation services
    - data_services/  Data storage, retrieval, and domain entities
    - shapers/        Pipeline management and shaper implementations
"""

from .data_services import (
    ConfigService,
    CsvPoolService,
    DataServicesAPI,
    DatasetSnapshotService,
    DefaultDataServicesAPI,
    PathService,
    PortfolioService,
    VariableService,
)
from .managers import (
    ArithmeticService,
    DefaultManagersAPI,
    ManagersAPI,
    OutlierService,
    ReductionService,
)
from .services_impl import DefaultServicesAPI
from .shapers import DefaultShapersAPI, PipelineService, ShaperFactory, ShapersAPI

__all__ = [
    # Primary API
    "DefaultServicesAPI",
    # Sub-API protocols
    "ManagersAPI",
    "DataServicesAPI",
    "ShapersAPI",
    # Sub-API implementations
    "DefaultManagersAPI",
    "DefaultDataServicesAPI",
    "DefaultShapersAPI",
    # Individual services (re-exports)
    "ArithmeticService",
    "OutlierService",
    "ReductionService",
    "CsvPoolService",
    "ConfigService",
    "PathService",
    "VariableService",
    "PortfolioService",
    "DatasetSnapshotService",
    "PipelineService",
    "ShaperFactory",
]
