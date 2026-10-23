"""Review guards and stable identities for derived workspace artifacts."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict
from typing import Any

import pandas as pd

from src.core.common.content_identity import content_signature, frame_signature
from src.core.models.preview_models import PreviewContext
from src.core.services.data_services.dataset_snapshot_service import DatasetSnapshotService
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.services.environment_metadata_service import EnvironmentMetadataService
from src.core.state.state_manager import StateManager


class WorkspaceInputService:
    """Own preview validation and reproducible artifact input signatures."""

    def __init__(self, state_manager: StateManager) -> None:
        self._state = state_manager

    def _source_snapshot(self) -> tuple[int, dict[str, Any], pd.DataFrame | None]:
        with self._state.transaction():
            selected = self._state.selected_dataset_name()
            revision = (
                self._state.get_dataset_lineage(selected).current_revision_id if selected else None
            )
            metadata = {
                "selected_dataset": selected,
                "revision": revision,
                "csv_path": self._state.get_csv_path(),
            }
            return self._state.get_source_version(), metadata, self._state.get_data()

    @staticmethod
    def _source_signature(version: int, metadata: dict[str, Any], data: pd.DataFrame | None) -> str:
        return content_signature(
            {"version": version, "source": metadata, "data": frame_signature(data)}
        )

    def preview_input_signature(self) -> str:
        """Capture source identity before computing a transformation outside the lock."""
        return self._source_signature(*self._source_snapshot())

    def set_preview(
        self,
        name: str,
        data: pd.DataFrame,
        *,
        operation_config: Mapping[str, Any] | None = None,
        source_signature: str | None = None,
    ) -> None:
        """Store a defensive preview with the exact source and reviewed options.

        Args:
            name: Session-unique operation name.
            data: Computed result; never retained by reference.
            operation_config: Options used to compute the result, or None for legacy storage.
            source_signature: Token captured before computation. Guarded previews require it.

        Raises:
            ValueError: Source changed during work or no guarded source token was supplied.
        """
        if operation_config is None:
            if source_signature is not None:
                raise ValueError("A source token requires reviewed operation options.")
            self._state.set_preview(name, data)
            return
        if not isinstance(operation_config, Mapping):
            raise ValueError("Preview operation options must be a mapping.")
        if not isinstance(source_signature, str) or not source_signature:
            raise ValueError("Capture a preview_input_signature before computing the preview.")
        version, metadata, source = self._source_snapshot()
        current = self._source_signature(version, metadata, source)
        if source_signature != current:
            raise ValueError("Preview source changed during computation; preview it again.")
        config = deepcopy(dict(operation_config))
        context = PreviewContext(current, version, config, content_signature(config))
        with self._state.transaction():
            if self._state.get_source_version() != version:
                raise ValueError("Preview source changed during computation; preview it again.")
            self._state.set_preview(name, data, context=context)

    def preview_matches(self, name: str, *, operation_config: Mapping[str, Any]) -> bool:
        """Whether the stored preview still matches the current source and options."""
        signature = content_signature(dict(operation_config))
        with self._state.transaction():
            context = self._state.get_preview_context(name)
            return bool(
                context is not None
                and self._state.has_preview(name)
                and context.source_version == self._state.get_source_version()
                and context.config_signature == signature
            )

    def get_preview_config(self, name: str) -> dict[str, Any] | None:
        """Return the reviewed options for history display without exposing owned state."""
        with self._state.transaction():
            context = self._state.get_preview_context(name)
            return deepcopy(context.operation_config) if context is not None else None

    def confirm_preview(
        self, name: str, *, operation_config: Mapping[str, Any], operation: str
    ) -> pd.DataFrame:
        """Atomically validate and apply the reviewed result, then consume its preview.

        Raises:
            ValueError: Preview is absent, legacy, stale, or its options changed.
        """
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError("Confirmed operations require a non-empty history label.")
        signature = content_signature(dict(operation_config))
        with self._state.transaction():
            context = self._state.get_preview_context(name)
            if (
                context is None
                or context.source_version != self._state.get_source_version()
                or context.config_signature != signature
            ):
                raise ValueError(
                    "Preview source or options changed; preview it again before confirming."
                )
            data = self._state.get_preview(name)
            if data is None:
                raise ValueError("Preview is no longer available; preview it again.")
            self._state.set_data(data, operation=operation.strip())
            self._state.clear_preview(name)
            result = self._state.get_data()
            if result is None:
                raise RuntimeError("Confirmed preview was not retained as source data.")
            return result

    def report_input_signature(
        self, selected_ids: Sequence[int], *, include_data: bool = True
    ) -> str:
        """Identify complete selected figures, workspace data and report provenance."""
        if not isinstance(include_data, bool):
            raise ValueError("Report include_data must be a boolean.")
        if isinstance(selected_ids, (str, bytes)) or any(
            type(identifier) is not int for identifier in selected_ids
        ):
            raise ValueError("Report plot IDs must be integers.")
        with self._state.transaction():
            available = {plot.plot_id: plot for plot in self._state.get_plots()}
            missing = set(selected_ids) - set(available)
            if missing:
                raise ValueError(f"Report references unknown plot IDs: {sorted(missing)}")
            plots: list[dict[str, Any]] = []
            for identifier in selected_ids:
                plot = available[identifier]
                figure_config = self._state.get_visualization_config(identifier)
                plots.append(
                    {
                        "id": plot.plot_id,
                        "name": plot.name,
                        "plot_type": plot.plot_type,
                        "config": deepcopy(plot.config),
                        "pipeline": deepcopy(plot.pipeline),
                        "pipeline_counter": plot.pipeline_counter,
                        "legend_mappings": deepcopy(plot.legend_mappings),
                        "legend_mappings_by_column": deepcopy(plot.legend_mappings_by_column),
                        "figure_config": (asdict(figure_config) if figure_config else None),
                        "source_data": (
                            plot.source_data.copy(deep=True)
                            if plot.source_data is not None
                            else None
                        ),
                        "processed_data": (
                            plot.processed_data.copy(deep=True)
                            if plot.processed_data is not None
                            else None
                        ),
                    }
                )
            selected = self._state.selected_dataset_name()
            payload = {
                "include_data": include_data,
                "plots": plots,
                "selected_dataset": selected,
                "revision": (
                    self._state.get_dataset_lineage(selected).current_revision_id
                    if selected
                    else None
                ),
                "global_config": deepcopy(self._state.get_config()),
                "csv_path": self._state.get_csv_path(),
                "use_parser": self._state.is_using_parser(),
                "stats_path": self._state.get_stats_path(),
                "stats_pattern": self._state.get_stats_pattern(),
                "parse_variables": self._state.get_parse_variables(),
                "scanned_variables": self._state.get_scanned_variables(),
                "parser_strategy": self._state.get_parser_strategy(),
                "simulator": self._state.get_simulator(),
                "manager_history": deepcopy(self._state.get_manager_history()),
                "portfolio_history": deepcopy(self._state.get_portfolio_history()),
            }
            source = self._state.get_data()
            processed = self._state.get_processed_data()
        for plot_input in plots:
            plot_input["source_data"] = frame_signature(plot_input["source_data"])
            plot_input["processed_data"] = frame_signature(plot_input["processed_data"])
        payload["data"] = frame_signature(source)
        payload["processed_data"] = frame_signature(processed)
        payload["environment"] = EnvironmentMetadataService.capture().to_dict()
        return content_signature(payload)

    def portfolio_bundle_signature(self, name: str, *, snapshot_name: str | None = None) -> str:
        """Hash exact verified saved portfolio and optional snapshot bytes."""
        portfolio = PortfolioService(self._state).export_portfolio_bytes(name)
        snapshot = (
            DatasetSnapshotService.export_snapshot(snapshot_name)
            if snapshot_name is not None
            else None
        )
        return content_signature(
            {
                "portfolio": name,
                "portfolio_sha256": hashlib.sha256(portfolio).hexdigest(),
                "snapshot": snapshot_name,
                "snapshot_sha256": (
                    hashlib.sha256(snapshot).hexdigest() if snapshot is not None else None
                ),
            }
        )
