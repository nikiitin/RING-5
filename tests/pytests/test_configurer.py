from src.data_plotter.plot_config.src.configurerBuilder import ConfigurerBuilder
from common.csvComparer import CsvComparer
import shutil
import os
import json

class TestConfigurer:
    testConfigurerJsonPath = os.path.relpath("tests/pytests/mock/config_files/json_components/config/")
    inputsDir = os.path.relpath("tests/pytests/mock/inputs")
    expectsDir = os.path.relpath("tests/pytests/mock/expects")
    def test_e2e(self, tmp_path, capsys):
        # Copy the input files to the temporary directory
        # It is a mock csv file
        dstCsvFile = shutil.copyfile(os.path.join(self.inputsDir,
                                     "csv/configurer/configurer_test_case01.csv"),
                                     os.path.join(tmp_path, "configurer_test_case01.csv"))
        # Read the json file for this configurer
        # It is a mock json file
        configurerJsonPath = os.path.join(self.testConfigurerJsonPath,
                                          "configurer_tests_e2e.json")
        with open(configurerJsonPath, "r") as file:
            configurerJson = json.load(file)
        # For this test case, we need the "test01" configurer
        configurerJson = configurerJson["test01"]
        # There should only be one configurer setting
        assert len(configurerJson) == 1
        configurerName = list(configurerJson.keys())[0]
        # Create the configurer object
        # Need implName and params
        # implName is the name or settin of the configurer
        # params is the parameters for the configurer
        configurer = ConfigurerBuilder().build(configurerName, configurerJson[configurerName])
        # Perform the configuration
        # Party starts here
        configurer.configurePlot(dstCsvFile)
        # Check the output
        comparer = CsvComparer(dstCsvFile, os.path.join(self.expectsDir,
                                "csv/configurer/configurer_test_e2e01.csv"))
        assert comparer.compare()
        
        # Remove the temporary files
        os.remove(dstCsvFile)
            