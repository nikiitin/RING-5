# Generic class for any type of configuration variable
# Will need to be mapped to a specific type of configuration variable
# see type_mapping/mapper.py
from typing import Any


class confType:
    # This contains all the repeated values of the variable
    # The variable is a list of whatever values needed
    # That will be resolved in the specific type
    
    def __init__(self, repeat: int) -> None:
        # Only save the content. Identifier is not needed here
        # Content will be the dynamic content of the variable
        # and will depend on the type
        self.__dict__["content"] = list()
        # Avoid using the __setattr__ method
        self.__dict__["repeat"] = repeat
        self.__dict__["reducedContent"] = 0
        self.__dict__["balancedContent"] = False
        self.__dict__["reducedDuplicates"] = False

    def __setattr__(self, __name: str, __value: Any) -> None:
        # Depending on the type of the variable, the content will be different
        # This is why we need to override the __setattr__ method...
        # ...to make sure we are setting the content correctly
        pass
    
    def __str__(self) -> str:
        # This method gives the string representation of the variable
        stringVariable = ""
        for value in self.content:
            stringVariable += str(value) + " "
        return str(stringVariable + "\n")

    def __repr__(self) -> str:
        return str(self.__str__())

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name == "content":
            if self.__dict__.get("content") is None:
                self.__dict__["content"] = list()
            return
        super().__setattr__(__name, __value)
            

    def __getattribute__(self, __name: str) -> Any:
        if __name == "content":
            if self.__dict__.get("content") is None:
                # This is unexpected. This should never happen
                raise AttributeError("Trying to access content of variable that has not been initialized")
        if __name == "reducedContent":
            if self.__dict__.get("reducedDuplicates") == False or self.__dict__.get("balancedContent") == False:
                raise AttributeError("Trying to access reduced content of variable that has not been reduced or balanced")
        return super().__getattribute__(__name)
    
    def balanceContent(self) -> None:
        # Balance the entries of the content list
        # This means that every entry will have the same number of values
        # This is done by filling the missing values with 0
        # The number of entries MUST be specified as repeat in the constructor
        self.balancedContent = True
        pass
    
    def reduceDuplicates(self) -> Any:
        # This method removes duplicates from the content
        # by doing arithmetic mean to the values
        # Only applyable to Scalars and Vectors
        self.reducedDuplicates = True
        # Better return NA than 0 if not found in file
        if len(self.content) == 0:
            self.reducedContent = "NA"
        pass
            
            