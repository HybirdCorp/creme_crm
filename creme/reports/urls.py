# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns

urlpatterns = patterns('reports.views',
    (r'^$', 'portal.portal'),

    (r'^graphs$',                       'graph.listview'),
    (r'^graph/add$',                    'graph.add'),
    (r'^graph/(?P<graph_id>\d+)/png$',  'graph.dl_png'),
    (r'^graph/edit/(?P<graph_id>\d+)$', 'graph.edit'),
    (r'^graph/(?P<graph_id>\d+)$',      'graph.detailview'),
)

urlpatterns += patterns('creme_core.views.generic',
    (r'^graph/delete/(?P<object_id>\d+)$',  'delete_entity'),
)
