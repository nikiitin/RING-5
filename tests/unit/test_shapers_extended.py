import numpy as np
import pandas as pd

from src.core.services.shapers.impl.mean import Mean
from src.core.services.shapers.impl.sort import Sort
from src.core.services.shapers.impl.transformer import Transformer


class TestTransformer:
    """Test Transformer shaper."""

    # [test->req~ring5.shaping.transformer~1]

    def test_scalar_conversion(self) -> None:
        """Test converting string to scalar."""
        df = pd.DataFrame({"A": ["1", "2.5", "3"]})
        transformer = Transformer({"column": "A", "target_type": "scalar"})
        result = transformer(df)

        assert pd.api.types.is_numeric_dtype(result["A"])
        assert result["A"].iloc[1] == 2.5

    def test_scalar_conversion_invalid(self) -> None:
        """Test converting invalid string to scalar."""
        df = pd.DataFrame({"A": ["1", "foo", "3"]})
        transformer = Transformer({"column": "A", "target_type": "scalar"})

        # Standard pd.to_numeric with errors='coerce' produces NaN
        result = transformer(df)
        assert pd.isna(result["A"].iloc[1])

    def test_factor_conversion_ordering(self) -> None:
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

    def test_geometric_mean(self) -> None:
        """Test geometric mean calculation."""
        # [test->req~ring5.shaping.mean~1]
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
        assert np.isclose(pd.Series(mean_row["Value"]).iloc[0], 10.0)

    def test_harmonic_mean(self) -> None:
        """Test harmonic mean calculation."""
        # [test->req~ring5.shaping.mean~1]
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
        assert np.isclose(pd.Series(mean_row["Value"]).iloc[0], 3.0)


class TestSortShaper:
    """Behavioral tests for explicit multi-column category ordering."""

    def test_reorders_rows_by_each_configured_category_order(self) -> None:
        # [test->req~ring5.shaping.sort~1]
        data = pd.DataFrame(
            {
                "group": ["B", "A", "B", "A"],
                "phase": ["warm", "hot", "hot", "warm"],
                "value": [1, 2, 3, 4],
            }
        )

        result = Sort({"order_dict": {"group": ["A", "B"], "phase": ["hot", "warm"]}})(data)

        assert list(zip(result["group"], result["phase"], strict=True)) == [
            ("A", "hot"),
            ("A", "warm"),
            ("B", "hot"),
            ("B", "warm"),
        ]
        assert data["group"].tolist() == ["B", "A", "B", "A"]
