source("src/data_plotter/src/plot_iface/plot.R")
# Define the S4 class for a lineplot
setClass("resulter", contains = "Plot")

# This plot simply print a table with the data

setMethod("initialize",
  "resulter",
  function(.Object, args) {
    .Object <- callNextMethod()
    .Object
  }
)

setMethod("pre_process", "resulter",
  function(object) {
    # DO NOT CALL PARENT METHOD
    # Pre-process the data
    object
  }
)

# Override create_plot method from Plot class
setMethod("create_plot",
  signature(object = "resulter"),
  function(object) {
    # DO NOT CALL PARENT METHOD
    # Print the table
    print(object@info@data_frame)
    object
  }
)

# Override apply_style method from Plot class
setMethod("apply_style",
  signature(object = "resulter"),
  function(object) {
    # DO NOT CALL PARENT METHOD
    # Apply the style to the plot

    object
  }
)

setMethod("save_plot_to_file",
  signature(object = "resulter"),
  function(object) {
        result_path <- paste(
      c(
        object@info@result_path,
        ".",
        "csv"
      ),
      collapse = ""
    )
    # # Stor
    write.table(object@info@data_frame, result_path, row.names = FALSE, sep = " ")
  }
)
