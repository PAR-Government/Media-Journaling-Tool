# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

from subprocess import Popen, PIPE

with open('foo.txt','w') as fp:
    lines = set([line.strip() for line in fp.readlines()])

p = Popen(['aws', 's3', 'ls', 's3://medifor/par/journal/ingested'],stdout=PIPE,stderr=PIPE)
stdout, stderr = p.communicate()
for line in stdout:
    print line
    if line in lines:
        lines.remove(line)
print lines

