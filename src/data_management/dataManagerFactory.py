from argumentParser import AnalyzerInfo
from src.data_management.impl import renamer, mixer, outlierRemover, seedsReducer

class DataManagerFactory:
    def getDataManager(params: AnalyzerInfo) -> list:
        """
        Factory function. It will read the json file and create a list of
        DataManager objects. The json file must contain the parameters for
        each DataManager. The json file must contain the following keys:
        - rename: A dictionary with the columns to be renamed.
        - mixer: A dictionary with the columns to be mixed.
        - outlierRemover: A boolean indicating if the outlier remover should be used.
        - seedsReducer: A boolean indicating if the seeds reducer should be used.
        The returned list will have to be called in order to apply the changes to the DataFrame.
        The order of some DataManagers could be important, all will be called in the same order
        they are specified in the json file.
        Args:
            params: The parameters for the DataManager. This MUST include the json file
        Returns:
            A list of DataManager objects. The list will be empty if no DataManager is present
            in the json file.
        """
        json = params.getJson()
        manager_json = json["dataManagers"]
        managers = []
        for element in manager_json.keys():

            # Check if the renamer is present in the json file
            if element == "rename":
                managers.append(renamer.Renamer(params, manager_json))
            
            # Check if the mixer is present in the json file
            if element == "mixer":
                managers.append(mixer.Mixer(params, manager_json))
            
            # Check if the outlierRemover is present in the json file
            if element == "outlierRemover":
                managers.append(outlierRemover.OutlierRemover(params, manager_json))
            
            # Check if the seedsReducer is present in the json file
            if element == "seedsReducer":
                managers.append(seedsReducer.seedsReducer(params, manager_json))
        
        return managers