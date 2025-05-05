#!/usr/bin/python3
# -*- coding: utf-8 -*-
from src.data_parser.src.dataParserFactory import DataParserFactory 
from src.data_management.dataManagerFactory import DataManagerFactory
from src.data_management.dataManager import DataManager
from src.data_parser.src.configurationManager import ConfigurationManager as ParserConfigurationManager
from argumentParser import AnalyzerInfo
from src.data_plotter.data_plotter import dataPlotter
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
manager = DataManagerFactory.getDataManager(info)
if len(manager) > 0:
    print("Data manager found, executing")
    for m in manager:
        m()
    DataManager.persist()
else:
    print("No data manager found, skipping data management")
# Get and execute plots
plots = info.getJson()["plots"]
dataPlotter(info.getOutputDir(), info.getWorkCsv(), plots).__call__()