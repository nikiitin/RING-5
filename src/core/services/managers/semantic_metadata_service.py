"""Attach semantic labels and perform explicit, compatible unit conversions."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np
import pandas as pd

from src.core.common.semantic_metadata import (
    SEMANTICS_ATTR,
    UNIT_DEFINITIONS,
    inspect_semantics,
    validate_unit,
    semantics_to_payload,
    validate_semantic_data,
)
from src.core.models.semantic_metadata_models import ColumnSemantics, DatasetSemantics


class SemanticMetadataService:
    """Keep semantics portable without mutating caller-owned dataframes."""

    @classmethod
    def attach(
        cls,
        data: pd.DataFrame,
        semantics: DatasetSemantics,
    ) -> pd.DataFrame:
        """Return a copy carrying validated metadata in dataframe attributes."""
        # [impl->req~ring5.data.semantic-units~1]
        validate_semantic_data(data)
        if not isinstance(semantics, DatasetSemantics):
            raise TypeError("semantics must be a DatasetSemantics value.")
        missing = [column.name for column in semantics.columns if column.name not in data.columns]
        if missing:
            raise KeyError(f"Semantic column {missing[0]!r} does not exist.")
        normalized = DatasetSemantics(
            tuple(
                ColumnSemantics(
                    column.name,
                    column.label,
                    validate_unit(column.unit) if column.unit else "",
                )
                for column in semantics.columns
            )
        )
        result = data.copy(deep=True)
        result.attrs = dict(data.attrs)
        result.attrs[SEMANTICS_ATTR] = semantics_to_payload(normalized)
        return result

    @staticmethod
    def inspect(data: pd.DataFrame) -> DatasetSemantics:
        """Decode retained metadata, rejecting malformed external attributes."""
        return inspect_semantics(data)

    @classmethod
    def convert(cls, data: pd.DataFrame, column: str, target_unit: str) -> pd.DataFrame:
        """Convert a metric and its ``.sd`` companion without affine error offsets."""
        # [impl->req~ring5.data.semantic-units~1]
        validate_semantic_data(data)
        if not isinstance(column, str) or column not in data.columns:
            raise KeyError(f"Semantic column {column!r} does not exist.")
        semantics = cls.inspect(data)
        declared = semantics.for_column(column)
        if declared is None or not declared.unit:
            raise ValueError(f"Column {column!r} has no declared source unit.")
        source_name = validate_unit(declared.unit)
        target_name = validate_unit(target_unit)
        source, target = UNIT_DEFINITIONS[source_name], UNIT_DEFINITIONS[target_name]
        if source.dimension != target.dimension:
            raise ValueError(
                f"Cannot convert {source_name!r} to {target_name!r}: units are not compatible."
            )
        numeric = pd.to_numeric(data[column], errors="coerce")
        invalid = data[column].notna() & numeric.isna()
        if invalid.any():
            raise ValueError(f"Column {column!r} contains non-numeric values.")
        converted = (
            (numeric.astype(float) * source.scale) + source.offset - target.offset
        ) / target.scale
        if not np.isfinite(converted.dropna().to_numpy(dtype=float)).all():
            raise ValueError(f"Converting column {column!r} produced non-finite values.")
        result = data.copy(deep=True)
        result[column] = converted
        sd_column = f"{column}.sd"
        if sd_column in data.columns:
            sd_metadata = semantics.for_column(sd_column)
            sd_source = (
                UNIT_DEFINITIONS[validate_unit(sd_metadata.unit)]
                if sd_metadata is not None and sd_metadata.unit
                else source
            )
            if sd_source.dimension != target.dimension:
                raise ValueError(f"Uncertainty column {sd_column!r} has an incompatible unit.")
            sd = pd.to_numeric(data[sd_column], errors="coerce")
            if (data[sd_column].notna() & sd.isna()).any() or (sd < 0).any():
                raise ValueError(f"Uncertainty column {sd_column!r} must be non-negative numeric.")
            scaled_sd = sd.astype(float) * abs(sd_source.scale / target.scale)
            if not np.isfinite(scaled_sd.dropna().to_numpy(dtype=float)).all():
                raise ValueError(f"Converting column {sd_column!r} produced non-finite values.")
            result[sd_column] = scaled_sd
        updated = DatasetSemantics(
            tuple(
                (
                    ColumnSemantics(item.name, item.label, target_name)
                    if item.name in {column, sd_column}
                    else item
                )
                for item in semantics.columns
            )
        )
        result.attrs = dict(data.attrs)
        result.attrs[SEMANTICS_ATTR] = semantics_to_payload(updated)
        return result

    @staticmethod
    def supported_units() -> tuple[str, ...]:
        """Return canonical units in stable declaration order."""
        return tuple(UNIT_DEFINITIONS)

    @classmethod
    def enrich_figure_config(
        cls,
        data: pd.DataFrame,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Fill absent axis/dimension labels from retained semantics."""
        # [impl->req~ring5.data.semantic-units~1]
        semantics = cls.inspect(data)
        if not semantics.columns:
            return config
        enriched = copy.deepcopy(config)

        def label_for(column: object) -> str:
            metadata = semantics.for_column(str(column)) if column else None
            return metadata.display_label if metadata is not None else ""

        if not (enriched.get("xlabel") or enriched.get("xaxis_title")):
            x_label = label_for(enriched.get("x"))
            if x_label:
                enriched["xlabel"] = x_label
        if not (enriched.get("ylabel") or enriched.get("yaxis_title")):
            y_columns: list[object] = []
            if enriched.get("y"):
                y_columns = [enriched["y"]]
            elif enriched.get("y_bar"):
                y_columns = [enriched["y_bar"]]
            elif isinstance(enriched.get("y_columns"), list):
                y_columns = enriched["y_columns"]
            y_label = cls._shared_axis_label(semantics, y_columns)
            if y_label:
                enriched["ylabel"] = y_label
        if not enriched.get("ylabel_right"):
            right_label = label_for(enriched.get("y_dot"))
            if right_label:
                enriched["ylabel_right"] = right_label

        dimensions = enriched.get("parallel_dimensions")
        if isinstance(dimensions, list):
            aliases = dict(enriched.get("parallel_labels") or {})
            for column in dimensions:
                inferred = label_for(column)
                if inferred:
                    aliases.setdefault(str(column), inferred)
            if aliases:
                enriched["parallel_labels"] = aliases
        return enriched

    @staticmethod
    def _shared_axis_label(
        semantics: DatasetSemantics,
        columns: list[object],
    ) -> str:
        declared = [semantics.for_column(str(column)) for column in columns]
        metadata = [value for value in declared if value is not None]
        if len(metadata) != len(columns) or not metadata:
            return ""
        if len(metadata) == 1:
            return metadata[0].display_label
        units = {value.unit for value in metadata}
        return f"Value ({metadata[0].unit})" if len(units) == 1 and metadata[0].unit else ""
