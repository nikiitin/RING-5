#!/usr/bin/python3
# -*- coding: utf-8 -*-
from src.data_parser.src.dataParserFactory import DataParserFactory 
from src.data_management.src.dataManagerFactory import DataManagerFactory
from src.data_parser.src.configurationManager import ConfigurationManager as ParserConfigurationManager
from argumentParser import AnalyzerInfo
from src.plots.src.plot_impl.plotFactory import PlotFactory 
import src.utils.utils as utils

info = AnalyzerInfo()
# Parse data, it will create a csv file in the output directory
# This will remain after execution, so it can be used again
if info.getSkipParse():
    print("Skipping data parse")
else:
    # Get the parser to use
    # DataParserFactory.getDataParser(info).__call__()
    DataParserFactory.getDataParser(info,
                                        ParserConfigurationManager
                                            .getParserImpl(
                                            info.getJson()
                                        )
                                    ).__call__()
# Make a csv copy
# exit()
info.createWorkCsv()

# Get and execute data manager
manager = DataManagerFactory.getDataManager("R", info).__call__()
# Get and execute plots
plots = info.getJson()["plots"]
for plot in plots:
    # Execute corresponding plot
    utils.checkElementExists(plot, "plotType")
    PlotFactory.plot(info, plot, plot["plotType"]).__call__()
