source("utils/R_structs/MapSet.R")
shift <- function(x, n) {
    c(x[-(seq(n))])
}
increment <- function(val) {
    val + 1
}

get_column_index <- function(column_name, dataframe) {
    which(colnames(dataframe) == column_name)
}

get_arg <- function(arguments, n_elements = 1) {
    if (n_elements == 1) {
        elem <- arguments[1]
        elem
    } else if (n_elements > 1) {
        elems <- NULL
        for (i in 1:n_elements) {
            elems <- c(elems, arguments[i])
        }
        elems
    } else {
        NULL
    }
}

check_column_exists <- function(column_name, dataframe) {
    column_name %in% colnames(dataframe)
}

mixStringCols <- function(val1, val2, dataframe) {
    dataFrameColumn <- ""
    for (var in val1:val2) {
        dataFrameColumn <- paste(dataFrameColumn, dataframe[,var], sep="")
    }
    dataFrameColumn
}

geomean <- function(x) {
    result <- exp(mean(log(x[x > 0])))
    if (is.nan(result)) {
        result <- 0
    }
    result
}

sd_dropna <- function(x) {
    sd(x, na.rm = TRUE)
}

arithmean <- function(x) {
    mean(x)
}

return_func <- function(x) {
    x
}

adjust_text_size <- function(text_size, plot_width, plot_height) {
  # Calculate a size based on the dimensions of the plot
  size <- text_size * sqrt(plot_width * plot_height) / 25
  return(size)
}