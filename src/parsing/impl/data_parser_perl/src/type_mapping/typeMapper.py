from src.parsing.impl.data_parser_perl.src.type_mapping.confType import confType
from src.parsing.impl.data_parser_perl.src.type_mapping.types.configuration import (
    Configuration,
)
from src.parsing.impl.data_parser_perl.src.type_mapping.types.distribution import (
    Distribution,
)
from src.parsing.impl.data_parser_perl.src.type_mapping.types.scalar import (
    Scalar,
)
from src.parsing.impl.data_parser_perl.src.type_mapping.types.vector import (
    Vector,
)


class TypeMapper:
    def __init__(self) -> None:
        raise NotImplementedError("TypeMapper class cannot be instantiated...")

    @classmethod
    def map(self, varType: str, repeat: int = 1, **kwargs) -> confType:
        if varType == "vector":
            # Get the vector entries
            entries = kwargs.get("vectorEntries")
            if entries is None:
                raise RuntimeError("VECTOR: Vector entries not specified...")
            return Vector(repeat, entries)
        elif varType == "distribution":
            # Get the maximum and minimum values
            maximum = kwargs.get("maximum")
            minimum = kwargs.get("minimum")
            if maximum is None or minimum is None:
                raise RuntimeError("DISTRIBUTION: Maximum or minimum not specified...")
            return Distribution(repeat, maximum, minimum)
        elif varType == "configuration":
            if kwargs.get("onEmpty") is None:
                raise RuntimeError("CONFIGURATION: OnEmpty not specified...")
            return Configuration(repeat, kwargs.get("onEmpty"))
        elif varType == "scalar":
            return Scalar(repeat)
        else:
            raise TypeError("Unknown type for variable type: " + varType)
