from typing import Any
from src.data_parser.src.impl.data_parser_perl.src.type_mapping.confType import confType
class Distribution(confType):
    #|| ReceivedForwardsCPU0::-1:freq
    #|| ReceivedForwardsCPU0::0:freq
    #|| ReceivedForwardsCPU0::1:freq
    #|| ReceivedForwardsCPU0::overflows:freq
    #|| ReceivedForwardsCPU0::underflows:freq

    def __init__(self, repeat: int, maximum: int, minimum: int) -> None:
        super().__init__(repeat)
        self.__dict__["maximum"] = maximum
        self.__dict__["minimum"] = minimum
        self.__dict__["content"] = dict()
        self.__dict__["reducedContent"] = dict()
        # Create the buckets
        # minimum - 1 and maximum + 2 are the underflow and overflow buckets
        self.content.update((str(x), []) for x in range(int(minimum), int(maximum) + 1))

    # Distribution must be a list of ints representing the number of times
    # a value (key) has appeared
    # Those are repeated n times for each cpu...
    # Have a fixed amout of buckets, which are the keys, the last key and the first key
    # are the underflow and overflow buckets, respectively and
    # are defined by the maximum and minimum values, the key format is:
    # - "underflows" which should be represented with "2nd element-" key
    # + "overflows" which should be represented with "last element+" key
    # "X" where X is the value of the bucket
    # so, as result we have a dict with the following format:
    # { "0-" : [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #  "0" : [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #  "1" : [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #  "1+" : [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    # }
        
    def __getattribute__(self, __name: str) -> Any:
        if __name == "entries":
            return super().__getattribute__("content").keys()
        return super().__getattribute__(__name)
        
    def __setattr__(self, __name: str, __value: dict) -> None:
        super().__setattr__(__name, __value)
        if __name == "content":
            try:
                # Check that value key is either an int or an underflow(-) or overflow(+)
                keys = __value.keys()
                for key in keys:
                    # Check that the values are ints or underflow or overflow
                    if key != "underflows" and key != "overflows":
                        int(key)
            except:
                raise TypeError("DISTRIBUTION: Variable non-convertible to int... value: " +
                                str(__value) +
                                " type: " +
                                str(type(__value)) +
                                " field: "
                                + __name)
            try:
                # Check if all values are ints
                map(int, __value.values())
            except:
                raise TypeError("DISTRIBUTION: Variable non-convertible to list of ints... value: " +
                                str(__value) +
                                " type: " +
                                str(type(__value)) +
                                " field: "
                                + __name)

            # Check "-" and "+" are in the keys
            if not "underflows" in __value.keys() or not "overflows" in __value.keys():
                raise TypeError("DISTRIBUTION: Variable does not contain underflows or overflows... value: " +
                                str(__value) +
                                " type: " +
                                str(type(__value)) +
                                " field: "
                                + __name)
            # Change "-" and "+" to "firstKey-" and "lastKey+"
            
            
            # Do it like this, so we can keep the order of the keys
            # in any case
            
            # Check if minimum and maximum are in the keys
            if not self.__dict__["minimum"] in keys or not self.__dict__["maximum"] in keys:
                # Using print instead of warning purposely as print is
                # proccess safe and warning is not :(
                raise RuntimeError("DISTRIBUTION: Minimum or maximum not in keys: \n" +
                        "Expected: " +
                        str(self.__dict__["minimum"]) + "\n" +
                        str(self.__dict__["maximum"]) + "\n" +
                        "Found: " +
                        str(keys) + "\n" +
                        "Maybe you should check the configuration file...")
            # Change the keys
            underflows = __value.pop("underflows")
            overflows = __value.pop("overflows")
            keys = __value.keys()
            __value[(self.__dict__["minimum"] + "-")] = underflows
            __value[(self.__dict__["maximum"] + "+")] = overflows
            # Turn every key into a string and every value into a float
            __value.update((str(x), list(y)) for x, y in __value.items())
            # Check if the keys are the same as the buckets
            # Expected values are the buckets
            expectedValues = []
            for i in range(int(self.__dict__["minimum"]), int(self.__dict__["maximum"]) + 1):
                expectedValues.append(str(i))
            expectedValues.append(str(self.__dict__["minimum"]) + "-")
            expectedValues.append(str(self.__dict__["maximum"]) + "+")
            if not set(__value.keys()).issubset(expectedValues):
                raise RuntimeError("DISTRIBUTION: Keys in file are not the same as the buckets in configuration: \n" +
                        "Expected: " +
                        str(expectedValues) + "\n" +
                        "Found: " +
                        str(__value.keys()) + "\n" +
                        "Maybe you should check the configuration file...")
            __value = dict((x, y) for x, y in __value.items() if x in expectedValues)
            # Update the content with the new dictionary
            self.__dict__["content"].update(__value)
        elif __name == "balancedContent" or __name == "reducedDuplicates" or __name == "reducedContent":
            # Default behaviour
            super().__setattr__(__name, __value)
        else:
            raise AttributeError("Distribution variable has no attribute " + __name)

    def __str__(self):
        return super().__str__()
    
    def balanceContent(self) -> None:
        super().balanceContent()
        # Balance the content
        for key in self.content:
            # Get the content of the key
            content = self.content[key]
            # Get the length of the content
            contentLen = len(content)
            # Get the repeat value
            repeat = int(self.repeat)
            # Check if the repeat value is greater than the length of the content
            if repeat > contentLen:
                # Fill the missing values with 0
                for i in range(contentLen, repeat):
                    content.append(0)
            elif repeat < contentLen:
                raise RuntimeError("DISTRIBUTION: Variable has more values than expected... values: " +
                                    str(content) +
                                    " length: " +
                                    str(contentLen) +
                                    " repeat: " +
                                    str(repeat))

    def reduceDuplicates(self) -> None:
        super().reduceDuplicates()
        # Reduce the duplicates
        # For each bucket, get the values and do arithmetic mean
        for bucket in self.content:
            # Get the values for the bucket
            self.reducedContent[bucket] = 0
            values = self.content.get(bucket)
            for i in range(0, int(self.repeat)):
                # Get the value for the bucket     
                self.reducedContent[bucket] += int(values[i])
            # Do arithmetic mean
            self.reducedContent[bucket] = self.reducedContent[bucket] / int(self.repeat)
