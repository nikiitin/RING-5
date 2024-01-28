from src.data_parser.src.impl.data_parser_perl.src.type_mapping.confType import confType
class Vector(confType):
    #|| cyclesinRegionCPU0::Region1:value
    #|| cyclesinRegionCPU0::Region2:value
    #|| cyclesinRegionCPU1::Region1:value
    def __init__(self, repeat: int, entries: list) -> None:
        super().__init__(repeat)
        self.__dict__["entries"] = entries
        self.__dict__["content"] = dict()
        self.__dict__["reducedContent"] = dict()
        self.content.update((x, []) for x in entries)

    # Vector variable can be a list of floats or ints
    # So, we need to override the __setattr__ method
    # to make sure we are setting the content correctly
    def __setattr__(self, __name: str, __value: dict) -> None:
        super().__setattr__(__name, __value)
        if __name == "content":
            try:
                map(str, __value.keys())
            except:
                raise TypeError("VECTOR: Unable to turn keys of dict into string: " +
                                str(__value) +
                                " type: " +
                                str(type(__value)) +
                                " field: "
                                + __name)
            try:
                # Check if all values are ints
                map(int, __value.values())
            except:
                try:
                    # Check if all values are floats
                    map(float, __value.values())
                except:
                    raise TypeError("VECTOR: Variable non-convertible to list of floats or ints... value: " +
                                    str(__value) +
                                    " type: " +
                                    str(type(__value)) +
                                    " field: "
                                    + __name)
            # Turn every key into a string and every value into a float
            __value.update((str(x), list(y)) for x, y in __value.items())
            # Check if the keys are the same as the entries
            if not set(__value.keys()).issubset(set(self.entries)):
                # Using print instead of warning purposely as print is
                # proccess safe and warning is not :(
                print("\nVECTOR: Entries in file are not the same as the entries in configuration: \n" +
                        "Expected: " +
                        str(self.entries) + "\n" +
                        "Found: " +
                        str(__value.keys()) + "\n" +
                        "Maybe you should check the configuration file... Skipping not defined entries...")
            __value = dict((x, list(y)) for x, y in __value.items() if x in self.entries)
            # Update the content with the new dictionary
            self.__dict__["content"].update(__value)
        elif __name == "balancedContent" or __name == "reducedDuplicates" or __name == "reducedContent":
            # Default behaviour
            super().__setattr__(__name, __value)
        else:
            raise AttributeError("Vector variable has no attribute " + __name)

    def __str__(self):
        return super().__str__()
    
    def balanceContent(self):
        super().balanceContent()
        for entry in self.content:
            # Iterating over the keys of the dictionary
            if len(self.content.get(entry)) < int(self.repeat):
                # Fill the missing values with 0
                for i in range(len(self.content.get(entry)), int(self.repeat)):
                    self.content[entry].append(0)
            elif len(self.content.get(entry)) > int(self.repeat):
                raise RuntimeError("VECTOR: Variable has more values than expected... values: " +
                                    str(self.content.get(entry)) +
                                    " length: " +
                                    str(len(self.content.get(entry))) +
                                    " repeat: " +
                                    str(self.repeat))
        
    def reduceDuplicates(self):
        super().reduceDuplicates()
        # Vectors can be picky. They can have different entries
        # So, we need to do arithmetic mean for each entry
        self.reducedContent = dict()
        self.reducedContent.update((x, []) for x in self.entries)
        # For each entry, get the values and do arithmetic mean
        for entry in self.entries:
            # Get the values for the entry
            self.reducedContent[entry] = 0
            values = self.content.get(entry)
            for i in range(0, int(self.repeat)):
                # Get the value for the entry     
                self.reducedContent[entry] += int(values[i])
            # Do arithmetic mean
            self.reducedContent[entry] = self.reducedContent[entry] / int(self.repeat)