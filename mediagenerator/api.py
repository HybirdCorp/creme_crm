from collections import defaultdict, OrderedDict
import os
import shutil
import logging

from django.utils.http import urlquote

from . import settings, utils
from .settings import GENERATED_MEDIA_DIR, GENERATED_MEDIA_NAMES_FILE, MEDIA_GENERATORS
from .utils import load_backend

# HACK: by Hybird (we should pass it as argument -- & modify all the API)
global_errors = defaultdict(OrderedDict)
# logger = logging.getLogger(__name__)
logger = logging.getLogger('mediagenerator')


def generate_media():
    if os.path.exists(GENERATED_MEDIA_DIR):
        shutil.rmtree(GENERATED_MEDIA_DIR)

    # This will make media_url() generate production URLs
    was_dev_mode = settings.MEDIA_DEV_MODE
    settings.MEDIA_DEV_MODE = False

    utils.NAMES = {}

    for backend_name in MEDIA_GENERATORS:
        backend = load_backend(backend_name)()

        for key, url, content in backend.get_output():
            version = backend.generate_version(key, url, content)
            if version:
                base, ext = os.path.splitext(url)
                url = '%s-%s%s' % (base, version, ext)

            path = os.path.join(GENERATED_MEDIA_DIR, url)

            parent = os.path.dirname(path)
            if not os.path.exists(parent):
                os.makedirs(parent)

            if isinstance(content, unicode):
                content = content.encode('utf8')

            with open(path, 'wb') as fp:
                fp.write(content)

            utils.NAMES[key] = urlquote(url)

    settings.MEDIA_DEV_MODE = was_dev_mode

    # Generate a module with media file name mappings
    with open(GENERATED_MEDIA_NAMES_FILE, 'w') as fp:
        fp.write('NAMES = %r' % utils.NAMES)

    for category, errors in global_errors.iteritems():
        # logger.warn('Error(s) in "%s"', category)

        for error in errors.itervalues():
            logger.warn('%s - %s', category, error)
