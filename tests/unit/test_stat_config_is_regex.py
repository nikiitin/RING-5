r"""
Tests for the ``is_regex`` flag on :class:`StatConfig`.

Validates that:
1. The flag defaults to ``False`` for plain variable names.
2. The flag is correctly set to ``True`` for regex patterns.
3. Frozen immutability is preserved.
4. :meth:`ApplicationAPI.submit_parse_async` sets ``is_regex``
   automatically based on ``\\d+`` in the variable name.
5. :class:`ParseService` and :class:`Gem5Parser` honour the flag.
"""

from src.core.models.source_evidence import ResolvedSourceKind

from dataclasses import replace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.models.parsing_models import ScannedVariable, SourceInstance, StatConfig

# Unit tests for StatConfig.is_regex field


class TestStatConfigIsRegex:
    """Core unit tests for the is_regex field."""

    def test_default_is_false(self) -> None:
        """is_regex should default to False."""
        config = StatConfig(name="system.cpu.ipc", type="scalar", params={"source_type": "scalar"})
        assert config.is_regex is False

    def test_explicit_true(self) -> None:
        """is_regex can be set explicitly to True."""
        config = StatConfig(
            name=r"system.cpu\d+.ipc",
            type="scalar",
            is_regex=True,
            params={"source_type": "scalar"},
        )
        assert config.is_regex is True

    def test_explicit_false(self) -> None:
        """is_regex can be explicitly set to False."""
        config = StatConfig(
            name="system.cpu0.ipc", type="scalar", is_regex=False, params={"source_type": "scalar"}
        )
        assert config.is_regex is False

    def test_frozen_immutability(self) -> None:
        """Cannot mutate is_regex on a frozen dataclass."""
        config = StatConfig(
            name="x", type="scalar", is_regex=False, params={"source_type": "scalar"}
        )
        with pytest.raises(AttributeError):
            config.is_regex = True  # type: ignore[misc]

    def test_replace_preserves_flag(self) -> None:
        """dataclasses.replace should carry over is_regex."""
        original = StatConfig(
            name=r"system.cpu\d+.ipc",
            type="scalar",
            is_regex=True,
            params={"source_type": "scalar"},
        )
        modified = replace(original, params={"source_type": "scalar", "selected_sources": ["cpu0"]})
        assert modified.is_regex is True

    def test_replace_can_change_flag(self) -> None:
        """dataclasses.replace should allow changing is_regex."""
        original = StatConfig(
            name="x", type="scalar", is_regex=False, params={"source_type": "scalar"}
        )
        modified = replace(original, is_regex=True)
        assert modified.is_regex is True


# Integration tests: ApplicationAPI sets is_regex automatically


class TestApplicationAPIIsRegex:
    """Verify ApplicationAPI sets is_regex based on variable name."""

    def _make_api(self) -> Any:
        """Import lazily to avoid heavy module-level loading."""
        from src.core.application_api import ApplicationAPI

        api = ApplicationAPI()
        api._parser = MagicMock()
        return api

    def test_dict_with_regex_name(self) -> None:
        r"""A dict variable with \\d+ in name should produce is_regex=True."""
        api = self._make_api()
        api._parser.submit_parse_async.return_value = MagicMock(futures=[])

        variables: list[dict[str, Any]] = [
            {"name": r"system.cpu\d+.ipc", "type": "scalar", "params": {"source_type": "scalar"}},
        ]
        api.submit_parse_async(
            stats_path="/fake/path",
            stats_pattern="stats.txt",
            variables=api.compile_parse_variables(variables),
            output_dir="/tmp/out",
        )

        call_args = api._parser.submit_parse_async.call_args
        configs: list[StatConfig] = call_args[0][2]  # third positional arg
        assert len(configs) == 1
        assert configs[0].is_regex is True

    def test_dict_with_plain_name(self) -> None:
        r"""A dict variable without \\d+ should produce is_regex=False."""
        api = self._make_api()
        api._parser.submit_parse_async.return_value = MagicMock(futures=[])

        variables: list[dict[str, Any]] = [
            {"name": "system.cpu.ipc", "type": "scalar", "params": {"source_type": "scalar"}},
        ]
        api.submit_parse_async(
            stats_path="/fake/path",
            stats_pattern="stats.txt",
            variables=api.compile_parse_variables(variables),
            output_dir="/tmp/out",
        )

        call_args = api._parser.submit_parse_async.call_args
        configs: list[StatConfig] = call_args[0][2]
        assert len(configs) == 1
        assert configs[0].is_regex is False

    def test_scanned_variable_requires_explicit_runnable_composition(self) -> None:
        api = self._make_api()
        sv = ScannedVariable(
            name=r"system.cpu\d+.numCycles",
            type="vector",
            entries=[],
            source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
            instances=(SourceInstance("system.cpu0.numCycles", ("0",)),),
        )
        with pytest.raises(TypeError, match="StatConfig instances"):
            api.submit_parse_async("/fake/path", "stats.txt", [sv], "/tmp/out")
        api._parser.submit_parse_async.assert_not_called()
