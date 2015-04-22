# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from . import rgenerator_model_is_custom


urlpatterns = patterns('creme.recurrents.views',
    (r'^$', 'portal.portal'),
)

if not rgenerator_model_is_custom():
    #TODO: give the forms to the view constructor (this view could not be used with other forms...)
    from .forms.recurrentgenerator import RecurrentGeneratorCreateForm
    from .views.recurrentgenerator import RecurrentGeneratorWizard

    urlpatterns += patterns('creme.recurrents.views.recurrentgenerator',
        url(r'^generators$',    'listview', name='recurrents__list_generators'),
        url(r'^generator/add$',
            #TODO NB: the second form is dynamically replaced
            RecurrentGeneratorWizard.as_view([RecurrentGeneratorCreateForm, RecurrentGeneratorCreateForm]),
            name='recurrents__create_generator',
           ),
        url(r'^generator/edit/(?P<generator_id>\d+)$', 'edit',       name='recurrents__edit_generator'),
        url(r'^generator/(?P<generator_id>\d+)$',      'detailview', name='recurrents__view_generator'),
    )
