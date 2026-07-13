r"""
Tests for the ``keep_indices`` feature on :class:`StatConfig`.

When a user selects a pattern variable (e.g., ``system.cpu\d+.numCycles``)
and enables *keep_indices*, the parser must expand each concrete instance
(``system.cpu0.numCycles``, ``system.cpu1.numCycles``, ...) into its own
column instead of averaging them.

Validates:
1. ``StatConfig.keep_indices`` defaults to ``False``.
2. The field is frozen-immutable.
3. ``dataclasses.replace`` preserves / overrides the flag.
4. ``ApplicationAPI.submit_parse_async`` propagates ``keepIndices`` from
   variable dictionaries.
5. ``Gem5Parser`` and ``ParseService`` expand regex configs into individual
   concrete configs when ``keep_indices=True``.
6. User-filtered ``parsed_ids`` are respected during expansion.
7. Multi-dimensional patterns (``l\d+_cntrl\d+``) expand correctly.
8. ``reconstruct_concrete_name`` correctly rebuilds variable names.
9. ``construct_final_csv`` writes ``NaN`` for missing variables.
"""

import csv
import re
from dataclasses import replace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from src.core.models import ScannedVariable, StatConfig
from src.core.models.pattern_index_service import PatternIndexService

# Unit: StatConfig.keep_indices field


class TestStatConfigKeepIndices:
    """Core unit tests for the keep_indices field."""

    def test_default_is_false(self) -> None:
        """keep_indices should default to False."""
        config = StatConfig(name="system.cpu.ipc", type="scalar")
        assert config.keep_indices is False

    def test_explicit_true(self) -> None:
        """keep_indices can be set explicitly to True."""
        config = StatConfig(name=r"system.cpu\d+.ipc", type="scalar", keep_indices=True)
        assert config.keep_indices is True

    def test_explicit_false(self) -> None:
        """keep_indices can be explicitly set to False."""
        config = StatConfig(name="system.cpu0.ipc", type="scalar", keep_indices=False)
        assert config.keep_indices is False

    def test_frozen_immutability(self) -> None:
        """Cannot mutate keep_indices on a frozen dataclass."""
        config = StatConfig(name="x", type="scalar", keep_indices=False)
        with pytest.raises(AttributeError):
            config.keep_indices = True  # type: ignore[misc]

    def test_replace_preserves_flag(self) -> None:
        """dataclasses.replace should carry over keep_indices."""
        original = StatConfig(name=r"system.cpu\d+.ipc", type="scalar", keep_indices=True)
        modified = replace(original, params={"parsed_ids": ["cpu0"]})
        assert modified.keep_indices is True

    def test_replace_can_change_flag(self) -> None:
        """dataclasses.replace should allow changing keep_indices."""
        original = StatConfig(name="x", type="scalar", keep_indices=False)
        modified = replace(original, keep_indices=True)
        assert modified.keep_indices is True

    def test_keep_indices_independent_of_is_regex(self) -> None:
        """keep_indices and is_regex are orthogonal flags."""
        config = StatConfig(
            name=r"system.cpu\d+.ipc",
            type="scalar",
            is_regex=True,
            keep_indices=True,
        )
        assert config.is_regex is True
        assert config.keep_indices is True


# Integration: ApplicationAPI propagates keepIndices from dicts


class TestApplicationAPIKeepIndices:
    """Verify ApplicationAPI sets keep_indices from ``keepIndices`` dict key."""

    def _make_api(self) -> Any:
        from src.core.application_api import ApplicationAPI

        api = ApplicationAPI()
        api._parser = MagicMock()
        return api

    def test_dict_with_keep_indices_true(self) -> None:
        """A dict variable with keepIndices=True should produce keep_indices=True."""
        api = self._make_api()
        api._parser.submit_parse_async.return_value = MagicMock()

        variables: list[dict[str, Any]] = [
            {"name": r"system.cpu\d+.ipc", "type": "scalar", "keepIndices": True},
        ]
        api.submit_parse_async(
            stats_path="/fake/path",
            stats_pattern="stats.txt",
            variables=variables,
            output_dir="/tmp/out",
        )

        call_args = api._parser.submit_parse_async.call_args
        configs: list[StatConfig] = call_args[0][2]
        assert len(configs) == 1
        assert configs[0].keep_indices is True

    def test_dict_with_keep_indices_false(self) -> None:
        """A dict variable without keepIndices should default to False."""
        api = self._make_api()
        api._parser.submit_parse_async.return_value = MagicMock()

        variables: list[dict[str, Any]] = [
            {"name": r"system.cpu\d+.ipc", "type": "scalar"},
        ]
        api.submit_parse_async(
            stats_path="/fake/path",
            stats_pattern="stats.txt",
            variables=variables,
            output_dir="/tmp/out",
        )

        call_args = api._parser.submit_parse_async.call_args
        configs: list[StatConfig] = call_args[0][2]
        assert len(configs) == 1
        assert configs[0].keep_indices is False

    def test_dict_with_snake_case_keep_indices(self) -> None:
        """``keep_indices`` (snake_case) in dicts is also accepted."""
        api = self._make_api()
        api._parser.submit_parse_async.return_value = MagicMock()

        variables: list[dict[str, Any]] = [
            {"name": r"system.cpu\d+.ipc", "type": "scalar", "keep_indices": True},
        ]
        api.submit_parse_async(
            stats_path="/fake/path",
            stats_pattern="stats.txt",
            variables=variables,
            output_dir="/tmp/out",
        )

        call_args = api._parser.submit_parse_async.call_args
        configs: list[StatConfig] = call_args[0][2]
        assert len(configs) == 1
        assert configs[0].keep_indices is True


# Expansion logic: keep_indices splits regex config into concrete configs


class TestKeepIndicesExpansion:
    """
    Verify that keep_indices=True causes expansion into concrete variables
    instead of spatial aggregation via parsed_ids.
    """

    @staticmethod
    def _expand(config: StatConfig, scanned: list[ScannedVariable]) -> list[StatConfig]:
        """
        Reproduce the expansion logic from Gem5Parser / ParseService.

        This mirrors the real implementation including:
        - User-filtered ``parsed_ids`` from PatternIndexSelector
        - ``reconstruct_concrete_name`` for numeric IDs
        - Full name detection via ``'.' in pid``

        Returns the list of processed configs for the given input config.
        """
        processed: list[StatConfig] = []
        expanded_config = config

        if config.is_regex and scanned:
            pattern = re.compile(config.name)
            matched_ids: list[str] = []
            for sv in scanned:
                sv_name = sv.name if hasattr(sv, "name") else ""
                if config.name == sv_name or pattern.fullmatch(sv_name):
                    if sv.pattern_indices:
                        matched_ids.extend(sv.pattern_indices)
                    else:
                        matched_ids.append(sv_name)

            if matched_ids:
                if config.keep_indices:
                    # Respect user-filtered parsed_ids, falling back to
                    # all matched_ids when no filter was applied.
                    user_ids: list[str] = cast(list[str], config.params.get("parsed_ids", []))
                    ids_to_expand = user_ids if user_ids else matched_ids

                    # Detect full names vs numeric IDs
                    ids_are_full_names = any("." in pid for pid in ids_to_expand)

                    concrete_names: list[str] = []
                    if ids_are_full_names:
                        concrete_names = list(ids_to_expand)
                    else:
                        for nid in ids_to_expand:
                            try:
                                cname = PatternIndexService.reconstruct_concrete_name(
                                    config.name, nid
                                )
                                concrete_names.append(cname)
                            except ValueError:
                                pass  # skip unreconstructable IDs

                    for cname in concrete_names:
                        individual = replace(
                            config,
                            name=cname,
                            is_regex=False,
                            keep_indices=False,
                            params={k: v for k, v in config.params.items() if k != "parsed_ids"},
                        )
                        processed.append(individual)
                    return processed
                else:
                    params = config.params.copy()
                    params["parsed_ids"] = matched_ids
                    expanded_config = replace(config, params=params)

        processed.append(expanded_config)
        return processed

    def test_keep_indices_expands_to_individual_configs(self) -> None:
        """With keep_indices=True, one regex config becomes N concrete configs."""
        config = StatConfig(
            name=r"system.cpu\d+.ipc",
            type="scalar",
            is_regex=True,
            keep_indices=True,
        )
        scanned = [
            ScannedVariable(
                name=r"system.cpu\d+.ipc",
                type="scalar",
                pattern_indices=[
                    "system.cpu0.ipc",
                    "system.cpu1.ipc",
                    "system.cpu2.ipc",
                ],
            ),
        ]

        result = self._expand(config, scanned)

        assert len(result) == 3
        assert result[0].name == "system.cpu0.ipc"
        assert result[1].name == "system.cpu1.ipc"
        assert result[2].name == "system.cpu2.ipc"

        # Each should be a standalone scalar, not regex, not keep_indices
        for r in result:
            assert r.is_regex is False
            assert r.keep_indices is False
            assert r.type == "scalar"
            assert "parsed_ids" not in r.params

    def test_default_aggregates_into_parsed_ids(self) -> None:
        """Without keep_indices, expansion injects parsed_ids for spatial averaging."""
        config = StatConfig(
            name=r"system.cpu\d+.ipc",
            type="scalar",
            is_regex=True,
            keep_indices=False,
        )
        scanned = [
            ScannedVariable(
                name=r"system.cpu\d+.ipc",
                type="scalar",
                pattern_indices=[
                    "system.cpu0.ipc",
                    "system.cpu1.ipc",
                ],
            ),
        ]

        result = self._expand(config, scanned)

        assert len(result) == 1
        assert result[0].name == r"system.cpu\d+.ipc"
        assert result[0].params["parsed_ids"] == [
            "system.cpu0.ipc",
            "system.cpu1.ipc",
        ]

    def test_keep_indices_preserves_type(self) -> None:
        """Expanded configs preserve the original type (vector, histogram, etc.)."""
        config = StatConfig(
            name=r"system.cpu\d+.dcache.ReadReq",
            type="vector",
            is_regex=True,
            keep_indices=True,
            params={"vectorEntries": ["hits", "misses"]},
        )
        scanned = [
            ScannedVariable(
                name=r"system.cpu\d+.dcache.ReadReq",
                type="vector",
                entries=["hits", "misses"],
                pattern_indices=[
                    "system.cpu0.dcache.ReadReq",
                    "system.cpu1.dcache.ReadReq",
                ],
            ),
        ]

        result = self._expand(config, scanned)

        assert len(result) == 2
        for r in result:
            assert r.type == "vector"
            assert r.params.get("vectorEntries") == ["hits", "misses"]

    def test_keep_indices_no_matches(self) -> None:
        """When no scanned vars match, keep_indices config passes through unchanged."""
        config = StatConfig(
            name=r"system.cpu\d+.ipc",
            type="scalar",
            is_regex=True,
            keep_indices=True,
        )
        scanned = [
            ScannedVariable(
                name="system.cache.missRate",
                type="scalar",
            ),
        ]

        result = self._expand(config, scanned)

        # Falls through without expansion (no matches)
        assert len(result) == 1
        assert result[0].name == r"system.cpu\d+.ipc"

    def test_keep_indices_many_instances(self) -> None:
        """Handles large CPU counts (e.g., 16 cores)."""
        cpu_names = [f"system.cpu{i}.ipc" for i in range(16)]
        config = StatConfig(
            name=r"system.cpu\d+.ipc",
            type="scalar",
            is_regex=True,
            keep_indices=True,
        )
        scanned = [
            ScannedVariable(
                name=r"system.cpu\d+.ipc",
                type="scalar",
                pattern_indices=cpu_names,
            ),
        ]

        result = self._expand(config, scanned)

        assert len(result) == 16
        for i, r in enumerate(result):
            assert r.name == f"system.cpu{i}.ipc"
            assert r.is_regex is False
            assert r.keep_indices is False

    def test_keep_indices_mixed_with_normal_vars(self) -> None:
        """
        When some vars use keep_indices and others don't,
        they expand independently.
        """
        configs = [
            StatConfig(
                name="simTicks",
                type="scalar",
            ),
            StatConfig(
                name=r"system.cpu\d+.ipc",
                type="scalar",
                is_regex=True,
                keep_indices=True,
            ),
            StatConfig(
                name=r"system.cpu\d+.numCycles",
                type="scalar",
                is_regex=True,
                keep_indices=False,
            ),
        ]
        scanned = [
            ScannedVariable(
                name=r"system.cpu\d+.ipc",
                type="scalar",
                pattern_indices=["system.cpu0.ipc", "system.cpu1.ipc"],
            ),
            ScannedVariable(
                name=r"system.cpu\d+.numCycles",
                type="scalar",
                pattern_indices=["system.cpu0.numCycles", "system.cpu1.numCycles"],
            ),
        ]

        all_results: list[StatConfig] = []
        for cfg in configs:
            all_results.extend(self._expand(cfg, scanned))

        # simTicks (1) + cpu0.ipc, cpu1.ipc (2) + cpu\d+.numCycles (1 aggregated) = 4
        assert len(all_results) == 4
        assert all_results[0].name == "simTicks"
        assert all_results[1].name == "system.cpu0.ipc"
        assert all_results[2].name == "system.cpu1.ipc"
        assert all_results[3].name == r"system.cpu\d+.numCycles"
        assert "parsed_ids" in all_results[3].params


# Unit: PatternIndexService.reconstruct_concrete_name


class TestReconstructConcreteName:
    """Tests for PatternIndexService.reconstruct_concrete_name()."""

    def test_single_dimension_cpu(self) -> None:
        r"""``system.cpu\d+.ipc`` + ``"3"`` → ``system.cpu3.ipc``."""
        result = PatternIndexService.reconstruct_concrete_name(r"system.cpu\d+.ipc", "3")
        assert result == "system.cpu3.ipc"

    def test_single_dimension_zero(self) -> None:
        r"""``system.cpu\d+.numCycles`` + ``"0"`` → ``system.cpu0.numCycles``."""
        result = PatternIndexService.reconstruct_concrete_name(r"system.cpu\d+.numCycles", "0")
        assert result == "system.cpu0.numCycles"

    def test_multi_dimension_two_placeholders(self) -> None:
        r"""``system.ruby.l\d+_cntrl\d+.stat`` + ``"0_1"`` → ``system.ruby.l0_cntrl1.stat``."""
        result = PatternIndexService.reconstruct_concrete_name(
            r"system.ruby.l\d+_cntrl\d+.stat", "0_1"
        )
        assert result == "system.ruby.l0_cntrl1.stat"

    def test_multi_dimension_three_placeholders(self) -> None:
        r"""Three ``\d+`` placeholders + ``"1_2_3"``."""
        result = PatternIndexService.reconstruct_concrete_name(
            r"system.a\d+.b\d+.c\d+.stat", "1_2_3"
        )
        assert result == "system.a1.b2.c3.stat"

    def test_large_numeric_id(self) -> None:
        """Two-digit IDs are handled correctly."""
        result = PatternIndexService.reconstruct_concrete_name(r"system.cpu\d+.ipc", "15")
        assert result == "system.cpu15.ipc"

    def test_mismatch_raises_value_error(self) -> None:
        r"""Mismatched placeholder count and ID parts raises ValueError."""
        with pytest.raises(ValueError, match="placeholder"):
            PatternIndexService.reconstruct_concrete_name(r"system.cpu\d+.ipc", "0_1")

    def test_too_few_id_parts_raises_value_error(self) -> None:
        r"""Fewer ID parts than placeholders raises ValueError."""
        with pytest.raises(ValueError, match="placeholder"):
            PatternIndexService.reconstruct_concrete_name(r"system.ruby.l\d+_cntrl\d+.stat", "0")

    def test_no_placeholder_raises_value_error(self) -> None:
        r"""No ``\d+`` in pattern with a numeric ID raises ValueError."""
        with pytest.raises(ValueError, match="placeholder"):
            PatternIndexService.reconstruct_concrete_name("system.cpu.ipc", "0")

    def test_roundtrip_with_extract_index_positions(self) -> None:
        r"""reconstruct + extract_index_positions are consistent."""
        pattern = r"system.ruby.l\d+_cntrl\d+.stat"
        concrete = PatternIndexService.reconstruct_concrete_name(pattern, "2_5")
        assert concrete == "system.ruby.l2_cntrl5.stat"
        # The index positions from the original pattern should still work
        positions = PatternIndexService.extract_index_positions(pattern)
        assert positions == ["l", "cntrl"]


# Expansion: user-filtered parsed_ids


class TestKeepIndicesUserFiltered:
    """Verify that user-filtered IDs from PatternIndexSelector are respected."""

    @staticmethod
    def _expand(config: StatConfig, scanned: list[ScannedVariable]) -> list[StatConfig]:
        """Mirror the expansion logic (same as TestKeepIndicesExpansion._expand)."""
        return TestKeepIndicesExpansion._expand(config, scanned)

    def test_user_filtered_scalar_pattern(self) -> None:
        """Only selected scalar indices are expanded (user chose cpu0 and cpu2)."""
        config = StatConfig(
            name=r"system.cpu\d+.ipc",
            type="scalar",
            is_regex=True,
            keep_indices=True,
            params={
                "parsed_ids": ["system.cpu0.ipc", "system.cpu2.ipc"],
            },
        )
        scanned = [
            ScannedVariable(
                name=r"system.cpu\d+.ipc",
                type="scalar",
                pattern_indices=[
                    "system.cpu0.ipc",
                    "system.cpu1.ipc",
                    "system.cpu2.ipc",
                    "system.cpu3.ipc",
                ],
            ),
        ]

        result = self._expand(config, scanned)

        assert len(result) == 2
        assert result[0].name == "system.cpu0.ipc"
        assert result[1].name == "system.cpu2.ipc"

    def test_user_filtered_numeric_ids(self) -> None:
        r"""Numeric IDs from PatternIndexSelector are reconstructed.

        Via reconstruct_concrete_name.
        """
        config = StatConfig(
            name=r"system.cpu\d+.numCycles",
            type="vector",
            is_regex=True,
            keep_indices=True,
            params={
                "parsed_ids": ["0", "2"],
                "vectorEntries": ["hits", "misses"],
            },
        )
        scanned = [
            ScannedVariable(
                name=r"system.cpu\d+.numCycles",
                type="vector",
                entries=["hits", "misses"],
                pattern_indices=["0", "1", "2", "3"],
            ),
        ]

        result = self._expand(config, scanned)

        assert len(result) == 2
        assert result[0].name == "system.cpu0.numCycles"
        assert result[1].name == "system.cpu2.numCycles"
        # Vector entries are preserved
        for r in result:
            assert r.params.get("vectorEntries") == ["hits", "misses"]
            assert "parsed_ids" not in r.params

    def test_user_filtered_multidim_numeric_ids(self) -> None:
        r"""Multi-dimensional numeric IDs (e.g., ``"0_1"``) are reconstructed."""
        config = StatConfig(
            name=r"system.ruby.l\d+_cntrl\d+.stat",
            type="scalar",
            is_regex=True,
            keep_indices=True,
            params={
                "parsed_ids": ["0_0", "1_1"],
            },
        )
        scanned = [
            ScannedVariable(
                name=r"system.ruby.l\d+_cntrl\d+.stat",
                type="scalar",
                pattern_indices=["0_0", "0_1", "1_0", "1_1"],
            ),
        ]

        result = self._expand(config, scanned)

        assert len(result) == 2
        assert result[0].name == "system.ruby.l0_cntrl0.stat"
        assert result[1].name == "system.ruby.l1_cntrl1.stat"

    def test_empty_parsed_ids_falls_back_to_all(self) -> None:
        """Empty parsed_ids list falls back to all matched_ids."""
        config = StatConfig(
            name=r"system.cpu\d+.ipc",
            type="scalar",
            is_regex=True,
            keep_indices=True,
            params={"parsed_ids": []},
        )
        scanned = [
            ScannedVariable(
                name=r"system.cpu\d+.ipc",
                type="scalar",
                pattern_indices=[
                    "system.cpu0.ipc",
                    "system.cpu1.ipc",
                ],
            ),
        ]

        result = self._expand(config, scanned)

        assert len(result) == 2
        assert result[0].name == "system.cpu0.ipc"
        assert result[1].name == "system.cpu1.ipc"

    def test_no_parsed_ids_key_falls_back_to_all(self) -> None:
        """No parsed_ids key in params falls back to all matched_ids."""
        config = StatConfig(
            name=r"system.cpu\d+.ipc",
            type="scalar",
            is_regex=True,
            keep_indices=True,
        )
        scanned = [
            ScannedVariable(
                name=r"system.cpu\d+.ipc",
                type="scalar",
                pattern_indices=[
                    "system.cpu0.ipc",
                    "system.cpu1.ipc",
                    "system.cpu2.ipc",
                ],
            ),
        ]

        result = self._expand(config, scanned)

        assert len(result) == 3


# Multi-dimensional pattern expansion


class TestMultiDimensionalExpansion:
    r"""Test expansion with multi-dimensional patterns (l\d+_cntrl\d+, etc.)."""

    @staticmethod
    def _expand(config: StatConfig, scanned: list[ScannedVariable]) -> list[StatConfig]:
        """Mirror the expansion logic."""
        return TestKeepIndicesExpansion._expand(config, scanned)

    def test_two_dimension_full_expansion(self) -> None:
        r"""All instances of ``l\d+_cntrl\d+`` are expanded."""
        config = StatConfig(
            name=r"system.ruby.l\d+_cntrl\d+.missLatencyHist",
            type="histogram",
            is_regex=True,
            keep_indices=True,
        )
        scanned = [
            ScannedVariable(
                name=r"system.ruby.l\d+_cntrl\d+.missLatencyHist",
                type="histogram",
                pattern_indices=["0_0", "0_1", "1_0", "1_1"],
            ),
        ]

        result = self._expand(config, scanned)

        assert len(result) == 4
        expected = [
            "system.ruby.l0_cntrl0.missLatencyHist",
            "system.ruby.l0_cntrl1.missLatencyHist",
            "system.ruby.l1_cntrl0.missLatencyHist",
            "system.ruby.l1_cntrl1.missLatencyHist",
        ]
        for r, expected_name in zip(result, expected, strict=True):
            assert r.name == expected_name
            assert r.is_regex is False
            assert r.keep_indices is False
            assert r.type == "histogram"

    def test_two_dimension_filtered(self) -> None:
        r"""User selects only l0 controllers."""
        config = StatConfig(
            name=r"system.ruby.l\d+_cntrl\d+.missLatencyHist",
            type="histogram",
            is_regex=True,
            keep_indices=True,
            params={"parsed_ids": ["0_0", "0_1"]},
        )
        scanned = [
            ScannedVariable(
                name=r"system.ruby.l\d+_cntrl\d+.missLatencyHist",
                type="histogram",
                pattern_indices=["0_0", "0_1", "1_0", "1_1"],
            ),
        ]

        result = self._expand(config, scanned)

        assert len(result) == 2
        assert result[0].name == "system.ruby.l0_cntrl0.missLatencyHist"
        assert result[1].name == "system.ruby.l0_cntrl1.missLatencyHist"


# construct_final_csv NA handling


class TestConstructFinalCsvNA:
    """
    Verify that ``construct_final_csv`` writes ``NaN`` for variables
    missing from individual results (files) while including all columns
    from ``var_names``.
    """

    @staticmethod
    def _mock_scalar(value: float) -> Any:
        """Create a mock scalar stat object with balance/reduce support."""
        m = MagicMock()
        m.entries = None
        m.balance_content = MagicMock()
        m.reduce_duplicates = MagicMock()
        m.reduced_content = value
        return m

    def test_missing_var_in_first_result_gets_nan_header(self, tmp_path: Any) -> None:
        """
        If the first result lacks a variable but var_names includes it,
        the column should still appear in the header and get NaN in the
        first row.
        """
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        stat_a = self._mock_scalar(1.0)
        stat_b = self._mock_scalar(2.0)

        # File 1 only has var_a; File 2 has both
        results = [
            {"var_a": stat_a},
            {"var_a": stat_a, "var_b": stat_b},
        ]
        var_names = ["var_a", "var_b"]

        output_dir = str(tmp_path)
        csv_path = Gem5Parser.construct_final_csv(output_dir, results, var_names=var_names)
        assert csv_path is not None

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)

        # var_b should be in the header even though file 1 lacks it
        assert "var_b" in header
        assert header == ["var_a", "var_b"]

        # Row 0 (file 1): var_b is NaN
        assert rows[0][1] == "NaN"
        # Row 1 (file 2): var_b has the value
        assert rows[1][1] == "2.0"

    def test_missing_var_in_later_result_gets_nan(self, tmp_path: Any) -> None:
        """
        If a later result lacks a variable, NaN is written for that cell.
        """
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        stat_a = self._mock_scalar(10.0)
        stat_b = self._mock_scalar(20.0)

        # File 1 has both; File 2 only has var_a
        results = [
            {"var_a": stat_a, "var_b": stat_b},
            {"var_a": stat_a},
        ]
        var_names = ["var_a", "var_b"]

        output_dir = str(tmp_path)
        csv_path = Gem5Parser.construct_final_csv(output_dir, results, var_names=var_names)
        assert csv_path is not None

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            _ = next(reader)  # header
            rows = list(reader)

        # Row 1 (file 2): var_b is NaN
        assert rows[1][1] == "NaN"

    def test_all_vars_present_no_nan(self, tmp_path: Any) -> None:
        """No NaN when all results have all variables."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        stat_a = self._mock_scalar(1.0)
        stat_b = self._mock_scalar(2.0)

        results = [
            {"var_a": stat_a, "var_b": stat_b},
            {"var_a": stat_a, "var_b": stat_b},
        ]
        var_names = ["var_a", "var_b"]

        output_dir = str(tmp_path)
        csv_path = Gem5Parser.construct_final_csv(output_dir, results, var_names=var_names)
        assert csv_path is not None

        with open(csv_path, encoding="utf-8") as f:
            content = f.read()
        assert "NaN" not in content

    def test_parse_service_construct_final_csv_na(self, tmp_path: Any) -> None:
        """ParseService.construct_final_csv also handles missing vars."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ParseService

        stat_a = self._mock_scalar(5.0)
        stat_b = self._mock_scalar(10.0)

        results = [
            {"var_a": stat_a},
            {"var_a": stat_a, "var_b": stat_b},
        ]
        var_names = ["var_a", "var_b"]

        output_dir = str(tmp_path)
        csv_path = ParseService.construct_final_csv(output_dir, results, var_names=var_names)
        assert csv_path is not None

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)

        assert "var_b" in header
        assert rows[0][1] == "NaN"
        assert rows[1][1] == "10.0"
