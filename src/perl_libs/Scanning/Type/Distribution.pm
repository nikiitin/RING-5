package Scanning::Type::Distribution;

use strict;
use warnings;
use Exporter 'import';
use Scanning::RegexUtils qw(:all);

our @EXPORT_OK = qw($distRegex $distEntry);

# Distribution components regexes
# | ::5
my $distEntryNumericRegex = qr/::-?\d+/;
my $distEntryOverflowRegex = qr/::overflows/;
my $distEntryUnderflowRegex = qr/::underflows/;
our $distEntry = qr/($distEntryNumericRegex|$distEntryOverflowRegex|$distEntryUnderflowRegex)/;

# | name::distEntryNumRegex  value  perc  cumm.percent  # Comment |
our $distRegex = qr/^$varNameRegex$distEntry\s+$complexValueRegex\s+$commentRegex?$/;

1;
