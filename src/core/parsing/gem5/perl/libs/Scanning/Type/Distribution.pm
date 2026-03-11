package Scanning::Type::Distribution;

use strict;
use warnings;
use Exporter 'import';
use Scanning::RegexUtils qw(:all);

our @EXPORT_OK = qw($distRegex $distEntryRegex);

# Distribution components regexes
# | ::5
my $distEntryNumericRegex = qr/::-?\d+/;
my $distEntryOverflowRegex = qr/::overflows/;
my $distEntryUnderflowRegex = qr/::underflows/;
our $distEntryRegex = qr/($distEntryNumericRegex|$distEntryOverflowRegex|$distEntryUnderflowRegex)/;

# | name::distEntryNumRegex  value  perc  cumm.percent  # Comment (unit) |
our $distRegex = qr/^$varNameRegex$distEntryRegex\s+$complexValueRegex\s*$commentRegex?\s*$unitRegex?$/;

1;
