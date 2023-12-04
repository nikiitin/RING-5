#!/usr/bin/python3
# -*- coding: utf-8 -*-
from data_parser.dataParserFactory import DataParserFactory 
from data_management.dataManagerFactory import DataManagerFactory
from argumentParser import AnalyzerInfo
from plots.plotFactory import PlotFactory 
import utils.utils as utils




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
DataManagerFactory.getDataManager("R", info).manageResults()
# Finish data format
# Start plotting
# TODO: Plotter must plot everything in one call
plots = info.getJson()["plots"]


for plot in plots:
    # Do plotting for each plot
    utils.checkElementExists(plot, "plotType")
    pl = PlotFactory.plot(info, plot, plot["plotType"])
    pl()


# Parse config file
