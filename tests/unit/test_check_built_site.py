"""Tests for generated documentation-site auditing."""

from pathlib import Path

from scripts.check_built_site import ReferenceParser, collect_failures, route_output


def _page(path: Path, *, route: str, redirect: str | None = None) -> None:
    redirects = f"\nredirect_from:\n  - {redirect}" if redirect else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "layout: default\n"
        f"title: {path.stem}\n"
        f"permalink: {route}"
        f"{redirects}\n"
        "---\n\n"
        "# Page\n"
    )


def test_reference_parser_collects_links_and_assets() -> None:
    parser = ReferenceParser()
    parser.feed('<a href="/RING-5/guide/">Guide</a><img src="../assets/logo.svg">')

    assert parser.references == ["/RING-5/guide/", "../assets/logo.svg"]


def test_route_output_uses_pretty_index_path(tmp_path: Path) -> None:
    assert route_output(tmp_path, "/guide/start/") == tmp_path / "guide/start/index.html"


def test_audit_accepts_canonical_redirect_and_local_asset(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    site = tmp_path / "_site"
    _page(docs / "index.md", route="/", redirect="/old/")
    (site / "old").mkdir(parents=True)
    (site / "old/index.html").write_text('<a href="/RING-5/">Home</a>')
    (site / "assets").mkdir()
    (site / "assets/logo.svg").write_text("<svg></svg>")
    (site / "index.html").write_text('<img src="/RING-5/assets/logo.svg">')

    assert collect_failures(site, docs) == []


def test_audit_reports_missing_route_and_reference(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    site = tmp_path / "_site"
    _page(docs / "guide.md", route="/guide/")
    site.mkdir()
    (site / "index.html").write_text('<a href="/RING-5/missing/">Missing</a>')

    failures = collect_failures(site, docs)

    assert any("generated route '/guide/' is missing" in failure for failure in failures)
    assert any("broken generated reference" in failure for failure in failures)


def test_audit_rejects_reference_that_escapes_generated_site(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    site = tmp_path / "_site"
    _page(docs / "index.md", route="/")
    site.mkdir()
    (tmp_path / "outside.txt").write_text("exists, but will not be deployed")
    (site / "index.html").write_text('<a href="../outside.txt">Outside</a>')

    failures = collect_failures(site, docs)

    assert any("broken generated reference '../outside.txt'" in failure for failure in failures)
