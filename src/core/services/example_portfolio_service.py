"""Read the bundled tutorial through the current portfolio contract."""

import gzip
import json
import zlib
from importlib.resources import files
from typing import Any, cast

from src.core.models.portfolio_models import PortfolioData
from src.core.services.data_services.portfolio_validation_service import (
    validate_portfolio_document,
)
from src.core.services.environment_metadata_service import EnvironmentMetadataService
from src.core.services.portfolio_integrity_service import PortfolioIntegrityService


def load_example_portfolio() -> PortfolioData:
    """Read a fresh, verified copy of the synthetic tutorial portfolio.

    Returns:
        A normal current-format portfolio, independent of previous loads.

    Raises:
        OSError: The installed tutorial resource cannot be read.
        ValueError: Its JSON, format, environment, tables, or integrity is invalid.
    """
    compressed = files("src.core").joinpath("resources/example-portfolio.json.gz").read_bytes()
    # [impl->req~ring5.portfolio.bundled-example~1]
    try:
        content = gzip.decompress(compressed).decode("utf-8")
    except (EOFError, zlib.error) as error:
        raise ValueError("The example portfolio compression is invalid.") from error
    value: Any = json.loads(content)
    if not isinstance(value, dict):
        raise ValueError("The example portfolio must contain one JSON object.")
    validate_portfolio_document(value)
    EnvironmentMetadataService.from_payload(value["environment_metadata"])
    PortfolioIntegrityService.require_restorable(PortfolioIntegrityService.verify(value))
    return cast(PortfolioData, value)
