"""Canonical arithmetic identifiers shared by domain services and presentation."""

from enum import StrEnum


class ArithmeticOperation(StrEnum):
    """Exact identifiers for binary column arithmetic."""

    DIVISION = "Division"
    SUM = "Sum"
    SUBTRACTION = "Subtraction"
    MULTIPLICATION = "Multiplication"


class MixerOperation(StrEnum):
    """Exact identifiers for column aggregation and label concatenation."""

    SUM = "Sum"
    MEAN = "Mean"
    CONCATENATE = "Concatenate"
