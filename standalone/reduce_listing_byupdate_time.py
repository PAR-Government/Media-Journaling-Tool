# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
from __future__ import print_function
import argparse

"""
Little tool to find images from one listing that exist in a master listing with time stamps
such that time stamp is less than the provided time.
"""

import os
import re

import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def parse_date(datestring):
    from datetime import datetime
    return datetime.strptime(datestring, '%Y-%m-%d %H:%M:%S')

prog = re.compile('\s+')

def fix_line(line):
    return prog.split(line)

def tuple_from_line(line):
    elements = fix_line(line.strip())
    return elements[-1], parse_date(elements[0] + ' ' + elements[1])

def load_masterset(filename):
    with open(filename,'r') as fp:
        return { t[0]:t[1] for t in  [tuple_from_line(line) for line in fp.readlines()]}

def load_journals(filename,postfix=''):
    with open(filename, 'r') as fp:
        return [line.strip() + postfix for line in fp.readlines()]

def write_matches(masterset_filename, journals_filename, time):
    matchtime = parse_date(time)
    masterset = load_masterset(masterset_filename)
    journals_list = load_journals(journals_filename,postfix='.tgz')
    for journal in journals_list:
        if journal not in masterset:
            eprint(journal)
        else:
            ingest_time = masterset[journal]
            if ingest_time < matchtime:
                print (journal)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--masterset', help='Master set listing from AWS (ls)', required=True)
    parser.add_argument('--journals',help='journal IDs to check', required=True)
    parser.add_argument('--timestamp',help='time for which journals have not be updated since', required=True)
    args = parser.parse_args()
    write_matches(args.masterset,args.journals,args.timestamp)

if __name__ == '__main__':
    main()