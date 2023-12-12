import tempfile
import json
import os
import shutil
import argparse
import utils.utils as utils

temp_dir = tempfile.gettempdir()
# TODO: Switch to specialized classes for each action
class AnalyzerInfo:
    
    # Private methods
    def _parseArgs(self):
        argParser = argparse.ArgumentParser()
        argParser.add_argument("-c", "--csv", dest='csv',
                    help="csv name you want to generate/use",
                    default="results.csv")
        argParser.add_argument("-f", "--configFile",dest='configFile',
                    default="./config_files/config.json",
                    help="config file to be used")
        argParser.add_argument('-s', '--skipParse', dest='skipParse',
                    default=False,
                    action='store_true',
                    help="skip transfering and parsing data if csv already exists")
        argParser.add_argument('-d', '--debug', dest='debug',
                    default=False,
                    action='store_true',
                    help="debug mode: do not delete temporary files and print more info")
        return argParser.parse_args()

    def _createOutDir(self):
        outDir = self._json["outputPath"]
        if not utils.checkDirExists(outDir):
            try:
                print("Output directory does not exist, want to create it? (y/n)")
                answer = input()
                if answer == "y":
                    # Create output directory
                    utils.createDir(outDir)
                else:
                    print("Exiting")
                    exit()
                # Create output directory
            except OSError as error:
                print(error)
                exit()
        else:
            print("Output directory found: " + outDir)
        
    # Getters
    def getArgs(self):
        return self._args

    def getJson(self):
        return self._json

    def getCsv(self):
        return os.path.join(self._json["outputPath"], self._args.csv)
    
    def getWorkCsv(self):
        return os.path.join(tempfile.gettempdir(), self._workCsv)
    
    def getTmpDir(self):
        return temp_dir
    
    def getSkipParse(self):
        return self._args.skipParse
    
    def getDebug(self):
        return self._args.debug
    
    # Public methods
    def __init__ (self):
        # Constant temporary csv to work.
        # Avoid modifying the original csv
        self._workCsv = "wresults.csv"
        self._args = self._parseArgs()
        # Read config
        with open(self._args.configFile, encoding='utf-8') as file:
            configString = file.read()
            self._json = json.loads(configString)
        self._createOutDir()
    
    def createWorkCsv(self):
        print("Creating work csv: " + self.getWorkCsv() + " from: " + self.getCsv())
        shutil.copyfile(self.getCsv(), self.getWorkCsv())
