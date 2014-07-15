# -*- coding: utf-8 -*-

from imp import find_module

from django.conf.urls import patterns
from django.conf import settings

from creme.recurrents.registry import recurrent_registry

#TODO: give the forms to the view constructor (this view could not be used with other forms...)
from .forms.recurrentgenerator import RecurrentGeneratorCreateForm
from .views.recurrentgenerator import RecurrentGeneratorWizard

urlpatterns = patterns('creme.recurrents.views',
    (r'^$', 'portal.portal'),

    (r'^generators$',                             'recurrentgenerator.listview'),
    #(r'^generator/add$',                          'recurrentgenerator.add'),
    (r'^generator/add$',                          RecurrentGeneratorWizard.as_view([RecurrentGeneratorCreateForm, RecurrentGeneratorCreateForm])), #TODO NB: the second form blbla
    (r'^generator/edit/(?P<generator_id>\d+)$',   'recurrentgenerator.edit'),
    (r'^generator/(?P<generator_id>\d+)$',        'recurrentgenerator.detailview'),
)


#TODO: do it lazily + use creme_core tools
for app in settings.INSTALLED_APPS:
    try:
        find_module("recurrents_register", __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
    except ImportError:
        # there is no recurrents_register.py in the app, skip it
        continue

    recurrents_import = __import__("%s.recurrents_register" % app , globals(), locals(), ['to_register'], -1)
    recurrent_registry.register(*recurrents_import.to_register)
