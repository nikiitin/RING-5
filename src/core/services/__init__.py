"""
RING-5 Services Module -- Business logic and data operations.

Public API:
    - ServicesAPI:         Protocol defining the unified services facade
    - DefaultServicesAPI:  Default implementation composing all services

Sub-APIs (accessed through ServicesAPI):
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
from .services_api import ServicesAPI
from .services_impl import DefaultServicesAPI
from .shapers import (
    DefaultShapersAPI,
    PipelineService,
    ShaperFactory,
    ShapersAPI,
)

__all__ = [
    # Primary API
    "ServicesAPI",
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
    "PipelineService",
    "ShaperFactory",
]
