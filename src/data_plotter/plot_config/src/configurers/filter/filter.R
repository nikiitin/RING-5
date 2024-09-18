#!/usr/bin/Rscript
source("src/data_plotter/plot_config/src/configurers/configurer.R")

#' @title Filter
#' @description Filter configurer. This configurer
#' will remove the selected elements with the selected
#' values from the data frame

setClass("Filter",
    contains = "Configurer",
    slots = list(
        # Arguments for the filter
        # Variable selected to filter
        filter_var = "character",
        # Values to remove from the data frame
        values = "nullable_vector"
    )
) -> Filter

setValidity(
    "Filter",
    function(object) {
        is_valid <- TRUE
        # Check if the values to remove are empty
        if (is.null(object@values) || length(object@values) == 0) {
            message("Values to remove from the data frame are empty")
            is_valid <- FALSE
        }
        # Check if the variable to filter is empty
        if (length(object@filter_var) == 0) {
            message("Variable to filter is empty")
            is_valid <- FALSE
        }
        is_valid
    }
)

# Override parse_args with the new arguments
setMethod(
    "parse_args",
    "Filter",
    function(.Object, args) {
        parse_result <- callNextMethod()
        args <- parse_result$arguments
        .Object <- parse_result$configurer
        # Parse the variable to filter
        .Object@filter_var <- get_arg(args, 1)
        args %<>% shift(1)
        # Parse the values to remove
        n_values <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        .Object@values <- get_arg(args, n_values)
        args %<>% shift(n_values)
        # Return the parsed arguments
        list(arguments = args, configurer = .Object)
    }
)

setMethod(
    "perform",
    "Filter",
    function(object) {
        # Check if the variable to filter is in the data frame
        if (!(object@filter_var %in% colnames(object@df))) {
            stop(paste0("Variable to filter: ",
                object@filter_var,
                " is not in the data frame"))
        }
        # Soft condition
        # Check if the values to remove are in the data frame
        if (!all(object@values %in%
            unique(object@df[, object@filter_var]))) {
            print(object@values)
            print(unique(object@df[, object@filter_var]))
            warning(paste0(
                "Values to remove: ",
                object@values,
                " are not in the data frame! ",
                "Continuing..."))
        }
        # Get the column that will be filtered
        # from the data frame with filter_var name
        column_to_filter <- object@df[, object@filter_var]
        # Remove the rows that contain the filtered value
        object@df <- object@df[!column_to_filter %in%
            object@values,
            ]
        # Return the object
        object
    }
)

invisible(run(Filter(args = commandArgs(trailingOnly = TRUE))))