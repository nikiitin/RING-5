#!/usr/bin/Rscript
source("src/utils/util.R")
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
    # Check if renaming was successful
    if (!check_column_exists(new_name, parsed_data)) {
      stop(paste("Could not rename column",
        old_name,
        "to",
        new_name,
        "!"))
    }
  }
}

# Write everything onto csv file
write.table(parsed_data, stats_file, sep = " ", row.names = FALSE)