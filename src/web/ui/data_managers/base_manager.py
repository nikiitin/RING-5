"""
Base Data Manager
Abstract base class for all data managers.
"""

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd
import streamlit as st

from src.web.state_manager import StateManager


class DataManager(ABC):
    """Abstract base class for data managers."""

    def __init__(self):
        """
        Initialize the data manager.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the manager (displayed in tab)."""
        pass

    @abstractmethod
    def render(self):
        """Render the manager's UI."""
        pass

    def get_data(self) -> Optional[pd.DataFrame]:
        """Helper to get current data from StateManager."""
        return StateManager.get_data()

    def set_data(self, data: pd.DataFrame):
        """Helper to update application data."""
        StateManager.set_data(data)
