import numpy as np
import pandas as pd

from src.core.services.shapers.impl.mean import Mean
from src.core.services.shapers.impl.transformer import Transformer


class TestTransformer:
    """Test Transformer shaper."""

    def test_scalar_conversion(self):
        """Test converting string to scalar."""
        df = pd.DataFrame({"A": ["1", "2.5", "3"]})
        transformer = Transformer({"column": "A", "target_type": "scalar"})
        result = transformer(df)

        assert pd.api.types.is_numeric_dtype(result["A"])
        assert result["A"].iloc[1] == 2.5

    def test_scalar_conversion_invalid(self):
        """Test converting invalid string to scalar."""
        df = pd.DataFrame({"A": ["1", "foo", "3"]})
        transformer = Transformer({"column": "A", "target_type": "scalar"})

        # Standard pd.to_numeric with errors='coerce' produces NaN
        result = transformer(df)
        assert pd.isna(result["A"].iloc[1])

    def test_factor_conversion_ordering(self):
        """Test converting to factor with explicit ordering."""
        df = pd.DataFrame({"Grade": ["B", "A", "C", "A"]})

        # Explicit order: C < B < A
        transformer = Transformer(
            {"column": "Grade", "target_type": "factor", "order": ["C", "B", "A"]}
        )
        result = transformer(df)

        assert isinstance(result["Grade"].dtype, pd.CategoricalDtype)
        assert result["Grade"].cat.ordered
        # Compare using category codes (0=C, 1=B, 2=A based on defined order)
        assert result["Grade"].cat.codes.iloc[0] < result["Grade"].cat.codes.iloc[1]  # B < A
        assert result["Grade"].cat.codes.iloc[2] < result["Grade"].cat.codes.iloc[0]  # C < B


class TestMeanExtended:
    """Extended tests for Mean shaper."""

    def test_geometric_mean(self):
        """Test geometric mean calculation."""
        # 1, 10, 100 -> geomean = 10
        df = pd.DataFrame({"Group": ["A", "A", "A"], "Value": [1, 10, 100]})

        shaper = Mean(
            {
                "meanAlgorithm": "geomean",
                "meanVars": ["Value"],
                "groupingColumn": "Group",
                "replacingColumn": "Group",  # dummy
            }
        )

        result = shaper(df)
        # Should append a row
        mean_row = result[result["Group"] == "geomean"]
        assert len(mean_row) == 1
        assert np.isclose(mean_row["Value"].iloc[0], 10.0)

    def test_harmonic_mean(self):
        """Test harmonic mean calculation."""
        # 2, 6 -> harmean = 2 / (1/2 + 1/6) = 2 / (3/6 + 1/6) = 2 / (4/6) = 12/4 = 3
        df = pd.DataFrame({"Group": ["A", "A"], "Value": [2.0, 6.0]})

        shaper = Mean(
            {
                "meanAlgorithm": "hmean",
                "meanVars": ["Value"],
                "groupingColumn": "Group",
                "replacingColumn": "Group",
            }
        )

        result = shaper(df)
        mean_row = result[result["Group"] == "hmean"]
        assert np.isclose(mean_row["Value"].iloc[0], 3.0)
