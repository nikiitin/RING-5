import subprocess

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


def reduceSeeds(configs, stat, workResultsCsv):
    print("Reducing seeds and calculating mean and sd")
    RScriptCall = ["./reduceSeeds.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(str(len(configs) + 1))
    RScriptCall.append(stat)
    subprocess.call(RScriptCall)

def removeOutliers(stat,workResultsCsv):
    print("Removing outliers")
    RScriptCall = ["./removeOutliers.R"]
    RScriptCall.append(workResultsCsv)
    RScriptCall.append(stat)
    subprocess.call(RScriptCall)
