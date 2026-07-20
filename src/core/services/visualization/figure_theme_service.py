"""Built-in, customizable, and portable figure-theme presets."""

from __future__ import annotations

import copy
import json
import math
import re
from dataclasses import asdict
from typing import Any, Final, Mapping, cast

from src.core.models.figure_theme_models import FigureTheme, FigureThemeContext
from src.core.services.visualization.accessibility_service import AccessibilityService
from src.core.services.visualization.palette_service import get_palette_names

_SCHEMA_VERSION: Final = 1
_MAX_PAYLOAD_BYTES: Final = 256 * 1024
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?$")
_RGB_COLOR = re.compile(r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$")
_RGBA_COLOR = re.compile(r"^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9]*\.?[0-9]+)\s*\)$")
_CONTEXTS: Final = {"paper", "presentation", "dashboard", "dark"}

# A theme changes appearance only. Data bindings, filters, plot-specific
# semantics, annotations, and per-series identities deliberately stay outside.
_THEME_CONFIG_KEYS: Final = {
    "accessibility_mode",
    "automargin",
    "axis_color",
    "axis_line_width",
    "color_palette",
    "document_width_preset",
    "enable_stripes",
    "export_scale",
    "font_family",
    "grid_color",
    "height",
    "height_inches",
    "legend_bgcolor",
    "legend_border_color",
    "legend_border_width",
    "legend_font_color",
    "legend_font_size",
    "legend_orientation",
    "legend_title_font_color",
    "legend_title_font_size",
    "margin_b",
    "margin_l",
    "margin_pad",
    "margin_r",
    "margin_t",
    "marker_size",
    "paper_bgcolor",
    "plot_bgcolor",
    "show_markers",
    "title_font_size",
    "width",
    "width_inches",
    "x_grid_alpha",
    "x_grid_color",
    "x_grid_width",
    "xaxis_tickfont_color",
    "xaxis_tickfont_size",
    "xaxis_title_font_size",
    "y_grid_alpha",
    "y_grid_color",
    "y_grid_width",
    "yaxis_tickfont_color",
    "yaxis_tickfont_size",
    "yaxis_title_font_size",
}
_BOOLEAN_KEYS: Final = {
    "accessibility_mode",
    "automargin",
    "enable_stripes",
    "show_markers",
}
_POSITIVE_KEYS: Final = {
    "axis_line_width",
    "export_scale",
    "height",
    "height_inches",
    "legend_font_size",
    "legend_title_font_size",
    "marker_size",
    "title_font_size",
    "width",
    "width_inches",
    "x_grid_width",
    "xaxis_tickfont_size",
    "xaxis_title_font_size",
    "y_grid_width",
    "yaxis_tickfont_size",
    "yaxis_title_font_size",
}
_NONNEGATIVE_KEYS: Final = {
    "legend_border_width",
    "margin_b",
    "margin_l",
    "margin_pad",
    "margin_r",
    "margin_t",
}
_ALPHA_KEYS: Final = {"x_grid_alpha", "y_grid_alpha"}


def _base_accessible() -> dict[str, Any]:
    return {
        "accessibility_mode": True,
        "automargin": True,
        "axis_line_width": 1.5,
        "color_palette": "ring5_accessible",
        "enable_stripes": True,
        "export_scale": 2,
        "font_family": "Arial",
        "paper_bgcolor": "#ffffff",
        "plot_bgcolor": "#ffffff",
        "axis_color": "#333333",
        "grid_color": "#d0d0d0",
        "xaxis_tickfont_color": "#222222",
        "yaxis_tickfont_color": "#222222",
        "legend_font_color": "#222222",
        "legend_title_font_color": "#111111",
        "legend_bgcolor": "#ffffff",
        "legend_border_color": "#777777",
        "legend_border_width": 0,
        "show_markers": True,
        "marker_size": 8,
    }


def _built_in_themes() -> dict[str, FigureTheme]:
    paper = _base_accessible() | {
        "document_width_preset": "Double Column (~7.0in)",
        "width_inches": 7.0,
        "height_inches": 4.0,
        "width": 700,
        "height": 400,
        "margin_l": 55,
        "margin_r": 20,
        "margin_t": 45,
        "margin_b": 55,
        "margin_pad": 2,
        "title_font_size": 18,
        "xaxis_title_font_size": 14,
        "yaxis_title_font_size": 14,
        "xaxis_tickfont_size": 11,
        "yaxis_tickfont_size": 11,
        "legend_font_size": 11,
        "legend_title_font_size": 12,
        "legend_orientation": "vertical",
    }
    presentation = _base_accessible() | {
        "document_width_preset": "Custom",
        "width_inches": 12.8,
        "height_inches": 7.2,
        "width": 1280,
        "height": 720,
        "margin_l": 85,
        "margin_r": 45,
        "margin_t": 75,
        "margin_b": 80,
        "margin_pad": 4,
        "title_font_size": 30,
        "xaxis_title_font_size": 22,
        "yaxis_title_font_size": 22,
        "xaxis_tickfont_size": 18,
        "yaxis_tickfont_size": 18,
        "legend_font_size": 18,
        "legend_title_font_size": 20,
        "legend_orientation": "horizontal",
        "marker_size": 11,
    }
    dashboard = _base_accessible() | {
        "document_width_preset": "Custom",
        "width_inches": 9.6,
        "height_inches": 5.4,
        "width": 960,
        "height": 540,
        "margin_l": 45,
        "margin_r": 25,
        "margin_t": 45,
        "margin_b": 45,
        "margin_pad": 2,
        "title_font_size": 18,
        "xaxis_title_font_size": 13,
        "yaxis_title_font_size": 13,
        "xaxis_tickfont_size": 11,
        "yaxis_tickfont_size": 11,
        "legend_font_size": 11,
        "legend_title_font_size": 12,
        "legend_orientation": "vertical",
        "paper_bgcolor": "#f7f9fc",
        "plot_bgcolor": "#ffffff",
    }
    dark = dashboard | {
        "color_palette": "ring5_accessible_dark",
        "paper_bgcolor": "#161a24",
        "plot_bgcolor": "#202633",
        "axis_color": "#f2f4f8",
        "grid_color": "#596273",
        "x_grid_color": "#596273",
        "y_grid_color": "#596273",
        "xaxis_tickfont_color": "#f2f4f8",
        "yaxis_tickfont_color": "#f2f4f8",
        "legend_font_color": "#f2f4f8",
        "legend_title_font_color": "#ffffff",
        "legend_bgcolor": "#161a24",
        "legend_border_color": "#8d96a8",
        "legend_border_width": 1,
    }
    return {
        "paper": FigureTheme(
            "paper",
            "Publication paper",
            "paper",
            "Compact print dimensions, restrained typography, and accessible marks.",
            paper,
        ),
        "presentation": FigureTheme(
            "presentation",
            "Presentation slide",
            "presentation",
            "Large 16:9 canvas with typography and marks readable at a distance.",
            presentation,
        ),
        "dashboard": FigureTheme(
            "dashboard",
            "Dashboard panel",
            "dashboard",
            "Balanced screen dimensions and compact labels for repeated panels.",
            dashboard,
        ),
        "dark": FigureTheme(
            "dark",
            "Dark background",
            "dark",
            "Dark surfaces, light text, visible grids, and a contrast-checked palette.",
            dark,
        ),
    }


_BUILT_INS: Final = _built_in_themes()


class FigureThemeService:
    """Validate, apply, customize, import, and export figure themes."""

    @classmethod
    def available_themes(cls) -> tuple[FigureTheme, ...]:
        """Return isolated copies of the ordered built-in themes."""
        # [impl->req~ring5.figure.theme-presets~1]
        return tuple(copy.deepcopy(theme) for theme in _BUILT_INS.values())

    @classmethod
    def get(cls, identifier: str) -> FigureTheme:
        """Resolve one built-in theme by stable identifier."""
        if not isinstance(identifier, str) or identifier not in _BUILT_INS:
            choices = ", ".join(_BUILT_INS)
            raise ValueError(f"Unknown figure theme {identifier!r}. Choose from: {choices}.")
        return copy.deepcopy(_BUILT_INS[identifier])

    @classmethod
    def apply(
        cls,
        config: Mapping[str, Any],
        theme: str | FigureTheme,
        plot_type: str,
    ) -> dict[str, Any]:
        """Apply only appearance keys while retaining data and plot semantics."""
        # [impl->req~ring5.figure.theme-presets~1]
        if not isinstance(config, Mapping):
            raise TypeError("Figure theme configuration must be a mapping.")
        if not isinstance(plot_type, str) or not plot_type.strip():
            raise ValueError("Applying a figure theme requires a plot type.")
        resolved = cls.get(theme) if isinstance(theme, str) else cls.validate(theme)
        result = copy.deepcopy(dict(config))
        result.update(copy.deepcopy(resolved.config))
        result["figure_theme_id"] = resolved.identifier
        result["figure_theme_name"] = resolved.name
        result["figure_theme_context"] = resolved.context
        return AccessibilityService.apply_defaults(result, plot_type.strip())

    @classmethod
    def customize(
        cls,
        theme: str | FigureTheme,
        overrides: Mapping[str, Any],
        *,
        name: str,
    ) -> FigureTheme:
        """Create a validated theme from a base and appearance-only overrides."""
        # [impl->req~ring5.figure.theme-presets~1]
        if not isinstance(overrides, Mapping):
            raise TypeError("Figure theme overrides must be a mapping.")
        base = cls.get(theme) if isinstance(theme, str) else cls.validate(theme)
        custom_name = cls._validate_name(name)
        identifier = cls._slug(custom_name)
        custom_config = copy.deepcopy(base.config)
        custom_config.update(cls._validate_config(dict(overrides), reject_unknown=True))
        return FigureTheme(
            identifier=identifier,
            name=custom_name,
            context=base.context,
            description=f"Customized from {base.name}.",
            config=custom_config,
        )

    @classmethod
    def from_config(
        cls,
        name: str,
        config: Mapping[str, Any],
        *,
        context: FigureThemeContext = "paper",
    ) -> FigureTheme:
        """Capture the portable appearance subset of a live figure configuration."""
        # [impl->req~ring5.figure.theme-presets~1]
        if not isinstance(config, Mapping):
            raise TypeError("Figure theme configuration must be a mapping.")
        custom_name = cls._validate_name(name)
        resolved_context = cls._validate_context(context)
        appearance = {
            key: copy.deepcopy(value) for key, value in config.items() if key in _THEME_CONFIG_KEYS
        }
        return FigureTheme(
            identifier=cls._slug(custom_name),
            name=custom_name,
            context=resolved_context,
            description="Customized RING-5 figure theme.",
            config=cls._validate_config(appearance, reject_unknown=True),
        )

    @classmethod
    def dumps(cls, theme: FigureTheme) -> bytes:
        """Return deterministic UTF-8 JSON for one validated theme."""
        # [impl->req~ring5.figure.theme-presets~1]
        resolved = cls.validate(theme)
        payload = asdict(resolved)
        return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )

    @classmethod
    def loads(cls, payload: str | bytes | bytearray) -> FigureTheme:
        """Load a bounded versioned theme JSON document."""
        # [impl->req~ring5.figure.theme-presets~1]
        if isinstance(payload, str):
            raw = payload.encode("utf-8")
        elif isinstance(payload, (bytes, bytearray)):
            raw = bytes(payload)
        else:
            raise TypeError("Figure theme import expects JSON text or bytes.")
        if len(raw) > _MAX_PAYLOAD_BYTES:
            raise ValueError("Figure theme JSON exceeds the 256 KiB limit.")
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Figure theme import is not valid UTF-8 JSON.") from exc
        if not isinstance(document, dict):
            raise ValueError("Figure theme JSON must contain one object.")
        required = {
            "identifier",
            "name",
            "context",
            "description",
            "config",
            "schema_version",
        }
        if set(document) != required:
            raise ValueError("Figure theme JSON has missing or unsupported fields.")
        if (
            not isinstance(document["schema_version"], int)
            or isinstance(document["schema_version"], bool)
            or document["schema_version"] != _SCHEMA_VERSION
        ):
            raise ValueError(
                f"Unsupported figure theme schema version {document['schema_version']!r}; "
                f"expected {_SCHEMA_VERSION}."
            )
        config = document["config"]
        if not isinstance(config, dict):
            raise ValueError("Figure theme config must be an object.")
        theme = FigureTheme(
            identifier=document["identifier"],
            name=document["name"],
            context=document["context"],
            description=document["description"],
            config=config,
            schema_version=document["schema_version"],
        )
        return cls.validate(theme)

    @classmethod
    def validate(cls, theme: FigureTheme) -> FigureTheme:
        """Return an isolated validated copy of a theme object."""
        if not isinstance(theme, FigureTheme):
            raise TypeError("Figure theme must be a FigureTheme instance.")
        if theme.schema_version != _SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported figure theme schema version {theme.schema_version!r}; "
                f"expected {_SCHEMA_VERSION}."
            )
        if not isinstance(theme.identifier, str) or not _IDENTIFIER.fullmatch(theme.identifier):
            raise ValueError("Figure theme identifier must be a lowercase portable identifier.")
        name = cls._validate_name(theme.name)
        context = cls._validate_context(theme.context)
        if not isinstance(theme.description, str) or len(theme.description) > 500:
            raise ValueError("Figure theme description must be text of at most 500 characters.")
        config = cls._validate_config(theme.config, reject_unknown=True)
        return FigureTheme(
            identifier=theme.identifier,
            name=name,
            context=context,
            description=theme.description,
            config=config,
            schema_version=theme.schema_version,
        )

    @staticmethod
    def _validate_name(name: object) -> str:
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
            raise ValueError("Figure theme name must contain 1 to 80 characters.")
        return name.strip()

    @staticmethod
    def _validate_context(context: object) -> FigureThemeContext:
        if not isinstance(context, str) or context not in _CONTEXTS:
            raise ValueError(
                "Figure theme context must be paper, presentation, dashboard, or dark."
            )
        return cast(FigureThemeContext, context)

    @staticmethod
    def _slug(name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return (slug or "custom-theme")[:64].rstrip("-")

    @staticmethod
    def _validate_config(
        config: object,
        *,
        reject_unknown: bool,
    ) -> dict[str, Any]:
        if not isinstance(config, Mapping):
            raise ValueError("Figure theme config must be an object.")
        unknown = sorted(set(config) - _THEME_CONFIG_KEYS)
        if reject_unknown and unknown:
            raise ValueError(
                "Figure themes cannot contain data or unsupported keys: " + ", ".join(unknown)
            )
        if len(config) > len(_THEME_CONFIG_KEYS):
            raise ValueError("Figure theme config contains too many settings.")
        validated: dict[str, Any] = {}
        for key, value in config.items():
            if key not in _THEME_CONFIG_KEYS:
                continue
            if not isinstance(value, (str, int, float, bool)) or value is None:
                raise ValueError(f"Figure theme setting {key!r} must be a scalar value.")
            if key in _BOOLEAN_KEYS and not isinstance(value, bool):
                raise ValueError(f"Figure theme setting {key!r} must be true or false.")
            if key in (_POSITIVE_KEYS | _NONNEGATIVE_KEYS | _ALPHA_KEYS) and (
                not isinstance(value, (int, float)) or isinstance(value, bool)
            ):
                raise ValueError(f"Figure theme setting {key!r} must be numeric.")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"Figure theme setting {key!r} must be finite.")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if abs(float(value)) > 100_000:
                    raise ValueError(f"Figure theme setting {key!r} is outside the safe range.")
            if isinstance(value, str) and len(value) > 200:
                raise ValueError(f"Figure theme setting {key!r} is too long.")
            if key in _POSITIVE_KEYS and float(value) <= 0:
                raise ValueError(f"Figure theme setting {key!r} must be positive.")
            if key in _NONNEGATIVE_KEYS and float(value) < 0:
                raise ValueError(f"Figure theme setting {key!r} cannot be negative.")
            if key in _ALPHA_KEYS and not 0 <= float(value) <= 1:
                raise ValueError(f"Figure theme setting {key!r} must be between zero and one.")
            if key == "legend_orientation" and value not in {"horizontal", "vertical"}:
                raise ValueError("Figure theme legend orientation must be horizontal or vertical.")
            if (
                key != "color_palette"
                and ("color" in key or key.endswith("bgcolor"))
                and isinstance(value, str)
            ):
                if not FigureThemeService._is_css_color(value):
                    raise ValueError(f"Figure theme setting {key!r} is not a supported CSS color.")
            validated[key] = copy.deepcopy(value)
        palette = validated.get("color_palette")
        if palette is not None and palette not in get_palette_names():
            raise ValueError(f"Unknown figure theme palette {palette!r}.")
        return validated

    @staticmethod
    def _is_css_color(value: str) -> bool:
        color = value.strip()
        if color in {"black", "white", "transparent"} or _HEX_COLOR.fullmatch(color):
            return True
        rgb = _RGB_COLOR.fullmatch(color)
        if rgb:
            return all(0 <= int(channel) <= 255 for channel in rgb.groups())
        rgba = _RGBA_COLOR.fullmatch(color)
        if rgba:
            channels = (int(channel) for channel in rgba.groups()[:3])
            alpha = float(rgba.group(4))
            return all(0 <= channel <= 255 for channel in channels) and 0 <= alpha <= 1
        return False
