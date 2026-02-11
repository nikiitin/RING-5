"""
Plot Controls Presenter — renders rename, save/load, delete, duplicate buttons.

Returns which actions the user triggered as a typed dict.
The controller handles the actual operations.

Save/Load dialog buttons accept optional ``on_click`` callbacks so that
state changes happen atomically in the callback phase, eliminating the
need for an explicit ``st.rerun()`` in the controller.
"""

from typing import Any, Callable, Dict, Optional

import streamlit as st


class PlotControlsPresenter:
    """
    Renders plot management controls (rename, pipeline I/O, delete, duplicate).

    Usage::

        actions = PlotControlsPresenter.render(plot_id=1, current_name="My Plot")
        if actions["delete_clicked"]:
            controller.delete_plot(1)
    """

    @staticmethod
    def render(
        plot_id: int,
        current_name: str,
        on_save: Optional[Callable[[], None]] = None,
        on_load: Optional[Callable[[], None]] = None,
    ) -> Dict[str, Any]:
        """
        Render plot control widgets.

        Args:
            plot_id: Unique plot ID (for widget keys).
            current_name: Current plot display name.
            on_save: Optional callback for Save Pipeline button.
                When provided, fires via ``on_click`` — the controller
                does not need to check ``save_clicked`` or call rerun.
            on_load: Optional callback for Load Pipeline button.
                When provided, fires via ``on_click`` — the controller
                does not need to check ``load_clicked`` or call rerun.

        Returns:
            Dict with:
                - new_name (str): Possibly changed name.
                - save_clicked (bool): Save Pipeline clicked.
                - load_clicked (bool): Load Pipeline clicked.
                - delete_clicked (bool): Delete clicked.
                - duplicate_clicked (bool): Duplicate clicked.
        """
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            new_name: str = st.text_input(
                "Rename plot", value=current_name, key=f"rename_{plot_id}"
            )

        with col2:
            c2_1, c2_2 = st.columns(2)
            with c2_1:
                save_kwargs: Dict[str, Any] = {
                    "key": f"save_plot_{plot_id}",
                    "help": "Save current pipeline",
                }
                if on_save is not None:
                    save_kwargs["on_click"] = on_save
                save_clicked: bool = st.button("Save Pipe", **save_kwargs)
            with c2_2:
                load_kwargs: Dict[str, Any] = {
                    "key": f"load_plot_{plot_id}",
                    "help": "Load to current pipeline",
                }
                if on_load is not None:
                    load_kwargs["on_click"] = on_load
                load_clicked: bool = st.button("Load Pipe", **load_kwargs)

        with col3:
            delete_clicked: bool = st.button("Delete", key=f"delete_plot_{plot_id}")

        with col4:
            duplicate_clicked: bool = st.button("Duplicate", key=f"dup_plot_{plot_id}")

        return {
            "new_name": new_name,
            "save_clicked": save_clicked,
            "load_clicked": load_clicked,
            "delete_clicked": delete_clicked,
            "duplicate_clicked": duplicate_clicked,
        }
