#!/usr/bin/Rscript
library(readr)
source("utils/util.R")
# Parse arguments
arguments <- commandArgs(trailingOnly = TRUE)
curr_arg <- 1
stats_file <- arguments[curr_arg]
curr_arg <- curr_arg + 1
mean_algorithm <- arguments[curr_arg]
curr_arg <- increment(curr_arg)
# Two types of ordering:
# None. no ordering, skip this step
# Specific, specific order -> specify the config names in
# the order you want them
sorting_type <- arguments[curr_arg]
curr_arg <- curr_arg + 1
# Until here, arguments are fixed

# Check available sort algorithms
if (sorting_type != "specific") {
    if (sorting_type != "none") {
        stop("Unexpected sorting type")
    } else {
        stop("Skipping stats sort step")
    }
}

n_confs_sorted <- as.integer(arguments[curr_arg])
curr_arg <- curr_arg + 1
confs_sort_order <- NULL
if (n_confs_sorted > 0) {
    for (i in 1:n_confs_sorted) {
        # Remember that here we are expecting the whole confKey
        # in case it is specific order
        confs_sort_order <- c(confs_sort_order, arguments[curr_arg])
        curr_arg <- curr_arg + 1
    }
}
benchmarks_sorted_order <- NULL
n_bench_sorted <- as.integer(arguments[curr_arg])

curr_arg <- increment(curr_arg)
if (n_bench_sorted > 0) {
    for (i in 1:n_bench_sorted) {
        benchmarks_sorted_order <-
        c(benchmarks_sorted_order,
            arguments[curr_arg])
        curr_arg <- increment(curr_arg)
    }
}
# Finish argument parsing

parsed_data <- read.table(stats_file, sep = " ", header = TRUE)

benchmarks_column <- get_column_index("benchmark_name", parsed_data)
config_ending_column <- benchmarks_column - 1

# Here we are expecting the number of benchmarks to sort
# but take into account that we will have one more benchmark
# which is the mean
if (n_bench_sorted != (length(unique(parsed_data[, "benchmark_name"])) - 1)) {
    # Crash or unexpected behavior could happen...
    # Notify the user
    warning(paste("Number of entries specified for sorting",
        "is different than the number of benchmarks found in stats file\n"))
}

# Order benchmarks as desired
# Put mean at the end!
if (mean_algorithm != "arithmean" && mean_algorithm != "geomean") {
    # This will actually work for any specified algorithm due to R magic
    mean_algorithm <- "NONEMEAN"
}

# Split mean from the rest of data as it is considered a benchmark
# TODO: improve this!!!!! this is a hack
parsed_data <-
    parsed_data[order(parsed_data[, "benchmark_name"], decreasing = FALSE), ]
mean_df <- parsed_data[parsed_data["benchmark_name"] != mean_algorithm, ]
# Get the name of the benchmarks in the order they appear in the stats
names_vector <- unique(as.character(mean_df[, "benchmark_name"]))
if (n_bench_sorted > 0) {
    if (length(names_vector) != n_bench_sorted) {
        # Crash or unexpected behavior could happen...
        # Notify the user
        # This is not a stop because it is not a fatal error...
        warning(paste("At sorting:",
            "CAREFUL! different number of benchmarks specified for",
            "ordering and found in stats!! unexpected result"), sep = " ")
    }
    # Use the order specified
    names_vector <- benchmarks_sorted_order
} else {
    # No benchmarks specified, use the order found in stats
    warning("Skipping benchmarks sort step")
}
names_vector <- c(names_vector, mean_algorithm)

# Reorder benchmarks to have the mean figure at the end,
# and the rest in the order specified. Order will sort data
# by the order of the names in the vector
parsed_data[["benchmark_name"]] <-
    factor(parsed_data[["benchmark_name"]], levels = unique(names_vector))
parsed_data <-
    parsed_data[order(parsed_data[, "benchmark_name"], decreasing = FALSE), ]

if (sorting_type == "none") {
    # Write data onto csv file
    write.table(parsed_data, stats_file, sep= " ", row.names = FALSE)
    stop("Skipping stats sort step")
}


# Order configurations as desired
if (length(n_confs_sorted) < 1) {
    stop("No elements were specified to sort stats")
}

# Prepare a column named confName with a mix of the configurations without
# confKey and the stats
conf_names <- mixStringCols(2, config_ending_column, parsed_data)
parsed_data <- cbind(conf_names = conf_names, parsed_data)

if (sorting_type == "specific") {
    # Here we will sort by confNames
    conf_keys <- parsed_data[, "conf_names"]
    parsed_data <-
        parsed_data[order(match(conf_keys, confs_sort_order)), ]
    # Drop confName column
    parsed_data <- parsed_data[, -get_column_index("conf_names", parsed_data)]
} else {
    stop("Unexpected sort type")
}
# Write filtered data onto csv file
write.table(parsed_data, stats_file, sep = " ", row.names = FALSE)
