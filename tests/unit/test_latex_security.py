"""TeX export treats every figure label as data, never as commands."""

import matplotlib.pyplot as plt

from src.web.rendering.latex_security import (
    disabled_figure_usetex,
    escape_latex_text,
    escaped_figure_text,
)


def test_latex_commands_are_neutralized() -> None:
    escaped = escape_latex_text(r"\input{/etc/hostname}_value")

    assert r"\input" not in escaped
    assert escaped.startswith(r"\textbackslash{}input\{")
    assert escaped.endswith(r"\_value")


def test_figure_text_is_escaped_temporarily() -> None:
    fig, ax = plt.subplots()
    ax.set_title(r"\input{/etc/hostname}")
    try:
        with escaped_figure_text(fig):
            assert r"\input" not in ax.title.get_text()
        assert ax.title.get_text() == r"\input{/etc/hostname}"
    finally:
        plt.close(fig)


def test_figure_usetex_is_disabled_temporarily() -> None:
    fig, ax = plt.subplots()
    ax.title.set_usetex(True)
    try:
        with disabled_figure_usetex(fig):
            assert not ax.title.get_usetex()
        assert ax.title.get_usetex()
    finally:
        plt.close(fig)
