import abc

class PreprocessorIface(metaclass=abc.ABCMeta):
    """! @brief Preprocessor interface
    """
    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, '__init__') and
                callable(subclass.__init__) and
                hasattr(subclass, '__call__') and
                callable(subclass.__call__) and
                hasattr(subclass, '_checkPrecoditions') and
                callable(subclass._checkPreconditions) and
                hasattr(subclass, '_perform') and
                callable(subclass._perform) and
                hasattr(subclass, '_toStr') and
                callable(subclass._toStr) and
                hasattr(subclass, '_configurePreprocessor') and
                callable(subclass._configurePreprocessor) or
                NotImplemented)

    @abc.abstractmethod
    def __init__(self, csvPath: str, json: dict) -> None:
        """! @brief Preprocessor constructor
        @param csvPath The path to the csv file
        @param json The json with the preprocessor configuration
        """
        pass

    @abc.abstractmethod
    def __call__(self) -> str:
        """! @brief Call for the preprocessor.
        """
        pass


    @abc.abstractmethod
    def _checkPreconditions(self) -> None:
        """! @brief Check the preconditions for the preprocessor
        """
        pass

    @abc.abstractmethod
    def _perform(self) -> None:
        """! @brief Perform the preprocessor
        """
        pass

    @abc.abstractmethod
    def _toStr(self) -> str:
        """! @brief Turn the preprocessor into a string
        """
        pass

    @abc.abstractmethod
    def _configurePreprocessor(self) -> None:
        """! @brief Configure the preprocessor
        """
        pass