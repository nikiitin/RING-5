options(error = function() {
  # On error, print the traceback and exit with status 1
  traceback(2)
  exit(1)}
)
# Any used source add it here
# Caution, cyclic dependencies may occur!
library(methods)
library(ggplot2)
library(dplyr, warn.conflicts = FALSE)
library(magrittr)
library(patchwork)
require(stringr)
library(ggh4x)
library(prismatic)
library(ggthemes)
library(tidyr)
library(tidyselect)
source("src/utils/util.R")
source("src/data_plotter/src/plot_iface/info.R")
source("src/data_plotter/src/plot_iface/style.R")

# Set old class gg and ggplot to be able to use ggplot2
# functions inside the S4 class
setOldClass(c("patchwork", "gg", "ggplot"))
#### CLASS DEFINITION ####

# Define the S4 class for a generic plot
setClass("Plot",
  # Define the fields of the class
  slots = list(
    # Put all parameters here!
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
# METHOD DECLARATIONS
#### GENERIC METHOD DEFINITIONS ####

setGeneric("draw_plot", function(object) {
  standardGeneric("draw_plot")
})

setGeneric("create_plot", function(object) {
  standardGeneric("create_plot")
})

setGeneric("apply_style", function(object) {
  standardGeneric("apply_style")
})

setGeneric("pre_process", function(object) {
  standardGeneric("pre_process")
})

setGeneric("save_plot_to_file", function(object) {
  standardGeneric("save_plot_to_file")
})
#### METHOD DEFINITIONS ####

## INITIALIZATION METHODS ##
# Define initialize method for the Plot class
setMethod(
  "initialize", "Plot",
  function(.Object, args) {
    .Object@args <- args
    ## Args parse ##
    # Create plotInfo object
    .Object@info <- new("Plot_info",
      args = .Object@args
    )
    # Update args to remove the ones already used
    .Object %<>% update_args(.Object@info@args)
    .Object@styles <- new("Plot_style",
      args = .Object@args
    )
    # Update args
    .Object %<>% update_args(.Object@styles@args)
    ## Data formating ##
    # Format data
    # Convert all stat columns to numeric
    .Object@info@data[, .Object@info@y] %<>% sapply(as.numeric)
    # Create a new data frame with only the columns we need
    # Create the data_frame object with x columns
    .Object@info@data_frame <- .Object@info@data[.Object@info@x]
    # Take into account that x column is an already ordered factor
    # so assign back the levels to the data frame
    .Object@info@data_frame %<>%
      mutate_at(.Object@info@x,
        as.character) %>%
      mutate_at(.Object@info@x,
        factor,
        levels = unique(pull(.Object@info@data, .Object@info@x)))
    # Add conf_z columns
    .Object@info@data_frame %<>%
      cbind(.Object@info@data[.Object@info@conf_z])
    # Take into account that conf_z column is an already ordered factor
    # so assign back the levels to the data frame
    .Object@info@data_frame[, .Object@info@conf_z] %<>%
      factor(levels = unique(.Object@info@data[, .Object@info@conf_z]))
    # Add stats to dataFrame
    stats <- .Object@info@data[.Object@info@y]
    # Get standard deviation too
    stats_sd <- .Object@info@data[paste(.Object@info@y, "sd", sep = ".")]
    # Add stats to dataFrame
    for (stat in seq_len(ncol(stats))) {
      .Object@info@data_frame <- cbind(
        .Object@info@data_frame,
        stats[stat]
      )
      .Object@info@data_frame <- cbind(
        .Object@info@data_frame,
        stats_sd[stat]
      )
    }
    .Object
  }
)

# Do plotting and persist it in filesystem
# Call this method after initializing the object
setMethod(
  "draw_plot",
  signature(object = "Plot"),
  function(object) {
    # Pre process the data
    object %<>% pre_process()
    # Create the plot
    object %<>% create_plot()
    # Call apply_format method from the format object
    object %<>% apply_style()
    # Save the plot to the result_path
    object %>% save_plot_to_file()
  }
)

# Define pre process method for the Plot class
setMethod(
  "pre_process",
  signature(object = "Plot"),
  function(object) {
    object
  }
)

# Define plot creation method for the Plot class
# This is an abstract method, so it must be overridden
setMethod(
  "create_plot",
  signature(object = "Plot"),
  function(object) {
    object
  }
)

# Define apply style method for the Plot class
setMethod(
  "apply_style",
  signature(object = "Plot"),
  function(object) {
    # Apply style to the plot
    # Set the number of elements per row in the legend
    # and the title of the legend
    object@plot <- object@plot +
      guides(
        fill = guide_legend(
          nrow = object@styles@legend_n_elem_row,
          title = object@styles@legend_title
        )
      )
    # Set the Title
    if (object@styles@title != "") {
      object@plot <- object@plot + ggtitle(object@styles@title)
    } else {
      object@plot <- object@plot + ggtitle(element_blank())
    }
    # Set the x axis title
    if (object@styles@x_axis_name != "") {
      object@plot <- object@plot + xlab(object@styles@x_axis_name)
    } else {
      object@plot <- object@plot + xlab(element_blank())
    }
    # Set the y axis title
    if (object@styles@y_axis_name != "") {
      object@plot <- object@plot + ylab(object@styles@y_axis_name)
    } else {
      object@plot <- object@plot + ylab(element_blank())
    }
    object
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
        object@styles@format
      ),
      collapse = ""
    )
    # # Store the r data in case it is needed
    # # afterwards
    # # Take all the path except the last part
    # cache_path <- object@info@result_path %>% strsplit("/") %>% unlist %>% head(-1) %>% paste0(collapse = "/")
    # id <- object@info@result_path %>% strsplit("/") %>% unlist %>% tail(1)
    # saveRDS(object@plot, file = paste0(cache_path,
    #   "/.sessionCache/",
    #   id,
    #   ".rds"))
    ggsave(
      filename = result_path,
      units = "cm",
      dpi = 320,
      device = object@styles@format,
      plot = object@plot,
      width = object@styles@width,
      height = object@styles@height
    )
  }
)
