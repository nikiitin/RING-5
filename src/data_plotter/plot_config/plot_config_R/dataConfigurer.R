#!/usr/bin/Rscript
options(error=function()traceback(2))
source("src/data_plotter/plot_config/plot_config_R/configurers/dataConfigurerIface.R")
source("src/data_plotter/plot_config/plot_config_R/configurers/dataConfigurerFactory.R")
library(dplyr, warn.conflicts = FALSE)
library(magrittr)
library(stringr)
store_data_in_file <- function(df, file) {
    # Store the data frame in the object
    write.table(df, file, sep = " ", row.names = FALSE)
}
read_data_file <- function(file) {
    # Read the data frame from the object
    read.table(file, sep = " ", header = TRUE)
}
# Main function
# Parse arguments
arguments <- commandArgs(trailingOnly = TRUE)
# Get the file name
file <- get_arg(arguments, 1)
arguments %<>% shift(1)
# Read the data frame
df <- read_data_file(file)
# Get the Data_configurator_args object
args <- new("Data_configurator_args", args = arguments)
cols_to_parse <- c()
sided_plot <- FALSE
# Drop unused columns (out of the ones that are used in the plot)
if (args@is_distribution == 0) {
    if (length(args@y[str_detect(args@y, "__side")]) > 0) {
        sided_plot <- TRUE
        # Copy the args object in other variable
        args_side <- args
        # Remove the __side modifier from the original args object
        args@y <- args@y[!str_detect(args@y, "__side")]
        args@y_sd <- args@y_sd[!str_detect(args@y_sd, "__side")]
        # Remove the non __side modifier from the copy
        args_side@y <- str_remove(args_side@y[str_detect(args_side@y, "__side")], "__side")
        args_side@y_sd <- str_remove(args_side@y_sd[str_detect(args_side@y_sd, "__side")], "__side")
        # Set cols_to_parse for the side modifier args
        cols_to_parse_side <- c(args_side@conf_z, args_side@x, args_side@y, args_side@y_sd)
    }
    cols_to_parse <- c(args@conf_z, args@x, args@y, args@y_sd)
    if (args@n_facets > 0) {
        cols_to_parse <- c(cols_to_parse, args@facets)
    }
} else {
    # Conf_z is the id for the distribution,
    # the columns consist on "id..number". We need
    # to recover all the columns that have the id
    # Get the id
    if (length(args@y[str_detect(args@y, "__side")]) > 0) {
        error("The __side modifier is not supported for distribution plots yet.")
    }
    id <- args@y
    # Add the split characters
    id <- paste0(id, "..")
    # Get the columns that have the id
    cols_to_parse <- grep(id, colnames(df), value=TRUE)
    cols_to_parse <- c(cols_to_parse, args@conf_z)
    if (args@n_facets > 0) {
        cols_to_parse <- c(cols_to_parse, args@facets)
    }
}

args@df <- df[, unique(cols_to_parse)]
if (sided_plot) {
    args_side@df <- df[, unique(cols_to_parse_side)]
    # Create the configurators
    for (action in args_side@actions) {
        print(paste("Sided_action:", action, sep=" "))
        # Create the configurator
        configurator <- get_configurer(action, args_side)
        # Perform the configuration
        args_side@df <- perform(configurator)
    }
}
# Create the configurators
for (action in args@actions) {
    print(action)
    if (args@is_distribution == 1) {
        if (action == "Filter") {
            # Create the configurator
            configurator <- get_configurer(action, args)
            # Perform the configuration
            args@df <- perform(configurator)    
        }
    } else {
        # Create the configurator
        configurator <- get_configurer(action, args)
        # Perform the configuration
        args@df <- perform(configurator)
    }
    
}
if (sided_plot) {
    # Merge y_side into the original data frame
    args@df <- cbind(args@df, args_side@df[args_side@y])
    args@df <- cbind(args@df, args_side@df[args_side@y_sd])
    # Add __side modifier to added columns
    # Y is used for both, y_sd and y
    colnames(args@df) <- str_replace(colnames(args@df),
        paste0("^", args_side@y, "$"),
        paste0(args_side@y, "__side")
        )
    colnames(args@df) <- str_replace(colnames(args@df),
        paste0("^", args_side@y_sd, "$"),
        paste0(args_side@y, "__side", ".sd")
        )
}
# Store the data frame in the object
store_data_in_file(args@df, file)