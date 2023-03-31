import os.path
import subprocess

def compressData(files, output, name, finalDirName):
    print("Compressing data")
    shellScriptCall = ["./dataCompressor.sh"]
    shellScriptCall.append(output)
    shellScriptCall.append(str(len(files)))
    shellScriptCall.extend(files)
    shellScriptCall.append(name)
    shellScriptCall.append(finalDirName)
    subprocess.call(shellScriptCall)

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

# Main function that must be called from stats_analyzer.py
def runParse(config, csvPath):
    outDir = config["outputPath"]
    statsFiles = config["filesPaths"]
    statsToParse = config["statsAnalyzed"]
    configsToAnalyze = config["configs"]
    compressedFile = os.path.join(outDir, "stats.tar")
    finalDirName = os.path.join(outDir, "stats")
    compressData(statsFiles, compressedFile, "*stats.txt", finalDirName)
    parseStats(finalDirName, statsToParse, configsToAnalyze, csvPath)
