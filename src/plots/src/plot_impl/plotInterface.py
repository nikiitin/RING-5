# This file contains the interface for the plot classes
from argumentParser import AnalyzerInfo
from src.plots.src.plot_config.plotConfigurerFactory import PlotConfigurerFactory
from src.plots.src.configurationManager import ConfigurationManager
import src.utils.utils as utils
import os
import random
import shutil

class PlotInterface:
    def __init__(self, info: AnalyzerInfo, plotJson: dict) -> None:
        # TODO: remove replicated info...
        self._plotJson = plotJson
        self._styleConfigJson = ConfigurationManager.getStyleConfiguration(plotJson)
        self._info = info
        self._plotPathDir = os.path.join(info.getJson()["outputPath"], "plots")
        self._plotPath = os.path.join(self._plotPathDir, plotJson["fileName"])
        if not utils.checkDirExists(self._plotPathDir):
            utils.createDir(self._plotPathDir)
        self._tmpDir = os.path.join(self._plotPathDir, ".tmp")
        if not utils.checkDirExists(self._tmpDir):
            utils.createDir(self._tmpDir)
        self._tmpCsv = os.path.join(self._plotPathDir, "" + str(random.random()) + "tmp.csv")
        # Create a random name for the temporary csv
        # Check it is not already taken
        while utils.checkFileExists(self._tmpCsv):
            self._tmpCsv = os.path.join(self._plotPathDir, ".tmp", str(random.random()) + "tmp.csv")
        shutil.copyfile(self._info.getWorkCsv(), self._tmpCsv)
        print("Created tmp csv: " + self._tmpCsv)
        # Check if all fields are present
        self._checkCorrectness()
        # Create plot configurer, this will filter, mean, sort and normalize the data
        # Using R implementation.
        # TODO: make this configurable
        self._configurer = PlotConfigurerFactory.getConfigurer(info, "R")

    def __call__(self) -> None:
        self._configurer.configurePlot(self._plotJson, self._tmpCsv)
        self._prepareScriptCall()

    def __del__(self) -> None:
        # Remove temporary csv
        utils.removeFile(self._tmpCsv)
        pass

    def _checkCorrectness(self) -> None:
        # Check plot format info
        utils.checkElementExists(self._styleConfigJson, "apparel")
        utils.checkElementExists(self._styleConfigJson, "title")
        utils.checkElementExists(self._styleConfigJson, "xAxisName")
        utils.checkElementExists(self._styleConfigJson, "yAxisName")
        utils.checkElementExists(self._styleConfigJson, "width")
        utils.checkElementExists(self._styleConfigJson, "height")
        utils.checkElementExists(self._styleConfigJson, "format")
        utils.checkElementExists(self._styleConfigJson, "legendTitle")
        utils.checkElementExists(self._styleConfigJson, "nLegendElementsPerRow")

        # Check plot info
        utils.checkElementExists(self._plotJson, "x")
        utils.checkElementExists(self._plotJson, "y")
        
    def _prepareScriptCall(self) -> None:
        pass

    def _preparePlotInfo(self) -> list:
        plotInfo = []
        plotInfo.append(self._tmpCsv)
        plotInfo.append(self._plotPath)
        plotInfo.extend(utils.jsonToArg(self._plotJson, "x"))
        plotInfo.extend(utils.jsonToArg(self._plotJson, "y"))
        if utils.checkElementExistNoException(self._plotJson, "showOnlyMean"):
            plotInfo.extend(utils.jsonToArg(self._plotJson, "showOnlyMean"))
        else:
            plotInfo.append("False")
        return plotInfo

    def _preparePlotStyleInfo(self) -> list:
        plotFormatInfo = []
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "apparel"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "title"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "xAxisName"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "yAxisName"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "width"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "height"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "format"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "legendTitle"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "nLegendElementsPerRow"))
        return plotFormatInfo
        