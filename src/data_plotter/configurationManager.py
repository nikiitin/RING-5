import json
import os

import src.utils.utils as utils


# This class will manage the configuration files.
# Allow to have several split configuration module files
# and load both, data configuration and style.
class ConfigurationManager:
    _pathToShaperFiles = "config_files/json_components"

    # No instance for this class
    def __init__(self):
        raise RuntimeError("Cannot create instance for this class")

    @classmethod
    def getPlotShaper(cls, plotJson: dict) -> dict:
        utils.checkElementExists(plotJson, "plotType")
        shaperPath = os.path.join(cls._pathToShaperFiles, "shapers")
        utils.checkDirExistsOrException(shaperPath)
        utils.checkElementExists(plotJson, "dataShaper")
        dataShaper = plotJson["dataShaper"]
        utils.checkElementExists(dataShaper, "file")
        utils.checkElementExists(dataShaper, "shaper")
        shaperPath = os.path.join(shaperPath, dataShaper["file"] + ".json")
        shaperName = dataShaper["shaper"]
        with open(shaperPath) as shaperFile:
            shaper = json.load(shaperFile)
        # Search for the config

        if utils.checkElementExistNoException(shaper, shaperName):
            shp = utils.getElementValue(shaper, shaperName)
            utils.checkVarType(shp, dict)
            return shp
        else:
            raise RuntimeError("Shaper: " + shaperName + " not found in file: " + shaperPath)

    @classmethod
    def getStyleConfiguration(cls, plotJson: dict):
        utils.checkElementExists(plotJson, "plotType")
        stylePath = os.path.join(cls._pathToShaperFiles, "style")
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
            if utils.getElementValue(element, "styleName") == styleName:
                utils.checkElementExists(element, "dataStyle")
                return element["dataStyle"]
        raise RuntimeError("Style not found")
