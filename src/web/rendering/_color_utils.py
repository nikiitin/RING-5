"""Shared CSS color descriptions and native opacity projections."""

import colorsys
import math
import re
from dataclasses import dataclass
from decimal import Decimal

_FUNCTION = re.compile(r"([a-z]+)\((.*)\)", re.IGNORECASE | re.DOTALL)
_COMPONENT_SEPARATORS = re.compile(r"[\s,/]+")
_ALPHA_FUNCTIONS = frozenset({"rgb", "hsl", "hwb", "lab", "lch", "oklab", "oklch"})


@dataclass(frozen=True)
class _FunctionalColor:
    """One functional color with untouched component tokens and separate opacity."""

    model: str
    components: tuple[str, ...]
    alpha: str | None = None


def _functional_color(color: str) -> _FunctionalColor | None:
    """Split a CSS function without converting its color space or channel precision."""
    match = _FUNCTION.fullmatch(color.strip())
    if match is None:
        return None
    model, body = match.groups()
    model = model.lower()
    if model in ("rgba", "hsla"):
        model = model[:-1]
    if model == "var":
        return _FunctionalColor(model, (body,))
    components = tuple(_COMPONENT_SEPARATORS.split(body.strip()))
    count = 4 if model == "color" else 3
    if len(components) not in (count, count + 1):
        raise ValueError(f"Invalid {model} background color component count.")
    return _FunctionalColor(
        model, components[:count], components[count] if len(components) > count else None
    )


def _unit_value(value: str, scale: float) -> float:
    """Read a concrete CSS channel or percentage in normalized units."""
    return float(value[:-1]) / 100.0 if value.endswith("%") else float(value) / scale


def _alpha_decimal(alpha: float) -> str:
    """Format a finite binary64 opacity without unsupported exponent notation."""
    if not math.isfinite(alpha) or not 0.0 <= alpha <= 1.0:
        raise ValueError("Background alpha must be finite and from zero through one.")
    if alpha == 0:
        return "0"
    if alpha == 1:
        return "1"
    return format(Decimal(str(alpha)), "f")


def _channel_decimal(value: float) -> str:
    """Retain numeric precision without unnecessary decimal zeros."""
    text = format(Decimal(str(value)), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def css_color_to_matplotlib(
    color: str | tuple[float, float, float] | tuple[float, float, float, float],
) -> str | tuple[float, float, float] | tuple[float, float, float, float]:
    """Project concrete RGB/HSL functions, retaining other native static color formats.

    Raises:
        ValueError: A functional color has no supported static Matplotlib projection.
    """
    if not isinstance(color, str):
        return color
    parsed = _functional_color(color)
    if parsed is None:
        if color.startswith("#") and len(color) in (5, 9):
            from matplotlib.colors import to_rgba

            return to_rgba(color)
        return color
    if parsed.model == "rgb":
        red, green, blue = (_unit_value(token, 255.0) for token in parsed.components)
    elif parsed.model == "hsl":
        hue, saturation, lightness = parsed.components
        red, green, blue = colorsys.hls_to_rgb(
            (float(hue.removesuffix("deg")) % 360.0) / 360.0,
            _unit_value(lightness, 100.0),
            _unit_value(saturation, 100.0),
        )
    else:
        raise ValueError(
            f"Matplotlib requires a static RGB, HSL, hexadecimal or named color; "
            f"convert the {parsed.model}() color before rendering."
        )
    if parsed.alpha is None:
        return red, green, blue
    return red, green, blue, _unit_value(parsed.alpha, 1.0)


def picker_hex_color(color: str) -> str:
    """Project a concrete CSS color to an RGB picker preview.

    The preview omits alpha; callers retain the original CSS value until an
    explicit edit. Unsupported static color spaces and variables raise instead
    of inventing a replacement color.

    Args:
        color: Saved CSS text to preview.

    Returns:
        A six-digit RGB hexadecimal color.

    Raises:
        ValueError: The value is not CSS text or has no static RGB projection.
    """
    # [impl->req~ring5.figure.colors~1]
    if not isinstance(color, str):
        raise ValueError("A saved color must be CSS text.")
    from matplotlib.colors import to_hex

    return to_hex(css_color_to_matplotlib(color), keep_alpha=False)


def color_with_alpha(color: str, alpha: float) -> str:
    """Replace opacity while preserving supported CSS functional component precision.

    Args:
        color: A static named, hexadecimal or functional CSS color.
        alpha: Finite opacity from zero through one.

    Returns:
        A CSS color carrying the requested opacity in plain decimal notation.

    Raises:
        ValueError: Color/opacity is invalid, or the current Plotly validator cannot
            represent opacity for a color profile or unresolved DDK variable.
    """
    # [impl->req~ring5.figure.legends~1]
    opacity = _alpha_decimal(alpha)
    parsed = _functional_color(color)
    if parsed is not None:
        if parsed.model in ("color", "var"):
            raise ValueError(
                f"Per-legend bgalpha cannot be represented for {parsed.model}() by the current "
                "Plotly validator. Supply a concrete RGB, HSL or hexadecimal color, "
                "or omit bgalpha."
            )
        if parsed.model not in _ALPHA_FUNCTIONS:
            raise ValueError(f"Unsupported functional background color: {parsed.model}().")
        if parsed.model == "rgb":
            return f"rgba({','.join(parsed.components)},{opacity})"
        return f"{parsed.model}({' '.join(parsed.components)} / {opacity})"
    from matplotlib.colors import to_rgba

    red, green, blue, _ = to_rgba(color)
    channels = [_channel_decimal(value * 255) for value in (red, green, blue)]
    return f"rgba({channels[0]},{channels[1]},{channels[2]},{opacity})"
