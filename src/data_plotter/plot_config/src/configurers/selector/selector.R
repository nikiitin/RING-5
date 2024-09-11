#!/usr/bin/Rscript
source("src/data_plotter/plot_config/src/configurers/configurer.R")
library(dplyr, warn.conflicts = FALSE)
library(magrittr)
#' @title Selector
#' @description Selector configurer. This configurer will
#' select the specified columns from the data frame
#' and will drop the rest
Selector <- setClass("Selector",
    contains = "Configurer",
    slots = list(
        # Variables to select
        select_vars = "vector"
    )
) -> Selector

# If not set to invisible, the function will print
# some stuff that we don't want to show
invisible(setValidity(
    "Selector",
    function(object) {
        is_valid <- TRUE
        # Check if the variable to select is empty
        if (length(object@select_vars) == 0) {
            message("Variables to select are empty")
            is_valid <- FALSE
        }
        # Check if the variable to select is in the data frame
        vars_to_skip <- c()
        for (var in object@select_vars) {
            if (!(var %in% colnames(object@df))) {
                # Print a warning, but don't stop the execution
                # just skip the variable
                warning(paste0("Variable to select: ",
                    var,
                    " is not in the data frame.",
                    "Skipping"))
            }
        }
        # If not, remove them from the select_vars
        if (length(vars_to_skip) > 0) {
            object@select_vars <-
                object@select_vars[!(object@select_vars %in% vars_to_skip)]
        }
        is_valid
    }
))

# Override parse_args with the new arguments
setMethod(
    "parse_args",
    "Selector",
    function(.Object, args) {
        parse_result <- callNextMethod()
        args <- parse_result$arguments
        .Object <- parse_result$configurer
        # Parse the variables to select
        n_selected_vars <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        .Object@select_vars <- get_arg(args, n_selected_vars)
        args %<>% shift(n_selected_vars)
        # Return the parsed arguments
        list(arguments = args, configurer = .Object)
    }
)

# Main action of the selector
setMethod(
    "perform",
    "Selector",
    function(object) {
        # Select the variables
        object@df <- object@df %>% select(object@select_vars)
        object
    }
)
# Run the selector configurer and keep it invisible
invisible(run(Selector(args = commandArgs(trailingOnly = TRUE))))