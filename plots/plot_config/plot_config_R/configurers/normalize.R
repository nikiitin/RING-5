#!/usr/bin/Rscript
# DO NOT SOURCE THE INTERFACE FILE!
# IT WILL OVERRIDE THE METHODS DEFINED IN THIS FILE
# Define the S4 class for data normalizer
setClass("Normalize",
    contains = "Data_configurator"
)

# Override perform method from Data_configurator class
setMethod(
  "perform",
  signature(object = "Normalize"),
  function(object) {
    # Get the unique combinations for x axis
    unique_x_keys <- unique(object@args@df[, object@args@x])
    # For every unique combination of x axis
    for (key in unique_x_keys) {
      # Get the data to normalize (one per x axis combination)
      norm_rows <- object@args@df[
        object@args@df[, object@args@x] == key,
        object@args@y
        ]
      norm_df_rows <- object@args@df[
        object@args@df[, object@args@x] == key,
        object@args@y_sd]
      # Get the normalizer (only one row per x axis combination)
      normalizer <- norm_rows[object@args@normalizer_index]
      # Normalize with respect to the normalizer
      object@args@df[
        object@args@df[, object@args@x] == key,
        object@args@y
        ] <-
        norm_rows / normalizer
      object@args@df[
        object@args@df[, object@args@x] == key,
        object@args@y_sd
        ] <-
        norm_df_rows / normalizer

    }
    # Return the object
    object@args@df
  }
)
