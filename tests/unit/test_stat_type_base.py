"""Tests for StatType base + StatTypeRegistry — target 78% → 95%+."""

import pytest

from src.core.parsing.gem5.types.base import StatType, StatTypeRegistry, register_type


class TestStatTypeRegistry:
    """Tests for the StatTypeRegistry."""

    def test_create_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown stat type"):
            StatTypeRegistry.create("definitely_not_a_real_type")

    def test_get_types_returns_list(self) -> None:
        types = StatTypeRegistry.get_types()
        assert isinstance(types, list)
        assert len(types) > 0

    def test_create_known_type(self) -> None:
        """Create a known registered type."""
        types = StatTypeRegistry.get_types()
        if types:
            instance = StatTypeRegistry.create(types[0])
            assert isinstance(instance, StatType)

    def test_register_decorator(self) -> None:
        """Custom type can be registered via decorator."""

        @register_type("test_custom_42")
        class CustomType(StatType):
            pass

        assert "test_custom_42" in StatTypeRegistry.get_types()
        inst = StatTypeRegistry.create("test_custom_42")
        assert isinstance(inst, CustomType)
        # Clean up
        StatTypeRegistry._types.pop("test_custom_42", None)


class TestStatType:
    """Tests for the StatType base class."""

    def test_init_defaults(self) -> None:
        st = StatType(repeat=3)
        assert st.repeat == 3
        assert st.content == []

    def test_content_append(self) -> None:
        st = StatType(repeat=2)
        st.content = 10
        st.content = 20
        assert st.content == [10, 20]

    def test_balance_content_pads_with_zeros(self) -> None:
        st = StatType(repeat=3)
        st.content = 42
        st.balance_content()
        assert st.content == [42, 0, 0]

    def test_balance_content_exact_match(self) -> None:
        st = StatType(repeat=2)
        st.content = 1
        st.content = 2
        st.balance_content()
        assert st.content == [1, 2]

    def test_balance_content_too_many_raises(self) -> None:
        st = StatType(repeat=1)
        st.content = 10
        st.content = 20
        with pytest.raises(RuntimeError, match="More values"):
            st.balance_content()

    def test_reduce_duplicates_mean(self) -> None:
        st = StatType(repeat=4)
        for v in [10, 20, 30, 40]:
            st.content = v
        st.balance_content()
        st.reduce_duplicates()
        assert st.reduced_content == 25.0

    def test_reduce_duplicates_empty(self) -> None:
        st = StatType(repeat=1)
        st.balance_content()
        st.reduce_duplicates()
        assert st.reduced_content == 0  # [0] padded -> 0/1

    def test_reduce_duplicates_non_numeric(self) -> None:
        st = StatType(repeat=1)
        st.content = "hello"
        st.balance_content()
        st.reduce_duplicates()
        assert st.reduced_content == "hello"

    def test_reduced_content_before_balance_raises(self) -> None:
        st = StatType(repeat=1)
        st.content = 5
        with pytest.raises(AttributeError, match="balance_content"):
            _ = st.reduced_content

    def test_reduced_content_before_reduce_raises(self) -> None:
        st = StatType(repeat=1)
        st.content = 5
        st.balance_content()
        with pytest.raises(AttributeError, match="reduce_duplicates"):
            _ = st.reduced_content

    def test_setattr_invalid_raises(self) -> None:
        st = StatType(repeat=1)
        with pytest.raises(AttributeError, match="Cannot set attribute"):
            st.foo = "bar"  # type: ignore[attr-defined]

    def test_entries_returns_none(self) -> None:
        st = StatType()
        assert st.entries is None

    def test_str_repr(self) -> None:
        st = StatType(repeat=1)
        st.content = 42
        s = str(st)
        assert "base" in s
        assert "42" in s
        assert repr(st) == s

    def test_repeat_int_conversion(self) -> None:
        st = StatType(repeat=2.0)  # type: ignore[arg-type]
        assert st.repeat == 2
        assert isinstance(st.repeat, int)

    def test_reduce_empty_content(self) -> None:
        """Reduce with truly empty content returns NA."""
        st = StatType(repeat=1)
        # Don't add any content, and skip balance (which would pad)
        object.__setattr__(st, "_balanced", True)
        st.reduce_duplicates()
        assert st.reduced_content == "NA"
