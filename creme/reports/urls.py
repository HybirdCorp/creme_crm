# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import url

from . import report_model_is_custom, rgraph_model_is_custom
from .views import portal, export, report, graph, blocks


urlpatterns = [
    url(r'^$', portal.portal),

    url(r'^export/preview/(?P<report_id>\d+)$',  export.preview),
    url(r'^export/filter/(?P<report_id>\d+)$',   export.filter),
    url(r'^export/(?P<report_id>\d+)$',          export.export),

    # Fields block
    # TODO: put field_id even on POST urls (instead of POST arg)
    url(r'^report/field/unlink_report$',                   report.unlink_report),
    url(r'^report/field/change_order$',                    report.change_field_order),
    url(r'^report/field/set_selected$',                    report.set_selected),
    url(r'^report/field/(?P<field_id>\d+)/link_report$',   report.link_report),
    url(r'^report/(?P<report_id>\d+)/edit_fields$',        report.edit_fields),

    url(r'^graph/get_available_types/(?P<ct_id>\d+)$',                                                     graph.get_available_report_graph_types),
    url(r'^graph/fetch_graph/(?P<graph_id>\d+)/(?P<order>\w+)$',                                           graph.fetch_graph),
    url(r'^graph/fetch_from_instance_block/(?P<instance_block_id>\d+)/(?P<entity_id>\d+)/(?P<order>\w+)$', graph.fetch_graph_from_instanceblock),

    url(r'^graph/(?P<graph_id>\d+)/block/add$', blocks.add_graph_instance_block),
]

if not report_model_is_custom():
    urlpatterns += [
        url(r'^reports$',                        report.listview,   name='reports__list_reports'),
        url(r'^report/add$',                     report.add,        name='reports__create_report'),
        url(r'^report/edit/(?P<report_id>\d+)$', report.edit,       name='reports__edit_report'),
        url(r'^report/(?P<report_id>\d+)$',      report.detailview, name='reports__view_report'),
    ]

if not rgraph_model_is_custom():
    urlpatterns += [
        url(r'^graph/(?P<report_id>\d+)/add$', graph.add,        name='reports__create_graph'),
        url(r'^graph/edit/(?P<graph_id>\d+)$', graph.edit,       name='reports__edit_graph'),
        url(r'^graph/(?P<graph_id>\d+)$',      graph.detailview, name='reports__view_graph'),
    ]

if settings.TESTS_ON:
    from .tests import fake_views

    urlpatterns += [
        # (r'^tests/folders$',                        'folder_listview'),
        # (r'^tests/folder/add$',                     'folder_add'),
        # (r'^tests/folder/edit/(?P<folder_id>\d+)$', 'folder_edit'),
        url(r'^tests/folder/(?P<folder_id>\d+)$', fake_views.folder_detailview),

        url(r'^tests/documents$', fake_views.document_listview),
        # (r'^tests/document/add$',                       'document_add'),
        # (r'^tests/document/edit/(?P<document_id>\d+)$', 'document_edit'),
        # (r'^tests/document/(?P<object_id>\d+)$',        'document_detailview'),
    ]
