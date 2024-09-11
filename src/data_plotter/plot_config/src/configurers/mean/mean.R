#!/usr/bin/Rscript
source("src/data_plotter/plot_config/src/configurers/configurer.R")

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
        mean_vars = "vector",
        # Column that will hold the categoric value for the mean
        reduced_column = "character",
        # Variables to skip for mean calculation
        skip_mean = "vector",
        # Name that will be assigned to the mean column
        mean_name = "character"
    )
)

setValidity(
    "Mean",
    function(object) {
        # Check if the variable to calculate the mean is empty
        if (length(object@mean_var) == 0) {
            stop("Variable to calculate the mean is empty")
        }
        # Check if the variable to calculate the mean is in the data frame
        if (!(object@mean_var %in% colnames(object@df))) {
            stop(paste0("Variable to calculate the mean: ", object@mean_var, " is not in the data frame"))
        }

        if (!(object@mean_algorithm %in% c("mean", "geomean"))) {
            stop(paste0("Mean algorithm: ",
                object@mean_algorithm,
                " is not valid\n",
                "Valid algorithms are: mean, geomean"))
        }

        if(!(object@reduced_column %in% colnames(object@df))) {
            stop(paste0("Reduced column: ", object@reduced_column, " is not in the data frame"))
        }

        # Check if the variables to skip are in the data frame # Correct me
        if (length(object@skip_mean) > 0) {
            if (!(object@skip_mean %in% colnames(object@df))) {
                #stop(paste0("Variables to skip: ", object@skip_mean, " are not in the data frame"))
            }
        }

        if (object@mean_name == "") {
            stop("Mean name is empty")

        }

        if (object@mean_name %in% object@df[, object@mean_var]) {
            warning(paste0("Mean name: ",
                object@mean_name,
                " is already in the data frame! It will be augmented"))
        }
        TRUE
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
        # Parse the variable to filter
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
        # Parse the name of the mean column
        .Object@mean_name <- get_arg(args, 1)
        args %<>% shift(1)
        # Return the parsed arguments
        list(arguments = args, configurer = .Object)
    }
)

setMethod(
    "perform",
    "Mean",
    function(object) {
        # Copy the data frame to store the mean values
        mean_df <- object@df
        if (object@skip_mean != NULL) {
            # Remove rows matching skip_mean values
            mean_df <- mean_df[!mean_df[, object@mean_var] %in%
                object@skip_mean, ]
        }
        # Apply the mean algorithm to every stat
        # removing the reduced_column categoric column
        # and having as categoric reference the mean_vars
        mean_df <- aggregate(
            (!names(mean_df) %in%
                c(object@mean_vars, object@reduced_column)) ~
                object@mean_vars,
            data = mean_df,
            FUN = object@mean_algorithm
        )
        # Add the reduced_column again to the data frame
        mean_df[object@mean_var] <- object@mean_name

        # Add the mean_df rows to the data frame
        object@df <- rbind(object@df, mean_df)
        # Return the object
        object@df
    }
)

mean <- new("Mean", args = commandArgs(trailingOnly = TRUE))
run(mean)