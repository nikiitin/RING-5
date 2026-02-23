"""
Services API Protocol -- Unified facade interface for the services subsystem.

Defines the contract for a complete services API that combines three
domain-aligned sub-APIs behind a single hierarchical facade.

Architecture:
    ServicesAPI
    +-- managers       -> ManagersAPI (arithmetic, outlier, reduction)
    +-- data_services  -> DataServicesAPI (CSV pool, config, variables, portfolios)
    +-- shapers        -> ShapersAPI (pipeline CRUD + shaper execution)

Implementations:
    - DefaultServicesAPI: Default implementation composing individual services
"""

from typing import Protocol, runtime_checkable

from src.core.services.data_services.data_services_api import DataServicesAPI
from src.core.services.managers.managers_api import ManagersAPI
from src.core.services.shapers.shapers_api import ShapersAPI


@runtime_checkable
class ServicesAPI(Protocol):
    """Unified facade for the services subsystem.

    Provides hierarchical access to all service operations through
    three domain-aligned sub-APIs. Analogous to ``ParserAPI`` in the
    parsing module.

    Usage::

        api = DefaultServicesAPI(state_manager)
        pool = api.data_services.load_csv_pool()
        result = api.managers.remove_outliers(df, col, groups)
        api.shapers.save_pipeline("my_pipeline", config)
    """

    @property
    def managers(self) -> ManagersAPI:
        """Access stateless data transformation operations."""
        ...

    @property
    def data_services(self) -> DataServicesAPI:
        """Access data storage, retrieval, and domain entity management."""
        ...

    @property
    def shapers(self) -> ShapersAPI:
        """Access pipeline and shaper operations."""
        ...
