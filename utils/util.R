increment <- function(val) {
    val + 1
}

get_column_index <- function(column_name, dataframe) {
    which(colnames(dataframe) == column_name)
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