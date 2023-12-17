increment <- function(val) {
    val + 1
}

get_column_index <- function(column_name, dataframe) {
    which(colnames(dataframe) == column_name)
}

get_arg <- function(arguments, curr_arg, n_elements = 1) {
    if (n_elements == 1) {
        elem <- arguments[curr_arg]
        elem
    } else if (n_elements > 1) {
        elems <- NULL
        for (i in 1:n_elements) {
            elems <- c(elems, arguments[curr_arg])
            curr_arg <- increment(curr_arg)
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
    exp(mean(log(x)))
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