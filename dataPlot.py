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

def plotFigure(plotInfo, plotType, nConfigs, workResultsCsv, outDir):
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