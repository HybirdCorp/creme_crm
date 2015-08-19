# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import graph_model_is_custom
from .views import portal, graph, root_node


urlpatterns = [
    url(r'^$', portal.portal),

    url(r'^graph/(?P<graph_id>\d+)/png$', graph.dl_png),

    url(r'^graph/(?P<graph_id>\d+)/relation_types/add$',   graph.add_relation_types),
    url(r'^graph/(?P<graph_id>\d+)/relation_type/delete$', graph.delete_relation_type),

    url(r'^graph/(?P<graph_id>\d+)/roots/add$', root_node.add),
    url(r'^root/edit/(?P<root_id>\d+)/',        root_node.edit),
    url(r'^root/delete$',                       root_node.delete),
]

if not graph_model_is_custom():
    urlpatterns += [
        url(r'^graphs$',                       graph.listview,   name='graphs__list_graphs'),
        url(r'^graph/add$',                    graph.add,        name='graphs__create_graph'),
        url(r'^graph/edit/(?P<graph_id>\d+)$', graph.edit,       name='graphs__edit_graph'),
        url(r'^graph/(?P<graph_id>\d+)$',      graph.detailview, name='graphs__view_graph'),
    ]
