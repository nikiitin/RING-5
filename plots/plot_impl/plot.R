source("utils/util.R")
source("plots/plot_impl/formats/plot_format.R")
library(methods)
library(ggplot2)
library(dplyr)
library(readr)

# Set old class gg and ggplot to be able to use ggplot2
# functions inside the S4 class
setOldClass(c("gg", "ggplot"))

#### CLASS DEFINITION ####

# Define the S4 class for a generic plot
setClass("Plot",
  # Define the fields of the class
  slots = list(
    # Format configuration class that contains all the
    # configuration for the plot
    # Each plot can have its own format configuration, see
    # plots/plot_impl/formats/plot_format.R
    # Number of x axis variables
    n_x = "numeric",
    # Columns to use as x axis
    x = "vector",
    # Number of y axis variables
    n_y = "numeric",
    # Columns to use as y axis
    y = "vector",
    # Format applied to the plot
    format = "Plot_format",
    # The path to the file where the plot will be saved
    result_path = "character",
    # The path to the file containing the data to be plotted
    stats_file = "character",
    # The number of legend names
    data = "data.frame",
    # Data frame to be plotted
    data_frame = "data.frame",
    # Plot object
    plot = "ggplot",
    # Args to parse
    args = "vector"
  )
)

#### GENERIC METHOD DEFINITIONS ####
# Define all generic methods for the Plot class
# These methods will be overridden in inheriting classes
# at demand
setGeneric(
  "parse_args",
  function(object, args) {
    standardGeneric("parse_args")
  }
)

setGeneric("create_format_plot", function(object) {
  standardGeneric("create_format_plot")
})

setGeneric("read_and_format_data", function(object) {
  standardGeneric("read_and_format_data")
})

setGeneric("read_data", function(object) {
  standardGeneric("read_data")
})

setGeneric("format_data", function(object) {
  standardGeneric("format_data")
})

setGeneric("add_stats_to_data", function(object) {
  standardGeneric("add_stats_to_data")
})

setGeneric("check_data_correct", function(object) {
  standardGeneric("check_data_correct")
})

setGeneric("draw_plot", function(object) {
  standardGeneric("draw_plot")
})

setGeneric("create_and_store_plot", function(object) {
  standardGeneric("create_and_store_plot")
})

setGeneric("create_plot", function(object) {
  standardGeneric("create_plot")
})

setGeneric("save_plot_to_file", function(object) {
  standardGeneric("save_plot_to_file")
})
#### END GENERIC METHOD DEFINITIONS ####
#### METHOD DEFINITIONS ####

## INITIALIZATION METHODS ##
# Define initialize method for the Plot class
setMethod(
  "initialize", "Plot",
  function(.Object, args) {
    .Object <- parse_args(.Object, args)
    # Prepare the format object
    # It will apply all format configurations to the plot
    .Object@format <- create_format_plot(.Object)
    # Call read_and_format_data method
    .Object <- read_and_format_data(.Object)
    # Check data is correct
    check_data_correct(.Object)
    # Return the object
    .Object
  }
)

# Define the parse_args method for the Plot class
setMethod(
  "parse_args",
  signature(object = "Plot", args = "vector"),
  function(object, args) {
    # Parse the arguments and store them in the object
    object@args <- args
    object@result_path <- get_arg(args, 1, 1)
    object@args %<>% shift(1)
    object@stats_file <- get_arg(args, 1)
    args %<>% shift(1)
    object@n_x <- as.numeric(get_arg(args, 1))
    args %<>% shift(1)
    object@x <- get_arg(args, object@n_x)
    args %<>% shift(object@n_x)
    object@n_y <- as.numeric(get_arg(args, 1))
    args %<>% shift(1)
    object@y <- get_arg(args, object@n_y)
    args %<>% shift(object@n_y)
    object
  }
)

# Define the create_format_plot method for the Plot class
setMethod(
  "create_format_plot",
  signature(object = "Plot"),
  function(object) {
    # Create a new format object
    object@format <- new("Plot_format",
      y = object@y,
      args = object@args
    )
    object
  }
)

# Prepare data for plotting. This will create a new
# data_frame with only the columns we need
setMethod(
  "read_and_format_data", "Plot",
  function(object) {
    # Read data from csv file and store it in the object
    object <- read_data(object)
    # Check if stat column can be turned to numeric
    if (!all(
      sapply(
        object@data[, object@y],
        is.numeric
      )
    )
    ) {
      stop("Stats are not numeric type! Stopping plot...")
    }
    # Convert all stat columns to numeric
    object@data[, object@y] <-
      sapply(object@data[, object@y], as.numeric)
    # Call format_data method to format the data that
    # will be plotted
    object <- format_data(object)
    object
  }
)

# Read data from file
setMethod(
  "read_data", "Plot",
  function(object) {
    # Read data from csv file
    object@data <- read.table(object@stats_file, sep = " ", header = TRUE)
    object
  }
)

# Format data
setMethod(
  "format_data", "Plot",
  function(object) {
    # Format data
    # Combine all x axis columns into one
    x_cols <- object@data[, object@x]
    x_cols <- factor(
      apply(x_cols, 1, paste, collapse = " "),
      levels = unique(apply(x_cols, 1, paste, collapse = " ")),
      ordered = TRUE
    )
    # Prepare dataFrame for future plotting
    # Add x axis column
    object@data_frame <- data.frame(
      x = x_cols
    )
    # Add stats to dataFrame... Should
    # be added in rows
    object <- add_stats_to_data(object)
    object
  }
)

# Add stats to plot
setMethod(
  "add_stats_to_data", "Plot",
  function(object) {
    # Get all required stats
    stats <- object@data[object@y]
    # Get standard deviation too
    stats_sd <- object@data[paste(object@y, "sd", sep = ".")]
    # Add stats to dataFrame
    for (stat in ncol(stats)) {
      object@data_frame <- cbind(
        object@data_frame,
        stats[stat]
      )
      object@data_frame <- cbind(
        object@data_frame,
        stats_sd[stat]
      )
    }
    object
  }
)

# Check data is correct
setMethod(
  "check_data_correct", "Plot",
  function(object) {
    # Critical errors
    # Stop the plot if any of these errors are found
    if (object@n_y < 1) {
      stop("No stats defined to plot! Stopping plot...")
    }
    # Check if all stats are present in the data
    if (!all(
      sapply(
        object@y,
        function(stats) {
          stats %in% colnames(object@data_frame)
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

## END INITIALIZATION METHODS ##
## PLOTTING METHODS ##

# Define the draw method for the Plot class
setMethod(
  "draw_plot",
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

# Define plot store method for the Plot class
# This method will call create_plot and store the plot in the object
# To implement a new plot, check create_plot method
setMethod(
  "create_and_store_plot",
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

# Define plot creation method for the Plot class
# Override this method in inheriting classes if new
# kind of plot is needed (i.e. barplot, lineplot, etc.)
setMethod(
  "create_plot",
  signature(object = "Plot"),
  function(object) {
    # Start a generic plot and store it in the object
    # All inheriting methods can call this method by calling
    # callNextMethod(object) and then add their own code
    # or override it.
    plot <- ggplot(
      object@data_frame, aes(
        x = x,
        y = .data[[object@y]]
      )
    )
    plot
  }
)

## END PLOTTING METHODS ##
## AFTER PLOTTING METHODS ##

# Save plot to file
setMethod(
  "save_plot_to_file", "Plot",
  function(object) {
    # Save the plot to the result_path
    result_path <- paste(
      c(
        object@result_path,
        ".",
        object@format@format
      ),
      collapse = ""
    )
    ggsave(
      filename = result_path,
      units = "cm",
      dpi = 320,
      device = object@format@format,
      plot = object@plot,
      width = object@format@width,
      height = object@format@height
    )
  }
)
## END AFTER PLOTTING METHODS ##