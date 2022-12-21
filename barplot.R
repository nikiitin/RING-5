#!/usr/bin/Rscript
library(readr)
require(ggplot2)
require(ggthemes)

arguments = commandArgs(trailingOnly = TRUE)

# Arguments parsing
plot.title <- arguments[1]
plot.fileName <- arguments[2]
plot.xAxisName <- arguments[3]
plot.yAxisName <- arguments[4]
plot.width <- as.integer(arguments[5])
plot.height <- as.integer(arguments[6])
nConfigs <- as.integer(arguments[7])
fileName <- arguments[8]

currArg <- 9
# Variable arguments start
nBenchFiltered <- arguments[currArg]
currArg <- currArg + 1
benchFiltered <- NULL
if (nBenchFiltered > 0){
  for (i in 1:nBenchFiltered) {
    benchFiltered <- c(benchFiltered, arguments[currArg])
    currArg <- currArg + 1
  }
}

configsFiltered <- new.env()
nConfigsFiltered <- arguments[currArg]
currArg <- currArg + 1
if (nConfigsFiltered > 0) {
  for (i in 1:nConfigsFiltered) {
    configName <- arguments[currArg]
    currArg <- currArg + 1
    configVal <- arguments[currArg]
    currArg <- currArg + 1
    configsFiltered[[configName]] <- configVal
  }
}

configsOrdering <- NULL
nConfigs <- arguments[currArg]
currArg <- currArg + 1
if (nConfigs > 0) {
  for (i in 1:nConfigs) {
    configsOrdering <- c(configsOrdering, as.integer(arguments[currArg]))
    currArg <- currArg + 1
  }
}

normalize <- arguments[currArg]
currArg <- currArg + 1
stat <- arguments[currArg]
currArg <- currArg + 1
legendNames <- NULL
nLegendNames <- arguments[currArg]
currArg <- currArg + 1
if (nLegendNames > 0) {
  for (i in 1:nLegendNames) {
    legendNames <- c(legendNames, arguments[currArg])
    currArg <- currArg + 1
  }
}
# Finish arguments parsing

# Start data collection
parsed_data <- read.table(fileName, sep = " ", header=TRUE)

# Data filtering for benchmarks
for (benchFilter in benchFiltered) {
  parsed_data <- parsed_data[parsed_data["benchmark_name"] != benchFilter,]
}

# Data filtering for configs
for (name in names(configsFiltered)) {
  parsed_data <- parsed_data[parsed_data[name] == configsFiltered[[name]],]
}

# Order benchmarks
parsed_data <- parsed_data[order(parsed_data[,"benchmark_name"], decreasing = FALSE),]


# Order configurations as desired
if (length(configsOrdering) > 1) {
  for (var in configsOrdering) {
    parsed_data <- parsed_data[order(parsed_data[,var], decreasing = FALSE),]
  }
}

# Create configuration names
parsed_data["confName"] <- ""
for (var in 1:nConfigs) {
  parsed_data["confName"] <- paste(parsed_data[,"confName"], parsed_data[,var])
}
print(stat)
# Create the sd name
stat.sd <- paste("sd", stat, sep=".")
# Normalize data
if (normalize == "True") {
  for (bench in parsed_data[,"benchmark_name"]){
    dataToNorm <- parsed_data[parsed_data["benchmark_name"] == bench,]
    # It is already ordered, take first element
    normalizer <- dataToNorm[1,]
    # Apply normalization
    for (i in 1:length(dataToNorm[,1])) {
      # It is supposed that every stat will have its own confName and bench that won't repeat.
      parsed_data[parsed_data["benchmark_name"] == bench & parsed_data["confName"] == dataToNorm[i, "confName"],stat] <- dataToNorm[i,stat] / normalizer[stat]
      # Normalize sd too
      parsed_data[parsed_data["benchmark_name"] == bench & parsed_data["confName"] == dataToNorm[i, "confName"],stat.sd] <- dataToNorm[i,stat.sd] / normalizer[stat]
    }
  }
}


# Basic plot
# Just plot the bar and sd

p <- ggplot(parsed_data, aes(x=benchmark_name, fill=confName, y=parsed_data[,stat])) +
  geom_bar(stat="identity", position="dodge", color="black") +
  geom_errorbar(aes(ymin=parsed_data[,stat] - parsed_data[,stat.sd], ymax=parsed_data[,stat] + parsed_data[,stat.sd]), width=.2, position=position_dodge(.9))

# Here you can change the theme  
p <- p + theme_hc()

# Add parameters to the plot
# Legend names
if (nLegendNames != 0) {
  p <- p + scale_fill_brewer(palette = "Set1", labels=legendNames)
} else {
  p <- p + scale_fill_brewer(palette = "Set1")
}

# Title
if (plot.title != "") {
  p <- p + ggtitle(plot.title)
  # In case you want to modify the style
  #p <- p + theme(plot.title = element_text(family, face, colour, size))
}

# X-axis title
if (plot.xAxisName != "") {
  p <- p + xlab(plot.xAxisName)
  # In case you want to modify the style
  #p + theme(axis.title.x = element_text(family, face, colour, size))
}

# Y-axis title
if (plot.yAxisName != "") {
  p <- p + ylab(plot.yAxisName)
  # In case you want to modify the style
  #p + theme(axis.title.y = element_text(family, face, colour, size))
}
ggsave(paste(c(plot.fileName, ".jpg"), collapse = ""), width=plot.width, height=plot.height, units="cm", dpi=320, device="jpg")
