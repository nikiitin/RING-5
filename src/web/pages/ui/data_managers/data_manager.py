"""
Base Data Manager
Abstract base class for all data managers.
"""

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from src.core.application_api import ApplicationAPI


class DataManager(ABC):
    """Abstract base class for data managers."""

    def __init__(self, api: ApplicationAPI):
        """Initialize the manager with ApplicationAPI."""
        self.api = api

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the manager (displayed in tab)."""
        pass

    @abstractmethod
    def render(self) -> None:
        """Render the manager's UI."""
        pass

    def get_data(self) -> Optional[pd.DataFrame]:
        """Helper to get current data from StateManager."""
        return self.api.state_manager.get_data()

    def set_data(self, data: pd.DataFrame) -> None:
        """Helper to update application data."""
        self.api.state_manager.set_data(data)
