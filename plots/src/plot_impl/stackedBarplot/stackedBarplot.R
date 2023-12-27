#!/usr/bin/Rscript
source("utils/util.R")
source("plots/plot_impl/plot.R")
source("plots/plot_impl/barplot/barplot.R")

# Define the S4 class for a stacked barplot
setClass("StackedBarplot", contains = "Barplot")

# Override all needed methods from the Barplot class
# Override parse_args method from Barplot class
setMethod("parse_args",
  signature(object = "StackedBarplot"),
  function(object, args) {
    # Call parent method
    object <- callNextMethod()
    # Add the stats to be plotted
    # TODO:
    # Return the object
    object
  }
)
# Override create_plot method from Barplot class
setMethod("create_plot",
  signature(object = "StackedBarplot"),
  function(object) {
    # We can call parent method here!
    # Call parent method
    plot <- ggplot(
      object@data_frame, aes(
        x = configurations,
        fill = stat,
        y = data))
    # Add the geom_bar to the plot object
    plot <- plot + geom_bar(
      stat = "identity",
      position = "stack")
    # Add standard deviation error bars
    plot <- plot + geom_errorbar(
      aes(ymin = data - data_sd,
      ymax = data + data_sd),
      width = .2,
      position = position_dodge(.9))
    plot <- plot + facet_grid(~ benchmarks, switch = "x")
    # Return the plot
    plot
  }
)

# Override read_and_format_data method from Barplot class
setMethod("format_data",
  signature(object = "StackedBarplot"),
  function(object) {
    # Create new data_frame with only the columns we need
    df <- data.frame(
        configurations = character(),
        benchmarks = character(),
        stat = character(),
        data = numeric(),
        data_sd = numeric(),
        stringsAsFactors = FALSE
    )
    # Get all required stats
    # Row by row add stats to dataFrame
    for (row in seq_len(nrow(object@data))) {
        # Get current row
        curr_row <- object@data[row, ]
        for (stat in object@stats) {
            # Extract data and data_sd from current row
            data <- curr_row[[stat]]
            data_sd <- curr_row[[paste(stat, "sd", sep = ".")]]
            # Add row to dataFrame with the following format:
            # configurations | benchmarks | statName | data | data_sd
            df[nrow(df) + 1, ] <- c(
                curr_row$conf_name,
                curr_row$benchmark_name,
                stat,
                data,
                data_sd
            )
        }
    }
    df <- df %>%
        mutate(
            configurations = factor(configurations,
                levels = unique(as.character(configurations)),
                ordered = TRUE
            ),
            benchmarks = factor(benchmarks,
                levels = unique(as.character(benchmarks)),
                ordered = TRUE
            ),
            stat = factor(stat,
                levels = unique(as.character(stat))
            )
        )
    object@data_frame <- df
    # Return the object
    object
  }
)
