package Scanning::RegexUtils;

use strict;
use warnings;
use Exporter 'import';

our @EXPORT_OK = qw($floatRegex $varNameRegex $confValueRegex $scalarValueRegex $commentRegex $complexValueRegex $summariesEntryRegex);
our %EXPORT_TAGS = (all => \@EXPORT_OK);

# Simple components regexes
our $floatRegex = qr/\d+\.\d+/;
our $varNameRegex = qr/[\d\.\w]+/;
our $confValueRegex = qr/[\d\.\w\-\/\(\)\,]+/;
our $scalarValueRegex = qr/\d+|$floatRegex/;
our $commentRegex = qr/#.*|\(Unspecified\)\s*/;

# Complex components regexes
#  Val perc   cumm. percent
# | 5  32.5%  63.4% |
our $complexValueRegex = qr/\d+\s+$floatRegex%\s+$floatRegex%/;
our $summariesEntryRegex = qr/::(samples|mean|gmean|stdev|total)/;

1;
