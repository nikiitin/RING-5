"""Tests for documentation structure and link validation."""

from pathlib import Path

from scripts import check_doc_links
from scripts.check_doc_structure import validate_structure


def _write_page(root: Path, relative: str, front_matter: str) -> None:
    """Write a minimal published page below a temporary docs root."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{front_matter}\n---\n\n# Page\n", encoding="utf-8")


def test_valid_navigation_and_redirects() -> None:
    """A rooted hierarchy with one retired route is valid."""
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as directory:
        root = Path(directory)
        _write_page(root, "index.md", "layout: default\ntitle: Home\npermalink: /")
        _write_page(
            root,
            "guide/index.md",
            "layout: default\ntitle: Guide\npermalink: /guide/\nhas_children: true",
        )
        _write_page(
            root,
            "guide/task.md",
            "layout: default\ntitle: Task\nparent: Guide\npermalink: /guide/task/\n"
            "redirect_from:\n  - /old-task/",
        )

        assert validate_structure(root) == []


def test_required_front_matter_and_unique_routes() -> None:
    """Missing fields and duplicate canonical routes are reported."""
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as directory:
        root = Path(directory)
        _write_page(root, "one.md", "layout: default\ntitle: One\npermalink: /same/")
        _write_page(root, "two.md", "layout: default\ntitle: Two\npermalink: /same/")
        _write_page(root, "missing.md", "layout: default\ntitle: Missing")

        failures = validate_structure(root)

    assert any("missing required front matter: permalink" in failure for failure in failures)
    assert any("duplicate route '/same/'" in failure for failure in failures)


def test_parent_and_grandparent_relationships() -> None:
    """Parents must exist, own children, and match the declared grandparent."""
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as directory:
        root = Path(directory)
        _write_page(root, "root.md", "layout: default\ntitle: Root\npermalink: /root/")
        _write_page(
            root,
            "child.md",
            "layout: default\ntitle: Child\nparent: Root\n"
            "grand_parent: Wrong\npermalink: /root/child/",
        )
        _write_page(
            root,
            "orphan.md",
            "layout: default\ntitle: Orphan\nparent: Missing\npermalink: /orphan/",
        )

        failures = validate_structure(root)

    assert any("does not set has_children: true" in failure for failure in failures)
    assert any("grand_parent 'Wrong' does not match" in failure for failure in failures)
    assert any("unknown parent 'Missing'" in failure for failure in failures)


def test_redirects_are_unique_and_do_not_shadow_pages() -> None:
    """Redirect sources cannot be duplicated or replace a canonical route."""
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as directory:
        root = Path(directory)
        _write_page(
            root,
            "one.md",
            "layout: default\ntitle: One\npermalink: /one/\n"
            "redirect_from:\n  - /retired/\n  - /two/",
        )
        _write_page(
            root,
            "two.md",
            "layout: default\ntitle: Two\npermalink: /two/\n" "redirect_from:\n  - /retired/",
        )

        failures = validate_structure(root)

    assert any("redirect '/two/' conflicts" in failure for failure in failures)
    assert any("duplicate redirect '/retired/'" in failure for failure in failures)


def test_repository_links_and_retired_paths_are_valid() -> None:
    """The repository-wide link validator accepts only resolved current or redirected paths."""
    assert "docs/engineering-reference/architecture" in (
        check_doc_links.redirected_documentation_paths()
    )
    assert "/user-guide/getting-started/concepts/" in (
        check_doc_links.published_documentation_routes()
    )
    assert check_doc_links.collect_failures() == []
