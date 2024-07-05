# Divider is a preprocessor
setClass("Divider", contains = "Preprocessor")

setValidity("Divider",
    function(object) {
        callNextMethod()
        if (length(object@operators) != 3) {
            paste(c("Divider must have exactly 3 operators!\n DIV: Dest, Num, Divisor\n", 
                    "Operators: ", object@operators), collapse = " ")
        }
        TRUE
    }
)

setMethod("preprocess",
    signature(object = "Divider"),
    function(object) {
        # Create the new column with the name of the first operator,
        # and the result of the division of the second operator by the third operator
        object@data[, object@operators[1]] <-
            object@data[, object@operators[2]] /
            object@data[, object@operators[3]]
        
        # Create the new column with the name of the first operator,
        # and the result of the division of the second operator by the third operator
        object@data[, paste0(object@operators[1], ".sd")] <-
            object@data[, paste0(object@operators[2], ".sd")] /
            object@data[, object@operators[3]]
        object@data
    }
)