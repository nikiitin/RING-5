from src.data_parser.src.impl.data_parser_perl.src.type_mapping.confType import \
    confType


class Configuration(confType):
    def __init__(self, repeat: int, onEmpty: str) -> None:
        super().__init__(repeat)
        self.__dict__["onEmpty"] = onEmpty

    # Configuration variables are always strings
    # So, we need to override the __setattr__ method
    # to make sure we are setting the content correctly
    def __setattr__(self, __name: str, __value: any) -> None:
        super().__setattr__(__name, __value)
        if __name == "content":
            try:
                __value = str(__value)
            except Exception:
                raise TypeError(
                    "CONFIGURATION: Variable non-convertible to string... value: "
                    + str(__value)
                    + " type: "
                    + str(type(__value))
                    + " field: "
                    + __name
                )
            self.__dict__["content"].append(__value)
        elif (
            __name == "balancedContent"
            or __name == "reducedDuplicates"
            or __name == "reducedContent"
        ):
            # Default behaviour
            super().__setattr__(__name, __value)
        else:
            raise AttributeError("Configuration variable has no attribute " + __name)

    def __str__(self):
        return super().__str__()

    def balanceContent(self) -> None:
        super().balanceContent()
        # Always balanced!
        return

    def reduceDuplicates(self):
        super().reduceDuplicates()
        # No duplicates to reduce
        self.reducedContent = self.content[0]
        return
