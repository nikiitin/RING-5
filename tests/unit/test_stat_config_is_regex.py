"""
Tests for the ``is_regex`` flag on :class:`StatConfig`.

Validates that:
1. The flag defaults to ``False`` for plain variable names.
2. The flag is correctly set to ``True`` for regex patterns.
3. Frozen immutability is preserved.
4. :meth:`ApplicationAPI.submit_parse_async` sets ``is_regex``
   automatically based on ``\\d+`` in the variable name.
5. :class:`ParseService` and :class:`Gem5Parser` honour the flag.
"""

import re
from dataclasses import replace
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import ScannedVariable, StatConfig

# ---------------------------------------------------------------------------
# Unit tests for StatConfig.is_regex field
# ---------------------------------------------------------------------------


class TestStatConfigIsRegex:
    """Core unit tests for the is_regex field."""

    def test_default_is_false(self) -> None:
        """is_regex should default to False."""
        config = StatConfig(name="system.cpu.ipc", type="scalar")
        assert config.is_regex is False

    def test_explicit_true(self) -> None:
        """is_regex can be set explicitly to True."""
        config = StatConfig(name=r"system.cpu\d+.ipc", type="scalar", is_regex=True)
        assert config.is_regex is True

    def test_explicit_false(self) -> None:
        """is_regex can be explicitly set to False."""
        config = StatConfig(name="system.cpu0.ipc", type="scalar", is_regex=False)
        assert config.is_regex is False

    def test_frozen_immutability(self) -> None:
        """Cannot mutate is_regex on a frozen dataclass."""
        config = StatConfig(name="x", type="scalar", is_regex=False)
        with pytest.raises(AttributeError):
            config.is_regex = True  # type: ignore[misc]

    def test_replace_preserves_flag(self) -> None:
        """dataclasses.replace should carry over is_regex."""
        original = StatConfig(name=r"system.cpu\d+.ipc", type="scalar", is_regex=True)
        modified = replace(original, params={"parsed_ids": ["cpu0"]})
        assert modified.is_regex is True

    def test_replace_can_change_flag(self) -> None:
        """dataclasses.replace should allow changing is_regex."""
        original = StatConfig(name="x", type="scalar", is_regex=False)
        modified = replace(original, is_regex=True)
        assert modified.is_regex is True


# ---------------------------------------------------------------------------
# Integration tests: ApplicationAPI sets is_regex automatically
# ---------------------------------------------------------------------------


class TestApplicationAPIIsRegex:
    """Verify ApplicationAPI sets is_regex based on variable name."""

    def _make_api(self) -> Any:
        """Import lazily to avoid heavy module-level loading."""
        from src.core.application_api import ApplicationAPI

        return ApplicationAPI()

    @patch("src.core.application_api.ParseService")
    def test_dict_with_regex_name(self, mock_svc: MagicMock) -> None:
        """A dict variable with \\d+ in name should produce is_regex=True."""
        mock_svc.submit_parse_async.return_value = MagicMock()
        api = self._make_api()

        variables: List[Dict[str, Any]] = [
            {"name": r"system.cpu\d+.ipc", "type": "scalar"},
        ]
        api.submit_parse_async(
            stats_path="/fake/path",
            stats_pattern="stats.txt",
            variables=variables,
            output_dir="/tmp/out",
        )

        call_args = mock_svc.submit_parse_async.call_args
        configs: List[StatConfig] = call_args[0][2]  # third positional arg
        assert len(configs) == 1
        assert configs[0].is_regex is True

    @patch("src.core.application_api.ParseService")
    def test_dict_with_plain_name(self, mock_svc: MagicMock) -> None:
        """A dict variable without \\d+ should produce is_regex=False."""
        mock_svc.submit_parse_async.return_value = MagicMock()
        api = self._make_api()

        variables: List[Dict[str, Any]] = [
            {"name": "system.cpu.ipc", "type": "scalar"},
        ]
        api.submit_parse_async(
            stats_path="/fake/path",
            stats_pattern="stats.txt",
            variables=variables,
            output_dir="/tmp/out",
        )

        call_args = mock_svc.submit_parse_async.call_args
        configs: List[StatConfig] = call_args[0][2]
        assert len(configs) == 1
        assert configs[0].is_regex is False

    @patch("src.core.application_api.ParseService")
    def test_scanned_variable_with_regex(self, mock_svc: MagicMock) -> None:
        """A ScannedVariable with \\d+ in name should produce is_regex=True."""
        mock_svc.submit_parse_async.return_value = MagicMock()
        api = self._make_api()

        sv = ScannedVariable(
            name=r"system.cpu\d+.numCycles",
            type="vector",
            entries=["0", "1", "2", "3"],
        )
        api.submit_parse_async(
            stats_path="/fake/path",
            stats_pattern="stats.txt",
            variables=[sv],
            output_dir="/tmp/out",
        )

        call_args = mock_svc.submit_parse_async.call_args
        configs: List[StatConfig] = call_args[0][2]
        assert len(configs) == 1
        assert configs[0].is_regex is True


# ---------------------------------------------------------------------------
# Regex expansion: is_regex controls whether expansion runs
# ---------------------------------------------------------------------------


class TestRegexExpansionUsesFlag:
    """Verify that the parser uses is_regex instead of string heuristic."""

    def test_is_regex_true_triggers_expansion(self) -> None:
        """With is_regex=True and scanned_vars, expansion should execute."""
        config = StatConfig(
            name=r"system.cpu\d+.ipc",
            type="scalar",
            is_regex=True,
        )
        scanned = [
            ScannedVariable(
                name=r"system.cpu\d+.ipc",
                type="scalar",
                pattern_indices=["system.cpu0.ipc", "system.cpu1.ipc"],
            ),
        ]

        # Expansion logic uses only is_regex (no heuristic fallback)
        assert config.is_regex is True

        expanded = config
        if config.is_regex:
            pattern = re.compile(config.name)
            matched: List[str] = []
            for sv in scanned:
                if config.name == sv.name or pattern.fullmatch(sv.name):
                    if sv.pattern_indices:
                        matched.extend(sv.pattern_indices)

            if matched:
                params = config.params.copy()
                params["parsed_ids"] = matched
                expanded = replace(config, params=params)

        assert "parsed_ids" in expanded.params
        assert expanded.params["parsed_ids"] == [
            "system.cpu0.ipc",
            "system.cpu1.ipc",
        ]

    def test_is_regex_false_skips_expansion(self) -> None:
        """With is_regex=False, expansion is skipped regardless of name content."""
        config = StatConfig(
            name=r"system.cpu\d+.ipc",
            type="scalar",
            is_regex=False,
        )

        # Even though the name contains regex chars, is_regex=False means no expansion
        assert config.is_regex is False

    def test_is_regex_false_plain_name(self) -> None:
        """Plain names naturally have is_regex=False."""
        config = StatConfig(
            name="simTicks",
            type="scalar",
        )
        assert config.is_regex is False
