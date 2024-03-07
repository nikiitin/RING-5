source("src/utils/util.R")
source("src/plots/src/info/plotInfo.R")
source("src/plots/src/styles/styleIface.R")
source("src/plots/src/styles/styleMapper.R")
library(methods)
library(ggplot2)
library(dplyr, warn.conflicts = FALSE)
library(magrittr)

# Set old class gg and ggplot to be able to use ggplot2
# functions inside the S4 class
setOldClass(c("gg", "ggplot"))

#### CLASS DEFINITION ####

# Define the S4 class for a generic plot
setClass("Plot",
  # Define the fields of the class
  slots = list(
    # Information about the plot
    info = "Plot_info",
    # Styles applied to the plot
    styles = "Plot_style",
    # Plot object
    plot = "ggplot",
    # Args to parse
    args = "vector"
  )
)

update_args <- function(object, args) {
  object@args <- args
  object
}
#### GENERIC METHOD DEFINITIONS ####
# Define all generic methods for the Plot class
# These methods will be overridden in inheriting classes
# at demand

setGeneric("create_plot_info", function(object) {
  standardGeneric("create_plot_info")
})

setGeneric("read_and_format_data", function(object) {
  standardGeneric("read_and_format_data")
})

setGeneric("create_style_plot", function(object) {
  standardGeneric("create_style_plot")
})

setGeneric("format_data", function(object) {
  standardGeneric("format_data")
})

setGeneric("add_stats_to_data", function(object) {
  standardGeneric("add_stats_to_data")
})

setGeneric("add_name_columns", function(object) {
  standardGeneric("add_name_columns")
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
    .Object@args <- args
    # Create info object
    .Object %<>% create_plot_info()
    # Update args
    .Object %<>% update_args(.Object@info@args)
    # Call read_and_format_data method
    .Object %<>% read_and_format_data()
    # Return the object
    .Object
  }
)

# Define create_plot_info method for the Plot class
setMethod(
  "create_plot_info",
  signature(object = "Plot"),
  function(object) {
    # Create a new plotInfo object
    object@info <- new("Plot_info",
      args = args
    )
    object
  }
)

# Prepare data for plotting. This will create a new
# data_frame with only the columns we need
setMethod(
  "read_and_format_data", "Plot",
  function(object) {
    # Call format_data method to format the data that
    # will be plotted
    object %<>% format_data()
    # Create the style object
    object %<>% create_style_plot()
    # Update args
    object %<>% update_args(object@styles@args)
    object
  }
)

# Define the create_format_plot method for the Plot class
setMethod(
  "create_style_plot",
  signature(object = "Plot"),
  function(object) {
    # Get the name of the style to be used
    # This is kinda tricky...
    style_name <- get_arg(object@args, 1)
    object@args %<>% shift(1)
    # Create a new style object
    # see plots/plot_impl/styleMapper.R
    object@styles <- get_style(
      tolower(class(object)[1]),
      style_name,
      object@args
    )
    # Set updated plot info to styles
    object@styles %<>% set_plot_info(object@info)
    # Note that the style object will depend
    # directly on the plot being created.
    # e.g. a barplot will have a barplot style
    # defined in its styles folder.
    # see plots/plot_impl/barplot/styles
    object
  }
)


# Format data
setMethod(
  "format_data", "Plot",
  function(object) {
    # Format data
    # Check if stat columns can be turned to numeric
    if (!all(
      sapply(
        object@info@data[, object@info@y],
        is.numeric
      )
    )) {
      stop("Stats are not numeric type! Stopping plot...")
    }
    # Convert all stat columns to numeric
    object@info@data[, object@info@y] %<>% sapply(as.numeric)
    # Create a new data frame with only the columns we need
    object %<>% add_name_columns()
    # Add stats to dataFrame... Should
    # be added in rows
    object %<>% add_stats_to_data()
    # Return the object
    object
  }
)

# Add name columns to data
setMethod(
  "add_name_columns", "Plot",
  function(object) {
    # Create the data_frame object with x columns
    # For now, those are the only names defined
    object@info@data_frame <- object@info@data[object@info@x]
    # Take into account that x column is an already ordered factor
    # so assign back the levels to the data frame
    object@info@data_frame %<>%
      mutate_at(object@info@x,
        as.character) %>%
      mutate_at(object@info@x,
        factor,
        levels = unique(pull(object@info@data, object@info@x)))
    print("add_name")
    print(pull(object@info@data, object@info@x))
    print("FIN")
    object
  }
)

# Add stats to plot
setMethod(
  "add_stats_to_data", "Plot",
  function(object) {
    # Get all required stats
    stats <- object@info@data[object@info@y]
    # Get standard deviation too
    stats_sd <- object@info@data[paste(object@info@y, "sd", sep = ".")]
    # Add stats to dataFrame
    for (stat in seq_len(ncol(stats))) {
      object@info@data_frame <- cbind(
        object@info@data_frame,
        stats[stat]
      )
      object@info@data_frame <- cbind(
        object@info@data_frame,
        stats_sd[stat]
      )
    }
    object
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
    object %<>% create_and_store_plot()
    # Call apply_format method from the format object
    object@plot <- apply_style(object@styles, object@plot)
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
    # Let the method not implemented, so must be overridden
    warning(paste0("Calling create_plot method from Plot class!!",
      " Only inherited version should be called!"))
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
        object@info@result_path,
        ".",
        object@styles@style_info@format
      ),
      collapse = ""
    )
    # Store the r data in case it is needed
    # afterwards
    # Take all the path except the last part
    cache_path <- object@info@result_path %>% strsplit("/") %>% unlist %>% head(-1) %>% paste0(collapse = "/")
    id <- object@info@result_path %>% strsplit("/") %>% unlist %>% tail(1)
    saveRDS(object@plot, file = paste0(cache_path,
      "/.sessionCache/",
      id,
      ".rds"))
    ggsave(
      filename = result_path,
      units = "cm",
      dpi = 320,
      device = object@styles@style_info@format,
      plot = object@plot,
      width = object@styles@style_info@width,
      height = object@styles@style_info@height
    )
  }
)
## END AFTER PLOTTING METHODS ##