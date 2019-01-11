# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import url

from creme.creme_core.conf.urls import Swappable, swap_manager

from . import report_model_is_custom, rgraph_model_is_custom
from .views import export, report, graph, bricks


urlpatterns = [
    url(r'^export/preview/(?P<report_id>\d+)[/]?$', export.Preview.as_view(),         name='reports__export_report_preview'),
    url(r'^export/filter/(?P<report_id>\d+)[/]?$',  export.ExportFilterURL.as_view(), name='reports__export_report_filter'),
    url(r'^export/(?P<report_id>\d+)[/]?$',         export.export,                    name='reports__export_report'),

    # Fields brick
    # TODO: put field_id even on POST urls (instead of POST arg) ?
    url(r'^report/field/unlink_report[/]?$',                                report.unlink_report,           name='reports__unlink_report'),
    url(r'^report/field/(?P<field_id>\d+)/link_report[/]?$',                report.ReportLinking.as_view(), name='reports__link_report'),
    url(r'^report/field/set_selected[/]?$',                                 report.set_selected,            name='reports__set_selected_field'),
    url(r'^report/(?P<report_id>\d+)/reorder_field/(?P<field_id>\d+)[/]?$', report.MoveField.as_view(),     name='reports__reorder_field'),
    url(r'^report/(?P<report_id>\d+)/edit_fields[/]?$',                     report.FieldsEdition.as_view(), name='reports__edit_fields'),

    url(r'^graph/get_available_types/(?P<ct_id>\d+)[/]?$', graph.get_available_report_graph_types, name='reports__graph_types'),

    url(r'^graph/fetch/(?P<graph_id>\d+)[/]?$', graph.fetch_graph, name='reports__fetch_graph'),

    url(r'^graph/fetch/from_instance_brick/(?P<instance_brick_id>\d+)/(?P<entity_id>\d+)[/]?$',
        graph.fetch_graph_from_instancebrick, name='reports__fetch_graph_from_brick',
       ),

    url(r'^graph/(?P<graph_id>\d+)/brick/add[/]?$',
        bricks.GraphInstanceBrickCreation.as_view(),
        name='reports__create_instance_brick',
    ),
    url(r'^graph/(?P<graph_id>\d+)/bricks[/]?$',
        bricks.GraphInstanceBricks.as_view(),
        name='reports__instance_bricks_info',
    ),
]

urlpatterns += swap_manager.add_group(
    report_model_is_custom,
    Swappable(url(r'^reports[/]?$',                        report.listview,                 name='reports__list_reports')),
    Swappable(url(r'^report/add[/]?$',                     report.ReportCreation.as_view(), name='reports__create_report')),
    Swappable(url(r'^report/edit/(?P<report_id>\d+)[/]?$', report.ReportEdition.as_view(),  name='reports__edit_report'), check_args=Swappable.INT_ID),
    Swappable(url(r'^report/(?P<report_id>\d+)[/]?$',      report.ReportDetail.as_view(),   name='reports__view_report'), check_args=Swappable.INT_ID),
    app_name='reports',
).kept_patterns()

urlpatterns += swap_manager.add_group(
    rgraph_model_is_custom,
    Swappable(url(r'^graph/(?P<report_id>\d+)/add[/]?$', graph.GraphCreation.as_view(), name='reports__create_graph'), check_args=Swappable.INT_ID),
    Swappable(url(r'^graph/edit/(?P<graph_id>\d+)[/]?$', graph.GraphEdition.as_view(),  name='reports__edit_graph'),   check_args=Swappable.INT_ID),
    Swappable(url(r'^graph/(?P<graph_id>\d+)[/]?$',      graph.GraphDetail.as_view(),   name='reports__view_graph'),   check_args=Swappable.INT_ID),
    app_name='reports',
).kept_patterns()

if settings.TESTS_ON:
    from .tests import fake_views

    urlpatterns += [
        url(r'^tests/folder/(?P<folder_id>\d+)[/]?$', fake_views.FakeReportsFolderDetail.as_view(),
            name='reports__view_fake_folder',
           ),

        url(r'^tests/documents[/]?$', fake_views.document_listview, name='reports__list_fake_documents'),
    ]
