source("utils/util.R")
source("plots/plot_impl/formats/plot_format.R")
library(methods)
library(ggplot2)
library(readr)

# Define the S4 class for a generic plot
setClass("Plot",
  # Define the fields of the class
  slots = list(
    # Format configuration class that contains all the
    # configuration for the plot
    format = "Plot_format",
    # The path to the file where the plot will be saved
    result_path = "character",
    # The path to the file containing the data to be plotted
    stats_file = "character",
    # The number of statistics to be plotted
    n_stats = "numeric",
    # The statistics to be plotted
    stat = "list",
    # The number of legend names
    data = "data.frame",
    # Data frame to be plotted
    data_frame = "data.frame",
    # Plot object
    plot = "ggplot"
  )
)

# Define the parse_args method for the Plot class
setMethod("parse_args",
  signature(object = "Plot", args = "list"),
  function(object, args) {
    # Parse the arguments and store them in the object
    curr_arg <- 1
    object@result_path <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    object@stats_file <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    x_axis_name <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    y_axis_name <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    width <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    height <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    object@n_stats <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    object@stat <- get_arg(args, curr_arg, object@n_stats)
    curr_arg <- curr_arg + object@n_stats
    n_legend_names <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    legend_names <- get_arg(args, curr_arg, object@n_legend_names)
    curr_arg <- curr_arg + object@n_legend_names
    n_y_breaks <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    y_breaks <- get_arg(args, curr_arg, object@n_y_breaks)
    curr_arg <- curr_arg + object@n_y_breaks
    y_limit_top <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    y_limit_bot <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    format <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    legend_title <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    legend_n_elem_row <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    n_x_split_points <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    x_split_points <- get_arg(args, curr_arg, object@n_x_split_points)
    curr_arg <- curr_arg + object@n_x_split_points
    # Prepare the format object
    # It will apply all format configurations to the plot
    object@format <- new("Plot_format",
      slots = list(
        x_axis_name = x_axis_name,
        y_axis_name = y_axis_name,
        width = width,
        height = height,
        n_legend_names = n_legend_names,
        legend_names = legend_names,
        n_y_breaks = n_y_breaks,
        y_breaks = y_breaks,
        y_limit_top = y_limit_top,
        y_limit_bot = y_limit_bot,
        format = format,
        legend_title = legend_title,
        legend_n_elem_row = legend_n_elem_row,
        n_x_split_points = n_x_split_points,
        x_split_points = x_split_points))
    object
  }
)

# Check data is correct
setMethod("check_data_correct", "Plot",
  function(object) {
    # Critical errors
    # Stop the plot if any of these errors are found
    if (object@n_stats < 1) {
      stop("No stats defined to plot! Stopping plot...")
    }
    # Check if all stats are present in the data
    if (!all(
        sapply(
          object@stat,
          function(stat) {
            stat %in% colnames(object@data_frame)
          }
        )
      )
    ) {
      stop("Stats not found in data! Stopping plot...")
    }
    # Non-critical errors
    # Tell the user the error to fix it
    # Call plot_format check_data_correct method
    check_data_format_correct(object@format, object@data_frame)
  }
)

# Prepare data for plotting. This will create a new
# data_frame with only the columns we need
setMethod("read_and_format_data", "Plot",
  function(object) {
    # Read data from csv file
    object@data <- read.table(object@stats_file, sep = " ", header = TRUE)
    # Check if stat column can be turned to numeric
    if (!all(
        sapply(
          object@data[, object@stat],
          is.numeric
        )
      )
    ) {
      stop("Stats are not numeric type! Stopping plot...")
    }
    # Convert all stat columns to numeric
    object@data[, object@stat] <-
      sapply(object@data[, object@stat], as.numeric)
    # Create new data_frame with only the columns we need
    # Get config_name column (configurations)
    confs <- factor(object@data$conf_name,
      levels = unique(as.character(object@data$conf_name)),
      ordered = TRUE)
    # Get benchmarks column (benchs)
    benchs <- factor(object@data$benchmark_name,
      levels = unique(as.character(object@data$benchmark_name)),
      ordered = TRUE)
    # Get all required stats
    stats <- object@data[, object@stat]
    # Prepare dataFrame for future plotting
    object@data_frame <- data.frame(configurations = confs,
      benchmarks = benchs)
    # Add stats to dataFrame
    for (stat in ncol(stats)) {
      object@data_frame <- cbind(object@data_frame, stats[, stat])
    }
    object
  }
)

# Save plot to file
setMethod("save_plot_to_file", "Plot",
  function(object) {
    # Save the plot to the result_path
    ggsave(
      paste(
        c(
          object@result_path,
          ".",
          object@format@format),
        collapse = ""),
      width = object@format@width,
      height = object@format@height,
      units = "cm",
      dpi = 320,
      device = object@format@format)
  }
)

# Define initialize method for the Plot class
setMethod("initialize",
  signature(object = "Plot", args = "list"),
  function(object, args) {
    object <- parse_args(object, args)
    # Call read_and_format_data method
    object <- read_and_format_data(object)
    # Check data is correct
    check_data_correct(object)
    # Return the object
    object
  }
)

# Define plot creation method for the Plot class
# Override this method in inheriting classes if new
# kind of plot is needed (i.e. barplot, lineplot, etc.)
setMethod("create_plot",
  signature(object = "Plot"),
  function(object) {
    # Start a generic plot and store it in the object
    # All inheriting methods can call this method by calling
    # callNextMethod(object) and then add their own code
    # or override it.
    plot <- ggplot(
      object@data_frame, aes(
        x = benchmarks,
        fill = configurations,
        y = object@data_frame[, object@stat]))
    plot
  }
)

# Define plot store method for the Plot class
# This method will call create_plot and store the plot in the object
# To implement a new plot, check create_plot method
setMethod("create_and_store_plot",
  signature(object = "Plot"),
  function(object) {
    # Start a generic plot and store it in the object
    # All inheriting methods can call this method by calling
    # callNextMethod(object) and then add their own code
    # or override it.
    object@plot <- create_plot(object)
    object
  }
)

# Define the draw method for the Plot class
setMethod("draw_plot",
  signature(object = "Plot"),
  function(object) {
    # Start a generic plot and store it in the object
    # All inheriting methods can call this method by calling
    # callNextMethod(object) and then add their own code
    # or override it.
    object <- create_and_store_plot(object)
    # Call apply_format method from the format object
    object@plot <- apply_format(object@format, object@plot, object@data_frame)
    # Save the plot to the result_path
    save_plot_to_file(object)
  }
)