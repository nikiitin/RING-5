"""
Default implementation of the ServicesAPI protocol.

Composes the three domain-aligned sub-APIs into a unified facade,
providing a single entry point for all service operations.

Each sub-API is self-contained. Cross-module dependencies are resolved
via dependency injection at this composition root.
"""

from src.core.services.data_services.data_services_impl import DefaultDataServicesAPI
from src.core.services.data_services.path_service import PathService
from src.core.services.managers.managers_impl import DefaultManagersAPI
from src.core.services.shapers.shapers_impl import DefaultShapersAPI
from src.core.state.state_manager import StateManager


class DefaultServicesAPI:
    """Default implementation of ServicesAPI.

    Composes all sub-API implementations and provides the unified
    entry point for service operations.

    Usage::

        api = DefaultServicesAPI(state_manager)
        pool = api.data_services.load_csv_pool()
        result = api.managers.remove_outliers(df, col, groups)
        api.shapers.save_pipeline("my_pipeline", config)
    """

    def __init__(self, state_manager: StateManager) -> None:
        """Initialize the services API with all sub-APIs.

        Cross-module dependencies are injected here:
        - ShapersAPI receives pipelines_dir from PathService.

        Args:
            state_manager: State manager instance for portfolio operations.
        """
        self._managers = DefaultManagersAPI()
        self._data_services = DefaultDataServicesAPI(state_manager)
        self._shapers = DefaultShapersAPI(PathService.get_pipelines_dir())

    @property
    def managers(self) -> DefaultManagersAPI:
        """Access stateless data transformation operations."""
        return self._managers

    @property
    def data_services(self) -> DefaultDataServicesAPI:
        """Access data storage, retrieval, and domain entity management."""
        return self._data_services

    @property
    def shapers(self) -> DefaultShapersAPI:
        """Access pipeline and shaper operations."""
        return self._shapers
