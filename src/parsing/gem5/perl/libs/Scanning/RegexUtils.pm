package Scanning::RegexUtils;

use strict;
use warnings;
use Exporter 'import';
our @EXPORT_OK = qw($floatRegex $varNameRegex $scalarValueRegex);
our $floatRegex = qr/-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/;
our $varNameRegex = qr/[\d.\w_]+/;
our $scalarValueRegex = qr/(?:$floatRegex|[+-]?(?:nan|inf))/i;
1;
