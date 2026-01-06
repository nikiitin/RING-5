import json
import os

import src.utils.utils as utils


class ConfigurationManager:
    _pathToConfigFiles = "config_files/json_components"
    _parseJson: dict = None

    # No instance for this class
    def __init__(self):
        raise RuntimeError("Cannot create instance for this class")

    @classmethod
    def reset(cls) -> None:
        """Reset the cached configuration."""
        cls._parseJson = None

    @classmethod
    def _getParseConfiguration(cls, configJson: dict) -> dict:
        utils.checkElementExists(configJson, "parseConfig")
        parseJson = configJson["parseConfig"]
        return parseJson

    @classmethod
    def _loadParseJson(cls, configJson: dict) -> dict:
        if cls._parseJson is not None:
            # Only load the json once
            return cls._parseJson
        pConfig = cls._getParseConfiguration(configJson)
        utils.checkElementExists(pConfig, "file")
        with open(
            os.path.join(cls._pathToConfigFiles, "parse", pConfig["file"] + ".json")
        ) as parseFile:
            cls._parseJson = json.load(parseFile)
        return cls._parseJson

    @classmethod
    def _getParserById(cls, configJson: dict, id: str) -> dict:
        cls._loadParseJson(configJson)
        for parser in cls._parseJson:
            utils.checkElementExists(parser, "id")
            if utils.getElementValue(parser, "id") == id:
                return parser
        raise RuntimeError("Parser not found, id: " + id)

    @classmethod
    def getParserId(cls, configJson: dict) -> str:
        parseConf = cls._getParseConfiguration(configJson)
        utils.checkElementExists(parseConf, "config")
        confId = utils.getElementValue(parseConf, "config")
        return confId

    @classmethod
    def getParserImpl(cls, configJson: dict) -> str:
        confId = cls.getParserId(configJson)
        parser = cls._getParserById(configJson, confId)
        utils.checkElementExists(parser, "impl")
        return utils.getElementValue(parser, "impl")

    @classmethod
    def getCompress(cls, configJson: dict) -> str:
        confId = cls.getParserId(configJson)
        parser = cls._getParserById(configJson, confId)
        utils.checkElementExists(parser, "compress")
        return utils.getElementValue(parser, "compress")

    @classmethod
    def getParser(cls, configJson: dict) -> dict:
        parser = cls._getParserById(configJson, cls.getParserId(configJson))
        utils.checkElementExists(parser, "parsings")
        return parser["parsings"]
