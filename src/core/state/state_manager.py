"""
RING-5 State Manager - Public Exports & Backward Compatibility.

Re-exports the AbstractStateManager protocol and the concrete
RepositoryStateManager for backward-compatible imports.

Architecture:
- AbstractStateManager: Protocol (lives in abstract_state_manager.py)
- RepositoryStateManager: Concrete implementation (lives in repository_state_manager.py)
"""

# Re-export Protocol for backward compatibility:
#   from src.core.state.state_manager import AbstractStateManager
from src.core.state.abstract_state_manager import (  # noqa: F401
    AbstractStateManager as AbstractStateManager,
)

# Re-export concrete implementation so existing imports keep working:
#   from src.core.state.state_manager import RepositoryStateManager
from src.core.state.repository_state_manager import RepositoryStateManager as RepositoryStateManager

# Backward compatibility alias
StateManager = RepositoryStateManager
