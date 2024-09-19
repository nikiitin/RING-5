''' @brief This module contains the CsvComparer class, which is used to compare two CSV files.
In case of a difference, the CsvComparer class will output the differences to the console.'''

import csv

class CsvComparer:
    ''' @brief CsvComparer class is used to compare two CSV files.
    In case of a difference, the CsvComparer class will output the differences to the console.'''
    def __init__(self, csv1: str, csv2: str):
        ''' @brief CsvComparer constructor.
        @param csv1 The first CSV file to compare.
        @param csv2 The second CSV file to compare.'''
        self._csv1 = csv1
        self._csv2 = csv2

    def compare(self):
        ''' @brief Compare the two CSV files.
        @return True if the files are the same, False otherwise.'''
        with open(self._csv1, 'r') as file1, open(self._csv2, 'r') as file2:
            csv1 = csv.reader(file1)
            csv2 = csv.reader(file2)
            for row1, row2 in zip(csv1, csv2):
                if row1 != row2:
                    print("Difference found:")
                    print("File 1: ", row1)
                    print("File 2: ", row2)
                    return False
        return True