library(prismatic)
library(ggthemes)
source("utils/util.R")
setClass("Plot_format",
  slots = list(
    # The title of the plot
    title = "character",
    # The name of the x axis
    x_axis_name = "character",
    # The name of the y axis
    y_axis_name = "character",
    # The width of the plot
    width = "numeric",
    # The height of the plot
    height = "numeric",
    # The number of legend names
    n_legend_names = "numeric",
    # The names that will appear in the legend
    # In the order of apparence
    legend_names = "vector",
    # The number of y breaks
    n_y_breaks = "numeric",
    # The y breaks
    y_breaks = "vector",
    # The top limit of the y axis
    y_limit_top = "numeric",
    # The bottom limit of the y axis
    y_limit_bot = "numeric",
    # The format of the plot: pdf, png, etc.
    format = "character",
    # The title of the legend
    legend_title = "character",
    # The number of elements (configs) per row in the legend
    legend_n_elem_row = "numeric",
    # The number of x split points
    n_x_split_points = "numeric",
    # The x split points (dotted vertical bars splitting the plot)
    x_split_points = "vector",
    # The statistics to be used
    stats = "vector"
  )
)
# Define all generic methods for the Plot_format class
setGeneric("parse_args_format",
  function(object, format_start_point, args) {
  standardGeneric("parse_args_format")
})

setGeneric("check_data_format_correct", function(object, df) {
  standardGeneric("check_data_format_correct")
})

setGeneric("apply_format", function(object, plot, df) {
  standardGeneric("apply_format")
})

# Define the parse_args method for the Plot_format class
setMethod("parse_args_format",
  signature(object = "Plot_format",
    format_start_point = "numeric",
    args = "vector"),
  function(object, format_start_point, args) {
    # Parse the arguments and store them in the object
    # Prepare the format object
    # It will apply all format configurations to the plot
    curr_arg <- format_start_point
    object@title <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    object@x_axis_name <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    object@y_axis_name <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    object@width <- as.numeric(get_arg(args, curr_arg, 1))
    curr_arg <- increment(curr_arg)
    object@height <- as.numeric(get_arg(args, curr_arg, 1))
    curr_arg <- increment(curr_arg)
    object@n_legend_names <- as.numeric(get_arg(args, curr_arg, 1))
    curr_arg <- increment(curr_arg)
    object@legend_names <- get_arg(args, curr_arg, object@n_legend_names)
    curr_arg <- curr_arg + object@n_legend_names
    object@n_y_breaks <- as.numeric(get_arg(args, curr_arg, 1))
    curr_arg <- increment(curr_arg)
    object@y_breaks <- as.numeric(get_arg(args, curr_arg, object@n_y_breaks))
    curr_arg <- curr_arg + object@n_y_breaks
    object@y_limit_top <- as.numeric(get_arg(args, curr_arg, 1))
    curr_arg <- increment(curr_arg)
    object@y_limit_bot <- as.numeric(get_arg(args, curr_arg, 1))
    curr_arg <- increment(curr_arg)
    object@format <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    object@legend_title <- get_arg(args, curr_arg, 1)
    curr_arg <- increment(curr_arg)
    object@legend_n_elem_row <- as.numeric(get_arg(args, curr_arg, 1))
    curr_arg <- increment(curr_arg)
    object@n_x_split_points <- as.numeric(get_arg(args, curr_arg, 1))
    curr_arg <- increment(curr_arg)
    object@x_split_points <- as.numeric(
      get_arg(
        args,
        curr_arg,
        object@n_x_split_points))
    curr_arg <- curr_arg + object@n_x_split_points
    # Return the object
    object
  }
)

# Define initialize method for the Plot class
setMethod("initialize", "Plot_format",
  function(.Object, format_start_point, stats, args) {
    .Object@stats <- stats
    # Call the parse_args method
    #options(error=function()traceback(2))
    .Object <- parse_args_format(.Object, format_start_point, args)
    # Return the object
    .Object
  }
)

# Check data is correct
setMethod("check_data_format_correct",
  signature(object = "Plot_format", df = "data.frame"),
  function(object, df) {
    # Non-critical errors
    # Tell the user the error to fix it
    # Check if any y break is over the top limit
    if (any(object@y_breaks > object@y_limit_top)) {
      warning("Y breaks are over the top limit!")
    }
    # Check if any y break is under the bottom limit
    if (any(object@y_breaks < object@y_limit_bot)) {
      warning("Y breaks are under the bottom limit!")
    }
    # Check if x split points is below 1
    if (object@n_x_split_points < 1) {
      warning("Number of x split points is below 1!")
    }
    # Check if number of n_legend_names is equal to number of configs
    if (object@n_legend_names > 0 &&
      object@n_legend_names != length(unique(df$configurations))) {
      warning(paste("Number of legend names is not equal to number of configs!",
        " Expected: ",
        length(unique(df$configurations)),
        " Got: ",
        object@n_legend_names, sep = ""))
    }
    # Check if x split points is greater than the number of benchmarks
    if (object@n_x_split_points > 0 &&
     object@n_x_split_points > length(unique(df$benchmarks))) {
      warning(paste("Number of x split points is over benchmarks number!",
        " Expected: ",
        length(unique(df$benchmarks)),
        " Got: ",
        object@n_x_split_points, sep = ""))
    }
  }
)
# Set old class gg and ggplot to be able to use ggplot2
# functions inside the S4 class
setOldClass(c("gg", "ggplot"))
# Define the draw method for the Plot class
setMethod(
  "apply_format",
  signature(object = "Plot_format", plot = "ggplot", df = "data.frame"),
  function(object, plot, df) {
    # Apply style to the plot
    # Set x split points. An split point
    # is a dotted vertical line that splits the plot
    # into two parts (or more) to make it easier to read.
    # The split points are the x coordinates of the lines (reference
    # points are benchmarks)
    if (object@n_x_split_points > 0) {
      plot <- plot +
        geom_vline(
          xintercept = object@x_split_points,
          linetype = "dashed",
          color = "black"
        )
    }
    # Set the theme to be used
    plot <- plot + theme_hc()
    # Add specific configs to the theme
    # TODO: This should be configurable
    plot <- plot + theme(
      axis.text.x = element_text(
        angle = 30,
        hjust = 1,
        size = 10,
        face = "bold"
      ),
      axis.text.y = element_text(
        hjust = 1,
        size = 10,
        face = "bold"
      ),
      legend.position = "top",
      legend.justification = "right"
    )


    # Add the colors to the plot (one color per config)
    # using viridis color palette, which is a colorblind
    # friendly palette. In case a label is used, make it match
    # the color black/white depending on the background color.
    colors <-
      farver::decode_colour(
        viridisLite::magma(
          length(
            unique(
              df$configurations
            )
          ),
          direction = -1
        ),
        "rgb",
        "hcl"
      )
    label_col <- ifelse(colors[, "l"] > 50, "black", "white")
    # Assign the colors to plot and labels to legend in case
    # legend names are specified
    if (object@n_legend_names != 0) {
      plot <- plot +
        scale_fill_viridis_d(
          option = "plasma",
          labels = object@legend_names,
          direction = -1
        )
    } else {
      plot <- plot +
        scale_fill_viridis_d(
          option = "plasma",
          direction = -1
        )
    }
    # Set the number of elements per row in the legend
    # and the title of the legend
    plot <- plot +
      guides(
        fill = guide_legend(
          nrow = object@legend_n_elem_row,
          title = object@legend_title
        )
      )
    # Limit the y axis and assign labels to those
    # statistics that overgo the top limit
    if (object@y_limit_top > 0) {
      if (object@y_limit_bot > object@y_limit_top) {
        warning("Y limit bot is greater than Y limit top! skipping limits")
      } else if (object@y_limit_bot < 0) {
        warning("Y limit bot is less than 0! skipping limits")
      } else {
        # Check if any stat goes over the top limit and
        # assign a label to it
        list_of_labels <-
          ifelse(
            (df[, object@stats] > (object@y_limit_top)),
            format(
              round(
                df[, object@stats],
                2
              ),
              nsmall = 2
            ),
            NA
          )
        # Set the breaks and the limits
        plot <- plot +
          scale_y_continuous(
            breaks = object@y_breaks,
            oob = scales::squish
          )
        plot <- plot + coord_cartesian(
          ylim = as.numeric(
            c(
              object@y_limit_bot,
              object@y_limit_top
            )
          )
        )
        # Add the labels to the plot
        plot <- plot +
          geom_text(
            position = position_dodge(.9),
            aes(
              label = list_of_labels,
              group = configurations,
              color = configurations,
              y = object@y_limit_top
            ),
            show.legend = FALSE,
            size = 2.5,
            angle = 90,
            hjust = "inward"
          )
        # Set the color of the labels
        plot <- plot +
          scale_color_manual(
            values = label_col
          )
      }
    }
    # Set the Title
    if (object@title != "") {
      plot <- plot + ggtitle(object@title)
    }
    # Set the x axis title
    if (object@x_axis_name != "") {
      plot <- plot + xlab(object@x_axis_name)
    }
    # Set the y axis title
    if (object@y_axis_name != "") {
      plot <- plot + ylab(object@y_axis_name)
    }
    # Return the plot
    plot
  }
)