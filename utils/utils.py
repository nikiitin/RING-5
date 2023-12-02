import os

# Description: Utility functions for the project
def jsonToArg(jsonElement, key):
    commandLineArgs = []
    arg = getElementValue(jsonElement, key)
    if isinstance(arg, list):
        commandLineArgs.append(str(len(arg)))
        commandLineArgs.extend(arg)
    else:
        commandLineArgs.append(arg)
    return commandLineArgs

def getElementValue(jsonElement, key):
    
    if key in jsonElement:
        if isinstance(jsonElement[key], bool):
            return str(jsonElement[key])
        elif isinstance(jsonElement[key], int):
            return str(jsonElement[key])
        elif isinstance(jsonElement[key], float):
            return str(jsonElement[key])
        elif isinstance(jsonElement[key], str):
            return jsonElement[key]
        elif isinstance(jsonElement[key], list):
            return jsonElement[key]
    else:
        raise Exception("Key not found: " + key)
    
def checkElementExists(jsonElement, key):
    if key not in jsonElement:
        raise Exception("Key not found: " + key)
    
def checkFilesExistOrException(filePaths):
    for filePath in filePaths:
        checkFileExistsOrException(filePath)

def checkDirsExistOrException(dirPaths):
    for dirPath in dirPaths:
        checkDirExistsOrException(dirPath)
    
def checkFileExistsOrException(filePath):
    if not os.path.isfile(filePath):
        raise Exception("File does not exist: " + filePath)
    
def checkFileExists(filePath):
    return os.path.file(filePath)

def checkDirExistsOrException(dirPath):
    if not os.path.isdir(dirPath):
        raise Exception("Directory does not exist: " + dirPath)

def checkDirExists(dirPath):
    return os.path.isdir(dirPath)

def createDir(dirPath):
    if not checkDirExists(dirPath):
        os.mkdir(dirPath)
    else:
        print("Directory already exists: " + dirPath)