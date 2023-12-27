#!/usr/bin/Rscript
source("plots/plot_config/plot_config_R/configurers/dataConfigurerIface.R")
source("plots/plot_config/plot_config_R/configurers/dataConfigurerFactory.R")
library(dplyr, warn.conflicts = FALSE)
library(magrittr)
store_data_in_file <- function(df, file) {
    # Store the data frame in the object
    write.table(df, file, sep = " ", row.names = FALSE)
}
read_data_file <- function(file) {
    # Read the data frame from the object
    read.table(file, sep = " ", header = TRUE)
}
options(error=traceback)
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

# Drop unused columns (out of the ones that are used in the plot)
args@df <- df[, c(args@conf_z, args@x, args@y, args@y_sd)]
# Create the configurators
for (action in args@actions) {
    # Create the configurator
    configurator <- get_configurer(action, args)
    # Perform the configuration
    args@df <- perform(configurator)
}
# Store the data frame in the object
store_data_in_file(args@df, file)