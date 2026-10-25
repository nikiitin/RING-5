"""Shaper for baseline-relative normalization within groups."""

import logging
from typing import Any, cast, override

import numpy as np
import pandas as pd
from pandas import DataFrame

from src.core.common.dataframe_copy import copy_dataframe
from src.core.models.shaper_models import NormalizeShaperConfig, ShaperValue
from src.core.performance import cached, compute_data_fingerprint
from src.core.services.shapers.uni_df_shaper import UniDfShaper

logger = logging.getLogger(__name__)


class Normalize(UniDfShaper):
    """
    Shaper that normalizes numeric columns relative to a baseline configuration.

    This shaper groups data by specified columns and scales the selected variables
    by the value(s) found in a designated baseline row within each group.
    """

    def __init__(self, params: dict[str, Any]) -> None:
        """
        Initialize the Normalize shaper with parameters.

        Args:
            params: Dictionary containing:
                - normalizeVars (List[str]): Columns to normalize.
                - normalizerVars (Optional[List[str]]): Columns to sum for the baseline value.
                - normalizerColumn (str): Column that identifies the baseline row.
                - normalizerValue (str | int | float | bool): Baseline category value.
                - groupBy (List[str]): Columns used to define groups.
                - normalizeSd (Optional[bool]): Whether to normalize .sd columns. Defaults to True.
        """
        super().__init__(params)
        # Use cast for type-safe access
        config = cast(NormalizeShaperConfig, self.params)

        self._normalize_vars: list[str] = config["normalizeVars"]
        self._normalizer_column: str = config["normalizerColumn"]
        self._normalizer_value: ShaperValue = config["normalizerValue"]
        self._group_by: list[str] = config["groupBy"]
        self._normalizer_vars: list[str] = config.get("normalizerVars", self._normalize_vars)
        self._normalize_sd: bool = config.get("normalizeSd", True)

        # Store params for caching fingerprint
        self._params = self.params

    @override
    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """
        Check that the dataframe contains all required columns and valid baseline values.

        Args:
            data_frame: The pandas DataFrame to check.

        Returns:
            True if all preconditions are met.

        Raises:
            ValueError: If columns are missing or normalization baseline is invalid.
        """
        super()._verify_preconditions(data_frame)

        # Verify columns exist and are numeric
        all_numeric_required = list(set(self._normalizer_vars + self._normalize_vars))
        for col in all_numeric_required:
            if col not in data_frame.columns:
                raise ValueError(f"Required numeric column '{col}' not found in dataframe.")
            if not pd.api.types.is_numeric_dtype(data_frame[col]):
                raise ValueError(f"Column '{col}' must be numeric for normalization.")

        if self._normalizer_column not in data_frame.columns:
            raise ValueError(f"Grouping column '{self._normalizer_column}' not found.")

        # Ensure baseline value exists
        if self._normalizer_value not in data_frame[self._normalizer_column].unique():
            raise ValueError(
                f"Baseline value '{self._normalizer_value}' not found "
                f"in column '{self._normalizer_column}'."
            )

        # Group validation
        groups = data_frame.groupby(self._group_by, dropna=False)
        if len(groups) == 0:
            raise ValueError("No groups found for the specified groupBy columns.")

        for name, group in groups:
            baseline_rows = group[group[self._normalizer_column] == self._normalizer_value]
            if len(baseline_rows) != 1:
                raise ValueError(
                    f"Ambiguous baseline: Group {name} has {len(baseline_rows)} baseline rows. "
                    "Each group must have exactly one row matching the normalizer value."
                )

        return True

    def _normalize_group(self, group: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize a single group of data.

        Args:
            group: A subdivision of the original dataframe.

        Returns:
            A new dataframe with normalized values.
        """
        # [impl->req~ring5.shaping.normalize~1]
        result = group.copy()

        # Identify the baseline row for this group
        baseline = result[result[self._normalizer_column] == self._normalizer_value]

        if baseline.empty:
            return result

        # Calculate denominator (sum of specified normalizer variables)
        baseline_vars = baseline[self._normalizer_vars]
        denominator = baseline_vars.iloc[0].sum(min_count=len(self._normalizer_vars))

        if pd.isna(denominator) or denominator == 0 or not np.isfinite(denominator):
            # An undefined ratio is missing data, never a measured zero.
            for var in self._normalize_vars:
                result[var] = float("nan")
                if self._normalize_sd:
                    sd_col = f"{var}.sd"
                    if sd_col in result.columns:
                        result[sd_col] = float("nan")
            return result

        # Perform the actual scaling
        for var in self._normalize_vars:
            result[var] = result[var] / denominator
            if self._normalize_sd:
                sd_col = f"{var}.sd"
                if sd_col in result.columns:
                    result[sd_col] = result[sd_col] / abs(denominator)

        return result

    @cached(ttl=300, maxsize=32, key_func=lambda self, df, fp: fp)
    def _normalize_with_cache(
        self, data_frame: pd.DataFrame, fingerprint: str | None
    ) -> pd.DataFrame:
        """
        Execute normalization with fingerprint-based caching.

        The @cached decorator uses the fingerprint parameter as the cache key,
        avoiding inefficient DataFrame stringification.

        Args:
            data_frame: Input data
            fingerprint: Data fingerprint for cache key (used by decorator)

        Returns:
            Normalized DataFrame
        """

        # [impl->req~ring5.quality.bounded-caching~1]

        # Validation scans the same relevant columns and groups as the
        # normalization. Keep it inside the cached body so an unchanged,
        # fingerprint-matched frame does not repeat that work on every hit.
        self._verify_preconditions(data_frame)

        # Positional row identity survives duplicate caller indexes and grouping
        # keys containing missing values. Iteration retains grouping columns.
        grouped = data_frame.reset_index(drop=True).groupby(
            self._group_by, sort=False, dropna=False
        )
        result = pd.concat([self._normalize_group(group) for _, group in grouped]).sort_index(
            kind="stable"
        )
        result.index = data_frame.index.copy()
        result.attrs = data_frame.attrs.copy()
        return copy_dataframe(result)

    @override
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Execute the normalization pipeline with caching.

        Args:
            data_frame: Input data.

        Returns:
            New dataframe with normalized columns.
        """
        # Include every retained value, not only the columns being normalized.
        # Include ``normalizer_vars`` because it supplies the denominator (see
        # ``_normalize_group``) and can differ from ``normalize_vars``; omitting it lets a
        # different baseline value return a stale (wrong) normalized frame within the TTL.
        relevant_cols = (
            self._normalize_vars
            + self._normalizer_vars
            + self._group_by
            + [self._normalizer_column]
        )
        fingerprint = compute_data_fingerprint(data_frame, self._params, relevant_cols)

        result: DataFrame = self._normalize_with_cache(data_frame, fingerprint)
        return copy_dataframe(result)
