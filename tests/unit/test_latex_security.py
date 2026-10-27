"""TeX export treats every figure label as data, never as commands."""

from contextlib import nullcontext

import matplotlib.pyplot as plt
import pytest

from src.web.rendering.latex_security import (
    disabled_figure_usetex,
    escape_latex_text,
    escaped_figure_text,
)


def test_latex_commands_are_neutralized() -> None:
    # [test->req~ring5.quality.safe-output-formatting~1]
    escaped = escape_latex_text(r"\input{/etc/hostname}_value")

    assert r"\input" not in escaped
    assert escaped.startswith(r"\textbackslash{}input\{")
    assert escaped.endswith(r"\_value")


def test_figure_text_is_escaped_temporarily() -> None:
    # [test->req~ring5.quality.safe-output-formatting~1]
    fig, ax = plt.subplots()
    ax.set_title(r"\input{/etc/hostname}")
    try:
        with escaped_figure_text(fig):
            assert r"\input" not in ax.title.get_text()
        assert ax.title.get_text() == r"\input{/etc/hostname}"
    finally:
        plt.close(fig)


def test_figure_usetex_is_disabled_temporarily() -> None:
    # [test->req~ring5.quality.safe-output-formatting~1]
    fig, ax = plt.subplots()
    ax.title.set_usetex(True)
    try:
        with disabled_figure_usetex(fig):
            assert not ax.title.get_usetex()
        assert ax.title.get_usetex()
    finally:
        plt.close(fig)


@pytest.mark.parametrize("parse_math", [False, True])
@pytest.mark.parametrize("fail", [False, True])
def test_literal_text_and_math_settings_are_restored(parse_math: bool, fail: bool) -> None:
    """Literal labels and per-artist math settings survive successful and failed exports."""
    fig, ax = plt.subplots()
    original = r"Measurement_1 & 50% $value$ \input{untrusted}"
    ax.set_title(original)
    ax.title.set_parse_math(parse_math)
    ax.set_xlabel("Plain label")
    ax.xaxis.label.set_parse_math(True)
    expected_error = pytest.raises(RuntimeError, match="export failed") if fail else nullcontext()
    try:
        with expected_error:
            with escaped_figure_text(fig):
                assert ax.title.get_text() == escape_latex_text(original)
                assert not ax.title.get_parse_math()
                assert ax.xaxis.label.get_text() == "Plain label"
                assert not ax.xaxis.label.get_parse_math()
                if fail:
                    raise RuntimeError("export failed")
        assert ax.title.get_text() == original
        assert ax.title.get_parse_math() is parse_math
        assert ax.xaxis.label.get_text() == "Plain label"
        assert ax.xaxis.label.get_parse_math()
    finally:
        plt.close(fig)
