import src.utils.utils as utils
from src.data_plotter.plot_config.src.configurerFactory import ConfigurerFactory
from src.data_plotter.plot_config.src.configurer import ConfigurerType, Configurer

class ConfigurerBuilder:
    def __init__(self):
        self.configurer = None

    def build(self, confType: str, configurerJson: dict) -> Configurer:
        # Create the configurer
        self.configurer = ConfigurerFactory.getConfigurer(confType, configurerJson)
        subconfigurerInfo = utils.getEnumValue(configurerJson, ConfigurerType)
        # If there is a subconfigurer, create it
        if subconfigurerInfo is not None:
            self.configurer.addConfigurer(ConfigurerBuilder().build(
                subconfigurerInfo, utils.getElementValue(
                    configurerJson, subconfigurerInfo)))
        
        return self.configurer