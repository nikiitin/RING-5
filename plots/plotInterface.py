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
        #utils.removeFile(self._tmpCsv)
        pass

    def _checkCorrectness(self) -> None:
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
        utils.checkElementExists(self._plotJson, "xSplitPoints")

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
        self._sufixScriptCall.extend(utils.jsonToArg(self._plotJson, "xSplitPoints"))

    def _preparePrefixScriptCall(self) -> None:
        self._prefixScriptCall = []
        self._prefixScriptCall.extend(utils.jsonToArg(self._plotJson, "title"))
        self._prefixScriptCall.append(self._plotPath)
        self._prefixScriptCall.append(self._tmpCsv)
        self._prefixScriptCall.extend(utils.jsonToArg(self._plotJson, "xAxisName"))
        self._prefixScriptCall.extend(utils.jsonToArg(self._plotJson, "yAxisName"))
        self._prefixScriptCall.extend(utils.jsonToArg(self._plotJson, "width"))
        self._prefixScriptCall.extend(utils.jsonToArg(self._plotJson, "height"))
        