#!/usr/bin/Rscript
source("utils/util.R")
library(readr)
library(dplyr, warn.conflicts = FALSE)

setClass("Data_configurator_args",
    slots = list(
        # Actions to perform
        n_actions = "numeric",
        actions = "vector",
        # Axis variables
        n_y = "numeric",
        y = "vector",
        y_sd = "vector",
        n_x = "numeric",
        x = "vector",
        n_conf_z = "numeric",
        conf_z = "vector",
        # Filter variables
        n_filters = "numeric",
        filters = "MapSet",
        # Sort variables
        n_sorts = "numeric",
        sorts = "MapSet",
        # Normalize variables
        normalizer_index = "numeric",
        # Mean variables
        mean_algorithm = "character",

        # Data frame that contains the data
        df = "data.frame"
    )
)

setMethod(
    "initialize",
    "Data_configurator_args",
    function(.Object, args) {
        # Parse the arguments and store them
        # We need to shift the args after each get_arg
        # because otherwise the next get_arg will get
        # the same argument
        # Number of actions
        .Object@n_actions <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        # Actions
        actions <- get_arg(args, .Object@n_actions)
        args %<>% shift(.Object@n_actions)
        # Number of y axis variables
        .Object@n_y <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        # Y axis variables
        .Object@y <- get_arg(args, .Object@n_y)
        # Add the .sd to the y axis variables
        .Object@y_sd <- paste0(.Object@y, ".sd")
        args %<>% shift(.Object@n_y)
        # Number of x axis variables
        .Object@n_x <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        # X axis variables
        .Object@x <- get_arg(args, .Object@n_x)
        args %<>% shift(.Object@n_x)
        # Number of conf_z axis variables
        .Object@n_conf_z <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        # Conf_z axis variables
        .Object@conf_z <- get_arg(args, .Object@n_conf_z)
        args %<>% shift(.Object@n_conf_z)
        # Actions
        # Should be in this exact order:
        # 1. Filter
        # 2. Mean
        # 3. Sort
        # 4. Normalize
        # Else the result probably won't be the expected
        # Check if filter is not in the actions
        if ("Filter" %in% actions) {
            .Object@actions <- c(.Object@actions, "Filter")
            .Object@n_filters <- as.numeric(get_arg(args, 1))
            args %<>% shift(1)
            # Filters
            filters <- new("MapSet", container_type = "character")
            for (i in 1:.Object@n_filters) {
                filter_var <- get_arg(args, 1)
                args %<>% shift(1)
                n_filters <- as.numeric(get_arg(args, 1))
                args %<>% shift(1)
                filter_list <- get_arg(args, n_filters)
                args %<>% shift(n_filters)
                filters[filter_var] <- filter_list
            }
            .Object@filters <- filters
        }
        # Check if mean is not in the actions
        if ("Mean" %in% actions) {
            .Object@actions <- c(.Object@actions, "Mean")
            .Object@mean_algorithm <- get_arg(args, 1)
            args %<>% shift(1)
        }
        # Check if sort is not in the actions
        if ("Sort" %in% actions) {
            .Object@actions <- c(.Object@actions, "Sort")
            .Object@n_sorts <- as.numeric(get_arg(args, 1))
            args %<>% shift(1)
            # Sorts
            sorts <- new("MapSet", container_type = "character")
            for (i in 1:.Object@n_sorts) {
                sort_var <- get_arg(args, 1)
                args %<>% shift(1)
                n_sorts <- as.numeric(get_arg(args, 1))
                args %<>% shift(1)
                sort_list <- get_arg(args, n_sorts)
                args %<>% shift(n_sorts)
                sorts[sort_var] <- sort_list
            }
            .Object@sorts <- sorts
        }
        # Check if normalize is not in the actions
        if ("Normalize" %in% actions) {
            .Object@actions <- c(.Object@actions, "Normalize")
            # Normalizer index
            .Object@normalizer_index <- as.numeric(get_arg(args, 1))
            args %<>% shift(1)
        }
        # Return the object
        .Object
    }
)

# Configurators will inherit from this class
# and override the perform method
# Each configurator will have its own behavior
# and we should check that a configurator that is not
# supposed to be used is not used
setClass("Data_configurator",
    slots = list(
        # Args to parse
        args = "Data_configurator_args"
    )
)

# Define all generic methods for the Data_configurer class
# These methods will be overridden in inheriting classes
# at demand
setGeneric("perform", function(object) {
    standardGeneric("perform")
})