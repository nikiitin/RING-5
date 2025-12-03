#!/usr/bin/env python3
from typing import Any
from src.data_plotter.src.shaper.uniDfShaper import UniDfShaper
import src.utils.utils as utils
import pandas as pd
import numpy as np

class Sort(UniDfShaper):

    # Getters and setters
    @property
    def order_dict(self) -> dict:
        return self.order_dict_data
    @order_dict.setter
    def order_dict(self, value: Any) -> None:
        utils.checkVarType(value, dict)
        for key, content in value.items():
            utils.checkVarType(key, str)
            utils.checkVarType(content, list)
            for item in content:
                utils.checkVarType(item, str)
        self.order_dict_data = value

    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self.order_dict = utils.getElementValue(self._params, "order_dict")
    
    def __call__(self, data_frame: Any) -> pd.DataFrame:
        data_frame = super().__call__(data_frame)
        # Make a copy to avoid SettingWithCopyWarning
        result = data_frame.copy()
        
        print("order_dict: ", self.order_dict)
        for column, orders in self.order_dict.items():
            print("column: ", column)
            print("orders: ", orders)
            print(pd.Categorical(result[column], categories=orders, ordered=True))
            result[column] = pd.Categorical(result[column], categories=orders, ordered=True)
        
        result = result.sort_values(by=list(self.order_dict.keys()))

        for column in self.order_dict:
            result[column] = result[column].astype(str)
        
        return result
    
# Main function to test the sort class
def test():
    # Create a sample data frame
    df = pd.DataFrame({
    'system_id': ['S1', 'S1', 'S1', 'S1', 'S2', 'S2', 'S2', 'S2', 'S3', 'S3', 'S3', 'S3', 'S3'],
    'benchmark': ['B1', 'B2', 'B1', 'B2', 'B1', 'B2', 'B1', 'B2', 'B1', 'B2', 'B1', 'B2', "B2"],
    'throughput': [100, 105, 120, 118, 80, 82, 78, 85, 90, 95, 100, 102, 84],
    'latency': [1.2, 1.1, 1.5, 1.4, 2.0, 1.9, 2.1, 2.2, 1.8, 1.7, 1.6, 1.5, 1.2],
    'config_param': ['A1', 'A1', 'A2', 'A2', 'B1', 'B1', 'B2', 'B2', 'C1', 'C1', 'C2', 'C2', 'C1']
    })
    params = {
        'order_dict': {'system_id' : ['S1', 'S2', 'S3'], 'config_param': ['C1', 'C2', 'A1', 'A2', 'B1', 'B2'] },
        'srcCsv': 'normtest.csv',
        'dstCsv': 'output_data.csv'
    }
    print("input: ")
    print(df)
    sort_shaper = Sort(params)
    df = sort_shaper(df)
    print("result: ")
    print(df)