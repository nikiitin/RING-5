"""Test LaTeX character escaping in exported plots."""

import plotly.graph_objects as go

from src.web.pages.ui.plotting.export.converters.layout_mapper import LayoutMapper


class TestLaTeXEscaping:
    """Test that special LaTeX characters are properly escaped."""

    def test_escape_underscores(self) -> None:
        """Test that underscores are escaped."""
        text = "TS_RS"
        result = LayoutMapper._escape_latex(text)
        assert result == r"TS\_RS"

    def test_escape_percent(self) -> None:
        """Test that percent signs are escaped."""
        text = "50% done"
        result = LayoutMapper._escape_latex(text)
        assert result == r"50\% done"

    def test_escape_ampersand(self) -> None:
        """Test that ampersands are escaped."""
        text = "A & B"
        result = LayoutMapper._escape_latex(text)
        assert result == r"A \& B"

    def test_escape_dollar(self) -> None:
        """Test that dollar signs are escaped."""
        text = "$100"
        result = LayoutMapper._escape_latex(text)
        assert result == r"\$100"

    def test_escape_hash(self) -> None:
        """Test that hash symbols are escaped."""
        text = "#define"
        result = LayoutMapper._escape_latex(text)
        assert result == r"\#define"

    def test_escape_braces(self) -> None:
        """Test that curly braces are escaped."""
        text = "{value}"
        result = LayoutMapper._escape_latex(text)
        assert result == r"\{value\}"

    def test_escape_tilde(self) -> None:
        """Test that tildes are escaped."""
        text = "~/path"
        result = LayoutMapper._escape_latex(text)
        assert result == r"\textasciitilde{}/path"

    def test_escape_caret(self) -> None:
        """Test that carets are escaped."""
        text = "x^2"
        result = LayoutMapper._escape_latex(text)
        assert result == r"x\^{}2"

    def test_escape_backslash(self) -> None:
        """Test that backslashes are escaped."""
        text = r"C:\path"
        result = LayoutMapper._escape_latex(text)
        # r"C:\path" contains ['C', ':', '\\', 'p', 'a', 't', 'h']
        assert result == r"C:\textbackslash{}path"

    def test_escape_multiple_special_chars(self) -> None:
        """Test escaping text with multiple special characters."""
        text = "TS_RS (50% & $10)"
        result = LayoutMapper._escape_latex(text)
        assert result == r"TS\_RS (50\% \& \$10)"

    def test_escape_config_names(self) -> None:
        """Test escaping gem5 configuration names."""
        configs = ["TS_RS", "CID_RS", "PiC_RS", "HW_TM"]
        expected = [r"TS\_RS", r"CID\_RS", r"PiC\_RS", r"HW\_TM"]
        results = [LayoutMapper._escape_latex(cfg) for cfg in configs]
        assert results == expected

    def test_tick_labels_with_special_chars(self) -> None:
        """Test that tick labels with special characters are escaped in layout application."""
        # Create a simple figure with custom tick labels containing underscores
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[0, 1, 2], y=[10, 20, 30]))

        # Create layout with special characters in tick labels
        layout_dict = {
            "x_tickvals": [0, 1, 2],
            "x_ticktext": ["TS_RS", "CID_RS", "PiC_RS"],
            "y_tickvals": [0, 10, 20, 30],
            "y_ticktext": ["0", "10%", "20%", "30%"],
        }

        # Extract and apply layout
        import matplotlib.pyplot as plt

        _, ax = plt.subplots()

        LayoutMapper.apply_to_matplotlib(ax, layout_dict)  # ax first, layout second

        # Verify x tick labels are escaped (no wrapper needed)
        x_labels = [label.get_text() for label in ax.get_xticklabels()]
        assert r"TS\_RS" in x_labels
        assert r"CID\_RS" in x_labels
        assert r"PiC\_RS" in x_labels

        # Verify y tick labels are escaped
        y_labels = [label.get_text() for label in ax.get_yticklabels()]
        assert any(r"\%" in label for label in y_labels if label)

        plt.close()

    def test_annotations_with_special_chars(self) -> None:
        """Test that annotations with special characters are escaped."""
        # Create layout with annotation containing special characters
        layout_dict = {
            "annotations": [
                {
                    "text": "50% improvement",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                }
            ]
        }

        import matplotlib.pyplot as plt

        _, ax = plt.subplots()

        LayoutMapper.apply_to_matplotlib(ax, layout_dict)  # ax first, layout second

        # Verify annotation text is escaped (no wrapper needed)
        annotations = ax.texts
        assert len(annotations) == 1
        text = annotations[0].get_text()
        assert r"\%" in text

        plt.close()
