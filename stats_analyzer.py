#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tempfile
import shutil
import json
import os.path
import argparse
import dataParse
import dataManager
import dataPlot

def getPlotType(x):
    return {
        0: "barplot",
        1: "stackBarplot"
    }.get(x, "Invalid")

csv = "results.csv"
workRCsv = "wresults.csv"
configFile = "config_reqLoses.json"
skipParse = False

# Parse arguments
argParser = argparse.ArgumentParser()
argParser.add_argument("-c", "--csv", dest='csv',
                       help="csv name you want to generate/use",
                       default="results.csv")
argParser.add_argument("-f", "--configFile",dest='configFile',
                       default="config.json",
                       help="config file to be used")
argParser.add_argument('-s', '--skipParse', dest='skipParse',
                    default=False,
                    action='store_true')
args = argParser.parse_args()

# Read config
file = open(configFile, encoding='utf-8')
configString = file.read()
config = json.loads(configString)
file.close()
# Parse data
outDir = config["outputPath"]
csvPath = os.path.join(outDir, csv)
try:
    # Create output directory
    os.mkdir(outDir)
except OSError as error:
    print(error)
if not skipParse:
    print("Skipping data parse")
    dataParse.runParse(config, csvPath)
# Finish data parsing
# Make a csv copy
wcsvPath = os.path.join(outDir, workRCsv)
shutil.copyfile(csvPath, wcsvPath)
# Format data for plotting
if config["reduceSeeds"]:
    dataManager.reduceSeeds(config["configs"], wcsvPath)

dataManager.renameStats(config["renameStats"], wcsvPath)
dataManager.mixStats(config["mixStats"], wcsvPath)
# Finish data format
# Start plotting
plots = config["plots"]
# Temp dir will be used
temp_dir = tempfile.gettempdir()
for plot in plots:
    # Create a temporary Csv file for each plot
    tempCsvPath = os.path.join(temp_dir, 'tempStats')
    shutil.copyfile(wcsvPath, tempCsvPath)  # Make a copy of the data
    dataPlot.plotFigure(plot,
              getPlotType(plot["plotType"]),
              str(len(config["configs"])),
              tempCsvPath,
              outDir)
    tempCsvPath.close()  # Close will delete temporary file

# Parse config file
