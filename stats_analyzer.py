#!/usr/bin/python3
# -*- coding: utf-8 -*-
from data_parser.dataParserFactory import DataParserFactory 
from data_management.dataManagerFactory import DataManagerFactory
from argumentParser import AnalyzerInfo
import plots.dataPlot as dataPlot




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
    DataParserFactory.getDataParser("bash", info).runParse()
# Make a csv copy
info.createWorkCsv()
# Manage data
DataManagerFactory.getDataManager("csv", info).manageResults()
# Finish data format
# Start plotting
# TODO: Plotter must plot everything in one call
plots = info.getJson["plots"]


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
