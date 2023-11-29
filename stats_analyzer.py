#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tempfile
import shutil
import json
import os.path
import argparse
import utils.utils as utils
from data_parser.dataParserInterface import DataParserFactory 
from data_management.dataManagerInterface import DataManagerFactory
import plots.dataPlot as dataPlot

temp_dir = tempfile.gettempdir()

class AnalyzerInfo:
    
    # Private methods
    def _parseArgs(self):
        argParser = argparse.ArgumentParser()
        argParser.add_argument("-c", "--csv", dest='csv',
                    help="csv name you want to generate/use",
                    default="results.csv")
        argParser.add_argument("-f", "--configFile",dest='configFile',
                    default="./config_files/config.json",
                    help="config file to be used")
        argParser.add_argument('-s', '--skipParse', dest='skipParse',
                    default=False,
                    action='store_true',
                    help="skip transfering and parsing data if csv already exists")
        argParser.add_argument('-d', '--debug', dest='debug',
                    default=False,
                    action='store_true',
                    help="debug mode: do not delete temporary files and print more info")
        return argParser.parse_args()

    def _createOutDir(self):
        outDir = self._json["outputPath"]
        if not utils.checkDirExists(outDir):
            try:
                print("Output directory does not exist, want to create it? (y/n)")
                answer = input()
                if answer == "y":
                    # Create output directory
                    os.mkdir(outDir)
                else:
                    print("Exiting")
                    exit()
                # Create output directory
            except OSError as error:
                print(error)
                exit()
        else:
            print("Output directory found: " + outDir)
        
    # Getters
    def getArgs(self):
        return self._args

    def getJson(self):
        return self._json

    def getCsv(self):
        return os.path.join(self._json["outputPath"], self._args.csv)
    
    def getWorkCsv(self):
        return os.path.join(tempfile.gettempdir, self._workCsv)
    
    def getSkipParse(self):
        return self._args.skipParse
    
    def getDebug(self):
        return self._args.debug
    
    # Public methods
    def __init__ (self):
        # Constant temporary csv to work.
        # Avoid modifying the original csv
        self._workCsv = "wresults.csv"
        self._args = self._parseArgs()
        # Read config
        with open(self._args.configFile, encoding='utf-8') as file:
            configString = file.read()
            self._json = json.loads(configString)
        self._createOutDir()
    
    def createWorkCsv(self):
        print("Creating work csv")
        shutil.copyfile(self._args.csv, self.getWorkCsv())


# def getPlotType(x):
#     return {
#         0: "barplot",
#         1: "stackBarplot",
#         2: "scalabilityPlot"
#     }.get(x, "Invalid")

# Main function

info = AnalyzerInfo()
# Parse data, it will create a csv file in the output directory
# This will remain after execution, so it can be used again
if info.getSkipParse():
    print("Skipping data parse")
else:
    DataParserFactory.getDataParser("json", info).runParse()
# Make a csv copy
info.createWorkCsv()
# Manage data
DataManagerFactory.getDataManager("csv", info).manageResults()
# Finish data format
# Start plotting
# TODO: Plotter must plot everything in one call
# plots = config["plots"]
# Temp dir will be used

# for plot in plots:
#     # Create a temporary Csv file for each plot
#     tempCsvPath = os.path.join(temp_dir, 'tempStats')
#     print(tempCsvPath)
#     shutil.copyfile(wcsvPath, tempCsvPath)  # Make a copy of the data
#     dataPlot.plotFigure(plot,
#               getPlotType(plot["plotType"]),
#               str(len(config["configs"])),
#               tempCsvPath,
#               outDir)
    #tempCsvPath.close()  # Close will delete temporary file

# Parse config file
