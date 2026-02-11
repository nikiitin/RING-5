"""
Web Layer State Management (Layer 4).

Provides centralized, typed access to Streamlit session_state,
replacing scattered st.session_state["key"] access throughout the codebase.

Architecture:
    Page → Controller → Presenter
                ↕
          UIStateManager  ← YOU ARE HERE
                ↕
             Models
"""

from src.web.state.ui_state_manager import UIStateManager

__all__ = ["UIStateManager"]
