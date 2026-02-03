# LaTeX Export Service - Implementation Plan

## 🎯 Mission Statement

Build a publication-quality export system that converts interactive Plotly figures to LaTeX-optimized static formats (PDF, PGF, EPS) while preserving all user-configured layout decisions (legend position, zoom, colors, etc.).

**CRITICAL**: This implementation **REPLACES** the existing Kaleido-based export system entirely. All legacy Kaleido code will be removed. Matplotlib provides superior LaTeX integration with PGF backend, Computer Modern fonts, and proper font embedding.

## 📐 Architecture Design

### Layered Architecture (STRICT SEPARATION)

```
Layer C (Presentation)
  ├─ src/web/ui/components/export_dialog.py
  │  └─ UI for selecting export format, preset, dimensions
  │  └─ NO business logic, only widget rendering
  │
Layer B (Domain - Business Logic)
  ├─ src/plotting/export/
  │  ├─ latex_export_service.py      # Facade/Orchestrator
  │  ├─ converters/
  │  │  ├─ base_converter.py         # Abstract base (Strategy Pattern)
  │  │  ├─ matplotlib_converter.py   # Plotly → Matplotlib (ONLY converter)
  │  │  └─ factory.py                # Converter Factory
  │  ├─ presets/
  │  │  ├─ preset_manager.py         # Load/validate presets
  │  │  └─ preset_schema.py          # TypedDict definitions
  │  └─ layout_mapper.py             # Maps Plotly config → Matplotlib
  │
Layer A (Data)
  ├─ config/latex_presets.yaml       # Journal-specific configs
  └─ tests/fixtures/sample_figures.py # Test data
```

### Design Patterns

1. **Strategy Pattern**: Extensible converter interface (currently Matplotlib, future alternatives possible)
2. **Factory Pattern**: `ConverterFactory.create(format="pdf")`
3. **Facade Pattern**: `LaTeXExportService` as single entry point
4. **Builder Pattern**: Matplotlib figure construction
5. **Template Method**: Base converter defines conversion flow

### Type Safety (MANDATORY)

All functions must have complete type annotations:

```python
from typing import TypedDict, Literal, Optional, Protocol

class LaTeXPreset(TypedDict):
    """LaTeX export preset configuration."""
    width_inches: float
    height_inches: float
    font_family: str
    font_size_base: int
    font_size_labels: int
    font_size_title: int
    font_size_ticks: int
    line_width: float
    marker_size: int
    dpi: int

class ExportResult(TypedDict):
    """Export operation result."""
    success: bool
    data: Optional[bytes]
    format: str
    error: Optional[str]
    metadata: dict[str, Any]

class FigureConverter(Protocol):
    """Protocol for figure converters (structural typing)."""
    def convert(
        self,
        fig: go.Figure,
        preset: LaTeXPreset,
        format: Literal["pdf", "pgf", "eps"]
    ) -> ExportResult: ...
```

---

## 📋 Implementation Plan - Phased TDD Approach

### **PHASE 1: Foundation & Configuration** (2-3 hours)

#### **Task 1.1: Define Type Schemas** ✅ Test First
**Objective**: Create TypedDict definitions for all data structures

**Files**:
- `src/plotting/export/presets/preset_schema.py`
- `tests/unit/export/test_preset_schema.py`

**Test Strategy**:
```python
def test_latex_preset_required_fields():
    """Verify LaTeXPreset has all required fields."""
    preset: LaTeXPreset = {
        "width_inches": 3.5,
        "height_inches": 2.625,
        # ... all fields
    }
    assert preset["width_inches"] == 3.5

def test_export_result_structure():
    """Verify ExportResult structure."""
    result: ExportResult = {
        "success": True,
        "data": b"mock data",
        "format": "pdf",
        "error": None,
        "metadata": {}
    }
    assert result["success"] is True
```

**Implementation**:
- Create TypedDict definitions
- Add docstrings for each field
- Run mypy --strict (must pass)

**Validation**:
```bash
pytest tests/unit/export/test_preset_schema.py -v
mypy src/plotting/export/presets/preset_schema.py --strict
```

---

#### **Task 1.2: Create YAML Preset Configuration** ✅ Test First
**Objective**: Define journal-specific presets with validation

**Files**:
- `config/latex_presets.yaml`
- `src/plotting/export/presets/preset_manager.py`
- `tests/unit/export/test_preset_manager.py`

**Test Strategy**:
```python
def test_load_single_column_preset():
    """Verify single column preset loads correctly."""
    preset = PresetManager.load_preset("single_column")
    assert preset["width_inches"] == 3.5
    assert preset["font_family"] == "serif"

def test_invalid_preset_raises_error():
    """Verify unknown preset raises ValueError."""
    with pytest.raises(ValueError, match="Unknown preset"):
        PresetManager.load_preset("nonexistent")

def test_preset_validation():
    """Verify preset validation catches invalid values."""
    invalid_preset = {"width_inches": -1}  # Invalid
    with pytest.raises(ValueError):
        PresetManager.validate_preset(invalid_preset)
```

**Implementation**:
1. Create YAML with presets: `single_column`, `double_column`, `nature`, `ieee`, `acm`
2. Implement `PresetManager.load_preset(name: str) -> LaTeXPreset`
3. Implement `PresetManager.validate_preset(preset: dict) -> bool`
4. Add schema validation (positive values, valid fonts, etc.)

**Validation**:
```bash
pytest tests/unit/export/test_preset_manager.py -v
mypy src/plotting/export/presets/preset_manager.py --strict
```

---

### **PHASE 2: Converter Foundation** (3-4 hours)

#### **Task 2.1: Abstract Base Converter** ✅ Test First
**Objective**: Define converter interface and common functionality

**Files**:
- `src/plotting/export/converters/base_converter.py`
- `tests/unit/export/converters/test_base_converter.py`

**Test Strategy**:
```python
def test_base_converter_is_abstract():
    """Verify BaseConverter cannot be instantiated."""
    with pytest.raises(TypeError):
        BaseConverter()

def test_base_converter_defines_convert_method():
    """Verify convert method is abstract."""
    # Use inspect to check abstractmethod decorator
    assert hasattr(BaseConverter, 'convert')
    assert BaseConverter.convert.__isabstractmethod__
```

**Implementation**:
```python
from abc import ABC, abstractmethod

class BaseConverter(ABC):
    """Abstract base for figure converters."""

    def __init__(self, preset: LaTeXPreset) -> None:
        self.preset = preset
        self._verify_preset()

    def _verify_preset(self) -> None:
        """Validate preset has required fields."""
        required = ["width_inches", "height_inches", "font_family"]
        for field in required:
            if field not in self.preset:
                raise ValueError(f"Missing required field: {field}")

    @abstractmethod
    def convert(
        self,
        fig: go.Figure,
        format: Literal["pdf", "pgf", "eps"]
    ) -> ExportResult:
        """Convert figure to specified format."""
        pass

    def _create_success_result(
        self, data: bytes, format: str
    ) -> ExportResult:
        """Helper to create success result."""
        return ExportResult(
            success=True,
            data=data,
            format=format,
            error=None,
            metadata={"preset": self.preset["width_inches"]}
        )

    def _create_error_result(
        self, error: str, format: str
    ) -> ExportResult:
        """Helper to create error result."""
        return ExportResult(
            success=False,
            data=None,
            format=format,
            error=error,
            metadata={}
        )
```

**Validation**:
```bash
pytest tests/unit/export/converters/test_base_converter.py -v
mypy src/plotting/export/converters/base_converter.py --strict
```

---

#### **Task 2.2: Layout Mapper** ✅ Test First
**Objective**: Map Plotly configuration to Matplotlib equivalents

**Files**:
- `src/plotting/export/layout_mapper.py`
- `tests/unit/export/test_layout_mapper.py`

**Test Strategy**:
```python
def test_map_legend_position():
    """Verify Plotly legend coords map to Matplotlib."""
    plotly_config = {
        "legend_x": 0.05,
        "legend_y": 0.95,
        "legend_xanchor": "left",
        "legend_yanchor": "top"
    }
    mpl_config = LayoutMapper.map_legend(plotly_config)
    assert mpl_config["loc"] == "upper left"
    assert mpl_config["bbox_to_anchor"] == (0.05, 0.95)

def test_map_axis_ranges():
    """Verify axis range mapping."""
    plotly_config = {
        "xaxis_range": [0, 10],
        "yaxis_range": [0, 100]
    }
    mpl_config = LayoutMapper.map_axes(plotly_config)
    assert mpl_config["xlim"] == (0, 10)
    assert mpl_config["ylim"] == (0, 100)

def test_map_font_settings():
    """Verify font configuration mapping."""
    plotly_config = {
        "xaxis_tickfont_size": 12,
        "yaxis_title_font_size": 14
    }
    preset = {"font_size_ticks": 8, "font_size_labels": 9}
    mpl_config = LayoutMapper.map_fonts(plotly_config, preset)
    # Preset overrides Plotly for LaTeX export
    assert mpl_config["xtick.labelsize"] == 8
```

**Implementation**:
```python
class LayoutMapper:
    """Maps Plotly config to Matplotlib/LaTeX equivalents."""

    @staticmethod
    def map_legend(config: dict[str, Any]) -> dict[str, Any]:
        """Map legend position and style."""
        # Plotly uses (0-1) normalized coords
        # Matplotlib uses similar but different anchor system
        x = config.get("legend_x", 1.0)
        y = config.get("legend_y", 1.0)
        xanchor = config.get("legend_xanchor", "left")
        yanchor = config.get("legend_yanchor", "top")

        # Map to Matplotlib location string + bbox
        loc = LayoutMapper._get_matplotlib_loc(xanchor, yanchor)
        return {
            "loc": loc,
            "bbox_to_anchor": (x, y),
            "frameon": config.get("legend_borderwidth", 1) > 0
        }

    @staticmethod
    def map_axes(config: dict[str, Any]) -> dict[str, Any]:
        """Map axis ranges and settings."""
        result = {}
        if "xaxis_range" in config:
            result["xlim"] = tuple(config["xaxis_range"])
        if "yaxis_range" in config:
            result["ylim"] = tuple(config["yaxis_range"])
        return result

    @staticmethod
    def map_fonts(
        config: dict[str, Any],
        preset: LaTeXPreset
    ) -> dict[str, Any]:
        """Map font settings (preset takes precedence)."""
        return {
            "xtick.labelsize": preset["font_size_ticks"],
            "ytick.labelsize": preset["font_size_ticks"],
            "axes.labelsize": preset["font_size_labels"],
            "axes.titlesize": preset["font_size_title"],
            "font.family": preset["font_family"]
        }
```

**Validation**:
```bash
pytest tests/unit/export/test_layout_mapper.py -v
mypy src/plotting/export/layout_mapper.py --strict
```

---

### **PHASE 3: Matplotlib Converter** (4-5 hours)

#### **Task 3.1: Basic Matplotlib Converter** ✅ Test First
**Objective**: Convert simple bar/line plots to Matplotlib

**Files**:
- `src/plotting/export/converters/matplotlib_converter.py`
- `tests/unit/export/converters/test_matplotlib_converter.py`

**Test Strategy**:
```python
@pytest.fixture
def simple_bar_figure():
    """Create simple bar chart for testing."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["A", "B", "C"],
        y=[1, 2, 3],
        name="Series 1"
    ))
    fig.update_layout(
        title="Test Plot",
        xaxis_title="Category",
        yaxis_title="Value"
    )
    return fig

def test_convert_bar_to_pdf(simple_bar_figure, single_column_preset):
    """Test bar chart conversion to PDF."""
    converter = MatplotlibConverter(single_column_preset)
    result = converter.convert(simple_bar_figure, "pdf")

    assert result["success"] is True
    assert result["data"] is not None
    assert result["format"] == "pdf"
    assert len(result["data"]) > 0  # Non-empty PDF

def test_preserve_legend_position(simple_bar_figure, single_column_preset):
    """Verify legend position is preserved."""
    # Add legend config
    simple_bar_figure.update_layout(
        legend=dict(x=0.05, y=0.95, xanchor="left", yanchor="top")
    )

    converter = MatplotlibConverter(single_column_preset)
    result = converter.convert(simple_bar_figure, "pdf")

    assert result["success"] is True
    # Metadata should contain legend info
    assert "legend_position" in result["metadata"]
```

**Implementation** (Incremental):

**Step 3.1a: Basic Structure**
```python
class MatplotlibConverter(BaseConverter):
    """Converts Plotly figures to Matplotlib for LaTeX."""

    def convert(
        self,
        fig: go.Figure,
        format: Literal["pdf", "pgf", "eps"]
    ) -> ExportResult:
        """Convert Plotly figure to Matplotlib format."""
        try:
            mpl_fig = self._create_matplotlib_figure()
            self._configure_latex_rendering()
            self._convert_traces(fig, mpl_fig)
            self._apply_layout(fig, mpl_fig)
            data = self._export_figure(mpl_fig, format)
            return self._create_success_result(data, format)
        except Exception as e:
            logger.error(f"Matplotlib conversion failed: {e}", exc_info=True)
            return self._create_error_result(str(e), format)
        finally:
            plt.close('all')  # Clean up
```

**Step 3.1b: Figure Creation**
```python
def _create_matplotlib_figure(self) -> tuple[Figure, Axes]:
    """Create Matplotlib figure with LaTeX dimensions."""
    import matplotlib.pyplot as plt

    width = self.preset["width_inches"]
    height = self.preset["height_inches"]
    dpi = self.preset["dpi"]

    fig, ax = plt.subplots(
        figsize=(width, height),
        dpi=dpi
    )
    return fig, ax

def _configure_latex_rendering(self) -> None:
    """Configure Matplotlib for LaTeX rendering."""
    import matplotlib as mpl
    from matplotlib import rc

    # Enable LaTeX rendering
    rc('text', usetex=True)
    rc('font', family=self.preset["font_family"])
    rc('font', size=self.preset["font_size_base"])
    rc('axes', labelsize=self.preset["font_size_labels"])
    rc('xtick', labelsize=self.preset["font_size_ticks"])
    rc('ytick', labelsize=self.preset["font_size_ticks"])
    rc('legend', fontsize=self.preset["font_size_labels"])
```

**Step 3.1c: Trace Conversion**
```python
def _convert_traces(
    self,
    plotly_fig: go.Figure,
    mpl_tuple: tuple[Figure, Axes]
) -> None:
    """Convert Plotly traces to Matplotlib."""
    fig, ax = mpl_tuple

    for trace in plotly_fig.data:
        if trace.type == "bar":
            self._convert_bar_trace(trace, ax)
        elif trace.type == "scatter":
            self._convert_scatter_trace(trace, ax)
        elif trace.type == "line":
            self._convert_line_trace(trace, ax)
        else:
            logger.warning(f"Unsupported trace type: {trace.type}")

def _convert_bar_trace(self, trace: go.Bar, ax: Axes) -> None:
    """Convert bar trace."""
    x = trace.x if trace.x is not None else []
    y = trace.y if trace.y is not None else []

    ax.bar(
        x=range(len(x)),
        height=y,
        label=trace.name or "",
        color=trace.marker.color if trace.marker else None,
        width=0.8,
        linewidth=self.preset["line_width"]
    )
    ax.set_xticks(range(len(x)))
    ax.set_xticklabels(x, rotation=45, ha='right')
```

**Validation**:
```bash
pytest tests/unit/export/converters/test_matplotlib_converter.py::test_convert_bar_to_pdf -v
mypy src/plotting/export/converters/matplotlib_converter.py --strict
```

---

#### **Task 3.2: Layout Application** ✅ Test First
**Objective**: Apply Plotly layout config to Matplotlib figure

**Test Strategy**:
```python
def test_apply_axis_titles(simple_bar_figure, single_column_preset):
    """Verify axis titles are preserved."""
    simple_bar_figure.update_layout(
        xaxis_title="Custom X",
        yaxis_title="Custom Y"
    )

    converter = MatplotlibConverter(single_column_preset)
    result = converter.convert(simple_bar_figure, "pdf")

    assert result["success"] is True
    assert "xlabel" in result["metadata"]
    assert result["metadata"]["xlabel"] == "Custom X"

def test_apply_axis_ranges(simple_bar_figure, single_column_preset):
    """Verify axis ranges (zoom) are preserved."""
    simple_bar_figure.update_layout(
        xaxis_range=[0, 2],
        yaxis_range=[0, 50]
    )

    converter = MatplotlibConverter(single_column_preset)
    result = converter.convert(simple_bar_figure, "pdf")

    assert result["success"] is True
```

**Implementation**:
```python
def _apply_layout(
    self,
    plotly_fig: go.Figure,
    mpl_tuple: tuple[Figure, Axes]
) -> None:
    """Apply layout settings from Plotly config."""
    fig, ax = mpl_tuple
    layout = plotly_fig.layout

    # Titles
    if layout.title and layout.title.text:
        ax.set_title(layout.title.text)
    if layout.xaxis and layout.xaxis.title:
        ax.set_xlabel(layout.xaxis.title.text)
    if layout.yaxis and layout.yaxis.title:
        ax.set_ylabel(layout.yaxis.title.text)

    # Axis ranges (zoom levels)
    if layout.xaxis and layout.xaxis.range:
        ax.set_xlim(layout.xaxis.range)
    if layout.yaxis and layout.yaxis.range:
        ax.set_ylim(layout.yaxis.range)

    # Legend
    if layout.showlegend:
        self._apply_legend(layout, ax)

    # Grid
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

def _apply_legend(self, layout: go.Layout, ax: Axes) -> None:
    """Apply legend configuration."""
    legend_config = LayoutMapper.map_legend(layout.legend.to_plotly_json())
    ax.legend(**legend_config)
```

**Validation**:
```bash
pytest tests/unit/export/converters/test_matplotlib_converter.py::test_apply_* -v
```

---

#### **Task 3.3: Export Formats (PDF/PGF/EPS)** ✅ Test First
**Objective**: Support multiple export formats

**Test Strategy**:
```python
@pytest.mark.parametrize("format", ["pdf", "pgf", "eps"])
def test_export_format(simple_bar_figure, single_column_preset, format):
    """Test export to different formats."""
    converter = MatplotlibConverter(single_column_preset)
    result = converter.convert(simple_bar_figure, format)

    assert result["success"] is True
    assert result["format"] == format
    assert len(result["data"]) > 0

def test_pgf_format_is_text():
    """Verify PGF format produces text file."""
    # PGF should be text-based (LaTeX commands)
    converter = MatplotlibConverter(single_column_preset)
    result = converter.convert(simple_bar_figure, "pgf")

    # Try to decode as UTF-8
    text = result["data"].decode('utf-8')
    assert "\\begin{pgfpicture}" in text  # PGF signature
```

**Implementation**:
```python
def _export_figure(
    self,
    mpl_tuple: tuple[Figure, Axes],
    format: Literal["pdf", "pgf", "eps"]
) -> bytes:
    """Export Matplotlib figure to specified format."""
    fig, ax = mpl_tuple
    buf = io.BytesIO()

    export_kwargs = {
        "bbox_inches": "tight",
        "pad_inches": 0.05
    }

    if format == "pdf":
        fig.savefig(
            buf,
            format="pdf",
            metadata={"Creator": "RING-5 LaTeX Export"},
            **export_kwargs
        )
    elif format == "pgf":
        # PGF: Best for LaTeX (vector + TeX fonts)
        fig.savefig(buf, format="pgf", **export_kwargs)
    elif format == "eps":
        # EPS: Legacy format for older journals
        fig.savefig(buf, format="eps", **export_kwargs)
    else:
        raise ValueError(f"Unsupported format: {format}")

    buf.seek(0)
    return buf.read()
```

**Validation**:
```bash
pytest tests/unit/export/converters/test_matplotlib_converter.py -v
```

---

### **PHASE 4: Legacy Code Removal & Migration** (1-2 hours)

#### **Task 4.1: Remove Legacy Kaleido Export Code** ⚠️ BREAKING CHANGE
**Objective**: Delete old Kaleido-based export system, migrate existing usage

**Files to DELETE**:
- `src/plotting/export/export_service_legacy.py` (formerly export.py)
- Any references to Kaleido in codebase
- Kaleido dependency from requirements

**Files to UPDATE**:
- `src/web/ui/components/plot_controls.py` - Update export button handler
- `pyproject.toml` - Remove `kaleido>=1.2.0` dependency
- Any tests using old export API

**Migration Strategy**:
```python
# OLD (Kaleido):
from src.plotting.export import ExportService
export_service = ExportService()
data = export_service.export_figure(fig, "pdf")

# NEW (Matplotlib):
from src.plotting.export import LaTeXExportService
from src.plotting.export.presets import PresetManager

export_service = LaTeXExportService()
preset = PresetManager.load_preset("single_column")
result = export_service.export(
    figure=fig,
    preset=preset,
    format="pdf",
    preserve_layout=True
)
if result["success"]:
    data = result["data"]
```

**Testing Strategy**:
- Verify all existing tests pass with new API
- Ensure no imports of Kaleido remain
- Check that PDF exports still work end-to-end

**Validation**:
```bash
# Verify no Kaleido imports
grep -r "import kaleido" src/
grep -r "from kaleido" src/
# Should return nothing

# Run all tests
pytest tests/ -v
```

---

### **PHASE 5: Factory & Service Layer** (2-3 hours)

#### **Task 5.1: Converter Factory** ✅ Test First
**Objective**: Factory pattern for creating converters

**Files**:
- `src/plotting/export/converters/factory.py`
- `tests/unit/export/converters/test_factory.py`

**Test Strategy**:
```python
def test_factory_creates_matplotlib_converter():
    """Verify factory creates Matplotlib converter."""
    preset = PresetManager.load_preset("single_column")
    converter = ConverterFactory.create(
        format="pdf",
        preset=preset
    )
    assert isinstance(converter, MatplotlibConverter)

def test_factory_creates_pgf_converter():
    """Verify factory handles PGF format (uses Matplotlib)."""
    preset = PresetManager.load_preset("single_column")
    converter = ConverterFactory.create(
        format="pgf",
        preset=preset
    )
    assert isinstance(converter, KaleidoConverter)

def test_factory_validates_preset():
    """Verify factory validates preset before creating converter."""
    invalid_preset = {}  # Missing required fields
    with pytest.raises(ValueError):
        ConverterFactory.create(use_matplotlib=True, preset=invalid_preset)
```

**Implementation**:
```python
class ConverterFactory:
    """Factory for creating figure converters."""

    @staticmethod
    def create(
        use_matplotlib: bool,
        preset: LaTeXPreset
    ) -> BaseConverter:
        """
        Create appropriate converter based on configuration.

        Args:
            use_matplotlib: If True, use Matplotlib converter
            preset: LaTeX export preset configuration

        Returns:
            Converter instance

        Raises:
            ValueError: If preset is invalid
        """
        # Validate preset first
        PresetManager.validate_preset(preset)

        if use_matplotlib:
            return MatplotlibConverter(preset)
        else:
            return KaleidoConverter(preset)

    @staticmethod
    def get_available_converters() -> list[str]:
        """Return list of available converter types."""
        return ["matplotlib", "kaleido"]
```

**Validation**:
```bash
pytest tests/unit/export/converters/test_factory.py -v
mypy src/plotting/export/converters/factory.py --strict
```

---

#### **Task 5.2: LaTeX Export Service (Facade)** ✅ Test First
**Objective**: Single entry point for LaTeX export

**Files**:
- `src/plotting/export/latex_export_service.py`
- `tests/unit/export/test_latex_export_service.py`

**Test Strategy**:
```python
def test_export_with_preset_name():
    """Test export using preset name."""
    service = LaTeXExportService()
    fig = create_sample_figure()

    result = service.export(
        fig=fig,
        preset="single_column",
        format="pdf",
        use_matplotlib=True
    )

    assert result["success"] is True
    assert result["format"] == "pdf"

def test_export_with_custom_preset():
    """Test export with custom preset dict."""
    service = LaTeXExportService()
    fig = create_sample_figure()

    custom_preset: LaTeXPreset = {
        "width_inches": 4.0,
        "height_inches": 3.0,
        # ... all required fields
    }

    result = service.export(
        fig=fig,
        preset=custom_preset,
        format="pdf",
        use_matplotlib=True
    )

    assert result["success"] is True

def test_export_preserves_layout():
    """Verify export preserves Plotly layout decisions."""
    service = LaTeXExportService()
    fig = create_sample_figure()

    # User adjusts legend position interactively
    fig.update_layout(
        legend=dict(x=0.05, y=0.95, xanchor="left", yanchor="top")
    )

    result = service.export(
        fig=fig,
        preset="single_column",
        format="pdf",
        use_matplotlib=True
    )

    assert result["success"] is True
    # Metadata should contain preserved layout info
    assert "legend_x" in result["metadata"]["layout_preserved"]
```

**Implementation**:
```python
class LaTeXExportService:
    """
    Facade for LaTeX-optimized plot export.

    Single entry point for all export operations.
    Delegates to appropriate converter based on configuration.
    """

    def __init__(self) -> None:
        """Initialize service."""
        self.preset_manager = PresetManager()

    def export(
        self,
        fig: go.Figure,
        preset: Union[str, LaTeXPreset],
        format: Literal["pdf", "pgf", "eps", "png", "svg"],
        use_matplotlib: bool = True
    ) -> ExportResult:
        """
        Export Plotly figure for LaTeX inclusion.

        Args:
            fig: Plotly figure (with user's interactive adjustments)
            preset: Preset name or custom preset dict
            format: Output format
            use_matplotlib: If True, use Matplotlib for better LaTeX integration

        Returns:
            ExportResult with data or error
        """
        try:
            # Load or validate preset
            if isinstance(preset, str):
                preset_dict = self.preset_manager.load_preset(preset)
            else:
                preset_dict = preset
                self.preset_manager.validate_preset(preset_dict)

            # Create converter
            converter = ConverterFactory.create(
                use_matplotlib=use_matplotlib and format in ["pdf", "pgf", "eps"],
                preset=preset_dict
            )

            # Convert
            result = converter.convert(fig, format)

            # Add layout preservation metadata
            result["metadata"]["layout_preserved"] = self._extract_layout(fig)

            return result

        except Exception as e:
            logger.error(f"LaTeX export failed: {e}", exc_info=True)
            return ExportResult(
                success=False,
                data=None,
                format=format,
                error=str(e),
                metadata={}
            )

    def _extract_layout(self, fig: go.Figure) -> dict[str, Any]:
        """Extract preserved layout settings from Plotly figure."""
        layout = fig.layout
        return {
            "legend_x": layout.legend.x if layout.legend else None,
            "legend_y": layout.legend.y if layout.legend else None,
            "xaxis_range": layout.xaxis.range if layout.xaxis else None,
            "yaxis_range": layout.yaxis.range if layout.yaxis else None,
        }

    def get_available_presets(self) -> list[str]:
        """Return list of available preset names."""
        return self.preset_manager.list_presets()
```

**Validation**:
```bash
pytest tests/unit/export/test_latex_export_service.py -v
mypy src/plotting/export/latex_export_service.py --strict
```

---

### **PHASE 6: UI Integration** (2-3 hours)

#### **Task 6.1: Export Dialog Component** ✅ Test First (UI Logic)
**Objective**: UI component for LaTeX export options

**Files**:
- `src/web/ui/components/export_dialog.py`
- `tests/ui_logic/test_export_dialog.py` (logic tests, not widget tests)

**Test Strategy**:
```python
def test_build_export_config():
    """Test building export config from UI selections."""
    ui_state = {
        "preset": "single_column",
        "format": "pdf",
        "use_matplotlib": True
    }

    config = ExportDialog.build_export_config(ui_state)
    assert config["preset"] == "single_column"
    assert config["format"] == "pdf"

def test_validate_export_config():
    """Test export config validation."""
    invalid_config = {"preset": "invalid"}

    is_valid, error = ExportDialog.validate_export_config(invalid_config)
    assert not is_valid
    assert "Unknown preset" in error
```

**Implementation**:
```python
class ExportDialog:
    """UI component for LaTeX export configuration."""

    @staticmethod
    def render(plot: BasePlot, key_prefix: str = "export") -> Optional[ExportResult]:
        """
        Render export dialog UI.

        Args:
            plot: Plot to export
            key_prefix: Prefix for widget keys

        Returns:
            ExportResult if export was triggered, None otherwise
        """
        st.markdown("### 📐 Export for LaTeX")

        col1, col2, col3 = st.columns(3)

        with col1:
            preset = st.selectbox(
                "Preset",
                options=LaTeXExportService().get_available_presets(),
                key=f"{key_prefix}_preset_{plot.plot_id}",
                help="Journal/document format"
            )

        with col2:
            format = st.selectbox(
                "Format",
                options=["pdf", "pgf", "eps"],
                key=f"{key_prefix}_format_{plot.plot_id}",
                help="PGF is best for LaTeX (vector + TeX fonts)"
            )

        with col3:
            use_mpl = st.checkbox(
                "Use Matplotlib",
                value=True,
                key=f"{key_prefix}_mpl_{plot.plot_id}",
                help="Better font control for LaTeX"
            )

        # Preview dimensions
        service = LaTeXExportService()
        preset_config = service.preset_manager.load_preset(preset)
        st.caption(
            f"📏 Output size: {preset_config['width_inches']:.2f}\" × "
            f"{preset_config['height_inches']:.2f}\" @ {preset_config['dpi']} DPI"
        )

        # Export button
        if st.button(
            "📥 Export for LaTeX",
            key=f"{key_prefix}_btn_{plot.plot_id}",
            type="primary"
        ):
            if plot.last_generated_fig is None:
                st.error("No figure to export. Generate plot first.")
                return None

            with st.spinner("Exporting..."):
                result = service.export(
                    fig=plot.last_generated_fig,
                    preset=preset,
                    format=format,
                    use_matplotlib=use_mpl
                )

            if result["success"]:
                # Render download button
                st.download_button(
                    label=f"💾 Download {format.upper()}",
                    data=result["data"],
                    file_name=f"{plot.name}_latex.{format}",
                    mime=_get_mime_type(format),
                    key=f"{key_prefix}_dl_{plot.plot_id}"
                )
                st.success("✅ Export complete!")
            else:
                st.error(f"Export failed: {result['error']}")

            return result

        return None

    @staticmethod
    def build_export_config(ui_state: dict[str, Any]) -> dict[str, Any]:
        """Build export config from UI state (for testing)."""
        return {
            "preset": ui_state["preset"],
            "format": ui_state["format"],
            "use_matplotlib": ui_state.get("use_matplotlib", True)
        }
```

**Validation**:
```bash
pytest tests/ui_logic/test_export_dialog.py -v
mypy src/web/ui/components/export_dialog.py --strict
```

---

#### **Task 6.2: Integrate into Plot Renderer** ✅ Test Integration
**Objective**: Add LaTeX export to plot UI

**Files**:
- `src/plotting/plot_renderer.py` (modify existing)
- `tests/integration/test_latex_export_integration.py`

**Test Strategy**:
```python
def test_latex_export_from_plot_ui():
    """Integration test: export from plot UI."""
    # Create plot with data
    plot = create_test_plot()
    plot.processed_data = load_test_data()

    # Generate figure
    plot.generate_figure()

    # Export via service
    service = LaTeXExportService()
    result = service.export(
        fig=plot.last_generated_fig,
        preset="single_column",
        format="pdf",
        use_matplotlib=True
    )

    assert result["success"] is True
    assert len(result["data"]) > 1000  # Non-trivial PDF
```

**Implementation**:
```python
# In plot_renderer.py, add after existing download button

@staticmethod
def render_plot(plot: BasePlot, should_generate: bool = False) -> None:
    """Render plot with LaTeX export option."""
    # ... existing rendering code ...

    # Add LaTeX export section
    with st.expander("📐 Export for Publications", expanded=False):
        ExportDialog.render(plot, key_prefix=f"latex_export_{plot.plot_id}")
```

**Validation**:
```bash
pytest tests/integration/test_latex_export_integration.py -v
```

---

### **PHASE 7: Documentation & Validation** (2-3 hours)

#### **Task 7.1: API Documentation**
**Files**:
- `docs/api/LaTeX-Export-API.md`
- Update `docs/api/Plotting-API.md`

#### **Task 7.2: User Guide**
**Files**:
- `docs/LaTeX-Export-Guide.md`
- Include example LaTeX snippets for `\includegraphics`

#### **Task 7.3: Integration Tests**
**Files**:
- `tests/integration/test_latex_export_workflow.py`

**Test Strategy**:
```python
def test_complete_export_workflow():
    """End-to-end test: create plot → configure → export → validate."""
    # 1. Create plot
    plot = GroupedBarPlot(plot_id=1, name="test")
    plot.processed_data = load_sample_data()
    plot.config = {
        "x": "benchmark",
        "y": "ipc",
        "group": "config",
        "legend_x": 0.05,
        "legend_y": 0.95
    }

    # 2. Generate figure
    plot.generate_figure()

    # 3. Export for LaTeX
    service = LaTeXExportService()
    result = service.export(
        fig=plot.last_generated_fig,
        preset="single_column",
        format="pdf",
        use_matplotlib=True
    )

    # 4. Validate
    assert result["success"] is True
    assert result["metadata"]["layout_preserved"]["legend_x"] == 0.05

    # 5. Verify PDF structure
    pdf_data = result["data"]
    assert b"PDF" in pdf_data[:10]  # PDF header
    assert len(pdf_data) > 5000  # Reasonable size
```

---

### **PHASE 8: Performance Optimization** (1-2 hours)

#### **Task 8.1: Caching**
**Objective**: Cache converted figures to avoid redundant conversions

**Implementation**:
```python
from functools import lru_cache
import hashlib

class LaTeXExportService:

    @staticmethod
    def _compute_figure_hash(fig: go.Figure) -> str:
        """Compute hash of figure for caching."""
        fig_json = fig.to_json()
        return hashlib.md5(fig_json.encode()).hexdigest()[:12]

    @lru_cache(maxsize=32)
    def _cached_export(
        self,
        fig_hash: str,
        preset_str: str,
        format: str,
        use_matplotlib: bool
    ) -> ExportResult:
        """Cached export operation."""
        # Actual export logic
        pass
```

---

## 📊 Testing Strategy Summary

### Test Pyramid

```
           E2E Tests (5)
         /              \
    Integration (15)     UI Tests (5)
   /                \              \
Unit Tests (50)      UI Logic (10)
```

### Coverage Requirements
- **Unit Tests**: 90%+ coverage
- **Integration Tests**: All critical paths
- **UI Logic Tests**: All config building/validation

### Test Execution Order
```bash
# Phase 1-2: Foundation
pytest tests/unit/export/test_preset_*.py -v
pytest tests/unit/export/test_layout_mapper.py -v

# Phase 3: Matplotlib
pytest tests/unit/export/converters/test_matplotlib_converter.py -v

# Phase 4-5: Integration
pytest tests/unit/export/test_latex_export_service.py -v

# Phase 6-7: Full system
pytest tests/integration/test_latex_export_*.py -v

# All together
pytest tests/unit/export/ tests/integration/test_latex_export_*.py -v --cov=src/plotting/export
```

---

## 🎯 Success Criteria

### Functional Requirements
- ✅ Export figures to PDF, PGF, EPS with correct dimensions
- ✅ Preserve all user layout adjustments (legend, zoom, colors)
- ✅ Support journal-specific presets
- ✅ Maintain font consistency with LaTeX documents
- ✅ Export completes in <5 seconds for typical plots

### Quality Requirements
- ✅ 90%+ test coverage
- ✅ All mypy --strict checks pass
- ✅ Zero pylint/flake8 violations
- ✅ All type hints complete
- ✅ Comprehensive docstrings
- ✅ No performance regression (export <5s)

### Documentation Requirements
- ✅ API documentation complete
- ✅ User guide with examples
- ✅ LaTeX integration snippets
- ✅ Troubleshooting guide

---

## 🚀 Execution Plan

### Week 1: Foundation (Phases 1-2)
- Day 1-2: Type schemas, presets, layout mapper
- Day 3: Base converter + tests

### Week 2: Core Implementation (Phases 3-5)
- Day 1-2: Matplotlib converter (basic traces)
- Day 3: Layout application + export formats
- Day 4: Kaleido refactor, factory, service

### Week 3: Integration & Polish (Phases 6-8)
- Day 1: UI integration
- Day 2: Documentation
- Day 3: Performance optimization
- Day 4: Final testing & validation

---

## 📦 Dependencies

### New Dependencies
```toml
[tool.poetry.dependencies]
# Matplotlib with LaTeX support
matplotlib = "^3.8.0"

[tool.poetry.group.dev.dependencies]
# Keep existing test dependencies
pytest = "^7.4.0"
pytest-cov = "^4.1.0"
```

### System Requirements
- LaTeX distribution (for PGF/TeX rendering)
  - Linux: `texlive-latex-base texlive-fonts-recommended`
  - macOS: `brew install --cask mactex`
  - Windows: MiKTeX or TeX Live

---

## 🔍 Risk Assessment

### High Risk
- **Matplotlib LaTeX rendering**: May fail if LaTeX not installed
  - Mitigation: Graceful fallback to Kaleido
  - Detection: Check for LaTeX at startup

### Medium Risk
- **Complex trace conversion**: Some Plotly features may not map to Matplotlib
  - Mitigation: Comprehensive test suite with various plot types
  - Fallback: Kaleido for unsupported features

### Low Risk
- **Performance**: Matplotlib conversion might be slow
  - Mitigation: Caching + async export (future)
  - Acceptable: <5s for typical plots

---

## 📋 Checklist Before Merge

- [ ] All tests passing (unit + integration)
- [ ] mypy --strict clean
- [ ] flake8 clean
- [ ] Test coverage ≥90%
- [ ] Documentation complete
- [ ] Performance validated (<5s exports)
- [ ] UI tested manually in Streamlit
- [ ] Example LaTeX document validates output
- [ ] Pre-commit hooks pass
- [ ] Code review completed

---

## 🎓 Learning Resources

- [Matplotlib PGF Backend](https://matplotlib.org/stable/tutorials/text/pgf.html)
- [Plotly Figure Reference](https://plotly.com/python/reference/)
- [LaTeX Graphics Guide](https://en.wikibooks.org/wiki/LaTeX/Importing_Graphics)
- [Strategy Pattern in Python](https://refactoring.guru/design-patterns/strategy/python)

---

This plan follows RING-5's strict principles:
✅ TDD approach (tests first)
✅ Layered architecture (no UI in domain layer)
✅ Strong typing (mypy strict)
✅ Small incremental chunks
✅ Zero hallucination (real tests, real code)
✅ SOLID principles (Strategy, Factory, Facade)
✅ Comprehensive testing

**Ready to begin implementation?** Let's start with Phase 1, Task 1.1: Define Type Schemas.
