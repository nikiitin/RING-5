"""
Card Components for RING-5.
Handles information cards for files, configurations, etc.
"""

import datetime
from typing import Any, Dict

import streamlit as st


class CardComponents:
    """Reusable information card components."""

    @staticmethod
    def file_info_card(file_info: Dict[str, Any], index: int):
        """
        Display a file information card with actions.

        Args:
            file_info: Dictionary with file information
            index: Unique index for the card

        Returns:
            Tuple of (load_clicked, preview_clicked, delete_clicked)
        """
        modified_time = datetime.datetime.fromtimestamp(file_info["modified"])

        with st.expander(
            f"{file_info['name']} ({file_info['size'] / 1024:.1f} KB)", expanded=(index == 0)
        ):
            st.text(f"Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")

            col1, col2, col3 = st.columns(3)

            with col1:
                load_clicked = st.button("Load This File", key=f"load_{index}")

            with col2:
                preview_clicked = st.button("Preview", key=f"preview_{index}")

            with col3:
                delete_clicked = st.button("Delete", key=f"delete_{index}")

            return load_clicked, preview_clicked, delete_clicked

    @staticmethod
    def config_info_card(config_info: Dict[str, Any], index: int):
        """
        Display a configuration information card with actions.

        Args:
            config_info: Dictionary with config information
            index: Unique index for the card

        Returns:
            Tuple of (load_clicked, delete_clicked)
        """
        modified_time = datetime.datetime.fromtimestamp(config_info["modified"])

        with st.expander(f"{config_info['name']}", expanded=(index == 0)):
            st.text(f"Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.text(f"Description: {config_info['description']}")

            col1, col2 = st.columns(2)

            with col1:
                load_clicked = st.button("Load This Configuration", key=f"load_cfg_{index}")

            with col2:
                delete_clicked = st.button("Delete", key=f"delete_cfg_{index}")

            return load_clicked, delete_clicked
