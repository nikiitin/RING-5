"""Owner-isolated bounded local drafts using the verified portfolio format."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import pandas as pd

from src.core.common.security_limits import (
    MAX_RECOVERY_DRAFT_BYTES,
    MAX_RECOVERY_DRAFTS_GLOBAL,
    MAX_RECOVERY_DRAFTS_PER_OWNER,
    MAX_RECOVERY_OWNER_BYTES,
    MAX_RECOVERY_OWNER_KEY_LENGTH,
    MAX_RECOVERY_TOTAL_BYTES,
)
from src.core.common.utils import validate_path_within
from src.core.models import PlotProtocol, PortfolioData, RecoveryDraftCapture, RecoveryDraftInfo
from src.core.services.data_services.path_service import PathService
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.services.portfolio_integrity_service import PortfolioIntegrityService
from src.core.services.portfolio_migrator import PortfolioMigrator
from src.core.state.state_manager import StateManager

_DRAFT_ID = re.compile(r"^[0-9]{20}-[0-9a-f]{64}$")
_DEFAULT_PARSE_VARIABLES = (
    ("simTicks", "scalar"),
    ("benchmark_name", "configuration"),
    ("config_description", "configuration"),
)


class AutosaveRecoveryService:
    """Capture and restore private, deduplicated, bounded workspace drafts."""

    _lock = threading.RLock()

    @classmethod
    def capture(
        cls,
        state_manager: StateManager,
        owner_key: str,
        *,
        figure_spec_enricher: None | (
            Callable[[dict[str, Any], str], dict[str, Any] | None]
        ) = None,
    ) -> RecoveryDraftCapture | None:
        """Capture meaningful state unless its content matches the newest draft."""
        # [impl->req~ring5.workspace.autosave-recovery~1]
        owner = cls._owner(owner_key)
        data = state_manager.get_data()
        plots = state_manager.get_plots()
        config = state_manager.get_config()
        parse_variables = state_manager.get_parse_variables()
        if not cls._meaningful(state_manager, data, plots, config, parse_variables):
            return None
        payload = PortfolioService(state_manager).serialize_workspace(
            data,
            plots,
            config,
            state_manager.get_plot_counter(),
            csv_path=state_manager.get_csv_path(),
            parse_variables=parse_variables,
            figure_spec_enricher=figure_spec_enricher,
        )
        if len(payload) > MAX_RECOVERY_DRAFT_BYTES:
            raise ValueError(f"Recovery drafts are limited to {MAX_RECOVERY_DRAFT_BYTES:,} bytes.")
        fingerprint = cls._workspace_fingerprint(payload)
        with cls._lock:
            directory = cls._owner_directory(owner, create=True)
            existing = cls._files(directory)
            if existing and existing[-1].stem.endswith(fingerprint):
                cls._prune(directory)
                return RecoveryDraftCapture(cls._info(existing[-1]), created=False)
            draft_id = f"{time.time_ns():020d}-{fingerprint}"
            path = cls._draft_path(directory, draft_id)
            cls._atomic_write(path, payload)
            cls._prune(directory)
            cls._prune_global()
            if not path.exists():
                raise OSError("The new recovery draft could not be retained within global limits.")
            return RecoveryDraftCapture(cls._info(path), created=True)

    @classmethod
    def list_drafts(cls, owner_key: str) -> tuple[RecoveryDraftInfo, ...]:
        """List newest-first recovery points without reading embedded workspace data."""
        owner = cls._owner(owner_key)
        with cls._lock:
            directory = cls._owner_directory(owner, create=False)
            if not directory.exists():
                return ()
            return tuple(cls._info(path) for path in reversed(cls._files(directory)))

    @classmethod
    def load(cls, owner_key: str, draft_id: str) -> PortfolioData:
        """Read one exact draft after size, checksum, and schema verification."""
        # [impl->req~ring5.workspace.autosave-recovery~1]
        owner = cls._owner(owner_key)
        with cls._lock:
            directory = cls._owner_directory(owner, create=False)
            path = cls._draft_path(directory, draft_id)
            if not path.exists():
                raise FileNotFoundError(f"Recovery draft {draft_id!r} was not found.")
            if path.is_symlink():
                raise ValueError("Recovery drafts must not be symbolic links.")
            if path.stat().st_size > MAX_RECOVERY_DRAFT_BYTES:
                raise ValueError("Recovery draft exceeds its safe local size limit.")
            raw = path.read_bytes()
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Recovery draft is not valid UTF-8 portfolio JSON.") from exc
        if not isinstance(value, dict):
            raise ValueError("Recovery draft must contain one portfolio object.")
        report = PortfolioIntegrityService.verify(value)
        PortfolioIntegrityService.require_restorable(report)
        return cast(PortfolioData, PortfolioMigrator.migrate(value))

    @classmethod
    def delete(cls, owner_key: str, draft_id: str) -> None:
        """Delete one exact owner-scoped draft and remove its empty directory."""
        owner = cls._owner(owner_key)
        with cls._lock:
            directory = cls._owner_directory(owner, create=False)
            path = cls._draft_path(directory, draft_id)
            if not path.exists():
                raise FileNotFoundError(f"Recovery draft {draft_id!r} was not found.")
            if path.is_symlink():
                raise ValueError("Recovery drafts must not be symbolic links.")
            path.unlink()
            if directory.exists() and not any(directory.iterdir()):
                directory.rmdir()

    @staticmethod
    def _meaningful(
        state_manager: StateManager,
        data: object,
        plots: list[PlotProtocol],
        config: dict[str, Any],
        parse_variables: list[Any],
    ) -> bool:
        return bool(
            (isinstance(data, pd.DataFrame) and not data.empty)
            or plots
            or config
            or AutosaveRecoveryService._custom_parse_variables(parse_variables)
            or state_manager.get_scanned_variables()
            or state_manager.get_stats_path() not in ("", "/path/to/stats")
            or state_manager.get_stats_pattern() != "stats.txt"
            or state_manager.get_csv_path()
            or state_manager.get_manager_history()
            or state_manager.get_portfolio_history()
        )

    @staticmethod
    def _custom_parse_variables(parse_variables: list[Any]) -> bool:
        if not parse_variables:
            return False
        signature = tuple(
            (item.get("name"), item.get("type"))
            for item in parse_variables
            if isinstance(item, dict)
        )
        return signature != _DEFAULT_PARSE_VARIABLES

    @staticmethod
    def _owner(owner_key: object) -> str:
        if not isinstance(owner_key, str) or not owner_key.strip():
            raise ValueError("Recovery owner key must be non-empty text.")
        key = owner_key.strip()
        if len(key) > MAX_RECOVERY_OWNER_KEY_LENGTH:
            raise ValueError(
                f"Recovery owner keys are limited to {MAX_RECOVERY_OWNER_KEY_LENGTH} characters."
            )
        if any(ord(character) < 32 for character in key):
            raise ValueError("Recovery owner key contains control characters.")
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    @staticmethod
    def _workspace_fingerprint(payload: bytes) -> str:
        value = json.loads(payload.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Serialized recovery workspace must be a portfolio object.")
        content = dict(value)
        content.pop("timestamp", None)
        content.pop("environment_metadata", None)
        content.pop("integrity_manifest", None)
        canonical = json.dumps(
            content,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    @classmethod
    def _owner_directory(cls, owner: str, *, create: bool) -> Path:
        root = PathService.get_recovery_drafts_dir()
        if root.is_symlink():
            raise ValueError("Recovery draft storage must not be a symbolic link.")
        directory = validate_path_within(root / owner, root)
        if directory.is_symlink():
            raise ValueError("Recovery owner storage must not be a symbolic link.")
        if create:
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(directory, 0o700)
        return directory

    @staticmethod
    def _draft_path(directory: Path, draft_id: object) -> Path:
        if not isinstance(draft_id, str) or not _DRAFT_ID.fullmatch(draft_id):
            raise ValueError("Recovery draft IDs have an invalid format.")
        return validate_path_within(directory / f"{draft_id}.json", directory)

    @classmethod
    def _files(cls, directory: Path) -> list[Path]:
        files: list[Path] = []
        for path in directory.glob("*.json"):
            if not _DRAFT_ID.fullmatch(path.stem):
                continue
            if path.is_symlink():
                raise ValueError("Recovery drafts must not be symbolic links.")
            if path.is_file():
                files.append(path)
        files.sort(key=lambda path: (path.stat().st_mtime_ns, path.name))
        return files

    @staticmethod
    def _info(path: Path) -> RecoveryDraftInfo:
        stat = path.stat()
        return RecoveryDraftInfo(
            draft_id=path.stem,
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            size_bytes=stat.st_size,
        )

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".ring5-recovery-",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @classmethod
    def _prune(cls, directory: Path) -> None:
        files = cls._files(directory)
        total = sum(path.stat().st_size for path in files)
        while files and (
            len(files) > MAX_RECOVERY_DRAFTS_PER_OWNER or total > MAX_RECOVERY_OWNER_BYTES
        ):
            oldest = files.pop(0)
            total -= oldest.stat().st_size
            oldest.unlink()

    @classmethod
    def _prune_global(cls) -> None:
        root = PathService.get_recovery_drafts_dir()
        files: list[Path] = []
        for directory in root.iterdir():
            if directory.is_symlink():
                raise ValueError("Recovery owner storage must not be a symbolic link.")
            if directory.is_dir():
                files.extend(cls._files(directory))
        files.sort(key=lambda path: (path.stat().st_mtime_ns, path.name))
        total = sum(path.stat().st_size for path in files)
        while files and (
            len(files) > MAX_RECOVERY_DRAFTS_GLOBAL or total > MAX_RECOVERY_TOTAL_BYTES
        ):
            oldest = files.pop(0)
            total -= oldest.stat().st_size
            parent = oldest.parent
            oldest.unlink()
            if not any(parent.iterdir()):
                parent.rmdir()
