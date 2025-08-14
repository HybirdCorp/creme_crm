from django.conf import settings
from django.urls import include, re_path

from creme.creme_core.conf.urls import Swappable, swap_manager

from . import report_model_is_custom  # rgraph_model_is_custom
from .views import bricks, chart, entity_filter, export, report  # graph

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

    # Entity Filters
    re_path(
        r'^entity_filter/',
        include([
            re_path(
                r'^view/(?P<efilter_id>.+)[/]?$',
                entity_filter.ReportEntityFilterDetail.as_view(),
                name='reports__efilter',
            ),
            re_path(
                r'^reload/(?P<efilter_id>.+)[/]?$',
                entity_filter.ReportEntityFilterBricksReloading.as_view(),
                name='reports__reload_efilter_bricks',
            ),
            re_path(
                r'^add/(?P<ct_id>\d+)[/]?$',
                entity_filter.ReportEntityFilterCreation.as_view(),
                name='reports__create_efilter',
            ),
            re_path(
                r'^edit/(?P<efilter_id>.+)[/]?$',
                entity_filter.ReportEntityFilterEdition.as_view(),
                name='reports__edit_efilter',
            ),
            re_path(
                r'^edit_popup/(?P<efilter_id>.+)[/]?$',
                entity_filter.ReportEntityFilterEditionPopup.as_view(),
                name='reports__edit_efilter_popup',
            ),
            re_path(
                r'^delete/(?P<efilter_id>.+)[/]?$',
                entity_filter.ReportEntityFilterDeletion.as_view(),
                name='reports__delete_efilter',
            ),
        ])
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
    #     r'^graph/fetch/(?P<graph_id>\d+)/settings[/]?$',
    #     graph.GraphFetchSettings.as_view(),
    #     name='reports__update_graph_fetch_settings',
    # ),
    # re_path(
    #     r'^graph/fetch/(?P<instance_brick_id>\d+)/settings/(?P<entity_id>\d+)[/]?$',
    #     graph.GraphFetchSettingsForInstance.as_view(),
    #     name='reports__update_graph_fetch_settings_for_instance',
    # ),
    # Charts
    re_path(
        r'^chart/(?P<report_id>\d+)/add[/]?$',
        chart.ChartCreation.as_view(),
        name='reports__create_chart',
    ),
    re_path(
        r'^chart/edit/(?P<chart_id>\d+)[/]?$',
        chart.ChartEdition.as_view(),
        name='reports__edit_chart',
    ),
    re_path(
        r'^chart/(?P<chart_id>\d+)[/]?$',
        chart.ChartDetail.as_view(),
        name='reports__view_chart',
    ),
    re_path(
        r'^chart/(?P<chart_id>\d+)/reload_bricks[/]?$',
        chart.ChartDetailBricksReloading.as_view(),
        name='reports__reload_chart_bricks',
    ),
    re_path(
        r'^chart/delete/(?P<chart_id>\d+)[/]?$',
        chart.ChartDeletion.as_view(),
        name='reports__delete_chart',
    ),
    re_path(
        r'^chart/fetch/(?P<chart_id>\d+)/settings[/]?$',
        chart.ChartFetchSettingsUpdate.as_view(),
        name='reports__update_chart_fetch_settings',
    ),

    re_path(
        # r'^graph/(?P<graph_id>\d+)/brick/add[/]?$',
        r'^chart/(?P<chart_id>\d+)/instance_brick/add[/]?$',
        # bricks.GraphInstanceBrickCreation.as_view(),
        bricks.ChartInstanceBrickCreation.as_view(),
        name='reports__create_instance_brick',
    ),
    re_path(
        # r'^graph/(?P<graph_id>\d+)/bricks[/]?$',
        r'^chart/(?P<chart_id>\d+)/instance_bricks[/]?$',
        # bricks.GraphInstanceBricks.as_view(),
        bricks.ChartInstanceBricksInfo.as_view(),
        name='reports__instance_bricks_info',
    ),
    re_path(
        r'^chart/(?P<chart_id>\d+)/instance_bricks/reload[/]?$',
        bricks.ChartInstanceBricksInfoReloading.as_view(),
        name='reports__reload_chart_ibci_bricks',
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

    # *swap_manager.add_group(
    #     rgraph_model_is_custom,
    #     Swappable(
    #         re_path(
    #             r'^graph/(?P<report_id>\d+)/add[/]?$',
    #             graph.GraphCreation.as_view(),
    #             name='reports__create_graph',
    #         ),
    #         check_args=Swappable.INT_ID,
    #     ),
    #     Swappable(
    #         re_path(
    #             r'^graph/edit/(?P<graph_id>\d+)[/]?$',
    #             graph.GraphEdition.as_view(),
    #             name='reports__edit_graph',
    #         ),
    #         check_args=Swappable.INT_ID,
    #     ),
    #     Swappable(
    #         re_path(
    #             r'^graph/(?P<graph_id>\d+)[/]?$',
    #             graph.GraphDetail.as_view(),
    #             name='reports__view_graph',
    #         ),
    #         check_args=Swappable.INT_ID,
    #     ),
    #     app_name='reports',
    # ).kept_patterns(),
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
