#!/usr/bin/perl
use strict;
use warnings;
use FindBin;
use lib "$FindBin::Bin/libs";
# Include TypeFormatRegex which will provide
# a strong data type syntax and can format
# the output to match needed syntax
use TypesFormatRegex;

# Stat file being parsed
my $filename = shift or die "Please provide a filename as an argument.\n";
# At least provide one filter
die "Please provide at least one filter as an argument.\n" unless @ARGV;
# Filters for variable names
setFilterRegexes(@ARGV);
# Open the statistics file with buffered I/O
open(my $fh, '<:raw', $filename) or die "Could not open file '$filename' $!";

# Optimization: Read in larger chunks and pre-allocate buffer
my $buffer;
my $line_count = 0;
my $max_lines = 1_000_000; # Safety limit to prevent infinite loops

# Parse every line, chomping the \n and printing
# the line with the needed format.
# @see TypesFormatRegex
while (defined($buffer = <$fh>) && $line_count++ < $max_lines) {
    chomp $buffer;
    # Skip empty lines early
    next if $buffer =~ /^\s*$/;
    # Parse and print line with format
    parseAndPrintLineWithFormat($buffer);
}
# Remember to close the filehandler
close($fh);
