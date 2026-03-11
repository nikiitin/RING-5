package Scanning::Type::Scalar;

use strict;
use warnings;
use Exporter 'import';
use Scanning::RegexUtils qw(:all);

our @EXPORT_OK = qw($scalarRegex);

# | name  value  comment (unit) |
our $scalarRegex = qr/^$varNameRegex\s+$scalarValueRegex\s*$commentRegex?\s*$unitRegex?$/;

1;
