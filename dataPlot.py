import subprocess
import os.path

def filterData(benchsFiltered, configsFiltered, workResultsCsv):
    print("Filtering data")
    RScriptCall = ["./dataFilter.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(str(len(benchsFiltered)))
    RScriptCall.extend(benchsFiltered)
    RScriptCall.append(str(len(configsFiltered)))
    for filt in configsFiltered:
        RScriptCall.append(filt["confName"])
        RScriptCall.append(str(len(filt["values"])))
        RScriptCall.extend(filt["values"])
    subprocess.call(RScriptCall)

def orderData(orderingType, configOrdering, workResultsCsv):
    print("Ordering data")
    RScriptCall = ["./ordering.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(str(orderingType))
    RScriptCall.append(str(len(configOrdering)))
    RScriptCall.extend(configOrdering)
    subprocess.call(RScriptCall)

def normalizeData(shouldNorm, sd, stats, workResultsCsv):
    print("Normalize data")
    RScriptCall = ["./normalize.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(shouldNorm)
    RScriptCall.append(str(sd))
    RScriptCall.append(str(len(stats)))
    RScriptCall.extend(stats)
    subprocess.call(RScriptCall)

def plotFigure(plotInfo, plotType, nConfigs, workResultsCsv, outDir):
    filterData(plotInfo["benchmarksFiltered"],
               plotInfo["configsFiltered"],
               workResultsCsv)

    orderData(plotInfo["orderingType"],
              plotInfo["configsOrdering"],
              workResultsCsv)
    exit
    
    if plotType == "stackBarplot":
        RScriptCall = ["./stackedBarplot.R"]
        normalizeData(str(plotInfo["normalized"]),
                False,
                plotInfo["stats"],
                workResultsCsv)
    elif plotType == "barplot":
        RScriptCall = ["./barplot.R"]
        normalizeData(str(plotInfo["normalized"]),
                True,
                plotInfo["stats"],
                workResultsCsv)
    else:
        RScriptCall = ["./scalabilityPlot.R"]
        normalizeData(str(plotInfo["normalized"]),
                False,
                plotInfo["stats"],
                workResultsCsv)
        
    
    RScriptCall.append(plotInfo["title"])
    plotPath = os.path.join(outDir, plotInfo["fileName"])
    RScriptCall.append(plotPath)
    RScriptCall.append(plotInfo["xAxisName"])
    RScriptCall.append(plotInfo["yAxisName"])
    RScriptCall.append(str(plotInfo["width"]))
    RScriptCall.append(str(plotInfo["height"]))
    RScriptCall.append(workResultsCsv)

    # Stacking info
    # TODO: Move into a method
    # NOTE: I am implementing in my free time and faster than ligth
    # take this into account as maybe some things are pure ad-hoc
    # Feel free to improve the tool!
    if plotType == "stackBarplot":
        RScriptCall.append(str(len(plotInfo["stats"])))
        RScriptCall.extend(plotInfo["stats"])
        RScriptCall.append(str(len(plotInfo["groupNames"])))
        RScriptCall.extend(plotInfo["groupNames"])
    elif plotType == "barplot":
        RScriptCall.append(str(len(plotInfo["stats"])))
        RScriptCall.extend(plotInfo["stats"])
    else:
        RScriptCall.append(str(nConfigs))
        RScriptCall.append(str(len(plotInfo["stats"])))
        RScriptCall.extend(plotInfo["stats"])
        RScriptCall.append(plotInfo["xAxis"])
        RScriptCall.append(plotInfo["iterate"])

    RScriptCall.append(str(len(plotInfo["legendNames"])))
    RScriptCall.extend(plotInfo["legendNames"])
    RScriptCall.append(str(len(plotInfo["breaks"])))
    RScriptCall.extend(plotInfo["breaks"])
    RScriptCall.append(str(plotInfo["limitTop"]))
    RScriptCall.append(str(plotInfo["limitBot"]))
    RScriptCall.append(plotInfo["format"])
    RScriptCall.append(plotInfo["legendTitle"])
    RScriptCall.append(str(plotInfo["nLegendElementsPerRow"]))
    print(RScriptCall)
    subprocess.call(RScriptCall)
