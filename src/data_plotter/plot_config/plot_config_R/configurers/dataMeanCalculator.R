#!/usr/bin/Rscript
# DO NOT SOURCE THE INTERFACE FILE!
# IT WILL OVERRIDE THE METHODS DEFINED IN THIS FILE
# Define the S4 class for data mean calculator
setClass("Mean",
    contains = "Data_configurator"
)

# Override perform method from Data_configurator class
setMethod(
    "perform",
    signature(object = "Mean"),
    function(object) {
        # Copy the data frame to store the mean values
        mean_df <- object@args@df
        # Remove rows matching skip_mean values
        print(object@args@mean_var)
        mean_df <- mean_df[!mean_df[, object@args@mean_var] %in%
            object@args@skip_mean, ]
        # Apply the mean algorithm to every stat (y values)
        # removing the x value and having as reference the conf_z value
        mean_df <- aggregate(mean_df[, c(object@args@y, object@args@y_sd)],
            by = mean_df[!names(mean_df) %in%
                c(object@args@mean_var,
                    object@args@y,
                    object@args@y_sd)],
            FUN = object@args@mean_algorithm)
        print(mean_df)
        # Add the x column again to the data frame
        mean_df[object@args@mean_var] <- object@args@mean_algorithm
        # Add the mean_df rows to the data frame
        object@args@df <- rbind(object@args@df, mean_df)
        # Return the object
        object@args@df
    }
)