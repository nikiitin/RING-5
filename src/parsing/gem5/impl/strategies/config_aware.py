"""Compose typed stats work with exact per-source configuration metadata."""

from __future__ import annotations

import configparser
import json
import io
import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from src.core.common.security_limits import MAX_PARSED_CELL_CHARACTERS, MAX_PARSE_FILE_BYTES
from src.core.models.parsed_output_models import ParsedCell, ParsedFileResult
from src.parsing.gem5.impl.source_bindings import SourcePlan
from src.parsing.gem5.impl.strategies.file_parser_strategy import ParseWorkItem
from src.parsing.gem5.impl.strategies.simple import SimpleStatsStrategy

logger = logging.getLogger(__name__)


class _LiteralConfigParser(configparser.ConfigParser):
    """Preserve case-sensitive simulator parameter names."""

    def optionxform(self, optionstr: str) -> str:
        """Return parameter names exactly as serialized by gem5."""
        return optionstr


@dataclass(frozen=True)
class ConfigAwareParseWork:
    """Decorate one typed worker with its required configuration companion file."""

    work: ParseWorkItem

    @property
    def source_path(self) -> str:
        """Return the source owned by the wrapped worker."""
        return self.work.source_path

    def __call__(self) -> ParsedFileResult:
        """Resolve typed statistics and literal metadata before this Future completes."""
        result = self.work()
        if type(result) is not ParsedFileResult or result.source_path != self.source_path:
            raise ValueError("PARSER: config-aware work returned invalid source provenance.")
        config_path = Path(self.source_path).parent / "config.ini"
        metadata = (
            ParsedCell("sim_path", "text", self.source_path),
            ParsedCell("config_json", "text", self._read_config(config_path)),
        )
        return replace(result, metadata=(*result.metadata, *metadata))

    @staticmethod
    def _read_config(config_path: Path) -> str:
        if not config_path.is_file():
            raise FileNotFoundError(f"PARSER: config.ini not found: {config_path}")
        if config_path.stat().st_size > MAX_PARSE_FILE_BYTES:
            raise ValueError("PARSER: configuration input exceeds the per-file byte limit.")
        parser = _LiteralConfigParser(interpolation=None)
        try:
            with config_path.open("rb") as handle:
                raw = handle.read(MAX_PARSE_FILE_BYTES + 1)
            if len(raw) > MAX_PARSE_FILE_BYTES:
                raise ValueError("PARSER: configuration input grew beyond the per-file byte limit.")
            parser.read_string(raw.decode("utf-8"))
            if not parser.sections():
                raise configparser.Error("configuration contains no sections")
            encoded = io.StringIO()
            characters = 0
            encoder = json.JSONEncoder(separators=(",", ":"))

            def append(fragment: str) -> None:
                nonlocal characters
                characters += len(fragment)
                if characters > MAX_PARSED_CELL_CHARACTERS:
                    raise ValueError(
                        "PARSER: configuration metadata exceeds the cell character limit."
                    )
                encoded.write(fragment)

            def append_text(value: str) -> None:
                # JSON escaping never shrinks a string. Reject oversized source
                # values before an encoder can allocate their escaped fragment.
                if len(value) > MAX_PARSED_CELL_CHARACTERS - characters:
                    raise ValueError(
                        "PARSER: configuration metadata exceeds the cell character limit."
                    )
                append(encoder.encode(value))

            # Defaults can be inherited by many sections. Charge the canonical
            # JSON as it is emitted instead of materializing that expanded graph.
            append("{")
            for section_index, section in enumerate(sorted(parser.sections())):
                if section_index:
                    append(",")
                append_text(section)
                append(":{")
                values = parser[section]
                for option_index, option in enumerate(sorted(values)):
                    if option_index:
                        append(",")
                    append_text(option)
                    append(":")
                    append_text(values[option])
                append("}")
            append("}")
            return encoded.getvalue()
        except (configparser.Error, OSError, UnicodeError) as exc:
            logger.error("PARSER: Failed to parse %s: %s", config_path, exc)
            raise RuntimeError(f"PARSER: Failed to parse {config_path}: {exc}") from exc


class ConfigAwareStrategy(SimpleStatsStrategy):
    """Wrap independent statistics work with required config.ini metadata."""

    # [impl->req~ring5.ingestion.config-aware-strategy~1]

    def get_work_items(
        self,
        stats_path: str,
        stats_pattern: str,
        plan: SourcePlan,
        *,
        file_paths: list[str] | None = None,
    ) -> Sequence[ParseWorkItem]:
        """Return one metadata-enriched typed task per selected statistics source."""
        return tuple(
            ConfigAwareParseWork(work)
            for work in super().get_work_items(
                stats_path, stats_pattern, plan, file_paths=file_paths
            )
        )
