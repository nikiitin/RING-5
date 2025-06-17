#!/usr/bin/Rscript
source("src/data_plotter/plot_config/src/configurers/configurer.R")
available_mean_algorithms <- c("arithmean", "geomean", "hmean", "hmean_grouped")
col_sums <- list()

geomean <- function(x) {
    result <- exp(mean(log(x[x > 0])))
    if (is.nan(result)) {
        result <- 0
    }
    result
}

hmean <- function(x) {
    print(x)
    result <- length(x) / sum(1 / x[x > 0])
    if (is.nan(result) || is.infinite(result)) {
        result <- 0
    }
    print(result)
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
        skip_mean = "MapSet",
        # Name that will be assigned to the mean column
        replacing_column = "character"
    )
) -> Mean

invisible(setValidity(
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
            message(paste0(
                "Mean algorithm: ",
                object@mean_algorithm,
                " is not valid\n",
                "Valid algorithms are: mean, geomean"
            ))
            is_valid <- FALSE
        }
        # Check if the mean name is empty
        if (object@replacing_column == "") {
            message("Mean name is empty")
            is_valid <- FALSE
        }
        is_valid
    }
))

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
        # Variables to skip are given by pairs of
        # variable name and values to skip
        .Object@skip_mean <- MapSet(container_type = "list")
        if (n_skip_mean != 0) {
            for (i in seq_along(n_skip_mean)) {
                skip_var_name <- get_arg(args, 1)
                args %<>% shift(1)
                skip_var_n_values <- as.numeric(get_arg(args, 1))
                args %<>% shift(1)
                skip_var_values <- get_arg(args, skip_var_n_values)
                args %<>% shift(skip_var_n_values)
                .Object@skip_mean %<>% emplace_element(
                    skip_var_name, skip_var_values
                )
            }
        }
        # Parse the name of the label for the mean column
        .Object@replacing_column <- get_arg(args, 1)
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
        if (length(object@skip_mean) != 0) {
            # Remove rows matching skip_mean values
            for (skip_var in get_all_keys(object@skip_mean)) {
                # Get the values to skip
                vars_to_skip <- object@skip_mean[skip_var]
                # Remove the rows with columns
                # which name is skip_var and
                # the values from those columns
                # are in vars_to_skip
                mean_df <- mean_df[!mean_df[[skip_var]] %in%
                    unlist(vars_to_skip), ]
            }
        }
        # Apply the mean algorithm to the stats
        # specified by the mean_vars. Keep the name of the
        # columns and those that are not mean_vars
        mean_function <- match.fun(object@mean_algorithm)
        # Create another data frame with the standard deviation
        # of the mean_vars
        sd_mean_df <- mean_df %>% select(ends_with(".sd"), all_of(object@reduced_column))
        # Calculate the standard deviation of the mean_vars
        sd_mean_df <- sd_mean_df %>%
            group_by(across(all_of(object@reduced_column))) %>%
            summarise(across(ends_with(".sd"), mean_function, .names = "{col}"), .groups = "drop")
        # Remove any column that is not in the mean_vars
        # or the reduced_column
        mean_df <- mean_df %>% select(all_of(object@mean_vars), all_of(object@reduced_column))
        mean_df <- mean_df %>%
            group_by(across(all_of(object@reduced_column))) %>%
            summarise(across(all_of(object@mean_vars), mean_function, .names = "{col}"), .groups = "drop")
        # Merge the mean_df with the sd_mean_df
        mean_df <- merge(mean_df, sd_mean_df, by = object@reduced_column)
        # Rename the columns to the replacing_column with the
        # algorithm used to calculate the mean
        mean_df[object@replacing_column] <- object@mean_algorithm
        # Use bind_rows to add the mean_df rows to the data frame
        # filling all the columns that are not in the mean_df with NA
        object@df <- dplyr::bind_rows(object@df, mean_df)
        # Add the mean_df rows to the data frame filling all
        # the columns that are not in the mean_df with NA
        invisible(object)
    }
)

setMethod(
    "perform",
    "Mean",
    function(object) {
        # Post-df parse checks
        # Check if the variable to calculate the mean is in the data frame
        if (!all(object@mean_vars %in% colnames(object@df))) {
            missing_vars <- NULL
            for (var in object@mean_vars) {
                if (!(var %in% colnames(object@df))) {
                    missing_vars <- c(missing_vars, var)
                }
            }
            message("Some variables to calculate the mean are not in the data frame")
            message("Missing variables: ")
            print(missing_vars)
            stop("Stopping...")
        }
        # Check if the reduced column is in the data frame
        if (!(object@reduced_column %in% colnames(object@df))) {
            stop(paste0("Reduced column: ", object@reduced_column, " is not in the data frame"))
        }
        # Check if the mean name is already in the data frame
        if (!(object@replacing_column %in% colnames(object@df))) {
            warning(paste0(
                "Column replacing name: ",
                object@replacing_column,
                " is not in the data frame. It will be added"
            ))
        }
        # Check if the variables to skip are in the data frame
        for (skip_var in get_all_keys(object@skip_mean)) {
            if (!(skip_var %in% colnames(object@df))) {
                warning(paste0(
                    "Variable to skip: ",
                    skip_var,
                    " is not in the data frame"
                ))
            }
            if (!all(object@skip_mean[skip_var] %in% object@df[[skip_var]])) {
                warning(paste0(
                    "Values to skip for variable: ",
                    skip_var,
                    " are not in the data frame"
                ))
            }
        }
        # Calculate the mean
        object <- calculate_mean(object)
        print(object@df)
        return(object)
    }
)

invisible(run(Mean(args = commandArgs(trailingOnly = TRUE))))