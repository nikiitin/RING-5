"""Models for recording and comparing reproducibility environments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

EnvironmentMatchStatus = Literal["match", "changed", "unavailable", "not-recorded"]


def _bounded_text(value: object, field_name: str) -> str:
    """Validate one bounded, human-readable metadata value."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Environment metadata field {field_name!r} must be text.")
    cleaned = " ".join(value.split())
    if len(cleaned) > 500:
        raise ValueError(f"Environment metadata field {field_name!r} is too long.")
    return cleaned


def _version_mapping(value: object, field_name: str) -> dict[str, str | None]:
    """Validate and normalize a version mapping from untrusted JSON."""
    if not isinstance(value, Mapping) or len(value) > 128:
        raise ValueError(f"Environment metadata field {field_name!r} must be a bounded object.")
    result: dict[str, str | None] = {}
    for raw_name, raw_version in value.items():
        name = _bounded_text(raw_name, f"{field_name} key")
        if len(name) > 100:
            raise ValueError(f"Environment metadata field {field_name!r} has an overlong key.")
        result[name] = (
            None if raw_version is None else _bounded_text(raw_version, f"{field_name}.{name}")
        )
    return dict(sorted(result.items()))


@dataclass(frozen=True)
class EnvironmentMetadata:
    # [impl->req~ring5.portfolio.environment-metadata~1]
    """Version information captured with a saved analysis.

    The payload deliberately excludes usernames, hostnames, executable paths,
    and environment variables. Those details are unnecessary for comparing
    runtimes and can disclose private machine information.

    Attributes:
        format_version: Version of this metadata document.
        ring5_version: Installed RING-5 package version.
        python_version: Python language runtime version.
        python_implementation: Python implementation name.
        operating_system: Operating-system name and release.
        architecture: Machine architecture reported by Python.
        dependencies: Direct Python dependency versions.
        renderers: Versions of the supported rendering engines.
        external_tools: Versions of optional external executables, or ``None``
            when a tool was unavailable at capture time.
    """

    format_version: int
    ring5_version: str
    python_version: str
    python_implementation: str
    operating_system: str
    architecture: str
    dependencies: dict[str, str | None] = field(default_factory=dict)
    renderers: dict[str, str | None] = field(default_factory=dict)
    external_tools: dict[str, str | None] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation.

        Returns:
            Environment metadata with deterministically ordered mappings.
        """
        return {
            "format_version": self.format_version,
            "ring5_version": self.ring5_version,
            "python_version": self.python_version,
            "python_implementation": self.python_implementation,
            "operating_system": self.operating_system,
            "architecture": self.architecture,
            "dependencies": dict(sorted(self.dependencies.items())),
            "renderers": dict(sorted(self.renderers.items())),
            "external_tools": dict(sorted(self.external_tools.items())),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EnvironmentMetadata":
        """Build metadata from an untrusted portfolio payload.

        Args:
            value: JSON mapping to validate.

        Returns:
            Validated environment metadata.

        Raises:
            ValueError: The payload has an unsupported version or malformed field.
        """
        format_version = value.get("format_version")
        if isinstance(format_version, bool) or format_version != 1:
            raise ValueError(
                f"Unsupported environment metadata version {format_version!r}; expected 1."
            )
        return cls(
            format_version=1,
            ring5_version=_bounded_text(value.get("ring5_version"), "ring5_version"),
            python_version=_bounded_text(value.get("python_version"), "python_version"),
            python_implementation=_bounded_text(
                value.get("python_implementation"), "python_implementation"
            ),
            operating_system=_bounded_text(value.get("operating_system"), "operating_system"),
            architecture=_bounded_text(value.get("architecture"), "architecture"),
            dependencies=_version_mapping(value.get("dependencies"), "dependencies"),
            renderers=_version_mapping(value.get("renderers"), "renderers"),
            external_tools=_version_mapping(value.get("external_tools"), "external_tools"),
        )


@dataclass(frozen=True)
class EnvironmentDifference:
    """One saved-versus-current environment comparison row."""

    section: str
    component: str
    recorded: str | None
    current: str | None
    status: EnvironmentMatchStatus


@dataclass(frozen=True)
class EnvironmentComparison:
    """Human-readable comparison between recorded and current environments."""

    recorded: EnvironmentMetadata | None
    current: EnvironmentMetadata
    differences: tuple[EnvironmentDifference, ...]

    @property
    def recorded_available(self) -> bool:
        """Whether the portfolio contains save-time environment metadata."""
        return self.recorded is not None

    @property
    def exact_match(self) -> bool:
        """Whether every recorded value exactly matches the current runtime."""
        return self.recorded is not None and all(
            item.status in {"match", "unavailable"} for item in self.differences
        )

    @property
    def changed_count(self) -> int:
        """Return the number of values that differ from the saved runtime."""
        return sum(item.status == "changed" for item in self.differences)

    @property
    def review_count(self) -> int:
        """Return the number of changed or absent saved values to review."""
        return sum(item.status in {"changed", "not-recorded"} for item in self.differences)
