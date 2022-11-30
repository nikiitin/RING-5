#!/usr/bin/python3
# -*- coding: utf-8 -*-

from curses.ascii import RS
from nis import match
from os import rename
import shutil
import subprocess
import json
import os.path
import sys

resultsCsv = "results.csv"
workResultsCsv = "wresults.csv"

def getPlotType(x):
    return {
        0 : "barplot",
        1 : "stackBarplot"
    }.get(x, "Invalid")

def parseStats(files, stats, configs):
    print("Parsing stats and turning into csv")
    shellScriptCall = ["./dataParser.sh"]
    shellScriptCall.append(resultsCsv)
    shellScriptCall.append(str(len(files)))
    shellScriptCall.extend(files)
    shellScriptCall.append(str(len(stats)))
    shellScriptCall.extend(stats)
    shellScriptCall.append(str(len(configs)))
    shellScriptCall.extend(configs)

    subprocess.call(shellScriptCall)

def renameStats(renamings):
    print("Renaming stats")
    RScriptCall = ["./dataRenamer.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(str(len(renamings)))
    for renameInfo in renamings:
        RScriptCall.append(renameInfo["oldName"])
        RScriptCall.append(renameInfo["newName"])

    subprocess.call(RScriptCall)

def mixStats(mixings):
    print("Mixing stats onto groups")
    RScriptCall = ["./dataMixer.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(str(len(mixings)))
    for mix in mixings:
        RScriptCall.append(mix["groupName"])
        RScriptCall.append(str(len(mix["mergingStats"])))
        RScriptCall.extend(mix["mergingStats"])
    
    subprocess.call(RScriptCall)

def reduceSeeds(configs):
    print("Reducing seeds and calculating mean and sd")
    RScriptCall = ["./reduceSeeds.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(str(len(configs) + 1))
    subprocess.call(RScriptCall)

def plotFigure(plotInfo, plotType, nConfigs):
    if (plotType == "stackBarplot"):
        RScriptCall = ["./stackedBarplot.R"]
    else:
        RScriptCall = ["./barplot.R"]
    
    RScriptCall.append(plotInfo["title"])
    RScriptCall.append(plotInfo["fileName"])
    RScriptCall.append(plotInfo["xAxisName"])
    RScriptCall.append(plotInfo["yAxisName"])
    RScriptCall.append(str(plotInfo["width"]))
    RScriptCall.append(str(plotInfo["height"]))
    RScriptCall.append(nConfigs)
    RScriptCall.append(workResultsCsv)
    
    # X-axis
    RScriptCall.append(str(len(plotInfo["benchmarksFiltered"])))
    RScriptCall.extend(plotInfo["benchmarksFiltered"])
    RScriptCall.append(str(len(plotInfo["configsFiltered"])))
    for filt in plotInfo["configsFiltered"]:
        RScriptCall.append(filt["confName"])
        RScriptCall.append(filt["value"])
    
    # Y-axis
    RScriptCall.append(str(len(plotInfo["configsOrdering"])))
    for order in plotInfo["configsOrdering"]:
        RScriptCall.append(str(order))

    RScriptCall.append(str(plotInfo["normalized"]))
    
    # Stacking info
    if (plotType == "stackBarplot"):
        RScriptCall.append(str(len(plotInfo["stackVariables"])))
        RScriptCall.extend(plotInfo["stackVariables"])
        RScriptCall.append(str(len(plotInfo["groupNames"])))
        RScriptCall.extend(plotInfo["groupNames"])
    else:
        RScriptCall.append(plotInfo["stat"])
    RScriptCall.append(str(len(plotInfo["legendNames"])))
    RScriptCall.extend(plotInfo["legendNames"])
    print(RScriptCall)
    subprocess.call(RScriptCall)

file = open("config.json", encoding='utf-8')
configString = file.read()
config = json.loads(configString)
file.close()
outDir = config["outputPath"]

statsFiles = config["filesPaths"]
statsToParse = config["statsAnalyzed"]
configsToAnalyze = config["configs"]
#parseStats(statsFiles, statsToParse, configsToAnalyze)
shutil.copyfile(resultsCsv, workResultsCsv) # Make a copy of the data (avoid modifying the)
shouldReduceSeeds = config["reduceSeeds"]
if shouldReduceSeeds:
    reduceSeeds(configsToAnalyze)

renamings = config["renameStats"]
renameStats(renamings)

mixings = config["mixStats"]
mixStats(mixings)
plots = config["plots"]
for plot in plots:
    plotFigure(plot, getPlotType(plot["plotType"]), str(len(config["configs"])))