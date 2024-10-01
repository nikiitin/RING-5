import src.utils.utils as utils
import enum
from src.data_preprocessing.src.preprocessorIface import PreprocessorIface
import abc

class PreprocessorType(enum.Enum):
    DIVIDER = "divider"

@PreprocessorIface.register
class Preprocessor:

    def __init__(self, csvPath: str, json: dict) -> None:
        self._csvPath = csvPath
        self._json = json
        self._operands = dict()
        self._RScriptCall = []
        self._checkPreconditions()
        self._configurePreprocessor()
    
    def addOperand(self, operandName: str, operand: any) -> None:
        if (operandName in self._operands):
            raise KeyError(f"Operand {operandName} already exists")
        if not isinstance(operand, Preprocessor) and not isinstance(operand, str):
            raise TypeError("Operand must be a preprocessor or a string")
        if operandName not in ["dst", "src1", "src2"]:
            raise KeyError(f"Key {operandName} not recognized in preprocessors")
        if operandName == "dst" and not isinstance(operand, str):
            raise TypeError("dst must be a string")
        self._operands[operandName] = operand

    def __call__(self) -> str:
        # Solve all the operands first
        solvedOperands = dict()
        for key, operand in self._operands.items():
            # If the operand is a preprocessor, solve it
            if isinstance(operand, Preprocessor):
                solvedOperands[key] = operand()
            elif isinstance(operand, str):
                solvedOperands[key] = operand
            else:
                raise TypeError("Operand must be a preprocessor or a string")
        # Replace the operands with the solved ones
        self._operands = solvedOperands
        # Then solve the preprocessor
        return self._perform()
    
    @abc.abstractmethod
    def _checkPreconditions(self) -> None:
        # Generic preconditions applicable to all preprocessors
        if not utils.checkFileExists(self._csvPath):
            raise FileNotFoundError(f"File {self._csvPath} does not exist")
        if not utils.checkElementExists(self._json, "dst"):
            raise KeyError("Could not find key 'dst' in json")
        pass
    
    @abc.abstractmethod
    def _perform(self) -> None:
        # Should be implemented by the subclass
        pass

    def _toStr(self) -> str:
        return f"Preprocessor: {type(self).__name__} with csvPath: {self._csvPath} and json: {self._json}. " \
               f"Operands are: {[str(operand) for operand in self._operands]}"
    
    @abc.abstractmethod
    def _configurePreprocessor(self) -> None:
        pass

    def __str__(self) -> str:
        super().__str__()
        return self._toStr()

