# This file contains the interface for the plot classes
from argumentParser import AnalyzerInfo
from plots.plot_config.plotConfigurerInterface import PlotConfigurerFactory
import utils.utils as utils
import os
import random
import shutil

class PlotInterface:
    def __init__(self, info: AnalyzerInfo, plotJson: dict) -> None:
        # TODO: remove replicated info...
        self._plotJson = plotJson
        self._info = info
        self._plotPath = os.path.join(info.getJson()["outputPath"], "plots")
        if not utils.dirExists(self._plotPath):
            utils.createDir(self._plotPath)
        self._tmpDir = os.path.join(self._plotPath, ".tmp")
        if not utils.dirExists(self._tmpDir):
            utils.createDir(self._tmpDir)
        self._tmpCsv = os.path.join(self._plotPath, "" + random.random + "tmp.csv")
        # Create a random name for the temporary csv
        # Check it is not already taken
        while utils.checkFileExists(self._tmpCsv):
            self._tmpCsv = os.path.join(self._plotPath, "" + random.random + "tmp.csv")
        shutil.copyfile(self._info.getWorkCsv, self._tmpCsv)
        print("Created tmp csv: " + self._tmpCsv)
        # Check if all fields are present
        self._checkCorrectness()
        # Create plot configurer, this will filter, mean, sort and normalize the data
        # Using R implementation.
        # TODO: make this configurable
        self._configurer = PlotConfigurerFactory.getConfigurer("R")

    def __call__(self) -> None:
        self._configurer.configurePlot(self._plotJson, self._tmpCsv)
        self._prepareScriptCall()

    def checkCorrectness(self) -> None:
        utils.checkElementExists(self._plotJson, "title")
        utils.checkElementExists(self._plotJson, "xAxisName")
        utils.checkElementExists(self._plotJson, "yAxisName")
        utils.checkElementExists(self._plotJson, "width")
        utils.checkElementExists(self._plotJson, "height")
        utils.checkElementExists(self._plotJson, "legendNames")
        utils.checkElementExists(self._plotJson, "breaks")
        utils.checkElementExists(self._plotJson, "limitTop")
        utils.checkElementExists(self._plotJson, "limitBot")
        utils.checkElementExists(self._plotJson, "format")
        utils.checkElementExists(self._plotJson, "legendTitle")
        utils.checkElementExists(self._plotJson, "nLegendElementsPerRow")

    def _prepareScriptCall(self) -> None:
        pass

    def _prepareSufixScriptCall(self) -> None:
        self._sufixScriptCall = []
        self._sufixScriptCall.extend(utils.jsonToArg(self._plotJson, "legendNames"))
        self._sufixScriptCall.extend(utils.jsonToArg(self._plotJson, "breaks"))
        self._sufixScriptCall.extend(utils.jsonToArg(self._plotJson, "limitTop"))
        self._sufixScriptCall.extend(utils.jsonToArg(self._plotJson, "limitBot"))
        self._sufixScriptCall.extend(utils.jsonToArg(self._plotJson, "format"))
        self._sufixScriptCall.extend(utils.jsonToArg(self._plotJson, "legendTitle"))
        self._sufixScriptCall.extend(utils.jsonToArg(self._plotJson, "nLegendElementsPerRow"))

    def _preparePrefixScriptCall(self) -> None:
        self._prefixScriptCall = []
        self._prefixScriptCall.extend(utils.jsonToArg(self._plotJson, "title"))
        self._prefixScriptCall.append(self._plotPath)
        self._prefixScriptCall.extend(utils.jsonToArg(self._plotJson, "xAxisName"))
        self._prefixScriptCall.extend(utils.jsonToArg(self._plotJson, "yAxisName"))
        self._prefixScriptCall.extend(utils.jsonToArg(self._plotJson, "width"))
        self._prefixScriptCall.extend(utils.jsonToArg(self._plotJson, "height"))
        self._prefixScriptCall.append(self._tmpCsv)