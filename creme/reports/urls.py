# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import url

from . import report_model_is_custom, rgraph_model_is_custom
from .views import export, report, graph, bricks  # portal


urlpatterns = [
    # url(r'^$', portal.portal, name='reports__portal'),

    url(r'^export/preview/(?P<report_id>\d+)[/]?$', export.preview, name='reports__export_report_preview'),
    url(r'^export/filter/(?P<report_id>\d+)[/]?$',  export.filter,  name='reports__export_report_filter'),
    url(r'^export/(?P<report_id>\d+)[/]?$',         export.export,  name='reports__export_report'),

    # Fields brick
    # TODO: put field_id even on POST urls (instead of POST arg) ?
    url(r'^report/field/unlink_report[/]?$',                 report.unlink_report, name='reports__unlink_report'),
    url(r'^report/field/(?P<field_id>\d+)/reorder[/]?$',     report.reorder_field, name='reports__reorder_field'),
    url(r'^report/field/(?P<field_id>\d+)/link_report[/]?$', report.link_report,   name='reports__link_report'),
    url(r'^report/field/set_selected[/]?$',                  report.set_selected,  name='reports__set_selected_field'),
    url(r'^report/(?P<report_id>\d+)/edit_fields[/]?$',      report.edit_fields,   name='reports__edit_fields'),

    url(r'^graph/get_available_types/(?P<ct_id>\d+)[/]?$', graph.get_available_report_graph_types, name='reports__graph_types'),

    # url(r'^graph/fetch_graph/(?P<graph_id>\d+)[/]?$', graph.fetch_graph, name='reports__fetch_graph'),
    url(r'^graph/fetch/(?P<graph_id>\d+)[/]?$', graph.fetch_graph, name='reports__fetch_graph'),

    # url(r'^graph/fetch_from_instance_block/(?P<instance_block_id>\d+)/(?P<entity_id>\d+)[/]?$',
    url(r'^graph/fetch/from_instance_brick/(?P<instance_brick_id>\d+)/(?P<entity_id>\d+)[/]?$',
        # graph.fetch_graph_from_instanceblock, name='reports__fetch_graph_from_brick',
        graph.fetch_graph_from_instancebrick, name='reports__fetch_graph_from_brick',
       ),

    # url(r'^graph/(?P<graph_id>\d+)/block/add[/]?$', bricks.add_graph_instance_brick, name='reports__create_instance_brick'),
    url(r'^graph/(?P<graph_id>\d+)/brick/add[/]?$', bricks.add_graph_instance_brick, name='reports__create_instance_brick'),
]

if not report_model_is_custom():
    urlpatterns += [
        url(r'^reports[/]?$',                        report.listview,   name='reports__list_reports'),
        # url(r'^report/add[/]?$',                     report.add,        name='reports__create_report'),
        url(r'^report/add[/]?$',                     report.ReportCreation.as_view(), name='reports__create_report'),
        # url(r'^report/edit/(?P<report_id>\d+)[/]?$', report.edit,       name='reports__edit_report'),
        url(r'^report/edit/(?P<report_id>\d+)[/]?$', report.ReportEdition.as_view(), name='reports__edit_report'),
        # url(r'^report/(?P<report_id>\d+)[/]?$',      report.detailview, name='reports__view_report'),
        url(r'^report/(?P<report_id>\d+)[/]?$',      report.ReportDetail.as_view(), name='reports__view_report'),
    ]

if not rgraph_model_is_custom():
    urlpatterns += [
        url(r'^graph/(?P<report_id>\d+)/add[/]?$', graph.add,        name='reports__create_graph'),
        url(r'^graph/edit/(?P<graph_id>\d+)[/]?$', graph.edit,       name='reports__edit_graph'),
        # url(r'^graph/(?P<graph_id>\d+)[/]?$',      graph.detailview, name='reports__view_graph'),
        url(r'^graph/(?P<graph_id>\d+)[/]?$',      graph.ReportGraphDetail.as_view(), name='reports__view_graph'),
    ]

if settings.TESTS_ON:
    from .tests import fake_views

    urlpatterns += [
        # url(r'^tests/folder/(?P<folder_id>\d+)[/]?$', fake_views.folder_detailview, name='reports__view_fake_folder'),
        url(r'^tests/folder/(?P<folder_id>\d+)[/]?$', fake_views.FakeReportsFolderDetail.as_view(),
            name='reports__view_fake_folder'
           ),

        url(r'^tests/documents[/]?$', fake_views.document_listview, name='reports__list_fake_documents'),
    ]
