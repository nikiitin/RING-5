package Scanning::RegexUtils;

use strict;
use warnings;
use Exporter 'import';

our @EXPORT_OK = qw($floatRegex $varNameRegex $confValueRegex $scalarValueRegex $commentRegex $unitRegex $complexValueRegex $summariesEntryRegex);
our %EXPORT_TAGS = (all => \@EXPORT_OK);

# Scientific Quality: Support for negative numbers, scientific notation, and standard floats.
our $floatRegex = qr/-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/;

# Gem5 Topology: Support for dots, underscores, and alphanumeric identifiers.
our $varNameRegex = qr/[\d\.\w\_]+/;

# Configuration values can include paths, numbers, and basic punctuation.
our $confValueRegex = qr/[\d\.\w\-\/\(\)\,]+/;

# Scalars are either integers or the scientific-compliant float.
our $scalarValueRegex = qr/-?\d+|$floatRegex/;

# Comments start with #
our $commentRegex = qr/#.*/;

our $unitRegex = qr/\(\w+\)/;

# Complex components (Distributions/Histograms):
# e.g., "10  5.23%  95.0%"
# Handles multiple spaces and integers/floats in the percentage fields.
our $complexValueRegex = qr/-?\d+\s+$floatRegex%\s+$floatRegex%/;

our $summariesEntryRegex = qr/::(samples|mean|gmean|stdev|total)/;

1;
