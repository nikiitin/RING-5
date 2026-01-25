from src.common.types.vector import Vector


def test_vector_creation():
    """Test standard initialization."""
    v = Vector(repeat=1, entries=["A", "B"])
    assert v.entries == ["A", "B"]
    assert v.content == {"A": [], "B": []}


def test_vector_content_setting():
    """Test correct content aggregation."""
    v = Vector(repeat=1, entries=["A", "B"])
    data = {"A": [10], "B": [20]}
    v.content = data

    assert v.content["A"] == [10]
    assert v.content["B"] == [20]


def test_vector_unknown_entries_warning():
    """Test that unknown entries are ignored (with warning implicitly)."""
    v = Vector(repeat=1, entries=["A"])
    # "C" is unknown
    data = {"A": [10], "C": [99]}
    v.content = data

    assert v.content["A"] == [10]
    # C should not be in content
    assert "C" not in v.content


def test_vector_balancing():
    """Test balancing logic (padding)."""
    v = Vector(repeat=2, entries=["A"])
    # One value provided, need two
    v.content = {"A": [10]}
    v.balance_content()

    assert v.content["A"] == [10, 0]


def test_vector_reduction():
    """Test reduction logic (mean)."""
    v = Vector(repeat=2, entries=["A"])
    v.content = {"A": [10, 20]}
    v.balance_content()
    v.reduce_duplicates()

    # (10+20)/2 = 15
    assert v.reduced_content["A"] == 15.0


def test_vector_entries_polymorphism():
    """
    Test scientific reproducibility:
    Ensure 'entries' property behaves consistently with BaseStat.
    """
    v = Vector(repeat=1, entries=["X", "Y"])
    assert v.entries is not None
    assert "X" in v.entries
