setClass("MapSet",
    slots = list(
        # Map table
        map_table = "data.frame"
    )
)

setGeneric("get_all_keys",
    function(object) {
        standardGeneric("get_all_keys")
    }
)

setGeneric("get_all_elements",
    function(object) {
        standardGeneric("get_all_elements")
    }
)

setGeneric("get_element_by_key",
    function(object, key) {
        standardGeneric("get_element_by_key")
    }
)

setGeneric("emplace_element",
    function(object, key, value) {
        standardGeneric("emplace_element")
    }
)

setGeneric("set_element",
    function(object, key, value) {
        standardGeneric("set_element")
    }
)

# Define a private method to insert
# the element in the map table unless
# the key already exists
setGeneric("put_element",
    function(object, key, value, overwrite = FALSE) {
        standardGeneric("put_element")
    }
)

# Define a private method to insert
# the element in the map table
setMethod(
    "put_element",
    signature(object = "MapSet", key = "character", value = "ANY"),
    function(object, key, value, overwrite = FALSE) {
        # Check if the key already exists in the map table
        if (key %in% rownames(object@map_table)) {
            # If the key already exists in the map table
            # and overwrite is set to FALSE
            # do nothing
            if (overwrite) {
                object@map_table[key, "value"] <- value
            }
        } else {
            # If the key does not exist in the map table
            # add the key and value
            object@map_table[key, "value"] <- value
        }
        # Return the object
        object
    }
)


# Initialize the map table empty
# and with key as character and value as
# type explicitly defined the function
# arguments
setMethod(
    "initialize",
    "MapSet",
    function(.Object, container_type) {
        # Initialize the map table
        # with key as character
        # Keep in mind it will work for
        # any type of value as long as
        # the value is R defined or can
        # be returned by mode() function
        .Object@map_table <- data.frame(
            key = character(),
            value = vector(mode = container_type),
            stringsAsFactors = FALSE,
            row.names = "key"
        )
        .Object
    }
)
# Get the element from the map table
# by key
setMethod(
    "get_element_by_key",
    signature(object = "MapSet", key = "character"),
    function(object, key) {
        # Get the element from the map table
        # by key
        element <- object@map_table[key, "value"]
        if (is.list(element)) {
            # If the element is a list of lists
            # turn it into a list
            element <- element[[1]]
        }
        # Return the element
        element
    }
)



# Emplace the element in the map table
# using key and value
# Note: if the key already exists in the map table
# nothing will be done
setMethod(
    "emplace_element",
    signature(object = "MapSet", key = "character", value = "ANY"),
    function(object, key, value) {
        if (is.vector(value)) {
            # If value is a vector turn it into a list of lists
            value <- list(list(value))
        } else if (is.list(value)) {
            # If value is a list turn it into a list of lists
            value <- list(value)
        }
        # If the value is not iterable do nothing with it
        # Check if the key already exists in the map table
        object <- put_element(object, key, value)
        # Return the object
        object
    }
)

# Set the element in the map table
# using key and value
# Note: if the key already exists in the map table
# the value will be overwritten
setMethod(
    "set_element",
    signature(object = "MapSet", key = "character", value = "ANY"),
    function(object, key, value) {
        if (is.vector(value)) {
            # If value is a vector turn it into a list of lists
            value <- list(list(value))
        } else if (is.list(value)) {
            # If value is a list turn it into a list of lists
            value <- list(value)
        }
        # If the value is not iterable do nothing with it
        # Check if the key already exists in the map table
        object <- put_element(object, key, value, overwrite = TRUE)
        # Return the object
        object
    }
)

setMethod(
    "get_all_keys",
    signature(object = "MapSet"),
    function(object) {
        # Get all the keys from the map table
        keys <- rownames(object@map_table)
        # Return the keys
        keys
    }
)

setMethod(
    "get_all_elements",
    signature(object = "MapSet"),
    function(object) {
        # Get all the elements from the map table
        elements <- object@map_table[, "value"]
        # Return the elements
        elements
    }
)

# Override the subscript operator
# to get the element from the map table
# by key
setMethod(
    "[",
    signature(x = "MapSet", i = "character"),
    function(x, i) {
        # Get the element from the map table
        # by key
        element <- get_element_by_key(x, i)
        # Return the element
        element
    }
)

# Override the subscript operator
# to set the element in the map table
# by key
setMethod(
    "[<-",
    signature(x = "MapSet", i = "character", value = "ANY"),
    function(x, i, value) {
        # Set the element in the map table
        # by key
        x <- set_element(x, i, value)
        # Return the object
        x
    }
)