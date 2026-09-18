# Convert all PNG images of a folder into greyscale PNG.

from argparse import ArgumentParser
from glob import glob

from PIL import Image

parser = ArgumentParser()
parser.add_argument(
    '-x', '--exclude',
    dest='excluded', action='append', default=[],
    help='exclude this file.', metavar='FILE',
)
parser.add_argument(
    'files',
    metavar='FILE', nargs='*',
    help='process this file(s). If not file is given, the *.png '
         'files of the current directory are used',
)

args = parser.parse_args()
excluded = {*args.excluded}
file_names = args.files

if file_names:
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
    print('Some excluded files were not used :', ', '.join(excluded))
