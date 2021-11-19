# -*- coding: utf-8 -*-

import re
from importlib import import_module
# from urllib.parse import quote
from os import path as os_path

# from django.utils.http import urlquote
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .settings import (  # MEDIA_GENERATORS
    GENERATED_MEDIA_NAMES_MODULE,
    GLOBAL_MEDIA_DIRS,
    IGNORE_APP_MEDIA_DIRS,
    PRODUCTION_MEDIA_URL,
)

try:
    NAMES = import_module(GENERATED_MEDIA_NAMES_MODULE).NAMES
except (ImportError, AttributeError):
    NAMES = None

_backends_cache: dict = {}
_media_dirs_cache: list = []

_generators_cache: list = []
_generated_names: dict = {}
_backend_mapping: dict = {}


# def _load_generators():
#     if not _generators_cache:
#         for name in MEDIA_GENERATORS:
#             backend = load_backend(name)()
#             _generators_cache.append(backend)
#
#     return _generators_cache


# def _refresh_dev_names():
#     _generated_names.clear()
#     _backend_mapping.clear()
#
#     for backend in _load_generators():
#         for key, url, hash in backend.get_dev_output_names():
#             # versioned_url = urlquote(url)
#             versioned_url = quote(url)
#
#             if hash:
#                 versioned_url += '?version=' + hash
#
#             _generated_names.setdefault(key, [])
#             _generated_names[key].append(versioned_url)
#             _backend_mapping[url] = backend


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
            raise ValueError(f'Pattern "{pattern}" cannot be compiled in {setting_name}')

    # Now return a combined pattern
    return re.compile('^(' + ')$|^('.join(patterns) + ')$', re.U)


def get_production_mapping():
    if NAMES is None:
        raise ImportError(
            f'Could not import {GENERATED_MEDIA_NAMES_MODULE}. '
            f'This file is needed for production mode. '
            f'Please run manage.py generatemedia to create it.'
        )

    return NAMES


def get_media_mapping():
    return get_production_mapping()  # TODO: inline ?


def get_media_url_mapping():
    base_url = PRODUCTION_MEDIA_URL
    mapping = {}

    for key, value in get_media_mapping().items():
        if isinstance(value, str):
            value = (value,)
        mapping[key] = [base_url + url for url in value]

    return mapping


def media_urls(key, refresh=False):
    return [PRODUCTION_MEDIA_URL + get_production_mapping()[key]]


def media_url(key, refresh=False):
    urls = media_urls(key, refresh=refresh)
    if len(urls) == 1:
        return urls[0]

    raise ValueError(
        'media_url() only works with URLs that contain exactly '
        'one file. Use media_urls() (or {% include_media %} in templates) instead.'
    )


def get_media_dirs():
    if not _media_dirs_cache:
        if not apps.ready:
            apps.populate(settings.INSTALLED_APPS)

        media_dirs = GLOBAL_MEDIA_DIRS[:]
        for app in apps.get_app_configs():
            if app.name in IGNORE_APP_MEDIA_DIRS:
                continue

            media_dirs.append(os_path.join(app.path, 'static'))
            media_dirs.append(os_path.join(app.path, 'media'))

        _media_dirs_cache.extend(media_dirs)

    return _media_dirs_cache


def find_file(name, media_dirs=None):
    if media_dirs is None:
        media_dirs = get_media_dirs()

    for root in media_dirs:
        path = os_path.normpath(os_path.join(root, name))
        if os_path.isfile(path):
            return path


# TODO: remove & use "with" directly ?
def read_text_file(path):
    with open(path, 'r', encoding='utf-8') as fp:
        return fp.read()


def load_backend(backend):
    if backend not in _backends_cache:
        _backends_cache[backend] = _load_backend(backend)

    return _backends_cache[backend]


def _load_backend(path):
    module_name, attr_name = path.rsplit('.', 1)

    try:
        mod = import_module(module_name)
    except (ImportError, ValueError) as e:
        raise ImproperlyConfigured(
            f'Error importing backend module {module_name}: "{e}"'
        )

    try:
        return getattr(mod, attr_name)
    except AttributeError:
        raise ImproperlyConfigured(
            f'Module "{module_name}" does not define a "{attr_name}" backend'
        )
