from hashlib import sha1
from mimetypes import guess_type
import os

from django.conf import settings

from mediagenerator.base import Generator
from mediagenerator.utils import get_media_dirs, find_file, prepare_patterns

COPY_MEDIA_FILETYPES = getattr(settings, 'COPY_MEDIA_FILETYPES', {
    'gif', 'jpg', 'jpeg', 'png', 'svg', 'svgz', 'ico', 'swf',
    'ttf', 'otf', 'eot', 'woff',
})
IGNORE_PATTERN = prepare_patterns(getattr(settings, 'IGNORE_MEDIA_COPY_PATTERNS', ()),
                                  'IGNORE_MEDIA_COPY_PATTERNS')


class CopyFiles(Generator):
    def get_dev_output(self, name):
        path = find_file(name)

        with open(path, 'rb') as fp:
            content = fp.read()

        mimetype = guess_type(path)[0]

        return content, mimetype

    def get_dev_output_names(self):
        media_files = {}
        for root in get_media_dirs():
            self.collect_copyable_files(media_files, root)

        for name, source in media_files.items():
            with open(source, 'rb') as fp:
                hash = sha1(fp.read()).hexdigest()

            yield name, name, hash

    def collect_copyable_files(self, media_files, root):
        for root_path, dirs, files in os.walk(root, followlinks=True):
            for file in files:
                ext = os.path.splitext(file)[1].lstrip('.')
                path = os.path.join(root_path, file)
                media_path = path[len(root) + 1:].replace(os.sep, '/')
                if ext in COPY_MEDIA_FILETYPES and not IGNORE_PATTERN.match(media_path):
                    media_files[media_path] = path
