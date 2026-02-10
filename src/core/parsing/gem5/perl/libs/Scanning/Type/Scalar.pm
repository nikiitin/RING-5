package Scanning::Type::Scalar;

use strict;
use warnings;
use Exporter 'import';
use Scanning::RegexUtils qw(:all);

our @EXPORT_OK = qw($scalarRegex);

# | name  value  comment |
our $scalarRegex = qr/^$varNameRegex\s+$scalarValueRegex$commentRegex$/;

1;
