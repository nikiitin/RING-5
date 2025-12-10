import typing


class ParseWork:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __call__(self) -> typing.Any:
        raise NotImplementedError("This method must be implemented by the child class")

    def __str__(self) -> str:
        pass
