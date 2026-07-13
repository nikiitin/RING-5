"""
Module: src.core.services/shapers/impl/mean.py

Purpose:
    Calculates aggregate means (arithmetic, geometric, harmonic) for selected variables
    across groups and appends summary rows to the dataset. Used for computing average
    performance metrics across benchmark suites.

Responsibilities:
    - Calculate arithmetic, geometric, or harmonic means
    - Group data by specified columns (e.g., by configuration)
    - Append mean rows with identifiable marker (e.g., benchmark='GEOMEAN')
    - Support multiple grouping strategies (single or multiple columns)
    - Preserve original data rows
    - Cache results to avoid redundant computations

Dependencies:
    - pandas: For DataFrame groupby operations
    - scipy.stats: For geometric and harmonic mean calculations
    - UniDfShaper: Base class for shaper interface
    - cached: For fingerprint-based result caching

Usage Example:
    >>> from src.core.services.shapers.impl.mean import Mean
    >>> import pandas as pd
    >>>
    >>> # Sample benchmark data
    >>> data = pd.DataFrame({
    ...     'benchmark': ['mcf', 'omnetpp', 'xalancbmk'],
    ...     'config': ['baseline', 'baseline', 'baseline'],
    ...     'ipc': [1.2, 1.5, 1.8]
    ... })
    >>>
    >>> # Calculate geometric mean across benchmarks
    >>> meaner = Mean({
    ...     'meanVars': ['ipc'],
    ...     'meanAlgorithm': 'geomean',
    ...     'groupingColumns': ['config'],
    ...     'replacingColumn': 'benchmark'
    ... })
    >>>
    >>> result = meaner(data)
    >>> print(result)
       benchmark    config   ipc
    0  mcf         baseline  1.2
    1  omnetpp     baseline  1.5
    2  xalancbmk   baseline  1.8
    3  geomean     baseline  1.48  # sqrt[3](1.2 * 1.5 * 1.8)

Design Patterns:
    - Strategy Pattern: One of many shaper implementations
    - Template Method: Implements UniDfShaper interface
    - Cache-Aside Pattern: Fingerprint-based result caching

Performance Characteristics:
    - Time Complexity: O(n) for arithmetic mean, O(n log n) for groupby
    - Space Complexity: O(k) where k = number of groups (new summary rows)
    - Cache: 5min TTL, 16 entry LRU (based on data fingerprint)
    - Typical: 5-20ms for 10k rows (uncached), <2ms (cached)

Error Handling:
    - Raises ValueError for invalid algorithm (must be arithmean/geomean/hmean)
    - Raises TypeError if meanVars is not a list
    - Raises ValueError if columns don't exist in data

Thread Safety:
    - Stateless transformation (thread-safe)
    - DataFrame operations not synchronized
    - Cache is thread-safe

Testing:
    - Unit tests: tests/unit/test_mean.py
    - Integration tests: tests/integration/test_e2e_managers_shapers.py

Version: 2.1.0
Last Modified: 2026-01-27
"""

from typing import Any, cast, override

import numpy as np
import pandas as pd
from scipy.stats import gmean, hmean

from src.core.models.shaper_models import MeanShaperConfig
from src.core.performance import cached, compute_data_fingerprint
from src.core.services.shapers.uni_df_shaper import UniDfShaper


def _safe_gmean(series: pd.Series) -> float:
    """Geometric mean that skips NaN and handles non-positive values."""
    clean = series.dropna()
    if clean.empty or (clean <= 0).any():
        return np.nan
    return float(gmean(clean))


def _safe_hmean(series: pd.Series) -> float:
    """Harmonic mean that skips NaN and handles non-positive values."""
    clean = series.dropna()
    if clean.empty or (clean <= 0).any():
        return np.nan
    return float(hmean(clean))


class Mean(UniDfShaper):
    """
    Shaper that calculates means (arithmetic, geometric, or harmonic) for
    selected variables across groups and appends the results to the dataframe.
    """

    def __init__(self, params: dict[str, Any]) -> None:
        """
        Initialize Mean shaper.

        Args:
            params: Dictionary containing:
                - meanVars (list[str]): Columns to average.
                - meanAlgorithm (str): 'arithmean', 'geomean', or 'hmean'.
                - groupingColumns (list[str]): Columns to group by.
                - replacingColumn (str): Column where the algorithm name
                  will be stored in the new rows.
        """
        # Use cast for type-safe access to params
        config = cast(MeanShaperConfig, params)

        # Assigning attributes before super().__init__
        self.mean_vars: list[str] = config.get("meanVars", [])
        self.mean_algorithm: str = config.get("meanAlgorithm", "")
        self.replacing_column: str = config.get("replacingColumn", "")

        # Support both new 'groupingColumns' and legacy 'groupingColumn'
        if "groupingColumns" in config:
            self.grouping_columns: list[str] = config["groupingColumns"]
        elif "groupingColumn" in config:
            # type ignore because we know groupingColumn might be in old configs
            self.grouping_columns = [config["groupingColumn"]]  # type: ignore[typeddict-item]
        else:
            self.grouping_columns = []

        # Store params for fingerprinting
        self._params = params

        super().__init__(params)

    @override
    def _verify_params(self) -> bool:
        """Validate parameter structure and algorithm choice."""
        super()._verify_params()
        config = cast(MeanShaperConfig, self.params)

        if "meanAlgorithm" not in config or config["meanAlgorithm"] not in [
            "arithmean",
            "geomean",
            "hmean",
        ]:
            raise ValueError(
                "Mean: 'meanAlgorithm' must be one of 'arithmean', 'geomean', or 'hmean'."
            )

        if not isinstance(config.get("meanVars"), list):
            raise TypeError("Mean: 'meanVars' must be a list.")

        return True

    @override
    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify columns exist and numeric requirements are met."""
        super()._verify_preconditions(data_frame)

        all_required = self.mean_vars + self.grouping_columns + [self.replacing_column]
        for col in all_required:
            if col not in data_frame.columns:
                raise ValueError(f"Mean: Required column '{col}' not found in dataframe.")

        for col in self.mean_vars:
            if not pd.api.types.is_numeric_dtype(data_frame[col]):
                raise ValueError(f"Mean: Column '{col}' must be numeric.")

        return True

    @cached(ttl=300, maxsize=16, key_func=lambda self, df, fp: fp)
    def _calculate_mean_with_cache(
        self, data_frame: pd.DataFrame, fingerprint: str
    ) -> pd.DataFrame:
        """
        Execute mean calculation with fingerprint-based caching.

        The @cached decorator uses the fingerprint parameter as the cache key,
        avoiding inefficient DataFrame stringification.

        Args:
            data_frame: Input data
            fingerprint: Data fingerprint for cache key (used by decorator)

        Returns:
            DataFrame with mean rows appended
        """
        result = data_frame.copy()
        grouped = result.groupby(self.grouping_columns)

        # Apply appropriate mean aggregation
        if self.mean_algorithm == "arithmean":
            mean_df = grouped[self.mean_vars].mean().reset_index()
        elif self.mean_algorithm == "geomean":
            mean_df = grouped[self.mean_vars].agg(_safe_gmean).reset_index()
        elif self.mean_algorithm == "hmean":
            mean_df = grouped[self.mean_vars].agg(_safe_hmean).reset_index()
        else:
            raise ValueError(f"Unknown algorithm: {self.mean_algorithm}")

        # Label the new rows
        mean_df[self.replacing_column] = self.mean_algorithm

        # The std-dev (``.sd``) column of an averaged variable must NOT be carried as the
        # first seed's value — that would fabricate the aggregate row's spread (and draw a
        # bogus error bar). Recompute it instead.
        sd_cols = [f"{v}.sd" for v in self.mean_vars if f"{v}.sd" in result.columns]

        # Carry over the remaining (metadata) columns by taking the first encountered value
        # in each group — this preserves e.g. 'config_description'.
        other_cols = [
            col
            for col in result.columns
            if col not in self.mean_vars
            and col not in self.grouping_columns
            and col != self.replacing_column
            and col not in sd_cols
        ]

        for col in other_cols:
            first_vals = grouped[col].first().reset_index()
            mean_df = mean_df.merge(first_vals, on=self.grouping_columns, how="left")

        # Standard error of the aggregate. For the arithmetic mean of N values each with
        # std sd_i, SE = sqrt(Σ sd_i²)/N (matching ArithmeticService.apply_mixer). The
        # geometric/harmonic means have no simple closed form → leave NaN rather than
        # fabricate.
        for sd in sd_cols:
            if self.mean_algorithm == "arithmean":
                se = grouped[sd].agg(
                    lambda s: (
                        float(np.sqrt(np.square(s.astype(float)).sum()) / len(s))
                        if len(s)
                        else np.nan
                    )
                )
                mean_df = mean_df.merge(se.reset_index(), on=self.grouping_columns, how="left")
            else:
                mean_df[sd] = np.nan

        # Append to the original data
        return pd.concat([result, mean_df], ignore_index=True)

    @override
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates group means and appends them as new rows with caching.

        Args:
            data_frame: Input DataFrame

        Returns:
            DataFrame with mean rows appended
        """
        self._verify_preconditions(data_frame)

        # Compute fingerprint for caching
        relevant_cols = self.mean_vars + self.grouping_columns + [self.replacing_column]
        fingerprint = compute_data_fingerprint(data_frame, self._params, relevant_cols)

        # Use cached calculation. Shallow copy (CoW) so callers can never
        # mutate the cache-resident frame in place and poison later hits.
        return self._calculate_mean_with_cache(data_frame, fingerprint).copy(deep=False)
