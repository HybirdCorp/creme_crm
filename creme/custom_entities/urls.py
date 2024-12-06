from django.urls import re_path

from creme.custom_entities import views

urlpatterns = [
    re_path(
        r'^type_(?P<type_id>\d+)/list[/]?$',
        views.CustomEntitiesList.as_view(),
        name='custom_entities__list_custom_entities',
    ),
    re_path(
        r'^type_(?P<type_id>\d+)/add[/]?$',
        views.CustomEntityCreation.as_view(),
        name='custom_entities__create_custom_entity',
    ),
    re_path(
        r'^type_(?P<type_id>\d+)/edit/(?P<entity_id>\d+)[/]?$',
        views.CustomEntityEdition.as_view(),
        name='custom_entities__edit_custom_entity',
    ),
    re_path(
        r'^type_(?P<type_id>\d+)/(?P<entity_id>\d+)[/]?$',
        views.CustomEntityDetail.as_view(),
        name='custom_entities__view_custom_entity',
    ),
]
