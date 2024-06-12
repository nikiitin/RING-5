import src.utils.utils as utils
import os
import json
# This class will manage the configuration files.
# Allow to have several split configuration module files
# and load both, data configuration and style.
class ConfigurationManager:
    _pathToConfigFiles = "config_files/json_components"
    # No instance for this class
    def __init__(self):
        raise RuntimeError("Cannot create instance for this class")
    
    @classmethod
    def getPlotConfiguration(cls, plotJson: dict):
        utils.checkElementExists(plotJson, "plotType")
        configPath = os.path.join(cls._pathToConfigFiles, "config")
        utils.checkDirExistsOrException(configPath)
        utils.checkElementExists(plotJson, "dataConfig")
        dataConfig = plotJson["dataConfig"]
        utils.checkElementExists(dataConfig, "file")
        utils.checkElementExists(dataConfig, "config")
        configPath = os.path.join(configPath, dataConfig["file"] + ".json")
        configName = dataConfig["config"]
        config = None
        with open(configPath) as configFile:
            config = json.load(configFile)
        # Search for the config
        for element in config:
            utils.checkElementExists(element, "configName")
            if (utils.getElementValue(element, "configName") == configName):
                return element["dataConfig"]
        raise RuntimeError("Config not found")

    @classmethod
    def getStyleConfiguration(cls, plotJson: dict):
        utils.checkElementExists(plotJson, "plotType")
        stylePath = os.path.join(cls._pathToConfigFiles,
                                 "style")
        utils.checkDirExistsOrException(stylePath)
        utils.checkElementExists(plotJson, "styleConfig")
        styleConfig = plotJson["styleConfig"]
        utils.checkElementExists(styleConfig, "file")
        utils.checkElementExists(styleConfig, "config")
        stylePath = os.path.join(stylePath, styleConfig["file"] + ".json")
        styleName = styleConfig["config"]
        style = None
        with open(stylePath) as configFile:
            style = json.load(configFile)
        # Search for the style
        for element in style:
            utils.checkElementExists(element, "styleName")
            if (utils.getElementValue(element, "styleName") == styleName):
                utils.checkElementExists(element, "dataStyle")
                return element["dataStyle"]
        raise RuntimeError("Style not found")