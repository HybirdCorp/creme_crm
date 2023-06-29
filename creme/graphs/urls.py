from django.urls import re_path

from creme.creme_core.conf.urls import Swappable, swap_manager

from . import graph_model_is_custom
from .views import graph, root_node

urlpatterns = [
    re_path(
        r'^graph/(?P<graph_id>\d+)/relation_types/add[/]?$',
        graph.RelationTypesAdding.as_view(),
        name='graphs__add_rtypes',
    ),
    re_path(
        r'^graph/(?P<graph_id>\d+)/relation_type/delete[/]?$',
        graph.RelationTypeRemoving.as_view(),
        name='graphs__remove_rtype',
    ),

    re_path(
        r'^graph/(?P<graph_id>\d+)/roots/add[/]?$',
        root_node.RootNodesAdding.as_view(),
        name='graphs__add_roots',
    ),
    re_path(
        r'^root/edit/(?P<root_id>\d+)[/]?',
        root_node.RootNodeEdition.as_view(),
        name='graphs__edit_root',
    ),
    re_path(
        r'^root/delete[/]?$',
        root_node.RootNodeDeletion.as_view(),
        name='graphs__remove_root',
    ),

    *swap_manager.add_group(
        graph_model_is_custom,
        Swappable(
            re_path(
                r'^graphs[/]?$',
                graph.GraphsList.as_view(),
                name='graphs__list_graphs',
            ),
        ),
        Swappable(
            re_path(
                r'^graph/add[/]?$',
                graph.GraphCreation.as_view(),
                name='graphs__create_graph',
            ),
        ),
        Swappable(
            re_path(
                r'^graph/edit/(?P<graph_id>\d+)[/]?$',
                graph.GraphEdition.as_view(),
                name='graphs__edit_graph',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^graph/(?P<graph_id>\d+)[/]?$',
                graph.GraphDetail.as_view(),
                name='graphs__view_graph',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='graphs',
    ).kept_patterns(),
]
