# -*- coding: utf-8 -*-

import logging

# from django.apps import apps
from django.conf import settings
from django.conf.urls import url, include
from django.contrib.auth.views import login, logout_then_login
from django.views.static import serve

# from creme.creme_core.registry import creme_registry
from creme.creme_core.apps import creme_app_configs

logger = logging.getLogger(__name__)
handler500 = 'creme.creme_core.views.exceptions.server_error'

urlpatterns = [
    url(r'^creme_login[/]?$',  login, {'template_name': 'authent/creme_login.html'}, name='creme_login'),
    url(r'^creme_logout[/]?$', logout_then_login, name='creme_logout'),

    url(r'^site_media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    # NB: in production, configure your web server to statically serve the files in the 'media/static/' dir
    #     (and so comment the following line)
    url(r'^static_media/(?P<path>.*)$', serve, {'document_root': settings.GENERATED_MEDIA_DIR}),
]

# for creme_app in creme_registry.iter_apps():
#     app_label = creme_app.name  # eg: 'persons'
#     regex_url = r'^' if app_label == 'creme_core' else r'^%s/' % app_label
#     app_name = apps.get_app_config(app_label).name  # eg: 'creme.persons'
#
#     urlpatterns.append(url(regex_url, include('%s.urls' % app_name)))
for app_config in creme_app_configs():
    app_name = app_config.name

    try:
        included = include(app_name + '.urls')
    except ImportError:
        logger.warn('The app "{}" has no "urls" module.'.format(app_name))
    else:
        urlpatterns.append(url(r'^' + app_config.url_root, included))
