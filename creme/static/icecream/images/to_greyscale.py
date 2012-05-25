# -*- coding: utf-8 -*-

# Convert all PNG images of a folder into greyscale PNG.

from glob import glob
from optparse import OptionParser

from PIL import Image


parser = OptionParser()
parser.add_option("-x", "--exclude", dest="excluded", action='append', default=[],
                  help="exclude this file.", metavar="FILE"
                 )
options, args = parser.parse_args()
excluded = set(options.excluded)

if args:
    file_names = args

    if excluded:
        parser.error("'-x/--exclude' option is not compatible with arguments.")
else:
    file_names = glob('*.png')

for file_name in file_names:
    if file_name in excluded:
        excluded.remove(file_name)
    else:
        Image.open(file_name).convert('LA').save(file_name)

if excluded:
    print 'Some excluded files were not used :', ', '.join(excluded)
