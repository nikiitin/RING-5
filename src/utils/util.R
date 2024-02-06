source("src/utils/R_structs/MapSet.R")
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

map_elements_df <- function(df, element, map_set, new_name) {
    # Check correct input
    if (!element %in% colnames(df)) {
        stop("The element is not in the dataframe")
    }
    if (!is(map_set, "MapSet")) {
        stop("map_set argument is not a MapSet object")
    }
    if (!length(unique(df[, element])) == length(get_all_keys(map_set))) {
        stop(paste0("Not all elements in the dataframe",
        "can be mapped from the map table"))
    }
    # Get the elements from the map table
    # Add a new empty column to the dataframe
    last_col <- ncol(df) + 1
    df[, last_col] <- NA
    colnames(df)[last_col] <- new_name
    # For each row in the dataframe
    for (i in seq_len(nrow(df))) {
        # Get the element from the map table
        # by key and add the element to the dataframe
        df[i, last_col] <- get_element_by_key(map_set, as.character(df[i, element]))
    }
    # Return the dataframe
    df
}