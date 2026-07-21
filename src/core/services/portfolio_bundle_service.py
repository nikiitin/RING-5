"""Create and validate bounded portable analysis bundles."""

from __future__ import annotations

import hashlib
import json
import mimetypes
from collections.abc import Mapping
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any, cast
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo

from src.core.common.security_limits import (
    MAX_PORTFOLIO_BUNDLE_BYTES,
    MAX_PORTFOLIO_BUNDLE_MEMBERS,
    MAX_PORTFOLIO_BUNDLE_RESULT_BYTES,
)
from src.core.models import (
    PortfolioBundleArtifact,
    PortfolioBundleContents,
    PortfolioBundleInfo,
    PortfolioBundleResult,
    PortfolioData,
)
from src.core.models.portfolio_bundle_models import PortfolioBundleArtifactRole
from src.core.services.data_services.dataset_snapshot_service import DatasetSnapshotService
from src.core.services.portfolio_integrity_service import PortfolioIntegrityService
from src.core.services.portfolio_migrator import PortfolioMigrator
from src.core.services.environment_metadata_service import EnvironmentMetadataService

_FORMAT = "ring5.portfolio-bundle"
_FORMAT_VERSION = 1
_MANIFEST_MEMBER = "manifest.json"
_PORTFOLIO_MEMBER = "portfolio/portfolio.json"
_SOURCE_MEMBER = "sources/manifest.json"
_ENVIRONMENT_MEMBER = "environment/metadata.json"
_REQUIREMENTS_MEMBER = "environment/requirements.txt"
_SNAPSHOT_MEMBER = "data/dataset.ring5-snapshot"
_ROLES: frozenset[str] = frozenset(
    {
        "portfolio",
        "source-manifest",
        "environment-metadata",
        "python-requirements",
        "dataset-snapshot",
        "result",
    }
)
_REQUIRED_ROLES = frozenset(
    {"portfolio", "source-manifest", "environment-metadata", "python-requirements"}
)


class PortfolioBundleService:
    """Build and read non-executable, checksummed ``.ring5-bundle`` archives."""

    @classmethod
    def create(
        cls,
        name: str,
        portfolio_bytes: bytes,
        *,
        dataset_snapshot: tuple[str, bytes] | None = None,
        results: Mapping[str, bytes] | None = None,
        signing_key: str | bytes | None = None,
        signing_key_id: str = "default",
    ) -> bytes:
        # [impl->req~ring5.portfolio.portable-bundles~1]
        """Create deterministic portable bundle bytes from verified artifacts.

        Args:
            name: Human-readable bundle name.
            portfolio_bytes: Complete saved portfolio JSON.
            dataset_snapshot: Optional ``(name, archive_bytes)`` exact snapshot.
            results: Optional safe relative result names mapped to file bytes.
            signing_key: Optional secret used to sign the bundled portfolio copy.
            signing_key_id: Non-secret identifier stored with a new signature.

        Returns:
            Complete ``.ring5-bundle`` ZIP bytes.

        Raises:
            ValueError: Any input is invalid, unsafe, modified, or over its limit.
        """
        resolved_name = cls._bounded_name(name, "Bundle")
        portfolio_raw = cls._json_object(portfolio_bytes, "Portfolio")
        integrity = PortfolioIntegrityService.verify(portfolio_raw)
        PortfolioIntegrityService.require_restorable(integrity)
        PortfolioMigrator.migrate(portfolio_raw)
        if signing_key is not None:
            portfolio_raw = dict(portfolio_raw)
            portfolio_raw["integrity_manifest"] = PortfolioIntegrityService.create_manifest(
                portfolio_raw,
                signing_key=signing_key,
                key_id=signing_key_id,
            )
            portfolio_bytes = cls._json_bytes(portfolio_raw, indent=2)
        if len(portfolio_bytes) > MAX_PORTFOLIO_BUNDLE_BYTES:
            raise ValueError("Portfolio exceeds the portable bundle size limit.")

        source_manifest = cls._source_manifest(portfolio_raw)
        environment = cls._environment(portfolio_raw.get("environment_metadata"))
        requirements = cls._requirements(environment)
        members: dict[str, tuple[PortfolioBundleArtifactRole, str, bytes]] = {
            _PORTFOLIO_MEMBER: ("portfolio", "application/json", portfolio_bytes),
            _SOURCE_MEMBER: (
                "source-manifest",
                "application/json",
                cls._json_bytes(source_manifest, indent=2),
            ),
            _ENVIRONMENT_MEMBER: (
                "environment-metadata",
                "application/json",
                cls._json_bytes(environment, indent=2),
            ),
            _REQUIREMENTS_MEMBER: (
                "python-requirements",
                "text/plain",
                requirements.encode("utf-8"),
            ),
        }
        if dataset_snapshot is not None:
            snapshot_name, snapshot_bytes = dataset_snapshot
            snapshot_info = DatasetSnapshotService.inspect_snapshot(snapshot_bytes)
            if snapshot_info.name != snapshot_name.strip():
                raise ValueError("Dataset snapshot name does not match its manifest.")
            members[_SNAPSHOT_MEMBER] = (
                "dataset-snapshot",
                "application/vnd.ring5.dataset-snapshot+zip",
                snapshot_bytes,
            )

        result_bytes = 0
        for raw_name, raw_data in sorted((results or {}).items()):
            result_name = cls._safe_result_name(raw_name)
            if not isinstance(raw_data, bytes):
                raise ValueError(f"Bundle result {result_name!r} must contain bytes.")
            result_bytes += len(raw_data)
            if result_bytes > MAX_PORTFOLIO_BUNDLE_RESULT_BYTES:
                raise ValueError("Generated results exceed the portable bundle result limit.")
            member = f"results/{result_name}"
            if member in members:
                raise ValueError(f"Duplicate portable bundle member {member!r}.")
            media_type = mimetypes.guess_type(result_name)[0] or "application/octet-stream"
            members[member] = ("result", media_type, raw_data)

        if len(members) > MAX_PORTFOLIO_BUNDLE_MEMBERS:
            raise ValueError("Portable bundle contains too many files.")
        artifacts = [
            {
                "path": path,
                "role": role,
                "media_type": media_type,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for path, (role, media_type, data) in sorted(members.items())
        ]
        timestamp = portfolio_raw.get("timestamp")
        manifest = {
            "format": _FORMAT,
            "format_version": _FORMAT_VERSION,
            "name": resolved_name,
            "portfolio_created_at": timestamp if isinstance(timestamp, str) else None,
            "members": artifacts,
        }
        archive_members = {_MANIFEST_MEMBER: cls._json_bytes(manifest, indent=2)}
        archive_members.update({path: value[2] for path, value in members.items()})
        total_uncompressed = sum(len(data) for data in archive_members.values())
        if total_uncompressed > MAX_PORTFOLIO_BUNDLE_BYTES:
            raise ValueError("Portable bundle contents exceed the size limit.")
        return cls._zip_bytes(archive_members)

    @classmethod
    def inspect(
        cls,
        payload: bytes,
        *,
        signing_key: str | bytes | None = None,
        require_signature: bool = False,
    ) -> PortfolioBundleInfo:
        # [impl->req~ring5.portfolio.portable-bundles~1]
        """Validate a portable bundle and return metadata without changing state.

        Args:
            payload: Complete ``.ring5-bundle`` bytes.
            signing_key: Optional shared secret for the contained portfolio.
            require_signature: Require that secret to authenticate the portfolio.

        Returns:
            Bundle contents, provenance, and integrity summary.
        """
        return cls.read(
            payload,
            signing_key=signing_key,
            require_signature=require_signature,
        ).info

    @classmethod
    def read(
        cls,
        payload: bytes,
        *,
        signing_key: str | bytes | None = None,
        require_signature: bool = False,
    ) -> PortfolioBundleContents:
        # [impl->req~ring5.portfolio.portable-bundles~1]
        """Return all files only after archive and portfolio verification.

        Args:
            payload: Complete ``.ring5-bundle`` bytes.
            signing_key: Optional shared secret for the contained portfolio.
            require_signature: Require that secret to authenticate the portfolio.

        Returns:
            Validated portfolio, provenance, optional snapshot, and result bytes.
        """
        archive = cls._read_archive(payload)
        manifest = cls._manifest(archive[_MANIFEST_MEMBER])
        artifacts = cls._artifacts(manifest, archive)
        by_role: dict[str, list[PortfolioBundleArtifact]] = {}
        for artifact in artifacts:
            by_role.setdefault(artifact.role, []).append(artifact)
        if any(len(by_role.get(role, ())) != 1 for role in _REQUIRED_ROLES):
            raise ValueError("Portable bundle is missing a required unique artifact.")
        if len(by_role.get("dataset-snapshot", ())) > 1:
            raise ValueError("Portable bundle can contain at most one dataset snapshot.")

        portfolio_artifact = by_role["portfolio"][0]
        portfolio_raw = cls._json_object(archive[portfolio_artifact.path], "Portfolio")
        integrity = PortfolioIntegrityService.verify(portfolio_raw, signing_key=signing_key)
        PortfolioIntegrityService.require_restorable(
            integrity,
            require_signature=require_signature,
        )
        portfolio = cast(PortfolioData, PortfolioMigrator.migrate(portfolio_raw))

        source_artifact = by_role["source-manifest"][0]
        source_manifest = cls._json_object(archive[source_artifact.path], "Source manifest")
        if (
            source_manifest.get("format") != "ring5.source-manifest"
            or source_manifest.get("format_version") != 1
            or not isinstance(source_manifest.get("sources"), list)
            or len(source_manifest["sources"]) > 32
        ):
            raise ValueError("Portable bundle source manifest is invalid.")
        if source_manifest != cls._source_manifest(portfolio_raw):
            raise ValueError("Portable bundle source manifest does not match its portfolio.")

        environment_artifact = by_role["environment-metadata"][0]
        environment = cls._json_value(archive[environment_artifact.path], "Environment metadata")
        recorded_environment = cls._environment(portfolio_raw.get("environment_metadata"))
        if environment != recorded_environment:
            raise ValueError("Portable bundle environment metadata does not match its portfolio.")
        requirements_artifact = by_role["python-requirements"][0]
        try:
            requirements = archive[requirements_artifact.path].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Portable bundle requirements must use UTF-8.") from exc
        if requirements != cls._requirements(environment):
            raise ValueError("Portable bundle requirements do not match its environment metadata.")
        requirement_count = sum(
            bool(line.strip()) and not line.lstrip().startswith("#")
            for line in requirements.splitlines()
        )

        snapshot_bytes: bytes | None = None
        snapshot_info = None
        snapshot_artifacts = by_role.get("dataset-snapshot", [])
        if snapshot_artifacts:
            snapshot_bytes = archive[snapshot_artifacts[0].path]
            snapshot_info = DatasetSnapshotService.inspect_snapshot(snapshot_bytes)

        result_files = tuple(
            PortfolioBundleResult(
                name=artifact.path.removeprefix("results/"),
                media_type=artifact.media_type,
                data=archive[artifact.path],
            )
            for artifact in sorted(by_role.get("result", []), key=lambda item: item.path)
        )
        name = cls._bounded_name(manifest.get("name"), "Bundle")
        created_at = manifest.get("portfolio_created_at")
        if created_at is not None and not isinstance(created_at, str):
            raise ValueError("Portable bundle portfolio_created_at must be text or null.")
        recorded_timestamp = portfolio_raw.get("timestamp")
        expected_created_at = recorded_timestamp if isinstance(recorded_timestamp, str) else None
        if created_at != expected_created_at:
            raise ValueError("Portable bundle timestamp does not match its portfolio.")
        info = PortfolioBundleInfo(
            name=name,
            format_version=_FORMAT_VERSION,
            portfolio_schema_version=int(portfolio["schema_version"]),
            portfolio_created_at=created_at,
            size_bytes=len(payload),
            source_count=len(source_manifest["sources"]),
            requirement_count=requirement_count,
            portfolio_integrity=integrity,
            dataset_snapshot=snapshot_info,
            result_names=tuple(result.name for result in result_files),
            artifacts=artifacts,
        )
        return PortfolioBundleContents(
            info=info,
            portfolio=portfolio,
            source_manifest=source_manifest,
            requirements=requirements,
            dataset_snapshot=snapshot_bytes,
            results=result_files,
        )

    @classmethod
    def _read_archive(cls, payload: bytes) -> dict[str, bytes]:
        if not isinstance(payload, bytes) or not payload:
            raise ValueError("Portable bundle must be non-empty bytes.")
        if len(payload) > MAX_PORTFOLIO_BUNDLE_BYTES:
            raise ValueError("Portable bundle exceeds the size limit.")
        try:
            with ZipFile(BytesIO(payload)) as bundle:
                infos = bundle.infolist()
                if not infos or len(infos) > MAX_PORTFOLIO_BUNDLE_MEMBERS + 1:
                    raise ValueError("Portable bundle contains an invalid number of files.")
                names = [info.filename for info in infos]
                if len(names) != len(set(names)):
                    raise ValueError("Portable bundle contains duplicate file names.")
                if any(
                    info.is_dir()
                    or info.flag_bits & 0x1
                    or info.compress_type not in {0, ZIP_DEFLATED}
                    or not cls._safe_member_path(info.filename)
                    for info in infos
                ):
                    raise ValueError("Portable bundle contains an unsafe archive member.")
                if sum(info.file_size for info in infos) > MAX_PORTFOLIO_BUNDLE_BYTES:
                    raise ValueError("Portable bundle expands beyond the size limit.")
                return {info.filename: bundle.read(info) for info in infos}
        except BadZipFile as exc:
            raise ValueError("Portable bundle is not a valid ZIP archive.") from exc

    @classmethod
    def _manifest(cls, raw: bytes) -> dict[str, Any]:
        manifest = cls._json_object(raw, "Bundle manifest")
        if set(manifest) != {
            "format",
            "format_version",
            "name",
            "portfolio_created_at",
            "members",
        }:
            raise ValueError("Portable bundle manifest fields are invalid.")
        if manifest.get("format") != _FORMAT:
            raise ValueError("File is not a RING-5 portable bundle.")
        if manifest.get("format_version") != _FORMAT_VERSION:
            raise ValueError(
                f"Unsupported portable bundle version {manifest.get('format_version')!r}."
            )
        if not isinstance(manifest.get("members"), list):
            raise ValueError("Portable bundle manifest members must be an array.")
        return manifest

    @classmethod
    def _artifacts(
        cls,
        manifest: Mapping[str, Any],
        archive: Mapping[str, bytes],
    ) -> tuple[PortfolioBundleArtifact, ...]:
        records = cast(list[Any], manifest["members"])
        if not 1 <= len(records) <= MAX_PORTFOLIO_BUNDLE_MEMBERS:
            raise ValueError("Portable bundle manifest has an invalid member count.")
        artifacts: list[PortfolioBundleArtifact] = []
        seen: set[str] = set()
        for record in records:
            if not isinstance(record, Mapping) or set(record) != {
                "path",
                "role",
                "media_type",
                "size_bytes",
                "sha256",
            }:
                raise ValueError("Portable bundle artifact metadata is invalid.")
            path = record.get("path")
            role = record.get("role")
            media_type = record.get("media_type")
            size_bytes = record.get("size_bytes")
            digest = record.get("sha256")
            if (
                not isinstance(path, str)
                or path in seen
                or not cls._safe_member_path(path)
                or path == _MANIFEST_MEMBER
                or role not in _ROLES
                or not isinstance(media_type, str)
                or not media_type
                or isinstance(size_bytes, bool)
                or not isinstance(size_bytes, int)
                or size_bytes < 0
                or not cls._digest(digest)
            ):
                raise ValueError("Portable bundle artifact metadata is invalid.")
            fixed_paths = {
                "portfolio": _PORTFOLIO_MEMBER,
                "source-manifest": _SOURCE_MEMBER,
                "environment-metadata": _ENVIRONMENT_MEMBER,
                "python-requirements": _REQUIREMENTS_MEMBER,
            }
            if role in fixed_paths and path != fixed_paths[cast(str, role)]:
                raise ValueError("Portable bundle required artifact path is invalid.")
            if role == "dataset-snapshot" and path != _SNAPSHOT_MEMBER:
                raise ValueError("Portable bundle dataset snapshot path is invalid.")
            if role == "result" and not path.startswith("results/"):
                raise ValueError("Portable bundle result path is invalid.")
            data = archive.get(path)
            if data is None or len(data) != size_bytes:
                raise ValueError(f"Portable bundle member {path!r} has the wrong size.")
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError(f"Portable bundle member {path!r} failed its checksum.")
            seen.add(path)
            artifacts.append(
                PortfolioBundleArtifact(
                    path=path,
                    role=cast(PortfolioBundleArtifactRole, role),
                    size_bytes=size_bytes,
                    sha256=digest,
                    media_type=media_type,
                )
            )
        if set(archive) != {_MANIFEST_MEMBER, *seen}:
            raise ValueError("Portable bundle contains undeclared or missing files.")
        return tuple(sorted(artifacts, key=lambda item: item.path))

    @staticmethod
    def _source_manifest(portfolio: Mapping[str, Any]) -> dict[str, Any]:
        sources: list[dict[str, Any]] = []
        if portfolio.get("use_parser"):
            if portfolio.get("stats_path"):
                sources.append(
                    {
                        "kind": "simulator-statistics",
                        "location": portfolio.get("stats_path"),
                        "pattern": portfolio.get("stats_pattern"),
                    }
                )
        elif portfolio.get("csv_path"):
            sources.append({"kind": "csv", "location": portfolio.get("csv_path")})
        data_csv = portfolio.get("data_csv")
        embedded_digest = (
            hashlib.sha256(data_csv.encode("utf-8")).hexdigest()
            if isinstance(data_csv, str)
            else None
        )
        return {
            "format": "ring5.source-manifest",
            "format_version": 1,
            "sources": sources,
            "embedded_data_sha256": embedded_digest,
            "parse_variables": portfolio.get("parse_variables", []),
        }

    @staticmethod
    def _requirements(environment: object) -> str:
        if not isinstance(environment, Mapping):
            return "# Environment metadata was not recorded.\n"
        dependencies = environment.get("dependencies")
        versions = dependencies if isinstance(dependencies, Mapping) else {}
        lines = ["# Captured Python package versions"]
        ring5_version = environment.get("ring5_version")
        if isinstance(ring5_version, str) and ring5_version:
            lines.append(f"ring5=={ring5_version}")
        for raw_name, raw_version in sorted(versions.items(), key=lambda item: str(item[0])):
            if isinstance(raw_name, str) and isinstance(raw_version, str) and raw_version:
                if raw_name.lower() != "ring5":
                    lines.append(f"{raw_name}=={raw_version}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _environment(value: object) -> dict[str, Any] | None:
        recorded = EnvironmentMetadataService.from_payload(value)
        if recorded is None:
            return None
        normalized = recorded.to_dict()
        if value != normalized:
            raise ValueError("Portfolio environment metadata has unexpected fields.")
        return normalized

    @staticmethod
    def _json_value(raw: bytes, label: str) -> Any:
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{label} must be valid UTF-8 JSON.") from exc

    @classmethod
    def _json_object(cls, raw: bytes, label: str) -> dict[str, Any]:
        value = cls._json_value(raw, label)
        if not isinstance(value, dict):
            raise ValueError(f"{label} must contain one JSON object.")
        return cast(dict[str, Any], value)

    @staticmethod
    def _json_bytes(value: object, *, indent: int) -> bytes:
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                indent=indent,
                sort_keys=True,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Portable bundle metadata is not valid JSON: {exc}") from exc

    @staticmethod
    def _zip_bytes(members: Mapping[str, bytes]) -> bytes:
        output = BytesIO()
        with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=6) as bundle:
            for name, data in sorted(members.items()):
                info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                bundle.writestr(info, data)
        payload = output.getvalue()
        if len(payload) > MAX_PORTFOLIO_BUNDLE_BYTES:
            raise ValueError("Compressed portable bundle exceeds the size limit.")
        return payload

    @staticmethod
    def _safe_member_path(value: object) -> bool:
        if not isinstance(value, str) or not value or len(value) > 255 or "\\" in value:
            return False
        path = PurePosixPath(value)
        return (
            not path.is_absolute()
            and all(part not in {"", ".", ".."} for part in path.parts)
            and any(path.parts)
        )

    @classmethod
    def _safe_result_name(cls, value: object) -> str:
        if (
            not isinstance(value, str)
            or not cls._safe_member_path(value)
            or len(f"results/{value}") > 255
        ):
            raise ValueError("Bundle result names must be safe relative POSIX paths.")
        if value.startswith("results/"):
            raise ValueError("Bundle result names are relative to the results directory.")
        return value

    @staticmethod
    def _bounded_name(value: object, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} name must be non-empty text.")
        resolved = value.strip()
        if len(resolved) > 120 or any(ord(character) < 32 for character in resolved):
            raise ValueError(f"{label} name is too long or contains control characters.")
        return resolved

    @staticmethod
    def _digest(value: object) -> bool:
        return (
            isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
        )
