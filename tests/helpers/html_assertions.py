"""Assertions for self-contained Plotly documents across supported versions."""

from html.parser import HTMLParser


class _DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: set[str] = set()
        self.external_scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)
        if tag == "script":
            source = dict(attrs).get("src")
            if source:
                self.external_scripts.append(source)


def assert_plotly_document(content: bytes | str) -> None:
    """Require a complete chart document with its JavaScript embedded.

    Args:
        content: Exported HTML, with or without a doctype declaration.
    """
    text = content.decode("utf-8") if isinstance(content, bytes) else content
    parser = _DocumentParser()
    parser.feed(text)
    assert {"html", "head", "body", "div", "script"} <= parser.tags
    assert "Plotly.newPlot(" in text
    assert not parser.external_scripts, "Plotly exports must work without a script CDN."
