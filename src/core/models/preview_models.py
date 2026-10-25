"""Captured input identities and reviewed data-operation results."""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.core.models.dataset_workspace_models import DatasetInputIdentity


@dataclass(frozen=True, slots=True)
class ActivePreviewInputs:
    """Identify the active source before a transformation begins."""

    source_signature: str
    source_version: int

    def __post_init__(self) -> None:
        """Reject incomplete identities before they can guard a result."""
        if not isinstance(self.source_signature, str) or not self.source_signature:
            raise ValueError("An active preview requires a source signature.")
        if type(self.source_version) is not int or self.source_version < 0:
            raise ValueError("An active preview requires a non-negative source version.")


@dataclass(frozen=True, slots=True)
class DatasetPreviewInputs:
    """Identify ordered named source revisions independently of active selection."""

    sources: tuple[DatasetInputIdentity, ...]

    def __post_init__(self) -> None:
        """Retain immutable identities from a concrete workspace generation."""
        if type(self.sources) is not tuple or not self.sources:
            raise ValueError("Named previews require captured dataset identities.")
        if any(type(source) is not DatasetInputIdentity for source in self.sources):
            raise ValueError("Named previews require exact dataset input identities.")


PreviewInputs = ActivePreviewInputs | DatasetPreviewInputs


@dataclass(frozen=True, slots=True)
class PreviewContext:
    """Bind reviewed operation options to their captured input identities."""

    inputs: PreviewInputs
    operation_config: dict[str, Any]
    config_signature: str

    def __post_init__(self) -> None:
        """Require the current captured-input and reviewed-options contract."""
        if not isinstance(self.inputs, (ActivePreviewInputs, DatasetPreviewInputs)):
            raise TypeError("Preview context requires captured inputs.")
        if not isinstance(self.operation_config, dict):
            raise TypeError("Preview context requires reviewed operation options.")
        if not isinstance(self.config_signature, str) or not self.config_signature:
            raise ValueError("Preview context requires an operation signature.")


@dataclass(frozen=True, slots=True, eq=False)
class PreviewRecord:
    """Keep a repository-owned result and its required review context together."""

    data: pd.DataFrame
    context: PreviewContext
