import os
import enum
import tempfile

# Description: Utility functions for the project
def getPathToRingRoot():
    pass

def jsonToArg(jsonElement, key):
    commandLineArgs = []
    arg = getElementValue(jsonElement, key)
    if isinstance(arg, list):
        commandLineArgs.append(str(len(arg)))
        commandLineArgs.extend(arg)
    else:
        commandLineArgs.append(str(arg))
    return commandLineArgs

def jsonToOptionalArg(jsonElement, key):
    if (checkElementExistNoException(jsonElement, key)):
        return jsonToArg(jsonElement, key)
    else:
        return ["0"]
    

def getElementValue(jsonElement, key, optional=True) -> bool | int | float | str | list | dict | None:
    if key in jsonElement:
        if jsonElement[key] is None:
            if optional:
                return None
            else:
                raise Exception("Value is None for key: " + key + " and is not optional")
        else:
            return jsonElement[key]
    else:
        raise Exception("Key not found: " + key) 
    
def checkElementExists(jsonElement, key):
    if key not in jsonElement:
        raise Exception("Key not found: " + key)

def checkElementExistNoException(jsonElement, key):
    if key not in jsonElement:
        return False
    else:
        return True

def checkEnumExistsNoException(jsonElement: dict, enum: enum.EnumMeta):
    for key in jsonElement:
        if key in enum.__members__:
            return True
    return False

def getEnumValue(jsonElement: dict, enumType: enum.EnumMeta):
    for key in jsonElement:
        for enum_member in enumType:
            if key == enum_member.value:
                return key
    return None


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
    return os.path.isfile(filePath)

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

def createTmpFile():
    # Create a temporary file and return the path
    tmp = tempfile.mkstemp()
    # Close the file descriptor and return the path
    os.close(tmp[0])
    return tmp[1]

def removeFile(filePath):
    if checkFileExists(filePath):
        os.remove(filePath)
    else:
        print("Cannot remove, file does not exist: " + filePath)

def checkVarType(var, varType):
    if not isinstance(var, varType):
        raise Exception("Variable is not of type " + str(varType) + ": " + str(var))