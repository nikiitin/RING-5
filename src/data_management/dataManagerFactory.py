from argumentParser import AnalyzerInfo

from src.data_management.impl import (
    mixer,
    outlierRemover,
    preprocessor,
    renamer,
    seedsReducer,
)


class DataManagerFactory:
    @staticmethod
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
            manager = None
            # Check if the renamer is present in the json file
            if element == "rename":
                manager = renamer.Renamer(params, manager_json)
                managers.append(manager)

            # Check if the mixer is present in the json file
            if element == "mixer":
                manager = mixer.Mixer(params, manager_json)
                managers.append(manager)

            # Check if the outlierRemover is present in the json file
            if element == "outlierRemover":
                manager = outlierRemover.OutlierRemover(params, manager_json)
                managers.append(manager)

            # Check if the seedsReducer is present in the json file
            if element == "seedsReducer":
                manager = seedsReducer.SeedsReducer(params, manager_json)
                managers.append(manager)

            if element == "preprocessor":
                manager = preprocessor.Preprocessor(params, manager_json)
                managers.append(manager)

            if manager is None:
                raise ValueError(f"DataManager {element} is not defined in the json file")

        return managers
