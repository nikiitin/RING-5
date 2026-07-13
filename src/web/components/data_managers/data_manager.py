"""
Base Data Manager
Abstract base class for all data managers.
"""

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd
import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.state.ui_state_manager import WidgetKeyBuilder


class DataManager(ABC):
    """Abstract base class for data managers."""

    def __init__(self, api: ApplicationAPI):
        """Initialize the manager with ApplicationAPI."""
        self.api = api

    # shared "restore a loaded operation" helpers
    # The per-manager decode (which columns map to which widget) is intentionally
    # distinct, but the warning text and the "write a widget key" step are shared so they
    # cannot drift across the four managers.
    @staticmethod
    def _warn_removed_columns(missing: list[str]) -> None:
        """One warning for columns dropped because they aren't in the current data."""
        if missing:
            st.warning(f"Columns removed (not in current data): {', '.join(missing)}")

    @staticmethod
    def _restore_selection(manager: str, field: str, value: Any) -> None:
        """Seed a manager widget's saved value into session state (if non-empty)."""
        if value:
            st.session_state[WidgetKeyBuilder.manager_key(manager, field)] = value

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the manager (displayed in tab)."""

    @abstractmethod
    def render(self) -> None:
        """Render the manager's UI."""

    def get_data(self) -> pd.DataFrame | None:
        """Helper to get current data from StateManager."""
        return self.api.state_manager.get_data()

    def set_data(self, data: pd.DataFrame) -> None:
        """Helper to update application data."""
        self.api.state_manager.set_data(data)
