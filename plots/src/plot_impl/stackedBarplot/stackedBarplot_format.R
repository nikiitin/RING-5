source("plots/plot_impl/formats/plot_format.R")
# Define the derived class stackedBarplot_format
setClass("StackedBarplot_format",
    contains = "plot_format",
)
# TODO: