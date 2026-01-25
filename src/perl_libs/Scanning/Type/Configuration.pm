package Scanning::Type::Configuration;

use strict;
use warnings;
use Exporter 'import';
use Scanning::RegexUtils qw(:all);

our @EXPORT_OK = qw($confRegex);

# | name=value |
our $confRegex = qr/^$varNameRegex=$confValueRegex$/;

1;
