# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns

urlpatterns = patterns('reports.views',
    (r'^$', 'portal.portal'),

    (r'^reports$',                        'report.listview'),
    (r'^report/add$',                     'report.add'),
    (r'^report/(?P<report_id>\d+)/csv$',  'report.view_csv'), ##?? r'^report/csv/(?P<report_id>\d*)$
    (r'^report/(?P<report_id>\d+)/odt$',  'report.view_odt'),
    (r'^report/edit/(?P<report_id>\d+)$', 'report.edit'),
    (r'^report/(?P<report_id>\d+)$',      'report.detailview'),

    (r'^ajax/load_filters$',          'ajax.get_filters_for_ct'),
    (r'^ajax/load_preview$',          'ajax.get_preview'),
    (r'^ajax/load_columns$',          'ajax.get_columns_for_ct'),
    (r'^ajax/load_operable_columns$', 'ajax.get_operable_columns'),
    (r'^ajax/save$',                  'ajax.save'),

    (r'^graphs$',                       'graph.listview'),
    (r'^graph/add$',                    'graph.add'),
    (r'^graph/(?P<graph_id>\d+)/png$',  'graph.dl_png'),
    (r'^graph/edit/(?P<graph_id>\d+)$', 'graph.edit'),
    (r'^graph/(?P<graph_id>\d+)$',      'graph.detailview'),
)

urlpatterns += patterns('creme_core.views.generic',
    (r'^report/delete/(?P<object_id>\d+)$', 'delete_entity'),
    (r'^graph/delete/(?P<object_id>\d+)$',  'delete_entity'),
)
