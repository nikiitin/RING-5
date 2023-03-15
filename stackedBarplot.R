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

stackVariables <- NULL
nStackVariables <- arguments[currArg]
currArg <- currArg + 1
if (nStackVariables > 0) {
  for (i in 1:nStackVariables) {
    stackVariables <- c(stackVariables, arguments[currArg])
    currArg <- currArg + 1
  }
} else {
  stop("For stacked barplot you should indicate more than one stacking variable.")
}

groupNames <- NULL
nGroupNames <- arguments[currArg]
currArg <- currArg + 1
if (nGroupNames > 0) {
  for (i in 1:nGroupNames) {
    groupNames <- c(groupNames, arguments[currArg])
    currArg <- currArg + 1
  }
}

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

# Create the sd name
# For now avoid sd
#stat.sd <- paste("sd", stat, sep=".")
# Normalize data
if (normalize == "True") {
  # Create new row (sum of all stacked variables)
  parsed_data["total"] <- 0
  for (stat in stackVariables) {
    parsed_data["total"] <- parsed_data["total"] + parsed_data[stat]
  }
  for (bench in unique(parsed_data[,"benchmark_name"])){
    dataToNorm <- parsed_data[parsed_data["benchmark_name"] == bench,]
    # It is already ordered, take first element
    normalizer <- dataToNorm[1,]
    # Apply normalization
    for (i in 1:length(dataToNorm[,1])) {
      for (stat in stackVariables) {
        parsed_data[parsed_data["benchmark_name"] == bench & parsed_data["confName"] == dataToNorm[i, "confName"],stat] <- dataToNorm[i,stat] / normalizer["total"]
      }
      # It is supposed that every stat will have its own confName and bench that won't repeat.
      #parsed_data[parsed_data["benchmark_name"] == bench & parsed_data["confName"] == dataToNorm[i, "confName"],stat] <- dataToNorm[i,stat] / normalizer[stat]
      # Normalize sd too
      # By now, avoid sd
      #parsed_data[parsed_data["benchmark_name"] == bench & parsed_data["confName"] == dataToNorm[i, "confName"],stat.sd] <- dataToNorm[i,stat.sd] / normalizer[stat]
    }
  }
}
# In this case we need a new df to obtain the plot we need
datos <- data.frame(config = character(), benchmark=character(), stat=character(), data=numeric(), stringsAsFactors = FALSE)
stackIndex <- 0
for (i in 1:nrow(parsed_data)) {
  currRow <- parsed_data[i,]
  for (var in stackVariables) {
    #stackIndex <- (stackIndex %% length(stackVariables)) + 1
    data <- currRow[[var]]
    if (is.nan(data)) {data = 0}
    datos[nrow(datos) + 1,] = c(
      as.character(currRow[["confName"]]),
      as.character(currRow[["benchmark_name"]]),
      var,
      data)  
  }
  
}
datos$config <- factor(datos$config, levels = unique(as.character(datos$config)), ordered = TRUE)
datos$benchmark <- factor(datos$benchmark, levels = unique(as.character(datos$benchmark)))
datos$stat <- factor(datos$stat, levels = unique(as.character(datos$stat)))
datos$data <- as.numeric(datos$data)
# Basic plot
# Just plot the bar and sd
p <- ggplot(datos, aes(x=config, fill=stat, y=data)) +
  geom_bar(stat="identity", position="stack") +
  facet_grid(~ benchmark)
  
# Here you can change the theme  
p <- p + theme_hc() +
  theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1))

#if(normalize == "True") {
#p <- p + scale_y_continuous(limits = c(0, 2), breaks = seq(0, 2, by = 0.5))
  
#}

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
if (nGroupNames != 0) {
  p <- p + scale_x_discrete(labels=groupNames)
}



ggsave(paste(c(plot.fileName, ".jpg"), collapse = ""), width=plot.width, height=plot.height, units="cm", dpi=320, device="jpg")
