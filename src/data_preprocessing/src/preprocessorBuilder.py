import src.utils.utils as utils
from src.data_preprocessing.src.preprocessorFactory import PreprocessorFactory
from src.data_preprocessing.src.preprocessor import Preprocessor, PreprocessorType

class PreprocessorBuilder:
    def __init__(self, preprocessorType: str, csvPath: str, json: dict):
        self.preprocessor = None,
        self.preprocessorType = preprocessorType
        self.csvPath = csvPath
        self.json = json

    def build(self) -> Preprocessor:
        # Create the preprocessor
        preprocessorTypeEnum = PreprocessorType(self.preprocessorType)
        self.preprocessor = PreprocessorFactory.getPreprocessor(
            preprocessorTypeEnum, self.csvPath, self.json)
        
        for key in self.json:
            operand = utils.getElementValue(self.json, key)
            if isinstance(operand, dict) and utils.checkEnumExistsNoException(operand, PreprocessorType):
                preprocessorJson = utils.getElementValue(
                    operand,
                    utils.getEnumValue(operand, PreprocessorType)) 
                self.preprocessor.addOperand(key, PreprocessorBuilder(
                    utils.getEnumValue(operand, PreprocessorType),
                    self.csvPath, preprocessorJson).build())
            elif isinstance(operand, str):
                self.preprocessor.addOperand(key, operand)
            else:
                raise TypeError(f"{key} must be a string or a preprocessor")
        return self.preprocessor