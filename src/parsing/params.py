from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class DataParserParams:
    """
    Parameters for DataParser.
    Replaces AnalyzerInfo for the parser module.
    """

    config_json: Dict[str, Any]

    def get_json(self) -> Dict[str, Any]:
        return self.config_json

    def getOutputDir(self) -> str:
        """Get the output directory path."""
        return self.config_json.get("outputPath")
