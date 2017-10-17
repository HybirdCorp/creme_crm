# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import graph_model_is_custom
from .views import portal, graph, root_node


urlpatterns = [
    url(r'^$', portal.portal, name='graphs__portal'),

    url(r'^graph/(?P<graph_id>\d+)/png[/]?$', graph.dl_png, name='graphs__dl_image'),

    url(r'^graph/(?P<graph_id>\d+)/relation_types/add[/]?$',   graph.add_relation_types,   name='graphs__add_rtypes'),
    url(r'^graph/(?P<graph_id>\d+)/relation_type/delete[/]?$', graph.delete_relation_type, name='graphs__remove_rtype'),

    url(r'^graph/(?P<graph_id>\d+)/roots/add[/]?$', root_node.add,    name='graphs__add_roots'),
    url(r'^root/edit/(?P<root_id>\d+)[/]?',         root_node.edit,   name='graphs__edit_root'),
    url(r'^root/delete[/]?$',                       root_node.delete, name='graphs__remove_root'),
]

if not graph_model_is_custom():
    urlpatterns += [
        url(r'^graphs[/]?$',                       graph.listview,   name='graphs__list_graphs'),
        url(r'^graph/add[/]?$',                    graph.add,        name='graphs__create_graph'),
        url(r'^graph/edit/(?P<graph_id>\d+)[/]?$', graph.edit,       name='graphs__edit_graph'),
        url(r'^graph/(?P<graph_id>\d+)[/]?$',      graph.detailview, name='graphs__view_graph'),
    ]
