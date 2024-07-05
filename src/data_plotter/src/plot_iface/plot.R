options(error = function() {
  # On error, print the traceback and exit with status 1
  traceback(2)
  quit(1)
  }
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
library(tidyr, warn.conflicts = FALSE)
library(tidyselect)
library(ggrepel)
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

#' Draw the plot
#'
#' This method is used as the entry point
#' for this class. This is the only method
#' that should be called from outside the class.
#' This method is usually the same for every plot
#' type, but it can be carefyully overridden if needed.
#'
#' @param object The plot object that will be drawn
#' @return The plot object after saving it to file
#' @seealso [create_plot(), pre_process() apply_style(), save_plot_to_file()]
#' That are the functions that are called inside this method
#' @export
setGeneric("draw_plot", function(object) {
  standardGeneric("draw_plot")
})

#' Create the plot object
#'
#' This method is used to create the plot object
#' that will be drawn. This method is overridden
#' for each plot type, as each plot type has
#' different requirements. If you want to create
#' a new plot type, you should always override this method.
#'
#' @param object The plot object that contains
#' the data and the styles to be used
#' @return The plot object with the plot object created
#' @seealso [pre_process() apply_style()] which are
#' called before and after this method
setGeneric("create_plot", function(object) {
  standardGeneric("create_plot")
})

#' Apply the style to the plot
#'
#' This method is used to apply the styles
#' to the plot object. This method can be
#' overridden if needed, and is called just
#' after the plot object is created.
#'
#' @param object The plot object that contains
#' the plot object to be styled
#' @return The plot object with the styles applied
#' @seealso [create_plot()] which is called before
setGeneric("apply_style", function(object) {
  standardGeneric("apply_style")
})

#' Pre process the data
#'
#' This method is used to pre process the data
#' before creating the plot object.
#' This method can be overridden if needed, and is called
#' just before the plot object is created.
#'
#' @param object The plot object that contains
#' the data to be pre processed
#' @return The plot object with the data pre processed
#' @seealso [create_plot()] which is called after
setGeneric("pre_process", function(object) {
  standardGeneric("pre_process")
})

#' Save the plot to a file
#'
#' This method is used to save the plot to a file.
#'
#' @param object The plot object that contains
#' the plot object to be saved
setGeneric("save_plot_to_file", function(object) {
  standardGeneric("save_plot_to_file")
})

#' Create the facet design
#'
#' This method is used to create the facet design
#' for the plot. Usually, it is not called if the
#' plot does not have faceting.
#'
#' @param object The plot object that contains
#' the facetting data
#' @param size_facet The size assigned for each facet.
#' It is a number and will specify how much equally sized
#' space will be assigned to each facet.
#' @param facet_keys If specified, only the facets specified here
#' will be used. If not specified, all facets will be used.
#' @param start_point The starting point for the facet design.
#' If not specified, it will start at 1. 1 means that the design
#' will start at A, 2 means that the design will start at B, and so on.
#' @return The facet design string
setGeneric("create_facet_design", function(object, size_facet, facet_keys = c(), start_point = 1) {
    standardGeneric("create_facet_design")
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
      bind_cols(.Object@info@data[.Object@info@conf_z])
    # If conf_z has more than one column, unite them
    if (length(.Object@info@conf_z) > 1) {
      .Object@info@data_frame %<>% tidyr::unite("conf_z",
        .Object@info@conf_z,
        sep = "_",
        remove = FALSE)
      .Object@info@conf_z <- "conf_z"
    }
    # Take into account that conf_z column is an already ordered factor
    # so assign back the levels to the data frame
    .Object@info@data_frame[, .Object@info@conf_z] %<>%
      factor(levels =
        unique(pull(.Object@info@data_frame, .Object@info@conf_z)))

    # Add stats to dataFrame
    stats <- .Object@info@data[.Object@info@y]
    # Get standard deviation too
    stats_sd <- .Object@info@data[paste(.Object@info@y, "sd", sep = ".")]
    # Add stats to dataFrame
    for (stat in seq_len(ncol(stats))) {
      .Object@info@data_frame <- bind_cols(
        .Object@info@data_frame,
        stats[stat]
      )
      .Object@info@data_frame <- bind_cols(
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
    # Remove hidden bars from data frame, filter by conf_z
    if (length(object@info@hidden_bars) > 0) {
      object@info@data_frame <-
        object@info@data_frame[
            !object@info@data_frame[, object@info@conf_z] %in%
            object@info@hidden_bars, ]
    }
    # Apply faceting for the data frame
    if (length(object@info@faceting_var) > 0) {
      object@info@data_frame %<>%
        map_elements_df(
          object@info@faceting_var,
          object@info@facet_map,
          "facet_column"
        )
    }
    object
  }
)

# Define default facet design for Plot class
setMethod(
    "create_facet_design",
    signature(object = "Plot"),
    function(object, size_facet, facet_keys, start_point) {
        # Get all the unique facets
        facets <- get_all_elements(object@info@facet_map)
        # If facet keys are not empty, filter the facets
        if (length(facet_keys) != 0) {
            # Get only the facets that are in the facet_keys
            facets <- facets[facets %in% facet_keys]
        }
        # Turn the returned list into a vector and
        # Then make a factor out of it with the same
        # order as the original list
        facets <- factor(unlist(facets), levels = unique(unlist(facets)))
        # Create the design string
        design <- ""
        # Remember in R index start at 1
        first_design_letter_index <- start_point
        last_design_letter_index <- start_point - 1
        for (i in levels(facets)) {
            last_design_letter_index <- last_design_letter_index + sum(facets == i)
            # Repeat the letters with the pattern AABB
            # where each one is repeated size_facet times
            design <- paste(design,
                paste(
                    strrep(
                        LETTERS[first_design_letter_index:last_design_letter_index],
                        times = size_facet),
                    collapse = ""
                    ),
                sep = ifelse(design == "", "", "#")
            )
            first_design_letter_index <- last_design_letter_index + 1
        }
        design
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
  "save_plot_to_file", 
  signature(object = "Plot"),
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