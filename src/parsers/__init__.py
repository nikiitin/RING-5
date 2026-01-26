"""
RING-5 Parsers Module

This module contains all parsing-related code for gem5 statistics files.

Architecture:
- perl/           : Perl scripts and libraries for low-level stats parsing
  - fileParser.pl : Parses individual stats file using filter regexes
  - statsScanner.pl : Scans stats file to discover variable types
  - libs/         : Perl modules (TypesFormatRegex, Scanning::*)
"""
