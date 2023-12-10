#!/usr/bin/Rscript
source("utils/util.R")
library(readr)
arguments <- commandArgs(trailingOnly = TRUE)
curr_arg <- 1
stats_file <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
renamings_count <- arguments[curr_arg]
curr_arg <- increment(curr_arg)

parsed_data <- read.table(stats_file, sep = " ", header = TRUE)

for (renaming in 1:renamings_count) {
  # Get the renaming for the stat we are looking for
  old_name <- arguments[curr_arg]
  curr_arg <- increment(curr_arg)
  new_name <- arguments[curr_arg]
  curr_arg <- increment(curr_arg)

  # Check if name exists
  if (!check_column_exists(old_name, parsed_data)) {
    warning(paste("Column",
      old_name,
      "does not exist! could not rename! Skipping..."))
  } else {
    # Do renaming
    colnames(parsed_data)[colnames(parsed_data) == old_name] <- new_name

    # Check if sd column exists
    if (!check_column_exists(paste("sd", old_name, sep = "."), parsed_data)) {
      warning(paste("Column",
        paste("sd", old_name, sep = "."),
        "does not exist! Unexpected but skipping..."))
    } else {
      # Rename sd column too
      old_name <- paste("sd", old_name, sep = ".")
      new_name <- paste("sd", new_name, sep = ".")
      colnames(parsed_data)[colnames(parsed_data) == old_name] <- new_name
    }
  }
}

# Write everything onto csv file
write.table(parsed_data, stats_file, sep = " ", row.names = FALSE)