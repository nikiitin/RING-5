# This file contains the interface for the plot classes
from argumentParser import AnalyzerInfo
from plots.plot_config.plotConfigurerFactory import PlotConfigurerFactory
import utils.utils as utils
import os
import random
import shutil

class PlotInterface:
    def __init__(self, info: AnalyzerInfo, plotJson: dict) -> None:
        # TODO: remove replicated info...
        self._plotJson = plotJson
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
        utils.checkElementExists(self._plotJson, "title")
        utils.checkElementExists(self._plotJson, "xAxisName")
        utils.checkElementExists(self._plotJson, "yAxisName")
        utils.checkElementExists(self._plotJson, "width")
        utils.checkElementExists(self._plotJson, "height")
        utils.checkElementExists(self._plotJson, "format")
        utils.checkElementExists(self._plotJson, "legendTitle")
        utils.checkElementExists(self._plotJson, "nLegendElementsPerRow")
        utils.checkElementExists(self._plotJson, "xSplitPoints")

        # Check plot info
        utils.checkElementExists(self._plotJson, "x")
        utils.checkElementExists(self._plotJson, "y")
        utils.checkElementExists(self._plotJson, "conf_z")
        

        

    def _prepareScriptCall(self) -> None:
        pass

    def _preparePlotInfo(self) -> list:
        plotInfo = []
        plotInfo.append(self._plotPath)
        plotInfo.append(self._tmpCsv)
        plotInfo.extend(utils.jsonToArg(self._plotJson, "x"))
        plotInfo.extend(utils.jsonToArg(self._plotJson, "y"))
        return plotInfo

    def _preparePlotFormatInfo(self) -> list:
        plotFormatInfo = []
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "title"))
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "xAxisName"))
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "yAxisName"))
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "width"))
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "height"))
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "format"))
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "legendTitle"))
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "nLegendElementsPerRow"))
        plotFormatInfo.extend(utils.jsonToArg(self._plotJson, "xSplitPoints"))
        return plotFormatInfo
        