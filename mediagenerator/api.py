import logging
import os
import shutil
from collections import OrderedDict, defaultdict
from urllib.parse import quote

from django.conf import settings

from . import utils
from .settings import GENERATED_MEDIA_NAMES_FILE, MEDIA_GENERATORS
from .utils import load_backend

# HACK: by Hybird (we should pass it as argument -- & modify all the API)
global_errors = defaultdict(OrderedDict)
logger = logging.getLogger('mediagenerator')


def generate_media():
    if hasattr(settings, 'GENERATED_MEDIA_DIR'):
        from django.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured(
            'The setting "GENERATED_MEDIA_DIR" is not used anymore ; '
            'define "STATIC_ROOT" instead.'
        )

    STATIC_ROOT = settings.STATIC_ROOT

    if os.path.exists(STATIC_ROOT):
        shutil.rmtree(STATIC_ROOT)

    utils.NAMES = {}

    for backend_name in MEDIA_GENERATORS:
        backend = load_backend(backend_name)()

        for key, url, content in backend.get_output():
            version = backend.generate_version(key, url, content)
            if version:
                base, ext = os.path.splitext(url)
                url = f'{base}-{version}{ext}'

            path = os.path.join(STATIC_ROOT, url)

            parent = os.path.dirname(path)
            if not os.path.exists(parent):
                os.makedirs(parent)

            if isinstance(content, str):
                content = content.encode('utf8')

            with open(path, 'wb') as fp:
                fp.write(content)

            utils.NAMES[key] = quote(url)

    # Generate a module with media file name mappings
    with open(GENERATED_MEDIA_NAMES_FILE, 'w') as fp:
        fp.write('NAMES = %r' % utils.NAMES)

    for category, errors in global_errors.items():
        for error in errors.values():
            logger.warning('%s - %s', category, error)
