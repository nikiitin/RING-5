from src.data_parser.src.impl.data_parser_perl.src.type_mapping.confType import confType
from src.data_parser.src.impl.data_parser_perl.src.type_mapping.types.vector import Vector
from src.data_parser.src.impl.data_parser_perl.src.type_mapping.types.configuration import Configuration
from src.data_parser.src.impl.data_parser_perl.src.type_mapping.types.scalar import Scalar
from src.data_parser.src.impl.data_parser_perl.src.type_mapping.types.distribution import Distribution
class TypeMapper():
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
            return Configuration(repeat)
        elif varType == "scalar":
            return Scalar(repeat)
        else:
            raise TypeError("Unknown type for variable type: " +
                            varType)