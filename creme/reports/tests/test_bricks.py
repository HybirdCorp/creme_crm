from functools import partial
from unittest import mock

from django.db.models.query_utils import Q
from django.urls.base import reverse
from django.utils.timezone import datetime, make_aware

from creme.creme_core.models import FakeOrganisation
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.queries import QSerializer
from creme.reports.bricks import (
    ReportChartBrick,
    ReportChartInstanceBrick,
    ReportChartsBrick,
)
from creme.reports.core.chart.hand import _generate_date_format
# from creme.reports.report_chart_registry import report_chart_registry
from creme.reports.core.chart.plot import plot_registry
from creme.reports.models import ReportChart
from creme.reports.tests.base import BaseReportsTestCase
# from .base import ReportGraph
from creme.reports.tests.fake_models import (
    FakeReportsColorCategory,
    FakeReportsDocument,
    FakeReportsFolder,
)


def create_fake_docs(user):
    create_folder = partial(FakeReportsFolder.objects.create, user=user)
    folder1 = create_folder(title='Internal', created=make_aware(datetime(2022, 5, 1)))
    folder2 = create_folder(title='External', created=make_aware(datetime(2022, 5, 1)))

    create_cat = FakeReportsColorCategory.objects.create
    cat_A = create_cat(title='Cat A')
    cat_B = create_cat(title='Cat B')

    create_doc = partial(FakeReportsDocument.objects.create, user=user)
    return (
        create_doc(
            title='Doc#1.1',
            linked_folder=folder1,
            category=cat_A,
            created=make_aware(datetime(2022, 5, 10)),
        ),
        create_doc(
            title='Doc#1.2',
            linked_folder=folder1,
            category=cat_A,
            created=make_aware(datetime(2022, 5, 30)),
        ),
        create_doc(
            title='Doc#2',
            linked_folder=folder2,
            category=cat_B,
            created=make_aware(datetime(2022, 8, 2)),
        ),
    )


def reverse_listview(name, q_filters):
    return get_listview_url(reverse(name), q_filters)


def get_listview_url(url, q_filters):
    if isinstance(q_filters, Q):
        q_filters = [q_filters]

    q = Q()

    for q_object in q_filters:
        q &= q_object if isinstance(q_object, Q) else Q(**q_object)

    return f'{url}?q_filter={QSerializer().dumps(q)}'


@mock.patch('creme.reports.bricks.ReportChartBrick._render')
class D3ReportChartBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    maxDiff = None

    def test_detailview_display__no_data(self, mock_brick_render):
        user = self.get_root_user()
        chart = self._create_documents_chart(user=user)

        context = self.build_context(user=user, instance=chart)

        brick = ReportChartBrick()
        brick.detailview_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'chart': chart,
            'data': [],
            'settings_update_url': reverse(
                'reports__update_chart_fetch_settings', args=(chart.id,)
            ),
            # 'charts': [chart for _, chart in report_chart_registry],
            # 'props': {
            #     name: chart.props(chart, []) for name, chart in report_chart_registry
            # },
        })

    def test_detailview_display(self, mock_brick_render):
        user = self.get_root_user()
        chart = self._create_documents_chart(user=user)

        create_fake_docs(user)

        context = self.build_context(user=user, instance=chart)
        data = [
            {
                'x': '2022',
                'y': 3,
                'color': None,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}],
                ),
            },
        ]

        brick = ReportChartBrick()
        brick.detailview_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'chart': chart,
            'data': data,
            'settings_update_url': reverse(
                'reports__update_chart_fetch_settings', args=(chart.id,),
            ),
            # 'charts': [chart for _, chart in report_chart_registry],
            # 'props': {
            #     name: chart.props(chart, data) for name, chart in report_chart_registry
            # }
        })

    def test_detailview_display__colors(self, mock_brick_render):
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)
        chart = self._create_documents_colors_chart(report)

        create_fake_docs(user)

        cat_A, cat_B = FakeReportsColorCategory.objects.all()

        context = self.build_context(user=user, instance=chart)
        data = [
            {
                'x': f'{cat_A}',
                'y': 2,
                'color': f'#{cat_A.color}',
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"category": cat_A.pk}],
                ),
            }, {
                'x': f'{cat_B}',
                'y': 1,
                'color': f'#{cat_B.color}',
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"category": cat_B.pk}],
                ),
            },
        ]

        brick = ReportChartBrick()
        brick.detailview_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'chart': chart,
            'data': data,
            'settings_update_url': reverse(
                'reports__update_chart_fetch_settings', args=(chart.id,),
            ),
            # 'charts': [chart for _, chart in report_chart_registry],
            # 'props': {
            #     name: chart.props(chart, data) for name, chart in report_chart_registry
            # }
        })


# @mock.patch('creme.reports.bricks.ReportGraphChartListBrick._render')
@mock.patch('creme.reports.bricks.ReportChartsBrick._render')
class D3ReportChartsBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    def _create_report_charts(self, report):
        return (
            # ReportGraph.objects.create(
            #     user=report.user,
            #     linked_report=report,
            #     name='Number of created documents / year',
            #     abscissa_cell_value='created',
            #     abscissa_type=ReportGraph.Group.YEAR,
            #     ordinate_type=ReportGraph.Aggregator.COUNT,
            # ),
            ReportChart.objects.create(
                linked_report=report,
                name='Number of created documents / year',
                abscissa_cell_value='created',
                abscissa_type=ReportChart.Group.YEAR,
                ordinate_type=ReportChart.Aggregator.COUNT,
            ),
            # ReportGraph.objects.create(
            #     user=report.user,
            #     linked_report=report,
            #     name='Number of created documents / month',
            #     abscissa_cell_value='created',
            #     abscissa_type=ReportGraph.Group.MONTH,
            #     ordinate_type=ReportGraph.Aggregator.COUNT,
            # ),
            ReportChart.objects.create(
                linked_report=report,
                name='Number of created documents / month',
                abscissa_cell_value='created',
                abscissa_type=ReportChart.Group.MONTH,
                ordinate_type=ReportChart.Aggregator.COUNT,
            ),
        )

    def test_detailview_display__no_chart(self, mock_brick_render):
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)

        context = self.build_context(user=user, instance=report)

        brick = ReportChartsBrick()
        brick.detailview_display(context)

        mock_brick_render.assert_called_once()
        render_context = mock_brick_render.call_args[0][0]

        # self.assertEqual(
        #     render_context['charts'],
        #     [chart for _, chart in report_chart_registry],
        # )
        self.assertEqual(render_context['plots'], [*plot_registry])

        self.assertEqual(render_context['rows'], [])

    def test_detailview_display__no_data(self, mock_brick_render):
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)
        chart_by_year, chart_by_month = self._create_report_charts(report)

        context = self.build_context(user=user, instance=report)

        brick = ReportChartsBrick()
        brick.detailview_display(context)

        data = []

        mock_brick_render.assert_called_once()
        render_context = mock_brick_render.call_args[0][0]

        self.assertEqual(render_context['plots'], [*plot_registry])

        self.assertEqual(render_context['rows'], [
            {
                'chart': chart_by_year,
                'data': data,
                'instance_brick_count': 0,
                'settings_update_url': reverse(
                    'reports__update_chart_fetch_settings', args=(chart_by_year.id,)
                ),
                'props': {
                    # name: chart.props(graph_by_year, data)
                    # for name, chart in report_chart_registry
                    plot.name: plot.props(chart=chart_by_year, data=data)
                    for plot in plot_registry
                },
            }, {
                'chart': chart_by_month,
                'data': data,
                'instance_brick_count': 0,
                'settings_update_url': reverse(
                    'reports__update_chart_fetch_settings', args=(chart_by_month.id,)
                ),
                'props': {
                    # name: chart.props(graph_by_month, data)
                    # for name, chart in report_chart_registry
                    plot.name: plot.props(chart=chart_by_month, data=data)
                    for plot in plot_registry
                },
            },
        ])

    def test_detailview_display(self, mock_brick_render):
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)
        chart_by_year, chart_by_month = self._create_report_charts(report)

        create_fake_docs(user)

        brick = ReportChartsBrick()
        brick.detailview_display(self.build_context(user=user, instance=report))

        chart_by_year_data = [
            {
                'x': '2022',
                'y': 3,
                'color': None,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}],
                ),
            },
        ]

        by_month_format = _generate_date_format(year=True, month=True)
        chart_by_month_data = [
            {
                'x': datetime(2022, 5, 1).strftime(by_month_format),  # 05-2022
                'y': 2,
                'color': None,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[
                        {"created__year": 2022, 'created__month': 5},
                    ]
                ),
            }, {
                'x': datetime(2022, 8, 1).strftime(by_month_format),  # 08-2022
                'y': 1,
                'color': None,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[
                        {"created__year": 2022, 'created__month': 8},
                    ],
                ),
            },
        ]

        mock_brick_render.assert_called_once()
        render_context = mock_brick_render.call_args[0][0]

        self.maxDiff = None
        self.assertListEqual(
            [
                {
                    'chart': chart_by_year,
                    'data': chart_by_year_data,
                    'instance_brick_count': 0,
                    'settings_update_url': reverse(
                        'reports__update_chart_fetch_settings', args=(chart_by_year.id,),
                    ),
                    'props': {
                        # name: chart.props(chart_by_year, graph_by_year_data)
                        # for name, chart in report_chart_registry
                        plot.name: plot.props(chart_by_year, chart_by_year_data)
                        for plot in plot_registry
                    },
                }, {
                    'chart': chart_by_month,
                    'data': chart_by_month_data,
                    'instance_brick_count': 0,
                    'settings_update_url': reverse(
                        'reports__update_chart_fetch_settings', args=(chart_by_month.id,),
                    ),
                    'props': {
                        # name: chart.props(chart_by_month, graph_by_month_data)
                        # for name, chart in report_chart_registry
                        plot.name: plot.props(chart_by_month, chart_by_month_data)
                        for plot in plot_registry
                    },
                },
            ],
            render_context['rows'],
        )

    def test_detailview_display__colors(self, mock_brick_render):
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)
        chart = self._create_documents_colors_chart(report)

        create_fake_docs(user)

        cat_A, cat_B = FakeReportsColorCategory.objects.all()
        data = [
            {
                'x': f'{cat_A}',
                'y': 2,
                'color': f'#{cat_A.color}',
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"category": cat_A.pk}],
                ),
            }, {
                'x': f'{cat_B}',
                'y': 1,
                'color': f'#{cat_B.color}',
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"category": cat_B.pk}],
                ),
            },
        ]

        brick = ReportChartsBrick()
        brick.detailview_display(self.build_context(user=user, instance=report))

        mock_brick_render.assert_called_once()
        render_context = mock_brick_render.call_args[0][0]

        self.maxDiff = None
        self.assertListEqual(
            [{
                'chart': chart,
                'data': data,
                'instance_brick_count': 0,
                'settings_update_url': reverse(
                    'reports__update_chart_fetch_settings', args=(chart.id,),
                ),
                'props': {
                    # name: chart.props(chart, data)
                    # for name, chart in report_chart_registry
                    plot.name: plot.props(chart=chart, data=data)
                    for plot in plot_registry
                },
            }],
            render_context['rows'],
        )


# @mock.patch('creme.reports.bricks.ReportGraphChartInstanceBrick._render')
@mock.patch('creme.reports.bricks.ReportChartInstanceBrick._render')
class D3ReportChartInstanceBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    def test_detailview_display__no_data(self, mock_brick_render):
        # user = self.login_as_root_and_get()
        user = self.login_as_standard(
            allowed_apps=['creme_core', 'reports'], admin_4_apps=['reports'],
        )
        self.add_credentials(role=user.role, all=['VIEW'])
        # graph = self._create_documents_rgraph(user=user)
        chart = self._create_documents_chart(user=user)
        # ibci = self._create_graph_instance_brick(graph)
        ibci = self._create_chart_instance_brick(chart)
        entity = FakeOrganisation.objects.create(user=user, name='Acme')

        context = self.build_context(user=user, instance=entity)

        # brick = ReportGraphChartInstanceBrick(ibci)
        brick = ReportChartInstanceBrick(ibci)
        brick.detailview_display(context)

        mock_brick_render.assert_called_once()
        self.maxDiff = None
        self.assertDictEqual(
            {
                **context,
                # 'graph': graph,
                'chart': chart,
                'data': [],
                'settings_update_url': reverse(
                    # 'reports__update_graph_fetch_settings', args=(graph.id,),
                    'reports__update_chart_fetch_settings', args=(chart.id,),
                ),
                # 'charts': [chart for _, chart in report_chart_registry],
                'plots': [*plot_registry],
                'props': {
                    # name: chart.props(graph, []) for name, chart in report_chart_registry
                    plot.name: plot.props(chart, []) for plot in plot_registry
                },
            },
            mock_brick_render.call_args[0][0],
        )

    def test_detailview_display(self, mock_brick_render):
        user = self.login_as_root_and_get()
        # graph = self._create_documents_rgraph(user=user)
        chart = self._create_documents_chart(user=user)
        # ibci = self._create_graph_instance_brick(graph)
        ibci = self._create_chart_instance_brick(chart)
        entity = FakeOrganisation.objects.create(user=user, name='Acme')

        create_fake_docs(user)

        context = self.build_context(user=user, instance=entity)
        data = [
            {
                'x': '2022',
                'y': 3,
                'color': None,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}],
                ),
            },
        ]

        # brick = ReportGraphChartInstanceBrick(ibci)
        brick = ReportChartInstanceBrick(ibci)
        brick.detailview_display(context)

        mock_brick_render.assert_called_once()
        self.maxDiff = None
        self.assertDictEqual(
            {
                **context,
                # 'graph': graph,
                'chart': chart,
                'data': data,
                # 'settings_update_url': reverse(
                #     'reports__update_graph_fetch_settings_for_instance',
                #     args=(ibci.id, graph.id),
                # ),
                'settings_update_url': reverse(
                    # 'reports__update_graph_fetch_settings', args=(graph.id,),
                    'reports__update_chart_fetch_settings', args=(chart.id,),
                ),
                # 'charts': [chart for _, chart in report_chart_registry],
                'plots': [*plot_registry],
                'props': {
                    # name: chart.props(graph, data) for name, chart in report_chart_registry
                    plot.name: plot.props(chart, data) for plot in plot_registry
                },
            },
            mock_brick_render.call_args[0][0],
        )

    def test_home_display__no_data(self, mock_brick_render):
        user = self.login_as_root_and_get()
        # graph = self._create_documents_rgraph(user=user)
        chart = self._create_documents_chart(user=user)
        # ibci = self._create_graph_instance_brick(graph)
        ibci = self._create_chart_instance_brick(chart)

        context = self.build_context(user=user)

        # brick = ReportGraphChartInstanceBrick(ibci)
        brick = ReportChartInstanceBrick(ibci)
        brick.home_display(context)

        mock_brick_render.assert_called_once()
        self.maxDiff = None
        self.assertDictEqual(
            {
                **context,
                # 'graph': graph,
                'chart': chart,
                'data': [],
                'settings_update_url': reverse(
                    # 'reports__update_graph_fetch_settings', args=(graph.id,),
                    'reports__update_chart_fetch_settings', args=(chart.id,),
                ),
                # 'charts': [chart for _, chart in report_chart_registry],
                'plots': [*plot_registry],
                'props': {
                    # name: chart.props(graph, []) for name, chart in report_chart_registry
                    plot.name: plot.props(chart, []) for plot in plot_registry
                },
            },
            mock_brick_render.call_args[0][0],
        )

    def test_home_display(self, mock_brick_render):
        user = self.login_as_root_and_get()
        # graph = self._create_documents_rgraph(user=user)
        chart = self._create_documents_chart(user=user)
        # ibci = self._create_graph_instance_brick(graph)
        ibci = self._create_chart_instance_brick(chart)

        create_fake_docs(user)

        context = self.build_context(user=user)
        data = [
            {
                'x': '2022',
                'y': 3,
                'color': None,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}],
                ),
            },
        ]

        # brick = ReportGraphChartInstanceBrick(ibci)
        brick = ReportChartInstanceBrick(ibci)
        brick.home_display(context)

        mock_brick_render.assert_called_once()
        self.maxDiff = None
        self.assertDictEqual(
            {
                **context,
                # 'graph': graph,
                'chart': chart,
                'data': data,
                'settings_update_url': reverse(
                    # 'reports__update_graph_fetch_settings', args=(graph.id,),
                    'reports__update_chart_fetch_settings', args=(chart.id,),
                ),
                # 'charts': [chart for _, chart in report_chart_registry],
                'plots': [*plot_registry],
                'props': {
                    # name: chart.props(graph, data) for name, chart in report_chart_registry
                    plot.name: plot.props(chart, data) for plot in plot_registry
                },
            },
            mock_brick_render.call_args[0][0],
        )

    def test_home_display__colors(self, mock_brick_render):
        user = self.login_as_root_and_get()
        report = self._create_simple_documents_report(user=user)
        # graph = self._create_documents_colors_rgraph(report)
        chart = self._create_documents_colors_chart(report)
        # ibci = self._create_graph_instance_brick(graph)
        ibci = self._create_chart_instance_brick(chart)

        create_fake_docs(user)

        cat_A, cat_B = FakeReportsColorCategory.objects.all()

        context = self.build_context(user=user)
        data = [
            {
                'x': f'{cat_A}',
                'y': 2,
                'color': f'#{cat_A.color}',
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"category": cat_A.pk}],
                ),
            }, {
                'x': f'{cat_B}',
                'y': 1,
                'color': f'#{cat_B.color}',
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"category": cat_B.pk}],
                ),
            },
        ]

        # brick = ReportGraphChartInstanceBrick(ibci)
        brick = ReportChartInstanceBrick(ibci)
        brick.home_display(context)

        mock_brick_render.assert_called_once()
        self.maxDiff = None
        self.assertDictEqual(
            {
                **context,
                # 'graph': graph,
                'chart': chart,
                'data': data,
                'settings_update_url': reverse(
                    # 'reports__update_graph_fetch_settings', args=(graph.id,),
                    'reports__update_chart_fetch_settings', args=(chart.id,),
                ),
                # 'charts': [chart for _, chart in report_chart_registry],
                'plots': [*plot_registry],
                'props': {
                    # name: chart.props(graph, data) for name, chart in report_chart_registry
                    plot.name: plot.props(chart, data) for plot in plot_registry
                },
            },
            mock_brick_render.call_args[0][0],
        )
