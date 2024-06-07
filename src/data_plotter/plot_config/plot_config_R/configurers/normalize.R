#!/usr/bin/Rscript
# DO NOT SOURCE THE INTERFACE FILE!
# IT WILL OVERRIDE THE METHODS DEFINED IN THIS FILE
# Define the S4 class for data normalizer
setClass("Normalize",
    contains = "Data_configurator"
)
setGeneric("normSelector", function(object, df) {
    standardGeneric("normSelector")
})
setMethod(
  "normSelector",
  signature(object = "Normalize"),
  function(object, df) {
    if (as.numeric(object@args@n_normalizer_selector) == 1 &&
        object@args@normalizer_selector[1] == "all") {
      df
    } else {
      df[, object@args@normalizer_selector]
    }
  }
)

# Override perform method from Data_configurator class
setMethod(
  "perform",
  signature(object = "Normalize"),
  function(object) {
    # Get the unique combinations for x axis
    unique_x_keys <- unique(object@args@df[, object@args@normalizer_var])
    # For every unique combination of x axis
    for (key in unique_x_keys) {
      # Get the data to normalize (one per x axis combination)
      norm_rows <- object@args@df[
        object@args@df[, object@args@normalizer_var] == key,
        object@args@y
        ]
      norm_df_rows <- object@args@df[
        object@args@df[, object@args@normalizer_var] == key,
        object@args@y_sd]
      # Check if y length is greater than 1 (is a vector)
      # Get the normalizer (only one row per x axis combination)
      if (length(object@args@y) > 1) {
        normalizer <- norm_rows[object@args@normalizer_index, ]
        normalizer <- normSelector(object, normalizer)
        print("normalizer")
        print(key)
        print(norm_rows)
        normalizer <- sum(normalizer)
      } else {
        normalizer <- norm_rows[object@args@normalizer_index]
        normalizer <- normSelector(object, normalizer)
      }

      if (normalizer == 0) {
        normalizer <- 1
      }
      # Normalize with respect to the normalizer
      ## TODO: mutate the normalizer to be the cumsum of all y values in the group
      object@args@df[
        object@args@df[, object@args@normalizer_var] == key,
        object@args@y
        ] <-
        norm_rows / normalizer
      object@args@df[
        object@args@df[, object@args@normalizer_var] == key,
        object@args@y_sd
        ] <-
        norm_df_rows / normalizer

    }
    # Return the object
    object@args@df
  }
)
