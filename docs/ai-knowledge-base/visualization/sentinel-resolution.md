---
title: "Sentinel Resolution System"
parent: Visualization
grand_parent: AI Knowledge Base
nav_order: 3
---

# Sentinel Resolution System

> **Scope**: The `-1` sentinel value pattern, which configs use it, resolution algorithm, and timing.
> **Key file**: `src/core/services/visualization/config_resolver.py` (lines 1-185)

---

## Sentinel Constants

| Constant | Value | Defined In | Used For |
|----------|-------|------------|----------|
| `SENTINEL_INT` | `-1` | `config_resolver.py:56` | Integer fields (font sizes, ncol) |
| `SENTINEL_FLOAT` | `-1.0` | `config_resolver.py:57` | Float fields (positions, spacing, padding) |
| `INHERIT` | `-1` | `typography_config.py:18` | Alias for `SENTINEL_INT` in typography |
| `INHERIT_F` | `-1.0` | `typography_config.py:19`, `axis_config.py:18`, `legend_config.py:19` | Alias for `SENTINEL_FLOAT` in various modules |

**Semantic meaning**: `-1` means "inherit this value from the nearest parent in the resolution chain." All config fields that accept sentinels are non-negative in valid configurations (font sizes, positions, spacing >= 0), making `-1` a safe sentinel.

---

## Which Configs Use Sentinels

### TypographyConfig -- 4 sentinel fields

| Field | Default | Inherits From |
|-------|---------|---------------|
| `font_size_y2label` | `-1` | `font_size_ylabel` |
| `font_size_y2ticks` | `-1` | `font_size_yticks` |
| `font_size_legend2` | `-1` | `font_size_legend` |
| `font_size_yticks` | `7` (explicit) | `font_size_ticks` (when set to -1) |

### LegendConfig -- sentinel fields on secondary/tertiary

| Field | Default | Inherits From |
|-------|---------|---------------|
| `font_size` | `-1` (on legend[1], legend[2]) | `legends[0].font_size` |
| `title_font_size` | `-1` | Own `font_size` (after resolution) |
| `position_x` | `-1.0` | NOT resolved (connectors handle "auto") |
| `position_y` | `-1.0` | NOT resolved (connectors handle "auto") |
| `col_width` | `-1.0` | NOT resolved |

### LegendSpacingConfig -- all 7 fields on secondary/tertiary

| Field | Default (secondary/tertiary) | Inherits From |
|-------|------------------------------|---------------|
| `columnspacing` | `-1.0` | `legends[0].spacing.columnspacing` |
| `handletextpad` | `-1.0` | `legends[0].spacing.handletextpad` |
| `labelspacing` | `-1.0` | `legends[0].spacing.labelspacing` |
| `handlelength` | `-1.0` | `legends[0].spacing.handlelength` |
| `handleheight` | `-1.0` | `legends[0].spacing.handleheight` |
| `borderpad` | `-1.0` | `legends[0].spacing.borderpad` |
| `borderaxespad` | `-1.0` | `legends[0].spacing.borderaxespad` |

### AxisConfig (y2 only) -- 2 sentinel fields

| Field | Default (y2) | Inherits From |
|-------|-------------|---------------|
| `label_pad` | `-1.0` | `axes.y.label_pad` |
| `tick_pad` | `-1.0` | `axes.y.tick_pad` |

### AnnotationConfig -- 1 sentinel field

| Field | Default | Inherits From |
|-------|---------|---------------|
| `font_size` | `-1` | NOT resolved by config_resolver (handled at render time) |

---

## Resolution Algorithm

**File**: `src/core/services/visualization/config_resolver.py:60`

```python
def resolve_config(spec: FigureConfig) -> FigureConfig:
    resolved = deepcopy(spec)          # PURE -- never mutates input
    _resolve_typography(resolved.typography)
    _resolve_legends(resolved.legends)
    _resolve_axes(resolved.axes)
    return resolved
```

### Properties

- **Pure function**: input is never mutated; returns a deep copy
- **Single pass**: all three chains resolved sequentially in ONE call
- **Idempotent**: running on an already-resolved config is a no-op
- **Fail-safe**: type checks (`isinstance`) skip chains on unexpected types

### Atomic operations

```python
def _resolve_int(value: int, parent: int) -> int:
    return parent if value == SENTINEL_INT else value    # line 78

def _resolve_float(value: float, parent: float) -> float:
    return parent if value == SENTINEL_FLOAT else value  # line 83
```

---

## Three Inheritance Chains

### Chain 1: Typography (`_resolve_typography`, line 88)

```
font_size_ylabel (9)
    +-- font_size_y2label (-1)  -> resolves to ylabel value

font_size_ticks (7)
    +-- font_size_yticks (7, or -1 -> ticks)
        +-- font_size_y2ticks (-1)  -> resolves to yticks value

font_size_legend (8)
    +-- font_size_legend2 (-1)  -> resolves to legend value
```

**Order matters**: `ticks -> yticks -> y2ticks` and `legend -> legend2`.

### Chain 2: Legends (`_resolve_legends`, line 114)

```
legends[0] (primary)
    font_size = 8 (concrete)
    title_font_size = -1  -> resolves to own font_size
    spacing = concrete values

legends[1] (secondary)
    font_size = -1         -> resolves to primary.font_size
    title_font_size = -1   -> resolves to own font_size (after font_size resolved)
    spacing.* = -1.0       -> each field resolves to primary.spacing.*

legends[2] (tertiary)
    (same pattern as secondary)
```

**Spacing resolution** (`_resolve_legend_spacing`, line 152): iterates all `dataclasses.fields()` of `LegendSpacingConfig` generically. Any field with value `-1.0` is replaced by the primary's corresponding field value.

### Chain 3: Axes (`_resolve_axes`, line 168)

```
axes.y
    label_pad = 10.0 (concrete)
    tick_pad = 5.0 (concrete)

axes.y2 (if not None)
    label_pad = -1.0  -> resolves to y.label_pad
    tick_pad = -1.0   -> resolves to y.tick_pad
```

Only 2 fields participate. If `axes.y2 is None`, resolution is a no-op.

---

## Resolution Timing

```
CRITICAL: Sentinels are resolved at RENDER TIME, not at PERSIST TIME.

  Creation          Persistence        Rendering
  --------          -----------        ---------
  FigureConfig      spec.to_dict()     resolve_config(spec)
  (has -1 values)   -> JSON            -> all -1 replaced
                    (preserves -1)     -> passed to connector
```

- **to_dict()** serializes `-1` values as-is into JSON
- **from_dict()** deserializes them back as `-1`
- **resolve_config()** is called just before passing to a connector
- Connectors NEVER see `-1` values

This ensures:
- Settings can leave `-1` for secondary values and the inheritance "just works"
- Portfolio files preserve the user's intent (inherit vs explicit)
- Re-resolution after loading works correctly

---

## Configs NOT Resolved by config_resolver

| Field / Config | Where Handled | Notes |
|---------------|---------------|-------|
| `LegendConfig.position_x = -1.0` | Connector (auto positioning) | Not an inheritance sentinel |
| `LegendConfig.position_y = -1.0` | Connector (auto positioning) | Not an inheritance sentinel |
| `LegendConfig.col_width = -1.0` | Connector | Not an inheritance sentinel |
| `AnnotationConfig.font_size = -1` | Plotly extraction / render-time fallback | Not part of inheritance chains |
| `AxisConfig.label_standoff = -1` | Connector skips standoff if -1 | Used as "skip" flag |

---

## File Index

| File | Role | Lines |
|------|------|-------|
| `src/core/services/visualization/config_resolver.py` | `resolve_config()`, `SENTINEL_INT`, `SENTINEL_FLOAT`, chain resolvers | 196 |
| `src/core/models/visualization/typography_config.py` | `INHERIT`, `INHERIT_F` aliases; sentinel default values | 72 |
| `src/core/models/visualization/legend_config.py` | `INHERIT_F` alias; LegendSpacingConfig sentinel defaults | 239 |
| `src/core/models/visualization/axis_config.py` | `INHERIT_F` alias; y2 sentinel defaults | 141 |
