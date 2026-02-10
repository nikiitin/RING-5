"""
Compliance test for TDD Chapter 1 rules.
Demonstrates: Solitary vs Sociable Unit Tests and the AAA pattern (Red-Green-Refactor context).
"""

from unittest.mock import Mock

# --- Domain Logic ---


class PriceCalculator:
    """A collaborator class."""

    def get_discount(self) -> float:
        return 0.10


class Order:
    """The System Under Test (SUT)."""

    def __init__(self, amount: float, calculator: PriceCalculator):
        self.amount = amount
        self.calculator = calculator

    def final_price(self) -> float:
        return self.amount * (1 - self.calculator.get_discount())


# --- Tests ---


def test_solitary_unit() -> None:
    """
    Solitary Unit Test: Mocks the collaborator (PriceCalculator).
    Pros: fast, isolated. Cons: coupled to implementation details (mocks).
    """
    # Arrange
    mock_calculator = Mock()
    mock_calculator.get_discount.return_value = 0.50  # 50% discount
    order = Order(100.0, mock_calculator)

    # Act
    price = order.final_price()

    # Assert
    assert price == 50.0


def test_sociable_unit() -> None:
    """
    Sociable Unit Test: Uses the real collaborator (PriceCalculator).
    Pros: realistic, robust to refactoring. Cons: slower if deps are heavy.
    """
    # Arrange
    real_calculator = PriceCalculator()  # 10% discount
    order = Order(100.0, real_calculator)

    # Act
    price = order.final_price()

    # Assert
    assert price == 90.0
