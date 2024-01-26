#!/usr/bin/Rscript
options(error = function() traceback(2))
library(tidyr)
library(dplyr)
library(tidyselect)
library(ggh4x)
source("utils/util.R")
source("plots/src/plot_impl/stackedbarplot/src/stackedBarplot.R")
# PlotType info, each plot type must have its own info
source("plots/src/plot_impl/groupedstackedbarplot/info/groupedStackedBarplotInfo.R")


# Define the S4 class for a barplot
setClass("GroupedStackedBarplot", contains = "StackedBarplot")

setMethod(
  "create_plot_info",
  signature(object = "GroupedStackedBarplot"),
  function(object) {
    # Create the specific info object for the plot
    object@info <- new("GroupedStackedBarplot_info",
      args = object@args
    )
    object
  }
)

setMethod("add_stats_to_data",
  signature(object = "GroupedStackedBarplot"),
  function(object) {
    # Call parent method
    object <- callNextMethod()
    # The vector ID is kept in csv to avoid collisions
    # There is a common part of the name of the columns that is
    # the same for all the entries. We need to remove it
    # to have only the name of the entries
    # Remove vector ID as all collisions are already removed
    # while adding elements to the data frame
    object@info@data_frame %<>%
      dplyr::rename_with(
        ~ sub(".*\\.\\.", "", .)
      )
    sd_df <- object@info@data_frame %>% tidyr::pivot_longer(
        cols = tidyselect::ends_with(".sd"),
        names_to = "entries",
        values_to = "values_sd"
      )
    object@info@data_frame %<>%
      select(-tidyselect::ends_with(".sd")) %>%
      tidyr::pivot_longer(
        cols = -c(object@info@x, object@info@conf_z),
        names_to = "entries",
        values_to = "values"
      ) %>%
      cbind(values_sd = sd_df$values_sd)
    # Return the object
    object
  }
)

# Override create_plot method from Plot class
# need different behavior for barplot
setMethod(
  "create_plot",
  signature(object = "GroupedStackedBarplot"),
  function(object) {
    # Get the cummulative sum of the y axis. It will be used
    # to set error bars for each entry
    # Just let it here, in case it is useful
    # error_df <- object@info@data_frame %>%
    #   group_by(conf_z,x) %>%
    #   mutate(error_bar_cumsum = cumsum(values)) %>%
    #   ungroup()
    
    # Data mapping performed here is hard to understand but
    # it would summarize to something like this:
    #        |
    # y_val  |
    #        |
    #        |
    #        -----------------------
    #        |                     |
    #     conf_z_a              conf_z_b
    #        |                     |
    #        -----------------------
    #                  X

    # Names from df should be always the same, it is a wrap
    # specific for this plot
    object@plot <- ggplot(object@info@data_frame, aes(
      x = .data[[object@info@conf_z]],
      y = values
    ))
    # Add the facet grid to the plot object. Switch it in to X,
    # this enforce style to group variables in x axis
    object@plot <- object@plot + facet_grid(
      ~ .data[[object@info@x]], switch = "x"
    )
    # Add the geom_bar to the plot object. Use position_stack to
    # stack the bars and reverse = TRUE to have the bars in the
    # same order as the legend.
    object@plot <- object@plot + geom_bar(
      stat = "identity",
      position = position_stack(reverse = TRUE),
      color = "black",
      aes(fill = entries)
    )

    # REALLY UGLY, I do not know if it
    # should be used, just let it here, maybe it is useful

    # # Add standard deviation error bars, use the caculated
    # # error_bar as y axis
    # object@plot <- object@plot + geom_errorbar(
    #   data = error_df,
    #   aes(
    #     ymin = error_bar_cumsum - values_sd,
    #     ymax = error_bar_cumsum + values_sd,
    #   ),
    #   width = .2
    # )


    # Return the plot
    object@plot
  }
)