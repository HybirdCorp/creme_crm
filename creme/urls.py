# -*- coding: utf-8 -*-

import logging
# from os.path import join
from pathlib import Path

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import render
from django.urls import include, re_path
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.static import serve

from creme.creme_core.apps import creme_app_configs
from creme.creme_core.views.exceptions import permission_denied

logger = logging.getLogger(__name__)
handler403 = permission_denied


def __prepare_static_url():
    static_url = settings.PRODUCTION_MEDIA_URL

    if not isinstance(static_url, str):
        raise ImproperlyConfigured(
            f"settings.PRODUCTION_MEDIA_URL must be a string ; "
            f"it's currently a {type(static_url)}."
        )

    if not static_url.startswith('/') or not static_url.endswith('/'):
        raise ImproperlyConfigured(
            f'settings.PRODUCTION_MEDIA_URL must starts & end with "/" '
            f'(current value is "{static_url}").'
        )

    return static_url[1:]


urlpatterns = [
    re_path(
        r'^creme_login[/]?$',
        auth_views.LoginView.as_view(template_name='authent/creme_login.html'),
        name='creme_login',
    ),
    re_path(
        r'^creme_logout[/]?$',
        auth_views.logout_then_login,
        name='creme_logout',
    ),
    re_path(
        r'^creme_about[/]?$',
        render,
        {'template_name': 'about/about.html'},
        name='creme_about',
    ),

    # re_path(r'^site_media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

    # TODO: remove this line when the Rich Text Editor is generated like other static media
    re_path(
        # r'^tiny_mce/(?P<path>.*)$', serve,
        # {'document_root': join(settings.MEDIA_ROOT, 'tiny_mce')}
        r'^tiny_mce/(?P<path>.*)$', xframe_options_sameorigin(serve),
        {'document_root': Path(__file__).resolve().parent / 'media' / 'tiny_mce'},
    ),

    # NB: in production, you can configure your web server to statically serve
    #     the files in the directory 'media/static/' (and so the following line is never used).
    re_path(
        # r'^static_media/(?P<path>.*)$',
        rf'^{__prepare_static_url()}(?P<path>.*)$',
        serve,
        # {'document_root': settings.GENERATED_MEDIA_DIR},
        {'document_root': settings.STATIC_ROOT},
    ),
]

for app_config in creme_app_configs():
    app_name = app_config.name

    try:
        included = include(app_name + '.urls')
    except ImportError as e:
        if e.args and 'urls' in e.args[0]:
            logger.warning(f'The app "{app_name}" has no "urls" module.')
        else:  # It seems a annoying ImportError make the existing 'urls' module to be imported.
            raise
    else:
        urlpatterns.append(re_path(r'^' + app_config.url_root, included))
