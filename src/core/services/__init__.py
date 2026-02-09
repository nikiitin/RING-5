"""
RING-5 Services Module -- Business logic and data operations.

Public API:
    - ServicesAPI:         Protocol defining the unified services facade
    - DefaultServicesAPI:  Default implementation composing all services

Sub-APIs (accessed through ServicesAPI):
    - data:      DataServicesAPI (CSV pool, config persistence)
    - compute:   ComputeServicesAPI (arithmetic, outlier, reduction)
    - pipeline:  PipelineServicesAPI (shaper pipeline CRUD + execution)
    - variable:  VariableServicesAPI (gem5 variable management)
    - portfolio: PortfolioServicesAPI (workspace persistence)

Individual services are re-exported for backward compatibility,
but new code should use ServicesAPI instead.
"""

from .arithmetic_service import ArithmeticService
from .config_service import ConfigService
from .csv_pool_service import CsvPoolService
from .outlier_service import OutlierService
from .path_service import PathService
from .pipeline_service import PipelineService
from .portfolio_service import PortfolioService
from .reduction_service import ReductionService
from .services_api import (
    ComputeServicesAPI,
    DataServicesAPI,
    PipelineServicesAPI,
    PortfolioServicesAPI,
    ServicesAPI,
    VariableServicesAPI,
)
from .services_impl import DefaultServicesAPI
from .variable_service import VariableService

__all__ = [
    # Primary API
    "ServicesAPI",
    "DefaultServicesAPI",
    # Sub-API protocols
    "DataServicesAPI",
    "ComputeServicesAPI",
    "PipelineServicesAPI",
    "VariableServicesAPI",
    "PortfolioServicesAPI",
    # Backward-compatible re-exports
    "ArithmeticService",
    "PipelineService",
    "VariableService",
    "ReductionService",
    "OutlierService",
    "PortfolioService",
    "PathService",
    "ConfigService",
    "CsvPoolService",
]
