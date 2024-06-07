#!/usr/bin/Rscript
# DO NOT SOURCE THE INTERFACE FILE!
# IT WILL OVERRIDE THE METHODS DEFINED IN THIS FILE
# Define the S4 class for a data sorter
setClass("Sort",
    contains = "Data_configurator"
)

# Override perform method from Data_configurator class
setMethod(
    "perform",
    signature(object = "Sort"),
    function(object) {
        # For every sort variable
        # in sorts data frame
        # Sort the data frame by the sort variable
        sorted_df <- object@args@df
        sort_vars <- get_all_keys(object@args@sorts)
        for (sort_var in sort_vars) {
            # Sort the data frame by the sort variable
            # using the order specified in the sorts data frame
            sorted_df[, sort_var] <- factor(
                sorted_df[, sort_var],
                levels = object@args@sorts[sort_var])
            sorted_df <- sorted_df[order(sorted_df[, sort_var]), ]
        }
        object@args@df <- sorted_df
        # Return the object
        object@args@df
    }
)
