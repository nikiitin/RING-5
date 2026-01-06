from src.data_parser.src.impl.data_parser_perl.src.type_mapping.confType import \
    confType


class Histogram(confType):
    # || cyclesinRegionCPU0::Region1:value
    # || cyclesinRegionCPU0::Region2:value
    # || cyclesinRegionCPU1::Region1:value
    def __init__(self, repeat: int, buckets: list) -> None:
        super().__init__(repeat)
        self.__dict__["buckets"] = buckets
        self.__dict__["content"] = dict()
        self.__dict__["reducedContent"] = dict()
        self.content.update((x, []) for x in buckets)

    # Histogram must be a list of floats or ints.
    # those are repeated n times for each cpu...
    # Have a fixed amout of buckets
    def __setattr__(self, __name: str, __value: dict) -> None:
        super().__setattr__(__name, __value)
        if __name == "content":
            try:
                # Check that value keys are a range of ints
                # This is the same as X-Y
                keys = __value.keys()
                for key in keys:
                    # Split the key into two values
                    # X-Y -> X and Y
                    values = key.split("-")
                    # Check that the values are ints
                    map(int, values)
                    # Check that the values are a range
                    if len(values) != 2:
                        raise TypeError(
                            "HISTOGRAM: Variable non-convertible to list of floats or ints... "
                            f"value: {__value} "
                            f"type: {type(__value)} "
                            f"field: {__name}"
                        )
                    # Check that the values are a range
                    if int(values[0]) >= int(values[1]):
                        raise TypeError(
                            "HISTOGRAM: Variable non-convertible to list of floats or ints... "
                            f"value: {__value} "
                            f"type: {type(__value)} "
                            f"field: {__name}"
                        )

            except Exception:
                raise TypeError(
                    "HISTOGRAM: Unable to turn keys of dict into ranges: "
                    f"value: {__value} "
                    f"type: {type(__value)} "
                    f"field: {__name}"
                )
            try:
                # Check if all values are ints
                map(int, __value.values())

            except Exception:
                raise TypeError(
                    "HISTOGRAM: Variable non-convertible to list of ints... value: "
                    + str(__value)
                    + " type: "
                    + str(type(__value))
                    + " field: "
                    + __name
                )
            # We have a fixed amount of buckets delimited each with a value.
            # Starting from 0 to the last bucket, which has the value N+
            # We have to add the samples to the corresponding bucket
            # For example, if we have 3 buckets, 2, 4, 4+
            # And we have the following dict as input: {0-2: 3, 3-5: 2, 6-8: 1, 9+: 10}
            # We have to add the values to the corresponding bucket
            # 2: 3
            # 4: 2
            # 4+: 11

            # Turn every key into a string and every value into a float
            __value.update((str(x), list(y)) for x, y in __value.items())
            # Check if the keys are the same as the entries
            if not set(__value.keys()).issubset(set(self.entries)):
                # Using print instead of warning purposely as print is
                # proccess safe and warning is not :(
                print(
                    "\nHISTOGRAM: Entries in file are not the same as the entries in "
                    "configuration: \n"
                    f"Expected: {self.entries}\n"
                    f"Found: {__value.keys()}\n"
                    "Maybe you should check the configuration file... Skipping not defined "
                    "entries..."
                )
            __value = dict((x, list(y)) for x, y in __value.items() if x in self.entries)
            # Update the content with the new dictionary
            self.__dict__["content"].update(__value)
        elif (
            __name == "balancedContent"
            or __name == "reducedDuplicates"
            or __name == "reducedContent"
        ):
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
                raise RuntimeError(
                    "HISTOGRAM: Variable has more values than expected... values: "
                    + str(self.content.get(entry))
                    + " length: "
                    + str(len(self.content.get(entry)))
                    + " repeat: "
                    + str(self.repeat)
                )

    def reduceDuplicates(self):
        super().reduceDuplicates()
        # HISTOGRAM can be picky. They can have different entries
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
