package Scanning::Type::Summary;

use strict;
use warnings;
use Exporter 'import';
use Scanning::RegexUtils qw(:all);

our @EXPORT_OK = qw($summaryRegex);

# | name::summVar  value  # Comment |
our $summaryRegex = qr/^$varNameRegex$summariesEntryRegex\s+$scalarValueRegex\s+$commentRegex?$/;

1;
