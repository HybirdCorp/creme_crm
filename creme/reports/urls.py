# -*- coding: utf-8 -*-

from django.conf.urls import patterns


urlpatterns = patterns('creme.reports.views',
    (r'^$', 'portal.portal'),

    (r'^reports$',                                               'report.listview'),
    (r'^report/add$',                                            'report.add'),
    (r'^report/edit/(?P<report_id>\d+)$',                        'report.edit'),
    (r'^report/(?P<report_id>\d+)$',                             'report.detailview'),
    (r'^report/preview/(?P<report_id>\d+)$',                     'report.preview'),
    (r'^report/export/(?P<report_id>\d+)/(?P<doc_type>[\w-]+)$', 'report.export'),

    #Fields block
    (r'^report/field/unlink_report$',                                                            'report.unlink_report'),
    (r'^report/field/change_order$',                                                             'report.change_field_order'),
    (r'^report/field/set_selected$',                                                             'report.set_selected'),
    (r'^report/(?P<report_id>\d+)/field/(?P<field_id>\d+)/link_report$',                         'report.link_report'),
    (r'^report/(?P<report_id>\d+)/field/(?P<field_id>\d+)/link_related_report$',                 'report.link_related_report'),
    (r'^report/(?P<report_id>\d+)/field/(?P<field_id>\d+)/link_relation_report/(?P<ct_id>\d+)$', 'report.link_relation_report'),
    (r'^report/(?P<report_id>\d+)/field/add$',                                                   'report.add_field'),
    (r'^get_aggregate_fields$',                                                                  'report.get_aggregate_fields'),
    (r'^get_related_fields$',                                                                    'report.get_related_fields'),
    (r'^date_filter_form/(?P<report_id>\d+)$',                                                   'report.date_filter_form'),

    (r'^graph/(?P<report_id>\d+)/add$',                                                                 'graph.add'),
    (r'^graph/edit/(?P<graph_id>\d+)$',                                                                 'graph.edit'),
    (r'^graph/(?P<graph_id>\d+)$',                                                                      'graph.detailview'),
    (r'^graph/get_available_types/(?P<ct_id>\d+)$',                                                     'graph.get_available_report_graph_types'),
    (r'^graph/fetch_graph/(?P<graph_id>\d+)/(?P<order>\w+)$',                                           'graph.fetch_graph'),
    (r'^graph/fetch_from_instance_block/(?P<instance_block_id>\d+)/(?P<entity_id>\d+)/(?P<order>\w+)$', 'graph.fetch_graph_from_instanceblock'),

    (r'^graph/(?P<graph_id>\d+)/block/add$', 'blocks.add_graph_instance_block'),

    (r'^get_predicates_choices_4_ct$', 'report.get_predicates_choices_4_ct'),
)
