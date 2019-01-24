# -*- coding: utf-8 -*-

from os import path as os_path
from importlib import import_module
import re

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
# from django.utils.importlib import import_module
from django.utils.http import urlquote

from . import settings as media_settings
from .settings import (GLOBAL_MEDIA_DIRS, PRODUCTION_MEDIA_URL,
    IGNORE_APP_MEDIA_DIRS, MEDIA_GENERATORS, DEV_MEDIA_URL,
    GENERATED_MEDIA_NAMES_MODULE)

try:
    NAMES = import_module(GENERATED_MEDIA_NAMES_MODULE).NAMES
except (ImportError, AttributeError):
    NAMES = None

_backends_cache = {}
_media_dirs_cache = []

_generators_cache = []
_generated_names = {}
_backend_mapping = {}


def _load_generators():
    if not _generators_cache:
        for name in MEDIA_GENERATORS:
            backend = load_backend(name)()
            _generators_cache.append(backend)

    return _generators_cache


def _refresh_dev_names():
    _generated_names.clear()
    _backend_mapping.clear()

    for backend in _load_generators():
        for key, url, hash in backend.get_dev_output_names():
            versioned_url = urlquote(url)

            if hash:
                versioned_url += '?version=' + hash

            _generated_names.setdefault(key, [])
            _generated_names[key].append(versioned_url)
            _backend_mapping[url] = backend


class _MatchNothing:
    def match(self, content):
        return False


def prepare_patterns(patterns, setting_name):
    """Helper function for patter-matching settings."""
    if isinstance(patterns, str):
        patterns = (patterns,)

    if not patterns:
        return _MatchNothing()

    # First validate each pattern individually
    for pattern in patterns:
        try:
            re.compile(pattern, re.U)
        except re.error:
            raise ValueError('Pattern "{}" cannot be compiled in {}'.format(pattern, setting_name))

    # Now return a combined pattern
    return re.compile('^(' + ')$|^('.join(patterns) + ')$', re.U)


def get_production_mapping():
    if NAMES is None:
        raise ImportError(
            'Could not import {}. This file is needed for production mode. Please '
            'run manage.py generatemedia to create it.'.format(
                        GENERATED_MEDIA_NAMES_MODULE
        ))

    return NAMES


def get_media_mapping():
    return _generated_names if media_settings.MEDIA_DEV_MODE else get_production_mapping()


def get_media_url_mapping():
    base_url = DEV_MEDIA_URL if media_settings.MEDIA_DEV_MODE else PRODUCTION_MEDIA_URL
    mapping = {}

    for key, value in get_media_mapping().items():
        if isinstance(value, str):
            value = (value,)
        mapping[key] = [base_url + url for url in value]

    return mapping


def media_urls(key, refresh=False):
    if media_settings.MEDIA_DEV_MODE:
        if refresh:
            _refresh_dev_names()

        return [DEV_MEDIA_URL + url for url in _generated_names[key]]

    return [PRODUCTION_MEDIA_URL + get_production_mapping()[key]]


def media_url(key, refresh=False):
    urls = media_urls(key, refresh=refresh)
    if len(urls) == 1:
        return urls[0]

    raise ValueError('media_url() only works with URLs that contain exactly '
                     'one file. Use media_urls() (or {% include_media %} in templates) instead.')


# def get_media_dirs():
#     if not _media_dirs_cache:
#         media_dirs = GLOBAL_MEDIA_DIRS[:]
#         for app in settings.INSTALLED_APPS:
#             if app in IGNORE_APP_MEDIA_DIRS:
#                 continue
#             for name in (u'static', u'media'):
#                 app_root = os.path.dirname(import_module(app).__file__)
#                 media_dirs.append(os.path.join(app_root, name))
#         _media_dirs_cache.extend(media_dirs)
#     return _media_dirs_cache
def get_media_dirs():
    if not _media_dirs_cache:
        if not apps.ready:
            apps.populate(settings.INSTALLED_APPS)

        media_dirs = GLOBAL_MEDIA_DIRS[:]
        for app in apps.get_app_configs():
            if app.name in IGNORE_APP_MEDIA_DIRS:
                continue

            media_dirs.append(os_path.join(app.path, u'static'))
            media_dirs.append(os_path.join(app.path, u'media'))

        _media_dirs_cache.extend(media_dirs)

    return _media_dirs_cache


def find_file(name, media_dirs=None):
    if media_dirs is None:
        media_dirs = get_media_dirs()

    for root in media_dirs:
        # path = os.path.normpath(os.path.join(root, name))
        path = os_path.normpath(os_path.join(root, name))
        # if os.path.isfile(path):
        if os_path.isfile(path):
            return path


# TODO: remove & use "with" directly ?
def read_text_file(path):
    # fp = open(path, 'r')
    # output = fp.read()
    # fp.close()
    # # return output.decode('utf8')
    # return output
    with open(path, 'r', encoding='utf-8') as fp:
        return fp.read()


def load_backend(backend):
    if backend not in _backends_cache:
        module_name, func_name = backend.rsplit('.', 1)  # TODO: useful ?
        _backends_cache[backend] = _load_backend(backend)

    return _backends_cache[backend]


def _load_backend(path):
    module_name, attr_name = path.rsplit('.', 1)

    try:
        mod = import_module(module_name)
    except (ImportError, ValueError) as e:
        raise ImproperlyConfigured('Error importing backend module {}: "{}"'.format(module_name, e))

    try:
        return getattr(mod, attr_name)
    except AttributeError:
        raise ImproperlyConfigured('Module "{}" does not define a "{}" backend'.format(module_name, attr_name))
