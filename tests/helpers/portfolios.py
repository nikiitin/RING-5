"""Current writer-backed portfolio fixtures for serialized boundary tests."""

import json
from typing import Any

from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.services.portfolio_integrity_service import PortfolioIntegrityService
from src.core.state.repository_state_manager import RepositoryStateManager


def portfolio_document(**fields: Any) -> dict[str, Any]:
    """Build a current portfolio with deterministic time and verified fixture content."""
    service = PortfolioService(RepositoryStateManager())
    document = json.loads(service.serialize_workspace(None, [], {}, 0))
    document["timestamp"] = "2026-10-25T10:00:00+00:00"
    document.update(fields)
    document["integrity_manifest"] = PortfolioIntegrityService.create_manifest(document)
    return document
