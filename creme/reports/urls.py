# -*- coding: utf-8 -*-

from django.conf import settings
from django.urls import re_path

from creme.creme_core.conf.urls import Swappable, swap_manager

from . import report_model_is_custom, rgraph_model_is_custom
from .views import bricks, export, graph, report

urlpatterns = [
    re_path(
        r'^export/preview/(?P<report_id>\d+)[/]?$',
        export.Preview.as_view(),
        name='reports__export_report_preview',
    ),
    re_path(
        r'^export/filter/(?P<report_id>\d+)[/]?$',
        export.ExportFilterURL.as_view(),
        name='reports__export_report_filter',
    ),
    re_path(
        r'^export/(?P<report_id>\d+)[/]?$',
        export.Export.as_view(),
        name='reports__export_report',
    ),

    # Fields brick
    # TODO: put field_id even on POST urls (instead of POST arg) ?
    re_path(
        r'^report/field/unlink_report[/]?$',
        report.ReportUnlinking.as_view(),
        name='reports__unlink_report',
    ),
    re_path(
        r'^report/field/(?P<field_id>\d+)/link_report[/]?$',
        report.ReportLinking.as_view(),
        name='reports__link_report',
    ),
    re_path(
        r'^report/field/set_selected[/]?$',
        report.FieldSelection.as_view(),
        name='reports__set_selected_field',
    ),
    re_path(
        r'^report/(?P<report_id>\d+)/reorder_field/(?P<field_id>\d+)[/]?$',
        report.MoveField.as_view(),
        name='reports__reorder_field',
    ),
    re_path(
        r'^report/(?P<report_id>\d+)/edit_fields[/]?$',
        report.FieldsEdition.as_view(),
        name='reports__edit_fields',
    ),

    # re_path(
    #     r'^graph/get_available_types/(?P<ct_id>\d+)[/]?$',
    #     graph.get_available_report_graph_types,
    #     name='reports__graph_types'
    # ),

    re_path(
        r'^graph/fetch/(?P<graph_id>\d+)[/]?$',
        graph.GraphFetching.as_view(),
        name='reports__fetch_graph'
    ),
    re_path(
        r'^graph/fetch/from_instance_brick/(?P<instance_brick_id>\d+)/(?P<entity_id>\d+)[/]?$',
        graph.GraphFetchingForInstance.as_view(),
        name='reports__fetch_graph_from_brick',
    ),

    re_path(
        r'^graph/(?P<graph_id>\d+)/brick/add[/]?$',
        bricks.GraphInstanceBrickCreation.as_view(),
        name='reports__create_instance_brick',
    ),
    re_path(
        r'^graph/(?P<graph_id>\d+)/bricks[/]?$',
        bricks.GraphInstanceBricks.as_view(),
        name='reports__instance_bricks_info',
    ),

    *swap_manager.add_group(
        report_model_is_custom,
        Swappable(
            re_path(
                r'^reports[/]?$',
                report.ReportsList.as_view(),
                name='reports__list_reports',
            ),
        ),
        Swappable(
            re_path(
                r'^report/add[/]?$',
                report.ReportCreationWizard.as_view(),
                name='reports__create_report',
            ),
        ),
        Swappable(
            re_path(
                r'^report/edit/(?P<report_id>\d+)[/]?$',
                report.ReportEdition.as_view(),
                name='reports__edit_report',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^report/(?P<report_id>\d+)[/]?$',
                report.ReportDetail.as_view(),
                name='reports__view_report',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='reports',
    ).kept_patterns(),

    *swap_manager.add_group(
        rgraph_model_is_custom,
        Swappable(
            re_path(
                r'^graph/(?P<report_id>\d+)/add[/]?$',
                graph.GraphCreation.as_view(),
                name='reports__create_graph',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^graph/edit/(?P<graph_id>\d+)[/]?$',
                graph.GraphEdition.as_view(),
                name='reports__edit_graph',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^graph/(?P<graph_id>\d+)[/]?$',
                graph.GraphDetail.as_view(),
                name='reports__view_graph',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='reports',
    ).kept_patterns(),
]

if settings.TESTS_ON:
    from .tests import fake_views

    urlpatterns += [
        re_path(
            r'^tests/folder/(?P<folder_id>\d+)[/]?$',
            fake_views.FakeReportsFolderDetail.as_view(),
            name='reports__view_fake_folder',
        ),

        re_path(
            r'^tests/documents[/]?$',
            fake_views.FakeReportsDocumentsList.as_view(),
            name='reports__list_fake_documents',
        ),
    ]
