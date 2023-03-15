#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tempfile
import shutil
import subprocess
import json
import os.path

csv = "results.csv"
workRCsv = "wresults.csv"
tempCsvPath = "temp.csv"
configFile = "config_reqLoses.json"


def getPlotType(x):
    return {
        0: "barplot",
        1: "stackBarplot"
    }.get(x, "Invalid")


def parseStats(files, stats, configs, resultsCsv):
    print("Parsing stats and turning into csv")
    shellScriptCall = ["./dataParser.sh"]
    shellScriptCall.append(resultsCsv)
    shellScriptCall.append(files)
    shellScriptCall.append(str(len(stats)))
    shellScriptCall.extend(stats)
    shellScriptCall.append(str(len(configs)))
    shellScriptCall.extend(configs)

    subprocess.call(shellScriptCall)


def renameStats(renamings, workResultsCsv):
    print("Renaming stats")
    RScriptCall = ["./dataRenamer.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(str(len(renamings)))
    for renameInfo in renamings:
        RScriptCall.append(renameInfo["oldName"])
        RScriptCall.append(renameInfo["newName"])

    subprocess.call(RScriptCall)


def mixStats(mixings, workResultsCsv):
    print("Mixing stats onto groups")
    RScriptCall = ["./dataMixer.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(str(len(mixings)))
    for mix in mixings:
        RScriptCall.append(mix["groupName"])
        RScriptCall.append(str(len(mix["mergingStats"])))
        RScriptCall.extend(mix["mergingStats"])

    subprocess.call(RScriptCall)


def reduceSeeds(configs, workResultsCsv):
    print("Reducing seeds and calculating mean and sd")
    RScriptCall = ["./reduceSeeds.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(str(len(configs) + 1))
    subprocess.call(RScriptCall)


def compressData(files, output, name, finalDirName):
    print("Compressing data")
    shellScriptCall = ["./dataCompressor.sh"]
    shellScriptCall.append(output)
    shellScriptCall.append(str(len(files)))
    shellScriptCall.extend(files)
    shellScriptCall.append(name)
    shellScriptCall.append(finalDirName)
    subprocess.call(shellScriptCall)


def filterData(benchsFiltered, configsFiltered, workResultsCsv):
    print("Filtering data")
    RScriptCall = ["./dataFilter.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(str(len(benchsFiltered)))
    RScriptCall.extend(benchsFiltered)
    RScriptCall.append(str(len(configsFiltered)))
    for filt in configsFiltered:
        RScriptCall.append(filt["confName"])
        RScriptCall.append(filt["value"])
    subprocess.call(RScriptCall)

def orderData(orderingType, configOrdering, workResultsCsv):
    print("Ordering data")
    RScriptCall = ["./ordering.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(orderingType)
    RScriptCall.append(str(len(configOrdering)))
    RScriptCall.extend(configOrdering)
    subprocess.call(RScriptCall)

def normalizeData(shouldNorm, sd, stats, workResultsCsv):
    print("Normalize data")
    RScriptCall = ["./ordering.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(shouldNorm)
    RScriptCall.append(sd)
    RScriptCall.append(str(len(stats)))
    RScriptCall.extend(stats)
    subprocess.call(RScriptCall)

def plotFigure(plotInfo, plotType, nConfigs, workResultsCsv):
    filterData(plotInfo["benchmarksFiltered"],
               plotInfo["configsFiltered"],
               workResultsCsv)

    orderData(plotInfo["orderingType"],
              plotInfo["configOrdering"],
              workResultsCsv)
    

    
    if (plotType == "stackBarplot"):
        RScriptCall = ["./stackedBarplot.R"]
        normalizeData(str(plotInfo["normalized"]),
                True,
                plotInfo["stackVariables"],
                workResultsCsv)
    else:
        RScriptCall = ["./barplot.R"]
        normalizeData(str(plotInfo["normalized"]),
                True,
                plotInfo["stackVariables"],
                workResultsCsv)

    RScriptCall.append(plotInfo["title"])
    plotPath = os.path.join(outDir, plotInfo["fileName"])
    RScriptCall.append(plotPath)
    RScriptCall.append(plotInfo["xAxisName"])
    RScriptCall.append(plotInfo["yAxisName"])
    RScriptCall.append(str(plotInfo["width"]))
    RScriptCall.append(str(plotInfo["height"]))
    RScriptCall.append(nConfigs)
    RScriptCall.append(workResultsCsv)

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


file = open(configFile, encoding='utf-8')

configString = file.read()
config = json.loads(configString)
file.close()
outDir = config["outputPath"]


statsFiles = config["filesPaths"]
statsToParse = config["statsAnalyzed"]
configsToAnalyze = config["configs"]
csvPath = os.path.join(outDir, csv)
wcsvPath = os.path.join(outDir, workRCsv)
compressedFile = os.path.join(outDir, "stats.tar")
finalDirName = os.path.join(outDir, "stats")
try:
    os.mkdir(outDir)
except OSError as error:
    print(error)


# compressData(statsFiles, compressedFile, "*stats.txt", finalDirName)
# parseStats(finalDirName, statsToParse, configsToAnalyze, csvPath)
shutil.copyfile(csvPath, wcsvPath)  # Make a copy of the data
shouldReduceSeeds = config["reduceSeeds"]
if shouldReduceSeeds:
    reduceSeeds(configsToAnalyze, wcsvPath)

renamings = config["renameStats"]
renameStats(renamings, wcsvPath)

mixings = config["mixStats"]
mixStats(mixings, wcsvPath)
plots = config["plots"]
# Temp dir will be used
temp_dir = tempfile.gettempdir()
for plot in plots:
    # Create a temporary Csv file for each plot
    temp = tempfile.TemporaryFile()
    tempCsvPath = os.path.join(temp_dir, 'tempStats')
    shutil.copyfile(wcsvPath, tempCsvPath)  # Make a copy of the data
    plotFigure(plot,
               getPlotType(plot["plotType"]),
               str(len(config["configs"])),
               tempCsvPath)
    temp.close()  # Close will delete temporary file
