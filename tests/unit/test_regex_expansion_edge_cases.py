"""
Unit tests for regex expansion edge cases in ParseService and Gem5Parser.

Covers:
- Literal dots in variable names (not expanded when is_regex=False)
- Literal dots with is_regex=True (dot acts as regex wildcard)
- No-match scenario (regex matches nothing in scanned_vars)
- Invalid regex (malformed pattern handled gracefully)
- Exact name match (config.name == sv.name path)
- Expansion via pattern_indices (aggregated variables)
- Expansion fallback to sv_name when no pattern_indices
- Dict-based scanned variable (legacy path)
- is_regex=True but scanned_vars is None or empty
- Multiple pattern groups merged correctly
"""

import re
from dataclasses import replace
from typing import Any, Dict, List, Optional

from src.core.models import ScannedVariable, StatConfig


def _expand_regex(
    config: StatConfig,
    scanned_vars: Optional[List[Any]],
) -> StatConfig:
    """
    Mirror the expansion logic from ParseService/Gem5Parser.

    This is an exact copy of the production code so we can unit-test
    it without needing filesystem access or worker pools.
    """
    expanded_config = config
    if scanned_vars and config.is_regex:
        try:
            pattern = re.compile(config.name)
            matched_ids: List[str] = []
            for sv in scanned_vars:
                sv_name = sv.name if hasattr(sv, "name") else str(sv.get("name", ""))
                if config.name == sv_name or pattern.fullmatch(sv_name):
                    if hasattr(sv, "pattern_indices") and sv.pattern_indices:
                        matched_ids.extend(sv.pattern_indices)
                    elif isinstance(sv, dict) and sv.get("pattern_indices"):
                        matched_ids.extend(sv.get("pattern_indices", []))
                    else:
                        matched_ids.append(sv_name)

            if matched_ids:
                params = config.params.copy()
                params["parsed_ids"] = matched_ids
                expanded_config = replace(config, params=params)
        except re.error:
            pass  # Invalid regex — config passes through unchanged

    return expanded_config


# ---------------------------------------------------------------------------
# Edge case: literal dots
# ---------------------------------------------------------------------------


class TestLiteralDots:
    """Dots in gem5 variable names are hierarchy separators, not regex."""

    def test_dots_not_expanded_when_is_regex_false(self) -> None:
        """system.cpu.ipc with is_regex=False must NOT trigger expansion."""
        config = StatConfig(name="system.cpu.ipc", type="scalar", is_regex=False)
        scanned = [
            ScannedVariable(name="system.cpu.ipc", type="scalar"),
            ScannedVariable(name="systemXcpuXipc", type="scalar"),  # dot-as-wildcard match
        ]

        result = _expand_regex(config, scanned)
        assert "parsed_ids" not in result.params

    def test_dots_act_as_wildcard_when_is_regex_true(self) -> None:
        """With is_regex=True, dots should match any character (regex semantics)."""
        config = StatConfig(name="system.cpu.ipc", type="scalar", is_regex=True)
        scanned = [
            ScannedVariable(name="systemXcpuXipc", type="scalar"),
        ]

        result = _expand_regex(config, scanned)
        # '.' matches any char → "systemXcpuXipc" matches "system.cpu.ipc"
        assert "parsed_ids" in result.params
        assert result.params["parsed_ids"] == ["systemXcpuXipc"]


# ---------------------------------------------------------------------------
# Edge case: no match
# ---------------------------------------------------------------------------


class TestNoMatch:
    """Regex matches nothing in scanned_vars."""

    def test_no_match_passes_config_through_unchanged(self) -> None:
        """When no scanned variable matches the pattern, config is unchanged."""
        config = StatConfig(
            name=r"system\.nonexistent\d+\.stat",
            type="scalar",
            is_regex=True,
        )
        scanned = [
            ScannedVariable(name="system.cpu0.ipc", type="scalar"),
            ScannedVariable(name="simTicks", type="scalar"),
        ]

        result = _expand_regex(config, scanned)
        assert "parsed_ids" not in result.params
        # Original config passed through
        assert result is config

    def test_no_match_empty_scanned_list(self) -> None:
        """Empty scanned_vars list results in no expansion."""
        config = StatConfig(name=r"system\.cpu\d+\.ipc", type="scalar", is_regex=True)

        result = _expand_regex(config, [])
        assert "parsed_ids" not in result.params
        assert result is config


# ---------------------------------------------------------------------------
# Edge case: invalid regex
# ---------------------------------------------------------------------------


class TestInvalidRegex:
    """Malformed regex patterns should be handled gracefully."""

    def test_invalid_regex_passes_config_unchanged(self) -> None:
        """An invalid regex should not crash; config passes through."""
        config = StatConfig(
            name=r"system.cpu[.ipc",  # Unclosed bracket
            type="scalar",
            is_regex=True,
        )
        scanned = [ScannedVariable(name="system.cpu0.ipc", type="scalar")]

        result = _expand_regex(config, scanned)
        assert "parsed_ids" not in result.params
        assert result is config

    def test_another_invalid_pattern(self) -> None:
        """Unbalanced parenthesis should also be handled."""
        config = StatConfig(
            name=r"system.cpu(\d+.ipc",  # Unclosed paren
            type="scalar",
            is_regex=True,
        )
        scanned = [ScannedVariable(name="system.cpu0.ipc", type="scalar")]

        result = _expand_regex(config, scanned)
        assert "parsed_ids" not in result.params

    def test_empty_pattern(self) -> None:
        """Empty name with is_regex=True should match empty-string scanned vars."""
        config = StatConfig(name="", type="scalar", is_regex=True)
        scanned = [ScannedVariable(name="", type="scalar")]

        # Empty pattern fullmatches empty string
        result = _expand_regex(config, scanned)
        assert "parsed_ids" in result.params
        assert result.params["parsed_ids"] == [""]


# ---------------------------------------------------------------------------
# Edge case: exact name match (config.name == sv.name)
# ---------------------------------------------------------------------------


class TestExactNameMatch:
    r"""The ``config.name == sv_name`` path in the expansion loop."""

    def test_exact_match_with_aggregated_pattern(self) -> None:
        r"""Exact match on pattern name uses pattern_indices."""
        config = StatConfig(name=r"system.cpu\d+.ipc", type="scalar", is_regex=True)
        scanned = [
            ScannedVariable(
                name=r"system.cpu\d+.ipc",
                type="scalar",
                pattern_indices=["system.cpu0.ipc", "system.cpu1.ipc", "system.cpu2.ipc"],
            ),
        ]

        result = _expand_regex(config, scanned)
        assert result.params["parsed_ids"] == [
            "system.cpu0.ipc",
            "system.cpu1.ipc",
            "system.cpu2.ipc",
        ]

    def test_exact_match_without_pattern_indices(self) -> None:
        """Exact match with no pattern_indices appends sv_name directly."""
        config = StatConfig(name=r"system.cpu\d+.ipc", type="scalar", is_regex=True)
        scanned = [
            ScannedVariable(name=r"system.cpu\d+.ipc", type="scalar"),
        ]

        result = _expand_regex(config, scanned)
        assert result.params["parsed_ids"] == [r"system.cpu\d+.ipc"]


# ---------------------------------------------------------------------------
# Edge case: pattern_indices vs no pattern_indices
# ---------------------------------------------------------------------------


class TestPatternIndicesExpansion:
    """Expansion uses pattern_indices when available, sv_name otherwise."""

    def test_expansion_with_pattern_indices(self) -> None:
        """Aggregated pattern variable with pattern_indices expands correctly."""
        config = StatConfig(
            name=r"system\.ruby\.l\d+_cntrl\d+\.hits",
            type="vector",
            is_regex=True,
        )
        scanned = [
            ScannedVariable(
                name=r"system\.ruby\.l\d+_cntrl\d+\.hits",
                type="vector",
                entries=["0_0", "0_1", "1_0", "1_1"],
                pattern_indices=[
                    "system.ruby.l0_cntrl0.hits",
                    "system.ruby.l0_cntrl1.hits",
                    "system.ruby.l1_cntrl0.hits",
                    "system.ruby.l1_cntrl1.hits",
                ],
            ),
        ]

        result = _expand_regex(config, scanned)
        assert len(result.params["parsed_ids"]) == 4
        assert "system.ruby.l0_cntrl0.hits" in result.params["parsed_ids"]
        assert "system.ruby.l1_cntrl1.hits" in result.params["parsed_ids"]

    def test_expansion_without_pattern_indices_uses_sv_name(self) -> None:
        """Non-aggregated variable without pattern_indices uses its name."""
        config = StatConfig(name=r"system\.cpu\d+\.ipc", type="scalar", is_regex=True)
        scanned = [
            ScannedVariable(name="system.cpu0.ipc", type="scalar"),
            ScannedVariable(name="system.cpu1.ipc", type="scalar"),
        ]

        result = _expand_regex(config, scanned)
        assert result.params["parsed_ids"] == ["system.cpu0.ipc", "system.cpu1.ipc"]

    def test_mixed_with_and_without_pattern_indices(self) -> None:
        """Mix of aggregated and non-aggregated matches merges correctly."""
        config = StatConfig(name=r"system\.cpu\d+\.ipc", type="scalar", is_regex=True)
        scanned = [
            # Aggregated pattern variable
            ScannedVariable(
                name=r"system\.cpu\d+\.ipc",
                type="scalar",
                pattern_indices=["system.cpu0.ipc", "system.cpu1.ipc"],
            ),
            # Additional non-aggregated match
            ScannedVariable(name="system.cpu2.ipc", type="scalar"),
        ]

        result = _expand_regex(config, scanned)
        ids = result.params["parsed_ids"]
        assert "system.cpu0.ipc" in ids
        assert "system.cpu1.ipc" in ids
        assert "system.cpu2.ipc" in ids
        assert len(ids) == 3


# ---------------------------------------------------------------------------
# Edge case: dict-based scanned variable (legacy path)
# ---------------------------------------------------------------------------


class TestDictBasedScannedVar:
    """Legacy dict-based scanned variables should still work."""

    def test_dict_with_pattern_indices(self) -> None:
        """Dict scanned var with pattern_indices should expand."""
        config = StatConfig(name=r"system\.cpu\d+\.ipc", type="scalar", is_regex=True)
        scanned: List[Dict[str, Any]] = [
            {
                "name": r"system\.cpu\d+\.ipc",
                "type": "scalar",
                "pattern_indices": ["system.cpu0.ipc", "system.cpu1.ipc"],
            },
        ]

        result = _expand_regex(config, scanned)  # type: ignore[arg-type]
        assert result.params["parsed_ids"] == ["system.cpu0.ipc", "system.cpu1.ipc"]

    def test_dict_without_pattern_indices(self) -> None:
        """Dict scanned var without pattern_indices uses name."""
        config = StatConfig(name=r"system\.cpu\d+\.ipc", type="scalar", is_regex=True)
        scanned: List[Dict[str, Any]] = [
            {"name": "system.cpu0.ipc", "type": "scalar"},
        ]

        result = _expand_regex(config, scanned)  # type: ignore[arg-type]
        assert result.params["parsed_ids"] == ["system.cpu0.ipc"]


# ---------------------------------------------------------------------------
# Edge case: is_regex=True but no scanned_vars
# ---------------------------------------------------------------------------


class TestNoScannedVars:
    """Expansion should be skipped when scanned_vars is None or empty."""

    def test_scanned_vars_none(self) -> None:
        """None scanned_vars → no expansion."""
        config = StatConfig(name=r"system\.cpu\d+\.ipc", type="scalar", is_regex=True)

        result = _expand_regex(config, None)
        assert "parsed_ids" not in result.params
        assert result is config

    def test_scanned_vars_empty_list(self) -> None:
        """Empty scanned_vars list → no expansion."""
        config = StatConfig(name=r"system\.cpu\d+\.ipc", type="scalar", is_regex=True)

        result = _expand_regex(config, [])
        assert "parsed_ids" not in result.params
        assert result is config


# ---------------------------------------------------------------------------
# Edge case: multiple pattern groups merged
# ---------------------------------------------------------------------------


class TestMultiplePatternGroups:
    """Expansion across multiple matching scanned variables."""

    def test_multiple_different_patterns_merged(self) -> None:
        """Multiple scanned vars matching the same regex produce merged parsed_ids."""
        config = StatConfig(name=r"system\.cpu\d+\.numCycles", type="scalar", is_regex=True)
        scanned = [
            ScannedVariable(
                name=r"system\.cpu\d+\.numCycles",
                type="scalar",
                pattern_indices=["system.cpu0.numCycles", "system.cpu1.numCycles"],
            ),
        ]

        result = _expand_regex(config, scanned)
        assert result.params["parsed_ids"] == [
            "system.cpu0.numCycles",
            "system.cpu1.numCycles",
        ]
        assert result.is_regex is True  # Flag preserved through replace

    def test_immutability_of_original_config(self) -> None:
        """Expansion returns new config; original is unchanged (frozen)."""
        config = StatConfig(
            name=r"system\.cpu\d+\.ipc",
            type="scalar",
            is_regex=True,
            params={"original_key": "value"},
        )
        scanned = [
            ScannedVariable(
                name=r"system\.cpu\d+\.ipc",
                type="scalar",
                pattern_indices=["system.cpu0.ipc"],
            ),
        ]

        result = _expand_regex(config, scanned)

        # Original untouched
        assert "parsed_ids" not in config.params
        assert config.params == {"original_key": "value"}

        # Result has merged params
        assert result.params["original_key"] == "value"
        assert result.params["parsed_ids"] == ["system.cpu0.ipc"]

    def test_preserves_existing_params(self) -> None:
        """Expansion merges parsed_ids into existing params without replacing."""
        config = StatConfig(
            name=r"system\.cpu\d+\.ipc",
            type="vector",
            is_regex=True,
            params={"entries": ["IntAlu", "IntMult"], "vectorEntries": ["IntAlu", "IntMult"]},
        )
        scanned = [
            ScannedVariable(
                name=r"system\.cpu\d+\.ipc",
                type="vector",
                pattern_indices=["system.cpu0.ipc"],
            ),
        ]

        result = _expand_regex(config, scanned)
        assert result.params["entries"] == ["IntAlu", "IntMult"]
        assert result.params["vectorEntries"] == ["IntAlu", "IntMult"]
        assert result.params["parsed_ids"] == ["system.cpu0.ipc"]
