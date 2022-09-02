from functools import partial
from unittest import mock

from django.contrib.sessions.backends.base import SessionBase
from django.db.models.query_utils import Q
from django.test.client import RequestFactory
from django.urls.base import reverse
from django.utils.timezone import datetime, make_aware

from creme.creme_core.gui.bricks import BricksManager
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.queries import QSerializer
from creme.reports.bricks import (
    ReportGraph,
    ReportGraphD3ChartBrick,
    ReportGraphD3ChartInstanceBrick,
    ReportGraphD3ChartListBrick,
)
from creme.reports.core.graph.hand import _generate_date_format
from creme.reports.report_chart_registry import report_chart_registry
from creme.reports.tests.base import BaseReportsTestCase
from creme.reports.tests.fake_models import (
    FakeReportsDocument,
    FakeReportsFolder,
)


def detailview_display_context(entity, user):
    request = RequestFactory().get(entity.get_absolute_url())
    request.session = SessionBase()
    request.user = user

    return {
        'object': entity,
        'request': request,
        'user': user,
        BricksManager.var_name: BricksManager(),
    }


def home_display_context(user):
    request = RequestFactory().get(reverse('creme_core__home'))
    request.session = SessionBase()
    request.user = user

    return {
        'request': request,
        'user': user,
        BricksManager.var_name: BricksManager(),
    }


def create_fake_docs(user):
    create_folder = partial(FakeReportsFolder.objects.create, user=user)
    folder1 = create_folder(title='Internal', created=make_aware(datetime(2022, 5, 1)))
    folder2 = create_folder(title='External', created=make_aware(datetime(2022, 5, 1)))

    create_doc = partial(FakeReportsDocument.objects.create, user=user)
    return (
        create_doc(
            title='Doc#1.1',
            linked_folder=folder1,
            created=make_aware(datetime(2022, 5, 10))
        ),
        create_doc(
            title='Doc#1.2',
            linked_folder=folder1,
            created=make_aware(datetime(2022, 5, 30))
        ),
        create_doc(
            title='Doc#2',
            linked_folder=folder2,
            created=make_aware(datetime(2022, 8, 2))
        ),
    )


def reverse_listview(name, q_filters):
    q = Q()

    for q_object in q_filters:
        q &= (
            q_object if isinstance(q_object, Q) else Q(**q_object)
        )

    qfilter = QSerializer().dumps(q)
    return reverse(name) + f'?q_filter={qfilter}'


@mock.patch('creme.reports.bricks.ReportGraphD3ChartBrick._render')
class ReportGraphD3ChartBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    def test_detailview_display__no_data(self, mock_brick_render):
        user = self.create_user()
        graph = self._create_documents_rgraph(user=user)

        context = detailview_display_context(graph, user)

        brick = ReportGraphD3ChartBrick()
        brick.detailview_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'graph': graph,
            'data': [],
            'settings_update_url': reverse(
                'reports__update_graph_fetch_settings', args=(graph.id,)
            ),
            'charts': [chart for _, chart in report_chart_registry],
            'props': {
                name: chart.props(graph, []) for name, chart in report_chart_registry
            }
        })

    def test_detailview_display(self, mock_brick_render):
        user = self.create_user()
        graph = self._create_documents_rgraph(user=user)

        create_fake_docs(user)

        context = detailview_display_context(graph, user)
        data = [
            {
                'x': '2022',
                'y': 3,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}]
                )
            },
        ]

        brick = ReportGraphD3ChartBrick()
        brick.detailview_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'graph': graph,
            'data': data,
            'settings_update_url': reverse(
                'reports__update_graph_fetch_settings', args=(graph.id,)
            ),
            'charts': [chart for _, chart in report_chart_registry],
            'props': {
                name: chart.props(graph, data) for name, chart in report_chart_registry
            }
        })


@mock.patch('creme.reports.bricks.ReportGraphD3ChartListBrick._render')
class ReportGraphD3ChartListBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    def _create_report_graphs(self, report):
        return (
            ReportGraph.objects.create(
                user=report.user,
                linked_report=report,
                name='Number of created documents / year',
                abscissa_cell_value='created',
                abscissa_type=ReportGraph.Group.YEAR,
                ordinate_type=ReportGraph.Aggregator.COUNT,
            ),
            ReportGraph.objects.create(
                user=report.user,
                linked_report=report,
                name='Number of created documents / month',
                abscissa_cell_value='created',
                abscissa_type=ReportGraph.Group.MONTH,
                ordinate_type=ReportGraph.Aggregator.COUNT,
            )
        )

    def test_detailview_display__no_graphs(self, mock_brick_render):
        user = self.create_user()
        report = self._create_simple_documents_report(user=user)

        context = detailview_display_context(report, user)

        brick = ReportGraphD3ChartListBrick()
        brick.detailview_display(context)

        mock_brick_render.assert_called_once()
        render_context = mock_brick_render.call_args[0][0]

        self.assertEqual(
            render_context['charts'],
            [chart for _, chart in report_chart_registry],
        )

        self.assertEqual(render_context['rows'], [])

    def test_detailview_display__no_data(self, mock_brick_render):
        user = self.create_user()
        report = self._create_simple_documents_report(user=user)
        graph_by_year, graph_by_month = self._create_report_graphs(report)

        context = detailview_display_context(report, user)

        brick = ReportGraphD3ChartListBrick()
        brick.detailview_display(context)

        data = []

        mock_brick_render.assert_called_once()
        render_context = mock_brick_render.call_args[0][0]

        self.assertEqual(
            render_context['charts'],
            [chart for _, chart in report_chart_registry],
        )

        self.assertEqual(render_context['rows'], [
            {
                'graph': graph_by_year,
                'data': data,
                'instance_brick_count': 0,
                'settings_update_url': reverse(
                    'reports__update_graph_fetch_settings', args=(graph_by_year.id,)
                ),
                'props': {
                    name: chart.props(graph_by_year, data)
                    for name, chart in report_chart_registry
                }
            },
            {
                'graph': graph_by_month,
                'data': data,
                'instance_brick_count': 0,
                'settings_update_url': reverse(
                    'reports__update_graph_fetch_settings', args=(graph_by_month.id,)
                ),
                'props': {
                    name: chart.props(graph_by_month, data)
                    for name, chart in report_chart_registry
                }
            },
        ])

    def test_detailview_display(self, mock_brick_render):
        user = self.create_user()
        report = self._create_simple_documents_report(user=user)
        graph_by_year, graph_by_month = self._create_report_graphs(report)

        create_fake_docs(user)

        brick = ReportGraphD3ChartListBrick()
        brick.detailview_display(detailview_display_context(report, user))

        graph_by_year_data = [
            {
                'x': '2022',
                'y': 3,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}]
                )
            },
        ]

        by_month_format = _generate_date_format(year=True, month=True)

        graph_by_month_data = [
            {
                'x': datetime(2022, 5, 1).strftime(by_month_format),  # 05-2022
                'y': 2,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[
                        {"created__year": 2022, 'created__month': 5}
                    ]
                )
            },
            {
                'x': datetime(2022, 8, 1).strftime(by_month_format),  # 08-2022
                'y': 1,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[
                        {"created__year": 2022, 'created__month': 8}
                    ]
                )
            },
        ]

        mock_brick_render.assert_called_once()
        render_context = mock_brick_render.call_args[0][0]

        self.maxDiff = None

        self.assertEqual(
            render_context['charts'],
            [chart for _, chart in report_chart_registry],
        )

        self.assertEqual(render_context['rows'], [
            {
                'graph': graph_by_year,
                'data': graph_by_year_data,
                'instance_brick_count': 0,
                'settings_update_url': reverse(
                    'reports__update_graph_fetch_settings', args=(graph_by_year.id,)
                ),
                'props': {
                    name: chart.props(graph_by_year, graph_by_year_data)
                    for name, chart in report_chart_registry
                }
            },
            {
                'graph': graph_by_month,
                'data': graph_by_month_data,
                'instance_brick_count': 0,
                'settings_update_url': reverse(
                    'reports__update_graph_fetch_settings', args=(graph_by_month.id,)
                ),
                'props': {
                    name: chart.props(graph_by_month, graph_by_month_data)
                    for name, chart in report_chart_registry
                }
            },
        ])


@mock.patch('creme.reports.bricks.ReportGraphD3ChartInstanceBrick._render')
class ReportGraphD3ChartInstanceBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    def test_detailview_display__no_data(self, mock_brick_render):
        user = self.login()
        graph = self._create_documents_rgraph(user=user)
        instance = self._create_graph_instance_brick(graph)

        context = detailview_display_context(graph, user)

        brick = ReportGraphD3ChartInstanceBrick(instance)
        brick.detailview_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'graph': graph,
            'data': [],
            'settings_update_url': reverse(
                'reports__update_graph_fetch_settings_for_instance', args=(instance.id, graph.id,)
            ),
            'charts': [chart for _, chart in report_chart_registry],
            'props': {
                name: chart.props(graph, []) for name, chart in report_chart_registry
            }
        })

    def test_detailview_display(self, mock_brick_render):
        user = self.login()
        graph = self._create_documents_rgraph(user=user)
        instance = self._create_graph_instance_brick(graph)

        create_fake_docs(user)

        context = detailview_display_context(graph, user)
        data = [
            {
                'x': '2022',
                'y': 3,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}]
                )
            },
        ]

        brick = ReportGraphD3ChartInstanceBrick(instance)
        brick.detailview_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'graph': graph,
            'data': data,
            'settings_update_url': reverse(
                'reports__update_graph_fetch_settings_for_instance', args=(instance.id, graph.id,)
            ),
            'charts': [chart for _, chart in report_chart_registry],
            'props': {
                name: chart.props(graph, data) for name, chart in report_chart_registry
            }
        })

    def test_home_display__no_data(self, mock_brick_render):
        user = self.login()
        graph = self._create_documents_rgraph(user=user)
        instance = self._create_graph_instance_brick(graph)

        context = home_display_context(user)

        brick = ReportGraphD3ChartInstanceBrick(instance)
        brick.home_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'graph': graph,
            'data': [],
            'settings_update_url': reverse(
                'reports__update_graph_fetch_settings_for_instance', args=(instance.id, graph.id,)
            ),
            'charts': [chart for _, chart in report_chart_registry],
            'props': {
                name: chart.props(graph, []) for name, chart in report_chart_registry
            }
        })

    def test_home_display(self, mock_brick_render):
        user = self.login()
        graph = self._create_documents_rgraph(user=user)
        instance = self._create_graph_instance_brick(graph)

        create_fake_docs(user)

        context = home_display_context(user)
        data = [
            {
                'x': '2022',
                'y': 3,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}]
                )
            },
        ]

        brick = ReportGraphD3ChartInstanceBrick(instance)
        brick.home_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'graph': graph,
            'data': data,
            'settings_update_url': reverse(
                'reports__update_graph_fetch_settings_for_instance', args=(instance.id, graph.id,)
            ),
            'charts': [chart for _, chart in report_chart_registry],
            'props': {
                name: chart.props(graph, data) for name, chart in report_chart_registry
            }
        })
