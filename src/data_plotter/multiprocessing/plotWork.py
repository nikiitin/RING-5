from abc import abstractmethod


class PlotWork:
    def __init__(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def __call__(self) -> None:
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass
