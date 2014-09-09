# -*- coding: utf-8 -*-

from django.conf.urls import patterns

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
