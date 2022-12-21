#!/usr/bin/Rscript

library(readr)
arguments = commandArgs(trailingOnly = TRUE)
statsFile <- arguments[1]
configs <- arguments[2]
configs <- as.numeric(configs)
dataToFilter <- arguments[3]
parsed_data <- read.table(statsFile, sep = " ", header=TRUE)


# Calculate mean
outputdf <- aggregate(parsed_data[(configs+1):ncol(parsed_data)], by=parsed_data[1:configs],FUN = mean)

# Filter outliers from current mean 
#parsed_data["outlier"] <- FALSE
#for (i in 1:nrow(parsed_data)) {
#  elemFilt <- NULL
#  elemFilt <- outputdf[outputdf["benchmark_name"] == parsed_data[i,"benchmark_name"]]
#  for (j in 1:configs) {
#    elemFilt <- elemFilt[elemFilt[,j] == parsed_data[i,j]]
#  }
#  parsed_data[i,"outlier"] <- parsed_data[i, dataToFilter] > elemFilt[,dataToFilter] * 1.2
#}

#outputdf <- parsed_data[parsed_data["outlier"] != TRUE]
#outputdf <- aggregate(parsed_data[(configs+1):ncol(parsed_data)], by=parsed_data[1:configs],FUN = mean)
outputdf["random_seed"] <- NULL
# Calculate sd
secondOdf <- aggregate(parsed_data[(configs+1):ncol(parsed_data)], by=parsed_data[1:configs],FUN = sd)
secondOdf["random_seed"] <- NULL

# Rename columns to differentiate between mean and sd
colnames(secondOdf)[(configs + 1):ncol(secondOdf)] <- paste("sd", colnames(secondOdf)[(configs + 1):ncol(secondOdf)], sep = "-")

# Merge both df
outputdf <- merge(x=outputdf, y=secondOdf, by = colnames(outputdf)[1:configs])

# Write everything onto csv file
write.table(outputdf, statsFile, sep=" ", row.names = F)