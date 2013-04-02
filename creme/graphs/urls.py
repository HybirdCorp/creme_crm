# -*- coding: utf-8 -*-

from django.conf.urls import patterns

urlpatterns = patterns('creme.graphs.views',
    (r'^$', 'portal.portal'),

    (r'^graphs$',                       'graph.listview'),
    (r'^graph/add$',                    'graph.add'),
    (r'^graph/(?P<graph_id>\d+)/png$',  'graph.dl_png'),
    (r'^graph/edit/(?P<graph_id>\d+)$', 'graph.edit'),
    (r'^graph/(?P<graph_id>\d+)$',      'graph.detailview'),

    (r'^graph/(?P<graph_id>\d+)/relation_types/add$',   'graph.add_relation_types'),
    (r'^graph/(?P<graph_id>\d+)/relation_type/delete$', 'graph.delete_relation_type'),

    (r'^graph/(?P<graph_id>\d+)/roots/add$', 'root_node.add'),
    (r'^root/edit/(?P<root_id>\d+)/',        'root_node.edit'),
    (r'^root/delete$',                       'root_node.delete'),
)
