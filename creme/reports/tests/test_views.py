from django.urls import reverse
from parameterized import parameterized

# from creme.reports.report_chart_registry import (
#     ReportPieChart,
#     report_chart_registry,
# )
from creme.reports.core.chart.plot import Pie, plot_registry
# from creme.reports.views import graph as graph_views
from creme.reports.views import chart as chart_views

from .base import BaseReportsTestCase, skipIfCustomReport


@skipIfCustomReport
# class GraphFetchSettingsTestCase(BaseReportsTestCase):
class ChartFetchSettingsTestCase(BaseReportsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # TODO: use a fake registry instead.
        # report_chart_registry.register(
        #     ReportPieChart(name='fakepie', label='Fake Pie')
        # )
        plot_registry.register(
            Pie(name='fakepie', label='Fake Pie'),
        )

    def test_update_settings__missing_id(self):
        self.login_as_root()
        self.assertPOST404(
            # path=reverse('reports__update_graph_fetch_settings', args=(99999,)),
            path=reverse('reports__update_chart_fetch_settings', args=(99999,)),
            # data={'chart': 'fakepie'},
            data={'plot': 'fakepie'},
        )

    def test_update_settings__not_allowed(self):
        """Edition on reports is needed to update the settings."""
        user = self.login_as_standard(allowed_apps=['reports'])
        self.add_credentials(user.role, own=['VIEW'])  # 'CHANGE'

        # graph = self._create_documents_rgraph(user=self.get_root_user())
        chart = self._create_documents_chart(user=self.get_root_user())
        # self.assertEqual(graph.asc, True)
        self.assertEqual(chart.asc, True)
        # self.assertEqual(graph.chart, None)
        self.assertEqual(chart.plot_name, None)

        # with self.assertLogs(graph_views.logger, level='WARNING') as logs:
        with self.assertLogs(chart_views.logger, level='WARNING') as logs:
            response = self.assertPOST200(
                # path=reverse('reports__update_graph_fetch_settings', args=(graph.pk,)),
                path=reverse('reports__update_chart_fetch_settings', args=(chart.id,)),
                # data={'sort': 'DESC', 'chart': 'fakepie'}
                data={'sort': 'DESC', 'plot': 'fakepie'}
            )

        # self.assertJSONEqual(response.content, {'sort': 'ASC', 'chart': None})
        self.assertJSONEqual(response.content, {'sort': 'ASC', 'plot': None})

        self.assertEqual([
            # f'WARNING:creme.reports.views.graph:The ReportGraph id="{graph.id}" '
            f'WARNING:creme.reports.views.chart:The ReportChart id="{chart.id}" '
            'cannot be edited, so the settings are not saved.'
        ], logs.output)

    @parameterized.expand([
        # ({}, 'Chart value is missing'),
        ({}, 'Plot name is missing'),
        # ({"sort": "ASC"}, 'Chart value is missing'),
        ({'sort': 'ASC'}, 'Plot name is missing'),
        # ({"chart": "unknown", "sort": "ASC"}, (
        ({'plot': 'unknown', 'sort': 'ASC'}, (
            # 'Chart value must be in '
            # f'{[c[0] for c in report_chart_registry] + ["fakepie"]} '
            # '(value=unknown)'
            'Plot name must be in '
            f'{[plot.name for plot in plot_registry] + ["fakepie"]} '
            '(given name="unknown")'
        )),
        # ({"chart": "fakepie", "sort": "unknown"}, (
        ({'plot': 'fakepie', 'sort': 'unknown'}, (
            'Order value must be ASC or DESC (value=unknown)'
        )),
    ])
    def test_update_settings__invalid_argument(self, data, expected):
        user = self.login_as_root_and_get()
        chart = self._create_documents_chart(user=user)

        response = self.assertPOST(
            400,
            path=reverse('reports__update_chart_fetch_settings', args=(chart.pk,)),
            data=data,
        )
        self.assertEqual(response.text, expected)

    def test_update_settings(self):
        user = self.login_as_root_and_get()

        chart = self._create_documents_chart(user=user)
        self.assertEqual(chart.asc, True)
        self.assertEqual(chart.plot_name, None)

        response = self.assertPOST200(
            path=reverse('reports__update_chart_fetch_settings', args=(chart.id,)),
            data={'sort': 'DESC', 'plot': 'fakepie'}
        )
        self.assertJSONEqual(response.content, {'sort': 'DESC', 'plot': 'fakepie'})

        chart.refresh_from_db()
        self.assertEqual(chart.asc, False)
        self.assertEqual(chart.plot_name, 'fakepie')

    def test_update_instance_settings__missing_id(self):
        user = self.login_as_root_and_get()
        url_name = 'reports__update_chart_fetch_settings_for_instance'
        data = {'plot': 'fakepie'}
        self.assertPOST404(
            path=reverse(url_name, args=(99999, 88888)), data=data,
        )

        chart = self._create_documents_chart(user=user)
        config = self._create_chart_instance_brick(chart)
        self.assertPOST404(
            path=reverse(url_name, args=(99999, chart.id)), data=data,
        )
        self.assertPOST404(
            path=reverse(url_name, args=(config.id, 888888)), data=data,
        )

    @parameterized.expand([
        # ({}, 'Chart value is missing'),
        ({}, 'Plot name is missing'),
        # ({"sort": "ASC"}, 'Chart value is missing'),
        ({'sort': 'ASC'}, 'Plot name is missing'),
        # ({"chart": "unknown", "sort": "ASC"}, (
        ({'plot': 'unknown', 'sort': 'ASC'}, (
            # 'Chart value must be in '
            # f'{[c[0] for c in report_chart_registry] + ["fakepie"]} '
            # '(value=unknown)'
            'Plot name must be in '
            f'{[plot.name for plot in plot_registry] + ["fakepie"]} '
            '(given name="unknown")'
        )),
        # ({"chart": "fakepie", "sort": "unknown"}, (
        ({'plot': 'fakepie', 'sort': 'unknown'}, (
            'Order value must be ASC or DESC (value=unknown)'
        )),
    ])
    def test_update_instance_settings__invalid_argument(self, data, expected):
        user = self.login_as_root_and_get()
        chart = self._create_documents_chart(user=user)
        config = self._create_chart_instance_brick(chart)

        response = self.assertPOST(
            400,
            path=reverse(
                'reports__update_chart_fetch_settings_for_instance',
                args=(config.id, chart.id),
            ),
            data=data,
        )
        self.assertEqual(response.text, expected)

    def test_update_instance_settings(self):
        user = self.login_as_root_and_get()
        chart = self._create_documents_chart(user=user)
        config = self._create_chart_instance_brick(chart)

        self.assertEqual(chart.asc, True)
        self.assertEqual(chart.plot_name, None)

        plot_name = 'fakepie'
        response = self.assertPOST200(
            path=reverse(
                'reports__update_chart_fetch_settings_for_instance',
                args=(config.id, chart.id),
            ),
            # data={'sort': 'DESC', 'chart': 'fakepie'},
            data={'sort': 'DESC', 'plot': plot_name},
        )

        # self.assertJSONEqual(response.content, {"sort": "DESC", "chart": "fakepie"})
        self.assertJSONEqual(response.content, {'sort': 'DESC', 'plot': plot_name})

        chart.refresh_from_db()
        self.assertIs(chart.asc, False)
        self.assertEqual(plot_name, chart.plot_name)
