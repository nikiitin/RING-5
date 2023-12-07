#!/usr/bin/python3
# -*- coding: utf-8 -*-
from data_parser.dataParserFactory import DataParserFactory 
from data_management.dataManagerFactory import DataManagerFactory
from argumentParser import AnalyzerInfo
from plots.plotFactory import PlotFactory 
import utils.utils as utils

info = AnalyzerInfo()
# Parse data, it will create a csv file in the output directory
# This will remain after execution, so it can be used again
if info.getSkipParse():
    print("Skipping data parse")
else:
    DataParserFactory.getDataParser("bash", info).__call__()
# Make a csv copy
info.createWorkCsv()

# Get and execute data manager
manager = DataManagerFactory.getDataManager("R", info).__call__()
# Get and execute plots
plots = info.getJson()["plots"]
for plot in plots:
    # Execute corresponding plot
    utils.checkElementExists(plot, "plotType")
    pl = PlotFactory.plot(info, plot, plot["plotType"]).__call__()
