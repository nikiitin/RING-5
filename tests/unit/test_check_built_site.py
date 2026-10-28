"""Tests for generated documentation-site auditing."""

from pathlib import Path

import pytest

from scripts.check_built_site import ReferenceParser, collect_failures, route_output


def _page(path: Path, *, route: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "layout: default\n"
        f"title: {path.stem}\n"
        f"permalink: {route}\n"
        "---\n\n"
        "# Page\n" + body
    )


def test_reference_parser_collects_links_and_assets() -> None:
    parser = ReferenceParser()
    parser.feed('<a href="/RING-5/guide/">Guide</a><img src="../assets/logo.svg">')

    assert parser.references == ["/RING-5/guide/", "../assets/logo.svg"]


def test_route_output_uses_pretty_index_path(tmp_path: Path) -> None:
    assert route_output(tmp_path, "/guide/start/") == tmp_path / "guide/start/index.html"


def test_audit_accepts_canonical_route_and_local_asset(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    site = tmp_path / "_site"
    _page(docs / "index.md", route="/")
    site.mkdir()
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


def test_reference_parser_joins_highlighted_code_and_excludes_inline_text() -> None:
    parser = ReferenceParser()
    parser.feed(
        "<p>{{outside}}</p><code>{{inline}}</code>"
        '<pre><code><span class="s">path="&#123;&#123;</span>'
        '<span class="n">input_csv</span><span class="s">&#125;&#125;"</span></code></pre>'
    )

    assert parser.code_blocks == ['path="{{input_csv}}"']


def test_audit_reports_placeholders_lost_from_fenced_examples(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    site = tmp_path / "_site"
    _page(
        docs / "index.md",
        route="/",
        body='```python\npath = "{{input_csv}}"\nthreshold = "{{minimum}}"\n```\n',
    )
    site.mkdir()
    (site / "index.html").write_text('<pre><code>path = ""\nthreshold = ""</code></pre>')

    failures = collect_failures(site, docs)

    assert len(failures) == 2
    assert any("lost 1 occurrence(s) of literal parameter {{input_csv}}" in x for x in failures)
    assert any("lost 1 occurrence(s) of literal parameter {{minimum}}" in x for x in failures)


def test_audit_accepts_highlighted_parameters_and_rendered_dotted_variables(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    site = tmp_path / "_site"
    _page(
        docs / "index.md",
        route="/",
        body='{% raw %}\n```python\npath = "{{ input_csv }}"\n```\n{% endraw %}\n'
        "```text\n{{site.baseurl}}/assets\n```\n",
    )
    site.mkdir()
    (site / "index.html").write_text(
        '<pre><code><span>path = "{{ </span><span>input_csv</span>'
        '<span> }}"</span></code></pre><pre><code>/RING-5/assets</code></pre>'
    )

    assert collect_failures(site, docs) == []


@pytest.mark.parametrize("outside", ["<p>{{input_csv}}</p>", "<code>{{input_csv}}</code>"])
def test_prose_and_inline_code_do_not_mask_missing_fenced_parameters(
    tmp_path: Path, outside: str
) -> None:
    docs = tmp_path / "docs"
    site = tmp_path / "_site"
    _page(docs / "index.md", route="/", body='```python\npath = "{{input_csv}}"\n```\n')
    site.mkdir()
    (site / "index.html").write_text(outside + '<pre><code>path = ""</code></pre>')

    failures = collect_failures(site, docs)

    assert len(failures) == 1
    assert "literal parameter {{input_csv}}" in failures[0]


def test_audit_counts_each_fenced_occurrence_separately(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    site = tmp_path / "_site"
    _page(
        docs / "index.md",
        route="/",
        body="```text\n{{input_csv}} {{input_csv}}\n```\n",
    )
    site.mkdir()
    (site / "index.html").write_text("<pre><code>{{input_csv}}</code></pre><p>{{input_csv}}</p>")

    failures = collect_failures(site, docs)

    assert len(failures) == 1
    assert "lost 1 occurrence(s)" in failures[0]


def test_audit_handles_tilde_and_long_backtick_fences(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    site = tmp_path / "_site"
    _page(
        docs / "index.md",
        route="/",
        body='````python\npath = "{{input_csv}}"\n```\n'
        'threshold = "{{minimum}}"\n````\n'
        '  ~~~json\n{"output": "{{output_dir}}"}\n  ~~~~\n',
    )
    site.mkdir()
    (site / "index.html").write_text(
        '<pre><code>path = "{{input_csv}}"\n```\nthreshold = "{{minimum}}"</code></pre>'
        '<pre><code>{"output": "{{output_dir}}"}</code></pre>'
    )

    assert collect_failures(site, docs) == []


def test_audit_keeps_placeholder_counts_separate_per_route(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    site = tmp_path / "_site"
    _page(docs / "one.md", route="/one/", body="```text\n{{input_csv}}\n```\n")
    _page(docs / "two.md", route="/two/", body="```text\n{{input_csv}}\n```\n")
    route_output(site, "/one/").parent.mkdir(parents=True)
    route_output(site, "/two/").parent.mkdir(parents=True)
    route_output(site, "/one/").write_text('<pre><code>""</code></pre>')
    route_output(site, "/two/").write_text("<pre><code>{{input_csv}} {{input_csv}}</code></pre>")

    failures = collect_failures(site, docs)

    assert len(failures) == 1
    assert failures[0].startswith("one/index.html:")
    assert "literal parameter {{input_csv}}" in failures[0]
