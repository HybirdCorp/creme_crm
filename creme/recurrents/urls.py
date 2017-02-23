# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import rgenerator_model_is_custom
from .views import portal


urlpatterns = [
    url(r'^$', portal.portal, name='recurrents__portal'),
]

if not rgenerator_model_is_custom():
    # TODO: give the forms to the view constructor (this view could not be used with other forms...)
    from .forms.recurrentgenerator import RecurrentGeneratorCreateForm
    from .views import recurrentgenerator

    urlpatterns += [
        url(r'^generators$', recurrentgenerator.listview, name='recurrents__list_generators'),
        url(r'^generator/add$',
            # NB: the second form is dynamically replaced
            recurrentgenerator.RecurrentGeneratorWizard.as_view([RecurrentGeneratorCreateForm,
                                                                 RecurrentGeneratorCreateForm,
                                                                ]
                                                               ),
            name='recurrents__create_generator',
           ),
        url(r'^generator/edit/(?P<generator_id>\d+)$', recurrentgenerator.edit,       name='recurrents__edit_generator'),
        url(r'^generator/(?P<generator_id>\d+)$',      recurrentgenerator.detailview, name='recurrents__view_generator'),
    ]
