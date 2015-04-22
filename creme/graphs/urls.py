# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from . import graph_model_is_custom


urlpatterns = patterns('creme.graphs.views',
    (r'^$', 'portal.portal'),

    (r'^graph/(?P<graph_id>\d+)/png$', 'graph.dl_png'),

    (r'^graph/(?P<graph_id>\d+)/relation_types/add$',   'graph.add_relation_types'),
    (r'^graph/(?P<graph_id>\d+)/relation_type/delete$', 'graph.delete_relation_type'),

    (r'^graph/(?P<graph_id>\d+)/roots/add$', 'root_node.add'),
    (r'^root/edit/(?P<root_id>\d+)/',        'root_node.edit'),
    (r'^root/delete$',                       'root_node.delete'),
)

if not graph_model_is_custom():
    urlpatterns += patterns('creme.graphs.views.graph',
        url(r'^graphs$',                       'listview',   name='graphs__list_graphs'),
        url(r'^graph/add$',                    'add',        name='graphs__create_graph'),
        url(r'^graph/edit/(?P<graph_id>\d+)$', 'edit',       name='graphs__edit_graph'),
        url(r'^graph/(?P<graph_id>\d+)$',      'detailview', name='graphs__view_graph'),
    )
