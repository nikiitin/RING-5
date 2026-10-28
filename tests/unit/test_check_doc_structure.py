"""Tests for documentation structure and link validation."""

from pathlib import Path

from scripts import check_doc_links
from scripts.check_doc_structure import validate_structure
from scripts.documentation import DOCS_ROOT, load_pages


def _write_page(root: Path, relative: str, front_matter: str) -> None:
    """Write a minimal published page below a temporary docs root."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{front_matter}\n---\n\n# Page\n", encoding="utf-8")


def test_valid_navigation() -> None:
    """A rooted hierarchy with one canonical route per page is valid."""
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
            "layout: default\ntitle: Task\nparent: Guide\npermalink: /guide/task/",
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


def test_redirects_are_rejected(tmp_path: Path) -> None:
    """Every published page has exactly one current route."""
    _write_page(
        tmp_path,
        "one.md",
        "layout: default\ntitle: One\npermalink: /one/\n" "redirect_from:\n  - /retired/",
    )

    assert any("redirect_from is unsupported" in item for item in validate_structure(tmp_path))


def test_repository_links_resolve_current_paths() -> None:
    """Source links resolve to current routes and existing repository files."""
    pages, failures = load_pages(DOCS_ROOT)
    assert failures == []
    assert "/user-guide/getting-started/concepts/" in {page.route for page in pages}
    assert check_doc_links.collect_failures() == []


def test_retired_repository_path_is_not_a_route_exemption(tmp_path: Path, monkeypatch) -> None:
    """A missing repository path cannot pass merely because it once had a route."""
    page = tmp_path / "README.md"
    page.write_text("`docs/engineering-reference/architecture/`\n")
    monkeypatch.setattr(check_doc_links, "ROOT", tmp_path)
    monkeypatch.setattr(check_doc_links, "DOC_ROOTS", (page,))
    assert any("missing repository path" in item for item in check_doc_links.collect_failures())
