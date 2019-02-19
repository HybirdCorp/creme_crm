# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.urls import re_path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import render
from django.views.static import serve

from creme.creme_core.apps import creme_app_configs
from creme.creme_core.views.exceptions import permission_denied

logger = logging.getLogger(__name__)

# handler403 = 'creme.creme_core.views.exceptions.permission_denied'
handler403 = permission_denied

urlpatterns = [
    re_path(r'^creme_login[/]?$',  auth_views.LoginView.as_view(template_name='authent/creme_login.html'), name='creme_login'),
    re_path(r'^creme_logout[/]?$', auth_views.logout_then_login, name='creme_logout'),
    re_path(r'^creme_about[/]?$',  render, {'template_name': 'about/about.html'}, name='creme_about'),

    re_path(r'^site_media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    # NB: in production, configure your web server to statically serve the files in the 'media/static/' dir
    #     (and so comment the following line)
    re_path(r'^static_media/(?P<path>.*)$', serve, {'document_root': settings.GENERATED_MEDIA_DIR}),
]

for app_config in creme_app_configs():
    app_name = app_config.name

    try:
        included = include(app_name + '.urls')
    except ImportError as e:
        if e.args and 'urls' in e.args[0]:
            logger.warning('The app "{}" has no "urls" module.'.format(app_name))
        else:  # It seems a annoying ImportError make the existing 'urls' module to be imported.
            raise
    else:
        urlpatterns.append(re_path(r'^' + app_config.url_root, included))
