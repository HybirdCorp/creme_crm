# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.creme_core.conf.urls import Swappable, swap_manager

from . import graph_model_is_custom
from .views import graph, root_node


urlpatterns = [
    url(r'^graph/(?P<graph_id>\d+)/png[/]?$', graph.dl_png, name='graphs__dl_image'),

    url(r'^graph/(?P<graph_id>\d+)/relation_types/add[/]?$',   graph.RelationTypesAdding.as_view(), name='graphs__add_rtypes'),
    url(r'^graph/(?P<graph_id>\d+)/relation_type/delete[/]?$', graph.delete_relation_type,          name='graphs__remove_rtype'),

    url(r'^graph/(?P<graph_id>\d+)/roots/add[/]?$', root_node.RootNodesAdding.as_view(), name='graphs__add_roots'),
    url(r'^root/edit/(?P<root_id>\d+)[/]?',         root_node.RootNodeEdition.as_view(), name='graphs__edit_root'),
    url(r'^root/delete[/]?$',                       root_node.delete,                    name='graphs__remove_root'),
]

urlpatterns += swap_manager.add_group(
    graph_model_is_custom,
    Swappable(url(r'^graphs[/]?$',                       graph.listview,                name='graphs__list_graphs')),
    Swappable(url(r'^graph/add[/]?$',                    graph.GraphCreation.as_view(), name='graphs__create_graph')),
    Swappable(url(r'^graph/edit/(?P<graph_id>\d+)[/]?$', graph.GraphEdition.as_view(),  name='graphs__edit_graph'), check_args=Swappable.INT_ID),
    Swappable(url(r'^graph/(?P<graph_id>\d+)[/]?$',      graph.GraphDetail.as_view(),   name='graphs__view_graph'), check_args=Swappable.INT_ID),
    app_name='graphs',
).kept_patterns()
