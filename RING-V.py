#!/usr/bin/python3
# -*- coding: utf-8 -*-
from src.data_parser.src.dataParserFactory import DataParserFactory 
from src.data_management.src.dataManagerFactory import DataManagerFactory
from src.data_parser.src.configurationManager import ConfigurationManager as ParserConfigurationManager
from src.data_preprocessing.src.preprocessorBuilder import PreprocessorBuilder
from src.data_preprocessing.src.preprocessor import PreprocessorType
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
manager = DataManagerFactory.getDataManager("R", info).__call__()

# Preprocess data if needed
if utils.checkElementExistNoException(info.getJson(), "preprocessor"):
    for preprocessor in utils.getElementValue(info.getJson(), "preprocessor"):

        preprocessorJson = utils.getElementValue(
            preprocessor,
            utils.getEnumValue(preprocessor, PreprocessorType))

        PreprocessorBuilder(
            utils.getEnumValue(preprocessor, PreprocessorType),
            info.getWorkCsv(),
            preprocessorJson).build().__call__()
# Get and execute plots
plots = info.getJson()["plots"]
dataPlotter(info.getOutputDir(), info.getWorkCsv(), plots).__call__()