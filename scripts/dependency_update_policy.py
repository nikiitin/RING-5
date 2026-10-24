"""Classify dependency-only changes without running repository or package code."""

from __future__ import annotations

import copy
import re
import tomllib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class VersionChange:
    """One stable release change and, for Actions, its immutable provenance.

    ``previous`` and ``current`` contain numeric release versions. Action refs
    are commit SHAs; tags retain the exact spelling used in version comments.
    """

    ecosystem: str
    name: str
    previous: str
    current: str
    action_repository: str | None = None
    previous_ref: str | None = None
    new_ref: str | None = None
    previous_tag: str | None = None
    new_tag: str | None = None


@dataclass(frozen=True)
class PolicyDecision:
    """Eligibility, concrete blockers, and all detected release changes."""

    eligible: bool
    reasons: tuple[str, ...]
    updates: tuple[VersionChange, ...]


_VERSION = re.compile(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){0,7}\Z")
_REQUIREMENT = re.compile(
    r"(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[A-Za-z0-9_, .-]+\])?"
    r"\s*(?P<operator>===|~=|==|!=|<=|>=|<|>)\s*(?P<version>[^,;\s]+)(?:\s*;[^\n]+)?\Z"
)
_GEM = re.compile(
    r"\s*gem\s+['\"](?P<name>[A-Za-z0-9_.-]+)['\"],\s*"
    r"['\"](?P<constraint>(?:~>|>=|<=|!=|=|>|<)?\s*(?P<version>[^'\"\s]+))['\"]\s*(?:#.*)?\Z"
)
_SPEC = re.compile(r"    (?P<name>[A-Za-z0-9_.-]+) \((?P<version>[^)]+)\)\Z")
_GEM_DEPENDENCY = re.compile(
    r"(?P<indent>  |      )(?P<name>[A-Za-z0-9_.-]+)(?: \((?P<constraint>[^)]+)\))?\Z"
)
_USES = re.compile(
    r"(?P<prefix>\s*(?:-\s*)?uses:\s*)"
    r"(?P<action>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)"
    r"@(?P<sha>[0-9a-f]{40})(?P<separator>\s+#\s*)"
    r"(?P<tag>v?[0-9]+(?:\.[0-9]+){1,7})(?P<tail>\s*)\Z"
)
_WORKFLOWS = {
    ".github/workflows/ci.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/pages.yml",
}
_PATHS = _WORKFLOWS | {"pyproject.toml", "uv.lock", "Gemfile", "Gemfile.lock"}
_PACKAGE_KEYS = {
    "name",
    "version",
    "source",
    "dependencies",
    "optional-dependencies",
    "sdist",
    "wheels",
    "metadata",
    "default-groups",
}


def _name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _release(value: str) -> tuple[int, ...]:
    if not isinstance(value, str) or len(value) > 100 or not _VERSION.fullmatch(value):
        raise ValueError(f"Unknown or non-stable version: {str(value)[:120]!r}")
    return tuple(int(part) for part in value.split("."))


def _ordered(value: str) -> tuple[int, ...]:
    parts = _release(value)
    return parts + (0,) * (8 - len(parts))


def _satisfies(version: str, operator: str, required: str) -> bool:
    actual, floor = _ordered(version), _ordered(required)
    if operator == "===":
        return version == required
    if operator in {"~=", "~>"}:
        upper = list(_release(required))
        if operator == "~=" and len(upper) < 2:
            raise ValueError("Compatible Python requirements need two release components.")
        index = max(0, len(upper) - 2)
        upper[index] += 1
        upper[index + 1 :] = [0] * (len(upper) - index - 1)
        return floor <= actual < tuple(upper) + (0,) * (8 - len(upper))
    return {
        "==": actual == floor,
        "=": actual == floor,
        "!=": actual != floor,
        ">=": actual >= floor,
        "<=": actual <= floor,
        ">": actual > floor,
        "<": actual < floor,
    }[operator]


def _requirement(value: str) -> tuple[str, str, str]:
    match = _REQUIREMENT.fullmatch(value)
    if match is None:
        raise ValueError(f"Unsupported requirement declaration: {value[:160]!r}")
    version = match["version"]
    _release(version)
    start, end = match.span("version")
    return _name(match["name"]), version, value[:start] + "{version}" + value[end:]


class _Assessment:
    def __init__(self, allow_major: bool) -> None:
        self.allow_major = allow_major
        self.reasons: list[str] = []
        self.updates: list[VersionChange] = []
        self.requirement_rules: dict[str, tuple[str, str]] = {}
        self.gem_requirements: dict[str, str] | None = None

    def block(self, reason: str) -> None:
        """Record one unique reason that prevents automatic merging."""
        if reason not in self.reasons:
            self.reasons.append(reason)

    def version(self, update: VersionChange) -> None:
        """Record a release change and enforce downgrade and breaking-change policy."""
        old, new = _ordered(update.previous), _ordered(update.current)
        if new == old:
            if update.previous != update.current:
                self.block(f"{update.name}: equivalent version spellings require review.")
            return
        if update not in self.updates:
            self.updates.append(update)
        if new < old:
            self.block(f"{update.name}: version downgrade requires review.")
        elif not self.allow_major and (new[0] != old[0] or old[0] == 0 and new[1] != old[1]):
            self.block(f"{update.name}: major or 0.x minor update requires review.")

    def project(self, text: str) -> tuple[dict[str, Any], dict[str, str]]:
        """Return version-masked project settings and named release declarations."""
        document = tomllib.loads(text)
        snapshot = copy.deepcopy(document)
        containers = [snapshot.get("project", {}).get("dependencies", [])]
        extras = snapshot.get("project", {}).get("optional-dependencies", {})
        if not isinstance(extras, dict):
            raise ValueError("Unsupported optional-dependencies structure.")
        containers.extend(extras.values())
        containers.append(snapshot.get("build-system", {}).get("requires", []))
        declarations: dict[str, str] = {}
        for container in containers:
            if not isinstance(container, list):
                raise ValueError("Requirement declarations must be lists.")
            for index, value in enumerate(container):
                if not isinstance(value, str):
                    raise ValueError("Requirement declarations must be strings.")
                name, version, template = _requirement(value)
                if name in declarations:
                    raise ValueError(f"Duplicate dependency declaration: {name}")
                declarations[name] = version
                container[index] = template
        return snapshot, declarations

    def projects(self, before: str, after: str) -> dict[str, str]:
        """Compare project policy and collect existing requirement version changes."""
        old_shape, old = self.project(before)
        new_shape, new = self.project(after)
        if old_shape != new_shape or old.keys() != new.keys():
            self.block("pyproject.toml: only versions of existing requirements may change.")
        for name in sorted(old.keys() & new.keys()):
            self.version(VersionChange("uv", name, old[name], new[name]))
        document = tomllib.loads(after)
        containers = [document.get("project", {}).get("dependencies", [])]
        containers.extend(document.get("project", {}).get("optional-dependencies", {}).values())
        for container in containers:
            for declaration in container:
                match = _REQUIREMENT.fullmatch(declaration)
                if match is not None:
                    self.requirement_rules[_name(match["name"])] = (
                        match["operator"],
                        match["version"],
                    )
        return new

    def artifact(self, item: Any, name: str, version: str) -> None:
        """Validate a hashed release artifact from the trusted PyPI file host."""
        if not isinstance(item, dict) or not {"url", "hash", "size"} <= item.keys():
            raise ValueError(f"{name}: incomplete locked artifact.")
        if item.keys() - {"url", "hash", "size", "upload-time"}:
            raise ValueError(f"{name}: unknown artifact schema.")
        if not isinstance(item["url"], str) or not isinstance(item["hash"], str):
            raise ValueError(f"{name}: invalid artifact URL or hash.")
        url = urlsplit(item["url"])
        if (
            url.scheme != "https"
            or url.netloc != "files.pythonhosted.org"
            or url.query
            or url.fragment
            or not url.path.startswith("/packages/")
            or unquote(url.path) != url.path
            or ".." in PurePosixPath(url.path).parts
        ):
            raise ValueError(f"{name}: artifact must use the trusted PyPI host.")
        filename = PurePosixPath(url.path).name
        delimiter = "-" + version
        prefix, found, suffix = filename.partition(delimiter)
        if (
            not found
            or _name(prefix) != name
            or not (
                suffix.startswith("-")
                and suffix.endswith(".whl")
                or suffix in {".tar.gz", ".zip", ".tar.bz2", ".tar.xz"}
            )
        ):
            raise ValueError(f"{name}: artifact filename does not identify the locked release.")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", item["hash"]):
            raise ValueError(f"{name}: artifact requires a SHA-256 digest.")
        if type(item["size"]) is not int or item["size"] <= 0:
            raise ValueError(f"{name}: invalid artifact size.")
        if "upload-time" in item and not isinstance(item["upload-time"], str):
            raise ValueError(f"{name}: invalid artifact timestamp.")

    def packages(self, document: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Validate supported uv package records and index their normalized names."""
        if document.keys() - {
            "version",
            "revision",
            "requires-python",
            "resolution-markers",
            "package",
        }:
            raise ValueError("uv.lock: unknown root schema.")
        if (
            type(document.get("version")) is not int
            or document.get("version") != 1
            or document.get("revision") != 5
        ):
            raise ValueError("uv.lock: unsupported lock schema version.")
        if (
            not isinstance(document.get("requires-python"), str)
            or not isinstance(document.get("resolution-markers", []), list)
            or any(not isinstance(marker, str) for marker in document.get("resolution-markers", []))
        ):
            raise ValueError("uv.lock: unsupported runtime/resolution schema.")
        if not isinstance(document.get("package"), list):
            raise ValueError("uv.lock: missing package list.")
        packages: dict[str, dict[str, Any]] = {}
        for package in document["package"]:
            if not isinstance(package, dict) or package.keys() - _PACKAGE_KEYS:
                raise ValueError("uv.lock: unknown package schema.")
            name, version = package.get("name"), package.get("version")
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
                raise ValueError("uv.lock: invalid package name.")
            name = _name(name)
            if not isinstance(version, str):
                raise ValueError(f"{name}: missing locked version.")
            _release(version)
            if name in packages:
                raise ValueError(f"uv.lock: ambiguous repeated package: {name}")
            source = package.get("source")
            if source == {"editable": "."}:
                if name != "ring5":
                    raise ValueError("uv.lock: unexpected local package.")
            elif source == {"registry": "https://pypi.org/simple"}:
                artifacts = package.get("wheels", [])
                if not isinstance(artifacts, list):
                    raise ValueError(f"{name}: invalid wheel list.")
                if "sdist" in package:
                    artifacts = [package["sdist"], *artifacts]
                if not artifacts:
                    raise ValueError(f"{name}: no locked release artifacts.")
                for artifact in artifacts:
                    self.artifact(artifact, name, version)
            else:
                raise ValueError(
                    f"{name}: only PyPI registry and the unchanged local project are allowed."
                )
            for group in [
                package.get("dependencies", []),
                *package.get("optional-dependencies", {}).values(),
            ]:
                if not isinstance(group, list) or any(
                    not isinstance(dep, dict)
                    or dep.keys() - {"name", "marker", "extra"}
                    or not isinstance(dep.get("name"), str)
                    or any(not isinstance(v, str) for k, v in dep.items() if k != "extra")
                    or (
                        "extra" in dep
                        and (
                            not isinstance(dep["extra"], list)
                            or any(not isinstance(v, str) for v in dep["extra"])
                        )
                    )
                    for dep in group
                ):
                    raise ValueError(f"{name}: unknown dependency-edge schema.")
            packages[name] = package
        for package in packages.values():
            groups = [
                package.get("dependencies", []),
                *package.get("optional-dependencies", {}).values(),
            ]
            if any(_name(dep["name"]) not in packages for group in groups for dep in group):
                raise ValueError("uv.lock: dependency edge has no locked package.")
        return packages

    def lock(self, before: str, after: str, project: dict[str, str] | None) -> None:
        """Check lock invariants and agreement between declared and locked releases."""
        old_doc, new_doc = tomllib.loads(before), tomllib.loads(after)
        old, new = self.packages(old_doc), self.packages(new_doc)
        if {k: v for k, v in old_doc.items() if k != "package"} != {
            k: v for k, v in new_doc.items() if k != "package"
        }:
            self.block("uv.lock: runtime, resolution or lock settings changed.")
        if old.keys() != new.keys():
            self.block("uv.lock: dependency additions/removals require review.")
        for name in sorted(old.keys() & new.keys()):
            a, b = old[name], new[name]
            if a == b:
                continue
            if a["source"] != b["source"]:
                self.block(f"{name}: locked source changed.")
            if a["source"] == {"editable": "."}:
                aa, bb = copy.deepcopy(a), copy.deepcopy(b)
                for package in (aa, bb):
                    metadata = package.get("metadata", {})
                    if metadata.keys() - {"requires-dist", "provides-extras"}:
                        raise ValueError("uv.lock: unknown local metadata schema.")
                    for req in metadata.get("requires-dist", []):
                        if not isinstance(req, dict) or req.keys() - {
                            "name",
                            "specifier",
                            "extras",
                            "marker",
                        }:
                            raise ValueError("uv.lock: unknown local requirement schema.")
                        if "specifier" in req:
                            req_name, version, template = _requirement(
                                req["name"] + req["specifier"]
                            )
                            if package is bb and (
                                project is None or project.get(req_name) != version
                            ):
                                self.block(
                                    "uv.lock: local requirements changed without "
                                    "matching pyproject versions."
                                )
                            req["specifier"] = template
                if aa != bb:
                    self.block("uv.lock: local project settings changed.")
            elif a["version"] == b["version"]:
                self.block(
                    f"{name}: source, artifacts or metadata changed without a release update."
                )
            else:
                invariant = {"name", "source", "metadata", "default-groups"}
                if {k: a.get(k) for k in invariant} != {k: b.get(k) for k in invariant}:
                    self.block(f"{name}: package policy or metadata changed.")
                self.version(VersionChange("uv", name, a["version"], b["version"]))
        rules = dict(self.requirement_rules)
        for package in new.values():
            if package["source"] == {"editable": "."}:
                for req in package.get("metadata", {}).get("requires-dist", []):
                    if "specifier" in req:
                        declaration = req["name"] + req["specifier"]
                        name, version, _ = _requirement(declaration)
                        match = _REQUIREMENT.fullmatch(declaration)
                        if match is not None:
                            if project is not None and self.requirement_rules.get(name) != (
                                match["operator"],
                                version,
                            ):
                                self.block(
                                    "uv.lock: local metadata does not match pyproject requirements."
                                )
                            rules[name] = (match["operator"], version)
        for name, (operator, version) in rules.items():
            if name not in new or not _satisfies(new[name]["version"], operator, version):
                self.block(f"{name}: locked version does not satisfy its declared requirement.")

    def gemfile(self, before: str, after: str) -> None:
        """Permit only literal versions in existing gem declarations."""
        old, new = before.splitlines(), after.splitlines()
        self.gem_requirements = {}
        for line in new:
            match = _GEM.fullmatch(line)
            if match is not None:
                if match["name"] in self.gem_requirements:
                    raise ValueError("Gemfile: duplicate gem declaration.")
                self.gem_requirements[match["name"]] = match["constraint"]
        if len(old) != len(new):
            self.block("Gemfile: dependency additions/removals or source changes require review.")
            return
        for a, b in zip(old, new):
            if a == b:
                continue
            left, right = _GEM.fullmatch(a), _GEM.fullmatch(b)
            if not left or not right:
                self.block(
                    "Gemfile: only literal versions of existing gem declarations may change."
                )
                continue
            sa, ea = left.span("version")
            sb, eb = right.span("version")
            if a[:sa] + "{version}" + a[ea:] != b[:sb] + "{version}" + b[eb:]:
                self.block(
                    "Gemfile: dependency identity, constraints or executable settings changed."
                )
            self.version(VersionChange("bundler", left["name"], left["version"], right["version"]))

    def gemlock(self, before: str, after: str, manifest_changed: bool) -> None:
        """Classify locked gems while preserving source, platform and runtime policy."""
        old, new = before.splitlines(), after.splitlines()
        if len(old) != len(new):
            self.block("Gemfile.lock: package/platform additions or removals require review.")
            return
        headers = {line for line in old + new if line and not line[0].isspace()}
        if headers - {"GEM", "PLATFORMS", "DEPENDENCIES", "BUNDLED WITH", "RUBY VERSION"}:
            raise ValueError("Gemfile.lock: GIT/PATH or unknown lock schema.")
        required_headers = ["GEM", "PLATFORMS", "DEPENDENCIES", "BUNDLED WITH"]
        for lines in (old, new):
            actual_headers = [line for line in lines if line and not line[0].isspace()]
            if actual_headers not in (
                required_headers,
                required_headers[:-1] + ["RUBY VERSION", "BUNDLED WITH"],
            ):
                raise ValueError("Gemfile.lock: incomplete, duplicated or reordered lock sections.")
        if any(
            [line for line in lines if line.startswith("  remote:")]
            != ["  remote: https://rubygems.org/"]
            for lines in (old, new)
        ):
            raise ValueError("Gemfile.lock: exactly the trusted RubyGems source is required.")
        section, owner_changed = "", False
        platforms: set[str] = set()
        for line in new:
            if line and not line[0].isspace():
                section = line
            elif section == "PLATFORMS" and line.strip():
                platforms.add(line.strip())
        section = ""
        locked_versions: dict[str, str] = {}
        requirements: dict[str, str] = {}
        for a, b in zip(old, new):
            if a and not a[0].isspace():
                section = a
            left, right = _SPEC.fullmatch(a), _SPEC.fullmatch(b)
            if section == "GEM" and left and right:
                old_version, old_platform = self.gem_version(left["version"], platforms)
                new_version, new_platform = self.gem_version(right["version"], platforms)
                if left["name"] != right["name"] or old_platform != new_platform:
                    self.block("Gemfile.lock: gem identities/platforms changed.")
                owner_changed = old_version != new_version
                if (
                    right["name"] in locked_versions
                    and locked_versions[right["name"]] != new_version
                ):
                    raise ValueError("Gemfile.lock: ambiguous versions across platforms.")
                locked_versions[right["name"]] = new_version
                self.version(VersionChange("bundler", left["name"], old_version, new_version))
            elif a != b:
                if (section == "DEPENDENCIES" and manifest_changed) or (
                    section == "GEM" and owner_changed and a.startswith("      ")
                ):
                    left_dep, right_dep = _GEM_DEPENDENCY.fullmatch(a), _GEM_DEPENDENCY.fullmatch(b)
                    if not left_dep or not right_dep or left_dep["name"] != right_dep["name"]:
                        self.block("Gemfile.lock: dependency identities changed.")
                    elif self.constraint_shape(a) != self.constraint_shape(b):
                        self.block("Gemfile.lock: dependency constraint policy changed.")
                else:
                    self.block(
                        "Gemfile.lock: source, platform, runtime, Bundler "
                        "or unchanged gem settings changed."
                    )
            if section == "DEPENDENCIES" and b.startswith("  ") and b.strip():
                requirement = _GEM_DEPENDENCY.fullmatch(b)
                if requirement is None or requirement["constraint"] is None:
                    raise ValueError("Gemfile.lock: unsupported direct gem requirement.")
                if requirement["name"] in requirements:
                    raise ValueError("Gemfile.lock: duplicate direct gem requirement.")
                requirements[requirement["name"]] = requirement["constraint"]
        if manifest_changed and requirements != self.gem_requirements:
            self.block("Gemfile.lock: direct requirements do not match Gemfile.")
        for name, constraint in requirements.items():
            if name not in locked_versions or not self.gem_satisfies(
                locked_versions[name], constraint
            ):
                self.block(f"{name}: locked gem does not satisfy its direct requirement.")

    @staticmethod
    def gem_satisfies(version: str, constraint: str) -> bool:
        """Check a stable gem release against one supported numeric constraint."""
        match = re.fullmatch(
            r"(?P<op>~>|>=|<=|!=|=|>|<)?\s*(?P<version>[0-9]+(?:\.[0-9]+)*)", constraint
        )
        if match is None:
            raise ValueError("Gemfile.lock: unknown direct gem constraint.")
        return _satisfies(version, match["op"] or "=", match["version"])

    @staticmethod
    def constraint_shape(line: str) -> str:
        """Mask constraint versions while retaining dependency names and operators."""
        return re.sub(
            r"(?<![A-Za-z0-9_.-])[0-9]+(?:\.[0-9]+)*(?![A-Za-z0-9_.-])", "{version}", line
        )

    @staticmethod
    def gem_version(value: str, platforms: set[str]) -> tuple[str, str]:
        """Split a stable gem release from its recognized platform suffix."""
        version, separator, platform = value.partition("-")
        _release(version)
        if separator and platform not in platforms:
            raise ValueError(f"Unknown gem platform or prerelease: {value!r}")
        return version, platform

    def workflow(self, before: str, after: str) -> None:
        """Permit only existing Action SHA and release-comment replacements."""
        old, new = before.splitlines(), after.splitlines()
        if len(old) != len(new):
            self.block(
                "Workflow: only immutable Action pin/version-comment replacements are allowed."
            )
            return
        scalar_indent: int | None = None
        steps_indent: int | None = None
        for a, b in zip(old, new):
            indent = len(a) - len(a.lstrip())
            if a.strip() and scalar_indent is not None and indent <= scalar_indent:
                scalar_indent = None
            inside_scalar = scalar_indent is not None
            if re.fullmatch(r"\s*[^#\n]+:\s*[|>][-+0-9]*\s*(?:#.*)?", a):
                scalar_indent = indent
            if not inside_scalar and re.fullmatch(r"\s*steps:\s*", a):
                steps_indent = indent
            elif a.strip() and steps_indent is not None and indent <= steps_indent:
                steps_indent = None
            if a == b:
                continue
            left, right = _USES.fullmatch(a), _USES.fullmatch(b)
            if inside_scalar or steps_indent is None or not left or not right:
                self.block(
                    "Workflow: executable content, structure or non-immutable Action pin changed."
                )
                continue
            if any(left[key] != right[key] for key in ("prefix", "action", "separator", "tail")):
                self.block("Workflow: Action identity or workflow structure changed.")
                continue
            if left["sha"] == right["sha"] or left["tag"] == right["tag"]:
                self.block("Workflow: both release tag and immutable SHA must advance together.")
                continue
            if _ordered(left["tag"].removeprefix("v")) == _ordered(right["tag"].removeprefix("v")):
                self.block("Workflow: a SHA replacement without a release change requires review.")
                continue
            action = left["action"]
            self.version(
                VersionChange(
                    "github-actions",
                    action,
                    left["tag"].removeprefix("v"),
                    right["tag"].removeprefix("v"),
                    "/".join(action.split("/")[:2]),
                    left["sha"],
                    right["sha"],
                    left["tag"],
                    right["tag"],
                )
            )


def assess_changes(
    changes: dict[str, tuple[str, str]], *, allow_major: bool = False
) -> PolicyDecision:
    """Assess fetched base/head file contents under the dependency update policy.

    Args:
        changes: Modified repository paths mapped to their base and head text.
        allow_major: Permit stable major and 0.x minor upgrades explicitly.

    Returns:
        An immutable decision containing detected releases and review blockers.
        Eligibility covers diff policy only; CI, authorship, registry provenance
        and exact-head merge authorization remain the caller's responsibility.
    """
    policy = _Assessment(allow_major)
    if type(allow_major) is not bool:
        policy.block("allow_major must be an explicit boolean policy value.")
    valid: dict[str, tuple[str, str]] = {}
    for path, pair in changes.items():
        if path not in _PATHS:
            policy.block(f"Unsupported dependency-update path: {path}")
        elif (
            not isinstance(pair, tuple)
            or len(pair) != 2
            or any(
                not isinstance(text, str) or len(text) > 8_000_000 or "\x00" in text
                for text in pair
            )
        ):
            policy.block(f"{path}: invalid or oversized fetched file contents.")
        elif pair[0] != pair[1]:
            valid[path] = pair
    project = None
    for path in ("pyproject.toml", "uv.lock", "Gemfile", "Gemfile.lock", *sorted(_WORKFLOWS)):
        if path not in valid:
            continue
        try:
            before, after = valid[path]
            if path == "pyproject.toml":
                project = policy.projects(before, after)
            elif path == "uv.lock":
                policy.lock(before, after, project)
            elif path == "Gemfile":
                policy.gemfile(before, after)
            elif path == "Gemfile.lock":
                policy.gemlock(before, after, "Gemfile" in valid)
            else:
                policy.workflow(before, after)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
            policy.block(f"{path}: {exc}")
    if "pyproject.toml" in valid and "uv.lock" not in valid:
        before_project = tomllib.loads(valid["pyproject.toml"][0]) if project is not None else {}
        build = before_project.get("build-system", {}).get("requires", [])
        build_names = {_requirement(value)[0] for value in build}
        if any(
            update.ecosystem == "uv" and update.name not in build_names for update in policy.updates
        ):
            policy.block(
                "pyproject.toml: application requirement changes need a matching uv.lock update."
            )
    if "Gemfile" in valid and "Gemfile.lock" not in valid:
        policy.block("Gemfile: declaration changes need a matching Gemfile.lock update.")
    if not policy.updates:
        policy.block("No supported release version changes were detected.")
    return PolicyDecision(not policy.reasons, tuple(policy.reasons), tuple(policy.updates))
