from django.urls import re_path

from creme.creme_core.conf.urls import Swappable, swap_manager

from . import rgenerator_model_is_custom
from .views import recurrentgenerator

urlpatterns = [
    *swap_manager.add_group(
        rgenerator_model_is_custom,
        Swappable(
            re_path(
                r'^generators[/]?$',
                recurrentgenerator.RecurrentGeneratorsList.as_view(),
                name='recurrents__list_generators',
            ),
        ),
        Swappable(
            re_path(
                r'^generator/add[/]?$',
                recurrentgenerator.RecurrentGeneratorWizard.as_view(),
                name='recurrents__create_generator',
            ),
        ),
        Swappable(
            re_path(
                r'^generator/edit/(?P<generator_id>\d+)[/]?$',
                recurrentgenerator.RecurrentGeneratorEdition.as_view(),
                name='recurrents__edit_generator',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^generator/(?P<generator_id>\d+)[/]?$',
                recurrentgenerator.RecurrentGeneratorDetail.as_view(),
                name='recurrents__view_generator',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='persons',
    ).kept_patterns(),
]
