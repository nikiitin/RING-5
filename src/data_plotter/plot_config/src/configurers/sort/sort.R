#!/usr/bin/Rscript
source("src/data_plotter/plot_config/src/configurers/configurer.R")
#' @title Sort
#' @description Sort configurer. This configurer will
#' sort the data frame by the selected variable
#' with the specified order

setClass("Sort",
    contains = "Configurer",
    slots = list(
        # Arguments for the sort
        # Variable selected to sort
        sort_var = "character",
        # Order of the sort
        sort_order = "nullable_vector"
    )
) -> Sort

invisible(setValidity(
    "Sort",
    function(object) {
        is_valid <- TRUE
        # Check if the variable to sort is empty
        if (length(object@sort_var) == 0) {
            message("Variable to sort is empty")
            is_valid <- FALSE
        }
        # Check if the variable to sort is in the data frame
        if (!(object@sort_var %in% colnames(object@df))) {
            message(paste0("Variable to sort: ",
                object@sort_var,
                " is not in the data frame"))
            is_valid <- FALSE
        }
        # Check if the order is empty
        if (is.null(object@sort_order) || length(object@sort_order) == 0) {
            message("Order of the sort is empty")
            is_valid <- FALSE
        }
        TRUE
    }
))

# Override parse_args with the new arguments
setMethod(
    "parse_args",
    "Sort",
    function(.Object, args) {
        parse_result <- callNextMethod()
        args <- parse_result$arguments
        .Object <- parse_result$configurer
        # Parse the variable to sort
        .Object@sort_var <- get_arg(args, 1)
        args %<>% shift(1)
        # Parse the order of the sort
        n_sorts <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        .Object@sort_order <- get_arg(args, n_sorts)
        args %<>% shift(n_sorts)
        # Return the parsed arguments
        list(arguments = args, configurer = .Object)
    }
)

setMethod(
    "perform",
    "Sort",
    function(object) {
        # Check if the order is missing any element
        if (!all(unique(object@df[, object@sort_var] %in% object@sort_order))) {
            warning(paste0("Order of the sort is missing elements in the data frame"))
            message("Order of the sort: ")
            print(paste(object@sort_order, sep=", "))
            message("Unique elements in the data frame: ")
            print(unique(object@df[, object@sort_var]))
        }
        if (length(object@sort_order) > length(unique(object@df[, object@sort_var]))) {
            warning(paste0("Order of the sort has more elements than the data frame"))
            message("Order of the sort: ")
            print(paste(object@sort_order, sep=", "))
            message("Unique elements in the data frame: ")
            print(unique(object@df[, object@sort_var]))
            warning("strange results can be expected")
        }
        object@df[, object@sort_var] <- factor(
            object@df[, object@sort_var],
            levels = object@sort_order)
        object@df <- object@df[order(object@df[, object@sort_var]), ]
        object
    }
)

# Run the configurer
invisible(run(Sort(args = commandArgs(trailingOnly = TRUE))))