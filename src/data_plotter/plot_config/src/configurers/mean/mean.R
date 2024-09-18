#!/usr/bin/Rscript
source("src/data_plotter/plot_config/src/configurers/configurer.R")
available_mean_algorithms <- c("arithmean", "geomean")

geomean <- function(x) {
    result <- exp(mean(log(x[x > 0])))
    if (is.nan(result)) {
        result <- 0
    }
    result
}

arithmean <- function(x) {
    mean(x)
}

#' @description Calculate the mean using the mean configurer
#' @param object Mean configurer object
#' @return Mean configurer object with the mean calculated
setGeneric(
    "calculate_mean",
    function(object) {
        standardGeneric("calculate_mean")
    }
)


#' @title Mean
#' @description Mean configurer. This configurer will
#' calculate the mean for all statistics grouped by
#' the selected variable
setClass("Mean",
    contains = "Configurer",
    slots = list(
        # Arguments for the mean
        # Algorithm to calculate the mean
        mean_algorithm = "character",
        # Variable selected to calculate the mean
        mean_vars = "nullable_vector",
        # Column that will hold the categoric value for the mean
        reduced_column = "character",
        # Variables to skip for mean calculation
        skip_mean = "nullable_vector",
        # Name that will be assigned to the mean column
        mean_name = "character"
    )
) -> Mean

setValidity(
    "Mean",
    function(object) {
        is_valid <- TRUE
        # Check if the variable to calculate the mean is empty
        if (length(object@mean_vars) == 0) {
            message("Variable to calculate the mean is empty")
            is_valid <- FALSE
        }
        # Check if the mean algorithm is valid
        if (!(object@mean_algorithm %in% available_mean_algorithms)) {
            message(paste0("Mean algorithm: ",
                object@mean_algorithm,
                " is not valid\n",
                "Valid algorithms are: mean, geomean"))
            is_valid <- FALSE
        }
        # Check if the mean name is empty
        if (object@mean_name == "") {
            message("Mean name is empty")
            is_valid <- FALSE
        }
        is_valid
    }
)

# Override parse_args with the new arguments
setMethod(
    "parse_args",
    "Mean",
    function(.Object, args) {
        parse_result <- callNextMethod()
        args <- parse_result$arguments
        .Object <- parse_result$configurer
        # Parse the mean algorithm to use
        # see available_mean_algorithms
        .Object@mean_algorithm <- get_arg(args, 1)
        args %<>% shift(1)
        # Parse mean variables
        n_mean_vars <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        .Object@mean_vars <- get_arg(args, n_mean_vars)
        args %<>% shift(n_mean_vars)
        # Parse the reduced column
        .Object@reduced_column <- get_arg(args, 1)
        args %<>% shift(1)
        # Parse the variables to skip
        n_skip_mean <- as.numeric(get_arg(args, 1))
        args %<>% shift(1)
        .Object@skip_mean <- get_arg(args, n_skip_mean)
        args %<>% shift(n_skip_mean)
        # Parse the name of the label for the mean column
        .Object@mean_name <- get_arg(args, 1)
        args %<>% shift(1)
        # Return the parsed arguments
        list(arguments = args, configurer = .Object)
    }
)

setMethod(
    "calculate_mean",
    "Mean",
    function(object) {
        # Copy the data frame to store the mean values
        mean_df <- object@df
        if (!is.null(object@skip_mean)) {
            # Remove rows matching skip_mean values
            mean_df <- mean_df[!mean_df[, object@mean_vars] %in%
                object@skip_mean, ]
        }
        # Apply the mean algorithm to the stats
        # specified by the mean_vars. Keep the name of the
        # columns and those that are not mean_vars
        formula <- as.formula(paste(paste(object@mean_vars, sep = "+"), "~", object@reduced_column))
        mean_df <- aggregate(formula, mean_df, get(object@mean_algorithm))
        # Add the reduced_column again to the data frame
        mean_df[object@mean_name] <- object@mean_algorithm
        # Add the mean_df rows to the data frame
        object@df <- rbind(object@df, mean_df)
        # Return the object
        object
    }
)

setMethod(
    "perform",
    "Mean",
    function(object) {
        # Post-df parse checks
        # Check if the variable to calculate the mean is in the data frame
        if (!(object@mean_vars %in% colnames(object@df))) {
            stop(paste0("Variable to calculate the mean: ", object@mean_vars, " is not in the data frame"))
        }
        # Check if the reduced column is in the data frame
        if(!(object@reduced_column %in% colnames(object@df))) {
            stop(paste0("Reduced column: ", object@reduced_column, " is not in the data frame"))
        }
        # Check if the mean name is already in the data frame
        if (object@mean_name %in% object@df[, object@mean_vars]) {
            warning(paste0("Mean name: ",
                object@mean_name,
                " is already in the data frame! It will be augmented"))
        }
        # Check if the variables to skip are in the data frame
        if (!is.null(object@skip_mean) && length(object@skip_mean) > 0) {
            if (!(object@skip_mean %in% colnames(object@df))) {
                stop(paste0("Variables to skip: ",
                    object@skip_mean,
                    " are not in the data frame"))
            }
        }
        # Calculate the mean
        object %<>% calculate_mean()
        return(object)
    }
)

invisible(run(Mean(args = commandArgs(trailingOnly = TRUE))))