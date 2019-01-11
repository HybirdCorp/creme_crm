# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.creme_core.conf.urls import Swappable, swap_manager

from . import rgenerator_model_is_custom
from .views import recurrentgenerator


urlpatterns = [

]

urlpatterns += swap_manager.add_group(
    rgenerator_model_is_custom,
    Swappable(url(r'^generators[/]?$', recurrentgenerator.listview, name='recurrents__list_generators')),
    Swappable(url(r'^generator/add[/]?$',
                  recurrentgenerator.RecurrentGeneratorWizard.as_view(),
                  name='recurrents__create_generator',
                 ),
             ),
    Swappable(url(r'^generator/edit/(?P<generator_id>\d+)[/]?$',
                  recurrentgenerator.RecurrentGeneratorEdition.as_view(),
                  name='recurrents__edit_generator',
                 ),
              check_args=Swappable.INT_ID,
             ),
    Swappable(url(r'^generator/(?P<generator_id>\d+)[/]?$',
                  recurrentgenerator.RecurrentGeneratorDetail.as_view(),
                  name='recurrents__view_generator',
                 ),
              check_args=Swappable.INT_ID,
             ),
    app_name='persons',
).kept_patterns()
