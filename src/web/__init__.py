"""
RING-5 Web Module
Export all web components.
"""

from .components import UIComponents
from .facade import BackendFacade
from .state_manager import StateManager
from .styles import AppStyles, PageConfig

__all__ = ["AppStyles", "PageConfig", "StateManager", "BackendFacade", "UIComponents"]
