import glob
import os

from tqdm import tqdm

import src.utils.utils as utils
from src.parsing.impl.data_parser_perl.src.compressor.compressor import Compressor
from src.parsing.impl.data_parser_perl.src.parser_impl.perlParseWork import (
    PerlParseWork,
)
from src.parsing.impl.data_parser_perl.src.type_mapping.typeMapper import TypeMapper
from src.parsing.interface import DataParserInterface
from src.parsing.params import DataParserParams


class DataParserPerl(DataParserInterface):
    def __init__(self, params: DataParserParams) -> None:
        super().__init__(params)
        self._results = []

    def _mapParsingVars(self, parsingVars: list) -> dict:
        varsToParse = dict()
        for var in parsingVars:
            utils.checkElementExists(var, "id")
            utils.checkElementExists(var, "type")
            identifier = utils.getElementValue(var, "id")
            dataType = utils.getElementValue(var, "type")
            # Put the info from json to variable
            if varsToParse.get(identifier) is not None:
                raise RuntimeError("Variable already defined in parsing: " + identifier)
            if utils.checkElementExistNoException(var, "repeat"):
                repeat = utils.getElementValue(var, "repeat")
            else:
                repeat = 1
            if dataType == "vector":
                utils.checkElementExists(var, "vectorEntries")
                vectorEntries = utils.getElementValue(var, "vectorEntries")
                varsToParse.update(
                    {identifier: TypeMapper.map(dataType, repeat, vectorEntries=vectorEntries)}
                )
            elif dataType == "distribution":
                utils.checkElementExists(var, "maximum")
                maximum = utils.getElementValue(var, "maximum")
                utils.checkElementExists(var, "minimum")
                minimum = utils.getElementValue(var, "minimum")
                varsToParse.update(
                    {identifier: TypeMapper.map(dataType, repeat, maximum=maximum, minimum=minimum)}
                )
            elif dataType == "configuration":
                # Add this variable as a categorical variable
                onEmpty = "None"
                if utils.checkElementExistNoException(var, "onEmpty"):
                    onEmpty = utils.getElementValue(var, "onEmpty")
                varsToParse.update({identifier: TypeMapper.map(dataType, repeat, onEmpty=onEmpty)})
            else:
                varsToParse.update({identifier: TypeMapper.map(dataType, repeat)})

            # Helper to map object
            obj = varsToParse[identifier]

            # Check for multi-ID mapping (Reduction)
            if utils.checkElementExistNoException(var, "parsed_ids"):
                parsed_ids = utils.getElementValue(var, "parsed_ids")
                if isinstance(parsed_ids, list):
                    for pid in parsed_ids:
                        if (
                            pid != identifier
                        ):  # identifier matches one of them usually, or is the reduced name
                            varsToParse[pid] = obj
        return varsToParse

    def _getFilesToParse(self, parsing: dict) -> list:
        # Get the values for the path, files and vars
        filesPath = utils.getElementValue(parsing, "path")
        files = utils.getElementValue(parsing, "files")
        # Look for all the files recursively that end with suffix
        print("Looking for files in path: " + filesPath)
        filesFound = glob.glob(filesPath + "/**/" + files, recursive=True)
        return filesFound

    def _parseFile(self, file: str, varsToParse: dict):
        # Add the parsing work to the pool
        self._parseWorkPool.addWork(PerlParseWork(file, varsToParse))

    def _compressData(self):
        # Use python to compress the data
        # Get the files to compress
        filesToCompress = []
        for parsing in self._parseConfig:
            # Get the files to parse
            filesFound = self._getFilesToParse(parsing)
            # Check if there are files found
            if len(filesFound) == 0:
                Warning(
                    "No files found for parsing in path: " + utils.getElementValue(parsing, "path")
                )
                # Nothing to do here...
                continue
            # Add the files to the list
            filesToCompress.extend(filesFound)
        # Create the compresor
        compressor = Compressor.getInstance()
        # Compress the files
        compressor(filesToCompress, self._args.getOutputDir(), "stats")

    def _parseStats(self):
        for parsing in self._parseConfig:
            # Get the files to parse
            if self._shouldCompress == "True":
                # Get the files from the compressed file
                # Get the files from the compressed file
                filesFound = glob.glob(
                    self._args.getOutputDir()
                    + utils.getElementValue(parsing, "path")
                    + "/**/"
                    + utils.getElementValue(parsing, "files"),
                    recursive=True,
                )
            else:
                # If data is not compressed, get the files from the path
                filesFound = self._getFilesToParse(parsing)
            # Check if there are files found
            if len(filesFound) == 0:
                Warning(
                    "No files found for parsing in path: " + utils.getElementValue(parsing, "path")
                )
                # Nothing to do here...
                continue
            # Map the vars to types used in parsing
            # Map the vars to types used in parsing
            parsingVars = parsing["vars"]
            mappedVars = self._mapParsingVars(parsingVars)
            # Take the name of the variables to parse and store
            # them in the object, this will be used later
            # to turn the results into csv
            # FIX: Only use the IDs defined in the config, not the mapped (concrete) IDs
            self._varsToParse = [v["id"] for v in parsingVars]

            # We must use mappedVars for the actual parsing work though
            parsingVars = mappedVars
            # Start the pool for parse workers
            self._parseWorkPool.startPool()
            # Parse the files
            print("Adding files to parse...")
            for file in tqdm(filesFound):
                # Parse the file
                self._parseFile(file, parsingVars)
            print("Parsing files...")
            # Get the results from the pool
            self._results = self._parseWorkPool.getResults()

    def _turnIntoCsv(self):
        # Turn the results into csv
        # First, create the header
        # print(self._results)
        header = ""
        # If there are no results, return
        if len(self._results) == 0:
            return
        # Get the first file. From here we will get the variables
        # Get the first file. From here we will get the variables
        file = self._results[0]
        for varName in self._varsToParse:
            # Get the variable
            var = file[varName]
            # Get the variable type
            varType = type(var).__name__
            # Check if the variable is a vector
            if varType == "Vector":
                # Get the vector entries
                vectorEntries = var.entries
                # Create the header for the vector
                for entry in vectorEntries:
                    header += varName + ".." + entry + ","
            elif varType == "Distribution":
                distEntries = var.entries
                # Create the header for the distribution
                for entry in distEntries:
                    header += varName + ".." + str(entry) + ","
            else:
                # Create the header for the rest of the variables
                header += varName + ","
        # Remove the last whitespace
        header = header[:-1]
        # Create the file
        output_dir = self._args.getOutputDir()
        print(f"Creating stats.csv in: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        print("Creating stats.csv file..." + os.path.join(output_dir, "stats.csv"))
        with open(os.path.join(output_dir, "results.csv"), "w") as statsFile:
            # Write the header
            statsFile.write(header + "\n")
            # Write the stats
            for file in range(0, len(self._results)):
                line = ""
                fileStats = self._results[file]
                for varName in self._varsToParse:
                    # Get the variable
                    var = fileStats[varName]
                    var.balanceContent()
                    var.reduceDuplicates()
                    # Get the variable type
                    varType = type(var).__name__
                    # Check if the variable is a vector
                    if varType == "Vector":
                        # Get the vector entries
                        vectorEntries = var.entries
                        for entry in vectorEntries:
                            # Write the content
                            line += str(var.reducedContent[entry]) + ","
                    elif varType == "Distribution":
                        # Get the distribution entries
                        distEntries = var.entries
                        for entry in distEntries:
                            # Write the content
                            line += str(var.reducedContent[entry]) + ","
                    else:
                        # Write the content
                        line += str(var.reducedContent) + ","
                # Remove the last comma
                line = line[:-1]
                # Write the line
                statsFile.write(line + "\n")
