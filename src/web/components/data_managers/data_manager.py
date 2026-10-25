"""
Base Data Manager
Abstract base class for all data managers.
"""

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd
import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models.preview_models import PreviewInputs
from src.web.state.ui_state_manager import WidgetKeyBuilder


class DataManager(ABC):
    """Abstract base class for data managers."""

    # [impl->req~ring5.extension.data-manager~1]

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
        """Restore a saved value, including an explicitly empty selection."""
        if value is not None:
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

    def set_data(self, data: pd.DataFrame, *, operation: str = "Update dataset") -> None:
        """Update active data and label its named-dataset lineage revision."""
        self.api.update_selected_dataset(data, operation=operation)

    def _store_preview(
        self,
        name: str,
        data: pd.DataFrame,
        config: dict[str, Any],
        inputs: PreviewInputs,
    ) -> None:
        """Bind a preview to the source and parameters that produced it."""
        self.api.set_preview(
            name,
            data,
            operation_config=config,
            inputs=inputs,
        )

    def _preview_available(self, name: str, config: dict[str, Any]) -> bool:
        """Invalidate a result when its source or operation controls change."""
        if not self.api.has_preview(name):
            return False
        if self.api.preview_matches(name, operation_config=config):
            return True
        self.api.clear_preview(name)
        st.warning(
            "The dataset or operation settings changed. Create a new preview before confirming."
        )
        return False

    def _confirm_preview(
        self,
        name: str,
        config: dict[str, Any],
        operation: str,
    ) -> tuple[pd.DataFrame, dict[str, Any]] | None:
        """Apply a current preview atomically and return its saved history inputs."""
        stored_config = self.api.get_preview_config(name)
        try:
            data = self.api.confirm_preview(name, operation_config=config, operation=operation)
        except ValueError as error:
            self.api.clear_preview(name)
            st.warning(str(error))
            return None
        return data, stored_config or {}
