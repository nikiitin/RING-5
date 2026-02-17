"""
Web Layer Services (Layer 4).

Provides reusable services that sit between controllers/presenters
and the domain layer.  Services encapsulate cross-cutting concerns
such as engine selection and preset application.
"""

from src.web.services.engine_manager import EngineManager
from src.web.services.preset_applicator import PresetApplicator

__all__ = ["EngineManager", "PresetApplicator"]
