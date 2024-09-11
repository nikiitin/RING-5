#!/usr/bin/Rscript
source("src/data_plotter/plot_config/src/configurers/configurer.R")

#' @title normalize
#' @description Normalize configurer. This configurer
#' will normalize the selected variables in the data frame
#' by the selected variable

setClass("Normalize",
    contains = "Configurer",
    slots = list(
        # Arguments for the normalize
        # Variable selected to normalize
        normalize_var = "character",
        # Value from variable taken as normalizer
        normalize_value = "character",
        # Variables that groups the data
        group_vars = "vector",
        # Stats to use in normalization
        stats = "vector",
        # Columns that will be skipped for normalization
        skip_normalize = "vector",
    )
)
#' @description Get the normalizer
#' the normalizer is the sum of the stats to apply
#' the normalization to other stats
#' @param object Normalize object
#' @return A vector with the sum of the row specified by the normalize_value
setGeneric(
    "get_normalizer",
    function(object) {
        standardGeneric("get_normalizer")
    }
)

#' @description Normalize the stats in the data frame
#' @param object Normalize object
#' @param normalizers A vector with the normalizers
#' @return The object with the normalized stats
setGeneric(
    "normalize",
    function(object, normalizers) {
        standardGeneric("normalize")
    }
)



setMethod(
    "get_normalizer",
    "Normalize",
    function(object) {
        # Get the unique stats that will normalize
        # Preconditions:
        #   for each group, there must be only one normalize_value
        #   for each group, normalize_var must exist
        #   for each group, stats must exist
        object@df %>%
            filter(.data[[object@normalize_var]] == object@normalize_value) %>%
            group_by(object@group_vars) %>% # Group by the group variables
            select(c(object@stats)) %>% # Select the stats to normalize
            group_modify(~ {
                sum(.x) %>%       # Add all the values of the row
                tibble::enframe() # Enframe to keep the name of the group
                }) %>%            # and the value of the sum for each row
            select(-c("name")) %>% # Grouped variable, name will contain thrash
            tibble::deframe() # Deframe will make a vector with group as key
    }
)

setMethod(
    "normalize",
    "Normalize",
    function(object, normalizers) {
        # Preconditions:
        #   The stats to normalize must be numeric,
        #   else, the normalization will fail
        #   Not numeric stats can be skipped
        object@df <- object@df %>%
            group_by(object@group_vars) %>% # Group by the group variables
            select(-c(object@normalize_var,
                object@group_vars)) %>% # Remove the group variables
            select(-c(object@skip_normalize)) %>% # Remove the variables to skip
            group_modify(~
                .x/normalizers[as.character(unlist(.y))]) # Normalize the values
    }
)
setValidity(
    "Normalize",
    function(object) {
        if (length(unique(object@stats)) != length(object@stats)) {
            stop("Stats must be unique")
        }
        if (length(unique(object@group_vars)) != length(object@group_vars)) {
            stop("Group variables must be unique")
        }
        if (length(unique(object@skip_normalize)) !=
            length(object@skip_normalize)) {
            stop("Skip normalize variables must be unique")
        }
        if (length(object@group_vars) == 0) {
            stop("Group variables are empty")
        }
        if (length(object@stats) == 0) {
            warning("Stats are empty, using all stats. Continuing...")
        }

        TRUE
    }
)

# Override parse_args with the new arguments
setMethod(
    "parse_args",
    "Normalize",
    function(.Object, args) {
        parse_result <- callNextMethod()
        args <- parse_result$arguments
        .Object <- parse_result$configurer
        # Parse the normalizer variable
        .Object@normalize_var <- get_arg(args, 1)
        args %<>% shift(1)
        # Parse the normalizer value
        .Object@normalizer_value <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        # Parse the group variables
        n_group_vars <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        .Object@group_vars <- get_arg(args, n_group_vars)
        args %<>% shift(n_group_vars)
        # Parse the stats
        n_stats <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        .Object@stats <- get_arg(args, n_stats)
        args %<>% shift(n_stats)
        # Skip_normalize variables
        n_skip_normalize <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        .Object@skip_normalize <- get_arg(args, n_skip_normalize)
        if (.Object@skip_normalize == NULL) {
            .Object@skip_normalize <- character(0)
        }
        args %<>% shift(n_skip_normalize)
        if (.Object@stats == NULL) {
            .Object@stats <- colnames(.Object@df)[
                    !colnames(.Object@df) %in%
                        c(.Object@group_vars,
                            .Object@normalize_var,
                            .Object@skip_normalize)
                ]
        }
        # Return the parsed arguments
        list(arguments = args, configurer = .Object)
    }
)

setMethod(
    "perform",
    "Normalize",
    function(object) {
        # Get the unique stats that will normalize
        normalizers <- get_normalizer(object)
        # Normalize the values
        object <- normalize(object, normalizers)
        object
    }
)

normalize <- new("Normalize", args = commandArgs(trailingOnly = TRUE))
run(normalize)