"""Supported compiler choices for a PGF export request."""

from typing import Literal, cast, get_args

TexSystem = Literal["xelatex", "pdflatex", "lualatex"]
TEX_SYSTEMS: tuple[str, ...] = get_args(TexSystem)


def validate_tex_system(value: object) -> TexSystem:
    """Validate an exact compiler identifier without accepting executable paths.

    Args:
        value: Requested compiler identifier.

    Returns:
        One supported compiler name.

    Raises:
        ValueError: The identifier is not supported.
    """
    # [impl->req~ring5.figure.matplotlib-tex-system~1]
    if type(value) is not str or value not in TEX_SYSTEMS:
        raise ValueError(f"TeX system must be one of {', '.join(TEX_SYSTEMS)}.")
    return cast(TexSystem, value)
