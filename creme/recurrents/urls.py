# -*- coding: utf-8 -*-

from imp import find_module

from django.conf.urls.defaults import patterns
from django.conf import settings

from recurrents.registry import recurrent_registry


urlpatterns = patterns('recurrents.views',
    (r'^$', 'portal.portal'),

    (r'^generators$',                             'recurrentgenerator.listview'),
    (r'^generator/add$',                          'recurrentgenerator.add'),
    (r'^generator/edit/(?P<generator_id>\d+)$',   'recurrentgenerator.edit'),
    (r'^generator/(?P<generator_id>\d+)$',        'recurrentgenerator.detailview'),
)


for app in settings.INSTALLED_APPS:
    try:
        find_module("recurrents_register", __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
    except ImportError, e:
        # there is no app creme_config.py, skip it
        continue

    recurrents_import = __import__("%s.recurrents_register" % app , globals(), locals(), ['to_register'], -1)
    recurrent_registry.register(*recurrents_import.to_register)
