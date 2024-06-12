#!/usr/bin/Rscript
# DO NOT SOURCE THE INTERFACE FILE!
# IT WILL OVERRIDE THE METHODS DEFINED IN THIS FILE
# Define the S4 class for a data filter
setClass("Filter",
  contains = "Data_configurator"
)

# Override all needed methods from the Data_configurator class

# Override perform method from Data_configurator class
setMethod(
  "perform",
  signature(object = "Filter"),
  function(object) {
    # For every filter variable
    # in filters data frame
    # Remove the rows that contain the filtered value
    filtered_df <- object@args@df
    filt_names <- get_all_keys(object@args@filters)
    for (filter_var in filt_names) {
      # Get the column that will be filtered
      # from the data frame with filter_var name
      column_to_filter <- filtered_df[, filter_var]
      # Remove the rows that contain the filtered value
      filtered_df <- filtered_df[!column_to_filter %in%
        object@args@filters[filter_var],
        ]
    }
    object@args@df <- filtered_df
    # Return the object
    object@args@df
  }
)