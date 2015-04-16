# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import patterns


urlpatterns = patterns('creme.reports.views',
    (r'^$', 'portal.portal'),

    (r'^reports$',                                   'report.listview'),
    (r'^report/add$',                                'report.add'),
    (r'^report/edit/(?P<report_id>\d+)$',            'report.edit'),
    (r'^report/(?P<report_id>\d+)$',                 'report.detailview'),

    (r'^export/preview/(?P<report_id>\d+)$',  'export.preview'),
    (r'^export/filter/(?P<report_id>\d+)$',   'export.filter'),
    (r'^export/(?P<report_id>\d+)$',          'export.export'),

    #Fields block
    #TODO: put field_id even on POST urls (instead of POST arg)
    (r'^report/field/unlink_report$',                   'report.unlink_report'),
    (r'^report/field/change_order$',                    'report.change_field_order'),
    (r'^report/field/set_selected$',                    'report.set_selected'),
    (r'^report/field/(?P<field_id>\d+)/link_report$',   'report.link_report'),
    (r'^report/(?P<report_id>\d+)/edit_fields$',        'report.edit_fields'),

    (r'^graph/(?P<report_id>\d+)/add$',                                                                 'graph.add'),
    (r'^graph/edit/(?P<graph_id>\d+)$',                                                                 'graph.edit'),
    (r'^graph/(?P<graph_id>\d+)$',                                                                      'graph.detailview'),
    (r'^graph/get_available_types/(?P<ct_id>\d+)$',                                                     'graph.get_available_report_graph_types'),
    (r'^graph/fetch_graph/(?P<graph_id>\d+)/(?P<order>\w+)$',                                           'graph.fetch_graph'),
    (r'^graph/fetch_from_instance_block/(?P<instance_block_id>\d+)/(?P<entity_id>\d+)/(?P<order>\w+)$', 'graph.fetch_graph_from_instanceblock'),

    (r'^graph/(?P<graph_id>\d+)/block/add$', 'blocks.add_graph_instance_block'),
)

if settings.TESTS_ON:
    urlpatterns += patterns('creme.reports.tests.fake_views',
        #(r'^tests/folders$',                        'folder_listview'),
        #(r'^tests/folder/add$',                     'folder_add'),
        #(r'^tests/folder/edit/(?P<folder_id>\d+)$', 'folder_edit'),
        (r'^tests/folder/(?P<folder_id>\d+)$',      'folder_detailview'),

        (r'^tests/documents$',                              'document_listview'),
        #(r'^tests/document/add$',                          'document_add'),
        #(r'^tests/document/edit/(?P<document_id>\d+)$',	'document_edit'),
        #(r'^tests/document/(?P<object_id>\d+)$',           'document_detailview'),
    )
