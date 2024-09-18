source("src/utils/R_structs/MapSet.R")
setClassUnion("nullable_vector", c("vector", "NULL"))
shift <- function(x, n) {
    if (n > 0) {
        c(x[-(seq(n))])
    } else x
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

sd_dropna <- function(x) {
    sd(x, na.rm = TRUE)
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
    if (!length(unique(pull(df, element))) == length(get_all_keys(map_set))) {
        stop(paste0("Not all elements in the dataframe",
        "can be mapped from the map table", " dataFrame:\n", unique(df[, element]),
        " mapTable:\n", get_all_keys(map_set)))
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
    # Turn this character vector into a factor
    df[, last_col] <- 
        factor(df[, last_col], levels = unique(unlist(get_all_elements(map_set))))
    # Return the dataframe
    df
}

get_stack_discrete_color_vector <- function(total_n_elements) {
    indexes <- c()
    for (i in seq_len(total_n_elements)) {
        if (i %% 2 == 0) {
            i / 2
            indexes <- c(indexes, ((i / 2) / total_n_elements))
        } else {
            indexes <- c(indexes, 0.5 + (((i + 1) / 2) / total_n_elements))
        }
    }
    indexes
}

read_data <- function(path) {
  # Check if the file exists
  if (!file.exists(path)) {
    stop(paste0("File not found: ", path, " Stopping..."))
  }
  # Read data from csv file
  data <- read.table(path, sep = " ", header = TRUE, stringsAsFactors = FALSE)
  # Return the data
  data
}