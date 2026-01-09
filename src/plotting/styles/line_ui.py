from typing import Any, Dict
import streamlit as st
from .base_ui import BaseStyleUI

class LineStyleUI(BaseStyleUI):
    def _render_specific_series_visuals(self, current_style: Dict[str, Any], key_suffix: str, key_prefix: str = ""):
         with st.expander("Marker & Line", expanded=False):
             symbols = ["circle", "square", "diamond", "cross", "x", "triangle-up", "triangle-down"]
             new_symbol = st.selectbox(
                 "Marker Symbol",
                 options=symbols,
                 index=symbols.index(current_style.get("symbol", "circle")) if current_style.get("symbol") in symbols else 0,
                 key=f"{key_prefix}sym_{self.plot_id}_{key_suffix}"
             )
             current_style["symbol"] = new_symbol
             
             marker_size = st.number_input(
                 "Marker Size",
                 min_value=0,
                 max_value=50,
                 value=current_style.get("marker_size", 8),
                 key=f"{key_prefix}msize_{self.plot_id}_{key_suffix}"
             )
             current_style["marker_size"] = marker_size

             line_width = st.number_input(
                 "Line Width",
                 min_value=1,
                 max_value=20,
                 value=current_style.get("line_width", 2),
                 key=f"{key_prefix}lwidth_{self.plot_id}_{key_suffix}"
             )
             current_style["line_width"] = line_width

class ScatterStyleUI(LineStyleUI):
    pass
