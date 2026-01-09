from typing import Any

from src.parsing.impl.data_parser_perl.src.type_mapping.confType import confType


class Scalar(confType):
    # Scalar variable can be a float or an int
    # So, we need to override the __setattr__ method
    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name == "content":
            try:
                __value = int(__value)
            except Exception:
                try:
                    __value = float(__value)
                except Exception as e_float:
                    raise TypeError(
                        "SCALAR: Variable non-convertible to float or int... value: "
                        + str(__value)
                        + " type: "
                        + str(type(__value))
                        + " field: "
                        + __name
                    ) from e_float
            # Put the value inside the list. This value maps directly
            # to a repeated field in the stats file. In the end it will
            # be one only field in the csv file
            self.__dict__["content"].append(__value)
        elif (
            __name == "balancedContent"
            or __name == "reducedDuplicates"
            or __name == "reducedContent"
        ):
            # Default behaviour
            super().__setattr__(__name, __value)
        else:
            raise AttributeError("Scalar variable has no attribute " + __name)

    def __str__(self):
        return super().__str__()

    def balanceContent(self) -> None:
        super().balanceContent()
        # Get the length of the content
        # If the length is less than the repeat, fill the missing values with 0
        # If the length is greater than the repeat, raise an error
        if len(self.content) < int(self.repeat):
            # Fill the missing values with 0
            missing_values = int(self.repeat) - len(self.content)
            if missing_values > 0:
                self.content.extend([0] * missing_values)
        elif len(self.content) > int(self.repeat):
            raise RuntimeError(
                "SCALAR: Variable has more values than expected... values: "
                + str(self.content)
                + " length: "
                + str(len(self.content))
                + " repeat: "
                + str(self.repeat)
            )

    def reduceDuplicates(self):
        super().reduceDuplicates()
        # Reduce the duplicates by doing arithmetic mean
        self.reducedContent = 0
        for i in range(0, int(self.repeat)):
            self.reducedContent += int(self.content[i])
        self.reducedContent = self.reducedContent / int(self.repeat)
