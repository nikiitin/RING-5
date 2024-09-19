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
        stats = "nullable_vector",
        # Columns that will be skipped for normalization
        skip_normalize = "nullable_vector"
    )
) -> Normalize
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
            group_by(.data[[object@group_vars]]) %>% # Group by the group variables
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
            group_by(.data[[object@group_vars]]) # Group by the group variables
        # Normalize the stats
        for (stat in object@stats) {
            # Do mutate each stat and divide by the normalizer
            object@df <- object@df %>%
                mutate(!!stat := .data[[stat]] / normalizers[as.character(.data[[object@group_vars]])])
        }
        object
    }
)
invisible(setValidity(
    "Normalize",
    function(object) {
        is_valid <- TRUE
        if (length(unique(object@stats)) != length(object@stats)) {
            message(paste0("Stats provided to normalizer must be unique.",
                "Provided stats: ", object@stats,
                "Suggested unique stats: ", unique(object@stats)),
                "Stopping...")
            is_valid <- FALSE
        }
        if (length(unique(object@group_vars)) != length(object@group_vars)) {
            message("Group variables must be unique")
            is_valid <- FALSE
        }
        if (length(unique(object@skip_normalize)) !=
            length(object@skip_normalize)) {
            message("Skip normalize variables must be unique")
            is_valid <- FALSE
        }
        if (length(object@group_vars) == 0) {
            message("Group variables are empty")
            is_valid <- FALSE
        }
        if (length(object@stats) == 0) {
            warning("Stats are empty, using all stats. Continuing...")
        }

        is_valid
    }
))

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
        .Object@normalize_value <- get_arg(args, 1)
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
        args %<>% shift(n_skip_normalize)
        # Return the parsed arguments
        list(arguments = args, configurer = .Object)
    }
)

setMethod(
    "perform",
    "Normalize",
    function(object) {
        # Get the unique stats that will normalize
        if (is.null(object@stats)) {
            # Pick all the stats from the data frame
            object@stats <- colnames(object@df)[
                !colnames(object@df) %in% c(object@skip_normalize,
                    object@group_vars,
                    object@normalize_var)]
        }
        normalizers <- get_normalizer(object)
        # Normalize the values
        object <- normalize(object, normalizers)
        object
    }
)
# Run the normalize configurer and keep it invisible
invisible(run(Normalize(args = commandArgs(trailingOnly = TRUE))))