"""Source and configuration identity retained with a reviewed transformation."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PreviewContext:
    """Guard a preview against source replacement and edited operation options."""

    source_signature: str
    source_version: int
    operation_config: dict[str, Any]
    config_signature: str
