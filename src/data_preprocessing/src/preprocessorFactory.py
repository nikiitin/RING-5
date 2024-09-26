from src.data_preprocessing.src.preprocessors.divider.divider import Divider
from src.data_preprocessing.src.preprocessor import Preprocessor, PreprocessorType

class PreprocessorFactory:
    @staticmethod
    def getPreprocessor(preprocessorType: PreprocessorType, csvPath: str, json: dict) -> Preprocessor:
        if preprocessorType == PreprocessorType.DIVIDER:
            return Divider(csvPath, json)
        else:
            raise ValueError(f"Preprocessor type {preprocessorType} not recognized")
