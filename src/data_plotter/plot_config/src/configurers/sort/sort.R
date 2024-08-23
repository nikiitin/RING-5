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
        sort_order = "vector"
    )
)

setValidity(
    "Sort",
    function(object) {
        # Check if the variable to sort is empty
        if (length(object@sort_var) == 0) {
            stop("Variable to sort is empty")
        }
        # Check if the variable to sort is in the data frame
        if (!(object@sort_var %in% colnames(object@df))) {
            stop(paste0("Variable to sort: ",
                object@sort_var,
                " is not in the data frame"))
        }
        # Check if the order is empty
        if (length(object@sort_order) == 0) {
            stop("Order of the sort is empty")
        }
        # Check if the order is valid
        if (!(all(object@sort_order
            %in% object@df %>% select(object@sort_var)))) {
            stop(paste0("Order of the sort: ",
                object@sort_order,
                " is not valid, ",
                "it must be a subset of the variable to sort"))
        }
        TRUE
    }
)

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
        shift(n_sorts)
        # Return the parsed arguments
        list(arguments = args, configurer = .Object)
    }
)

setMethod(
    "perform",
    "Sort",
    function(object) {
        object@df[, object@sort_var] <- factor(
            object@df[, object@sort_var],
            levels = object@sort_order)
        object@df <- object@df[order(object@df[, object@sort_var]), ]
        object
    }
)

sorter <- new("Sort", args = commandArgs(trailingOnly = TRUE))
run(sorter)