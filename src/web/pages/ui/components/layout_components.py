"""
Layout Components for RING-5.
Handles application layout, specific buttons, navigation, and sidebar.
"""

import streamlit as st


class LayoutComponents:
    """Reusable layout components and generic buttons."""

    @staticmethod
    def sidebar_info() -> None:
        """Display sidebar information about RING-5."""
        st.markdown("### About RING-5")
        st.info("""
        **Pure Python** implementation for gem5 data analysis.

        - Parse gem5 stats OR upload CSV
        - No R dependencies
        - Interactive configuration
        - Real-time visualization
        - Professional plots
        """)

    @staticmethod
    def navigation_menu() -> str:
        """
        Display navigation menu and return selected page.

        Returns:
            Selected page name
        """
        return st.radio(  # type: ignore[no-any-return]
            "Navigation",
            [
                "Data Source",
                "Upload Data",
                "Data Managers",
                "Configure Pipeline",
                "Generate Plots",
                "Load Configuration",
            ],
            label_visibility="collapsed",
        )

    @staticmethod
    def progress_display(step: int, total_steps: int, message: str) -> None:
        """
        Display a progress indicator.

        Args:
            step: Current step number
            total_steps: Total number of steps
            message: Status message
        """
        progress = step / total_steps
        st.progress(progress)
        st.text(message)

    @staticmethod
    def add_variable_button() -> bool:
        """
        Display an add variable button.

        Returns:
            True if button was clicked
        """
        col1, col2 = st.columns([1, 4])
        with col1:
            return st.button("+ Add Variable", width="stretch")  # type: ignore[no-any-return]
        return False

    @staticmethod
    def clear_data_button() -> bool:
        """
        Display clear data button.

        Returns:
            True if button was clicked
        """
        return st.button("Clear All Data", width="stretch")  # type: ignore[no-any-return]
