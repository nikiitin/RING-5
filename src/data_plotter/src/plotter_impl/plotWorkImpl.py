import os
import subprocess
import src.utils.utils as utils
import random
import shutil
from src.data_plotter.multiprocessing.plotWork import PlotWork
from src.data_plotter.configurationManager import ConfigurationManager
from src.data_plotter.plot_config.src.configurerBuilder import ConfigurerBuilder
from src.da
class PlotWorkImpl(PlotWork):
    def __init__(self, outputPath: str, workCsv: str, plotJson: dict) -> None:
        # Plot data
        self._plotJson = plotJson
        self._workCsv = workCsv
        self._copiedFile = False
        # Initialize style data
        # Initialize plot data
        # R script call
        self._RScriptCall = []
        # Get style configuration
        self._styleConfigJson = ConfigurationManager.getStyleConfiguration(plotJson)
        # Initialize paths
        self._plotPathDir = os.path.join(outputPath, "plots")
        self._plotPath = os.path.join(self._plotPathDir, plotJson["fileName"])
        # Create plot directory if it does not exist
        if not utils.checkDirExists(self._plotPathDir):
            utils.createDir(self._plotPathDir)
        # Create temporary directory if it does not exist
        self._tmpDir = os.path.join(self._plotPathDir, ".tmp")
        if not utils.checkDirExists(self._tmpDir):
            utils.createDir(self._tmpDir)
        # Create temporary csv with random name
        self._tmpCsv = os.path.join(self._tmpDir, str(random.random()) + "tmp.csv")
        # Is plot data correct?
        self._checkCorrectness()
        # Create plot configurer, this will filter, mean, sort and normalize the data
        # Using R implementation.
        self._plotShaper = ConfigurationManager.getPlotShaper(plotJson)
        # There should only be one configurer that
        # have the other configurers as children
        assert len(self._plotShaper) == 1
        shaperName = list(self._plotShaper.keys())[0]

        super().__init__()

    def __call__(self) -> None:
        # Create a random name for the temporary csv
        # Check it is not already taken
        while utils.checkFileExists(self._tmpCsv):
            self._tmpCsv = os.path.join(self._tmpDir, str(random.random()) + "tmp.csv")
        # Copy the work csv to the temporary csv
        shutil.copyfile(self._workCsv, self._tmpCsv)
        self._copiedFile = True
        # Configure plot
        self._configurer.configurePlot(self._tmpCsv)
        # Prepare R script call
        self._prepareScriptCall()
        # Call R script
        subprocess.call(self._RScriptCall)
    
    def __del__(self) -> None:
        # Remove temporary csv
        if self._copiedFile:
            utils.removeFile(self._tmpCsv)
        pass

    def __str__(self) -> str:
        return "File: " + self._fileToParse + " Vars: " + str(self._varsToParse)
    
    def _prepareScriptCall(self) -> None:
        # TODO: description file for locations
        # (Avoid hardcoding paths)
        self._RScriptCall = ["./src/data_plotter/src/plotter.R"]
        self._RScriptCall.extend(utils.jsonToArg(self._plotJson, "plotType"))
        self._RScriptCall.extend(self._preparePlotInfo())
        self._RScriptCall.extend(self._preparePlotStyleInfo())

    def _checkCorrectness(self) -> None:
        # Check plot format info
        utils.checkElementExists(self._styleConfigJson, "title")
        utils.checkElementExists(self._styleConfigJson, "xAxisName")
        utils.checkElementExists(self._styleConfigJson, "yAxisName")
        utils.checkElementExists(self._styleConfigJson, "width")
        utils.checkElementExists(self._styleConfigJson, "height")
        utils.checkElementExists(self._styleConfigJson, "format")
        utils.checkElementExists(self._styleConfigJson, "legendTitle")
        utils.checkElementExists(self._styleConfigJson, "nLegendElementsPerRow")
        utils.checkElementExists(self._styleConfigJson, "legendNames")
        utils.checkElementExists(self._styleConfigJson, "breaks")
        utils.checkElementExists(self._styleConfigJson, "limitTop")
        utils.checkElementExists(self._styleConfigJson, "limitBot")
        # Check plot info
        utils.checkElementExists(self._plotJson, "x")
        utils.checkElementExists(self._plotJson, "y")
        # Include conf_z even if it is empty
        utils.checkElementExists(self._plotJson, "conf_z")
        utils.checkElementExists(self._plotJson, "plotType")
    
    def _preparePlotInfo(self) -> list:
        plotInfo = []
        plotInfo.append(self._tmpCsv)
        plotInfo.append(self._plotPath)
        # X, Y and conf_z are mandatory
        plotInfo.extend(utils.jsonToArg(self._plotJson, "x"))
        plotInfo.extend(utils.jsonToArg(self._plotJson, "y"))
        plotInfo.extend(utils.jsonToArg(self._plotJson, "conf_z"))
        # Optional parameters
        if utils.checkElementExistNoException(self._plotJson, "showOnlyMean"):
            plotInfo.extend(utils.jsonToArg(self._plotJson, "showOnlyMean"))
        else:
            plotInfo.append("False")
        if utils.checkElementExistNoException(self._plotJson, "hiddenBars"):
            plotInfo.extend(utils.jsonToArg(self._plotJson, "hiddenBars"))
        else:
            plotInfo.append("0")
        # All plots are faceteables
        if utils.checkElementExistNoException(self._plotJson, "facet"):
            facet = self._plotJson["facet"]
            utils.checkElementExists(facet, "facetVar")
            utils.checkElementExists(facet, "facetMappings")
            plotInfo.extend(utils.jsonToArg(facet, "facetMappings"))
            plotInfo.extend(utils.jsonToArg(facet, "facetVar"))
        else:
            plotInfo.append("0")
        return plotInfo

    def _preparePlotStyleInfo(self) -> list:
        plotFormatInfo = []
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "title"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "xAxisName"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "yAxisName"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "width"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "height"))
        # pdf, png...
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "format"))
        # Mandatory but can be empty
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "legendTitle"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "nLegendElementsPerRow"))
        # Mandatory but can be empty
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "legendNames"))
        # Y breaks
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "breaks"))
        # Limits for Y axis
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "limitTop"))
        plotFormatInfo.extend(utils.jsonToArg(self._styleConfigJson, "limitBot"))
        return plotFormatInfo
