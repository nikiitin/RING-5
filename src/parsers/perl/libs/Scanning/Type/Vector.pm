package Scanning::Type::Vector;

use strict;
use warnings;
use Exporter 'import';
use Scanning::RegexUtils qw(:all);

our @EXPORT_OK = qw($vectorRegex $vectorEntryRegex);

# Vector components regexes
# Summaries already included in this regex (total)
# | ::Name | ::Total
our $vectorEntryRegex = qr/::[\w\.]+/;

# | name::vectorEntryName  value  perc  cumm.percent  # Comment
# OR
# | name::vectorEntryName  value  # Comment
our $vectorRegex = qr/^$varNameRegex$vectorEntryRegex\s+(?:$complexValueRegex|$scalarValueRegex)$commentRegex$/;

1;
