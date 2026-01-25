package Scanning::Type::Histogram;

use strict;
use warnings;
use Exporter 'import';
use Scanning::RegexUtils qw(:all);

our @EXPORT_OK = qw($histogramRegex $histogramEntryRangeRegex);

# Histogram component regexes
our $histogramEntryRangeRegex = qr/::\d+-\d+/;
# | ::1-5 |

# | name::range1-range2  value  perc  cumm.percent  # Comment |
our $histogramRegex = qr/^$varNameRegex$histogramEntryRangeRegex\s+$complexValueRegex\s+$commentRegex?$/;

1;
