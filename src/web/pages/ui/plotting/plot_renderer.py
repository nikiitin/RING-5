"""Plot rendering cache utilities.

Provides deterministic cache-key computation for figure caching.
Chart display, engine selection, and download are handled by
``ChartPresenter``; figure generation by ``PlotRenderController``.
"""

import hashlib
import json
from typing import Any

import pandas as pd


class PlotRenderer:
    """Cache-key utilities for plot figure caching.

    All rendering methods have been moved to ``ChartPresenter``
    (engine selector, chart display, download) and
    ``PlotRenderController`` (figure generation + caching).

    Retained utilities:
        - ``_compute_figure_cache_key`` — stable key from config + data hash
        - ``_compute_data_hash`` — fast DataFrame fingerprint
    """

    @staticmethod
    def _compute_figure_cache_key(plot_id: int, config: dict[str, Any], data_hash: str) -> str:
        """
        Compute stable cache key for plot figure.

        Uses config hash + data hash to detect when regeneration is needed.
        Ignores transient UI state (legend positions, etc.).

        Args:
            plot_id: Unique plot identifier
            config: Plot configuration dict
            data_hash: Hash of the processed data

        Returns:
            Cache key string
        """
        # Filter out transient config that shouldn't invalidate cache
        cache_relevant_config = {
            k: v
            for k, v in config.items()
            if k
            not in {
                "xaxis_range",
                "yaxis_range",  # User zoom/pan state
            }
        }

        # Create stable JSON representation of config
        config_json = json.dumps(cache_relevant_config, sort_keys=True, default=str)
        config_hash = hashlib.md5(config_json.encode(), usedforsecurity=False).hexdigest()[:8]

        return f"plot_{plot_id}_{config_hash}_{data_hash}"

    @staticmethod
    def _compute_data_hash(data: pd.DataFrame) -> str:
        """
        Compute fast hash of DataFrame for cache invalidation.

        Uses shape + first/last row hashes for speed.

        Args:
            data: DataFrame to hash

        Returns:
            Hash string
        """
        # Fast fingerprint: shape + sample of data
        shape_str = f"{data.shape[0]}x{data.shape[1]}"

        # Hash first and last rows for change detection
        if len(data) > 0:
            first_row = str(data.iloc[0].values.tolist())
            last_row = str(data.iloc[-1].values.tolist())
            columns = str(data.columns.tolist())

            content = f"{shape_str}|{columns}|{first_row}|{last_row}"
        else:
            content = shape_str

        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]
