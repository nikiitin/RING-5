increment <- function(val) {
    val + 1
}

mixStringCols <- function(val1, val2, dataframe) {
    dataFrameColumn <- ""
    for (var in val1:val2) {
        dataFrameColumn <- paste(dataFrameColumn, dataframe[,var], sep="")
    }
    dataFrameColumn
}