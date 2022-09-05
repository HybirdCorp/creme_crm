from django.urls import reverse
from parameterized import parameterized

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import SetCredentials
from creme.reports.report_chart_registry import (
    ReportPieChart,
    report_chart_registry,
)
from creme.reports.views import graph as graph_views

from .base import BaseReportsTestCase, skipIfCustomReport


@skipIfCustomReport
class GraphFetchSettingsTestCase(BaseReportsTestCase):
    @classmethod
    def setUpClass(cls):
        super(GraphFetchSettingsTestCase, cls).setUpClass()

        # TODO : Use a fake registry instead.
        report_chart_registry.register(
            ReportPieChart(name='fakepie', label='Fake Pie')
        )

    def test_update_settings__missing_id(self):
        self.login()
        self.assertPOST404(
            path=reverse('reports__update_graph_fetch_settings', args=(99999,)),
            data={
                "chart": "fakepie",
            }
        )

    def test_update_settings__not_allowed(self):
        """Edition on reports is needed to update the settings"""
        self.login(is_superuser=False, allowed_apps=['reports'])
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,  # EntityCredentials.CHANGE
            set_type=SetCredentials.ESET_OWN,
        )

        graph = self._create_documents_rgraph(user=self.other_user)
        self.assertEqual(graph.asc, True)
        self.assertEqual(graph.chart, None)

        with self.assertLogs(graph_views.logger, level='WARNING') as logs:
            response = self.assertPOST200(
                path=reverse('reports__update_graph_fetch_settings', args=(graph.pk,)),
                data={
                    "sort": "DESC",
                    "chart": 'fakepie',
                }
            )

        self.assertJSONEqual(response.content, {
            "sort": "ASC",
            "chart": None
        })

        self.assertEqual([
            f'WARNING:creme.reports.views.graph:The ReportGraph id="{graph.id}" '
            'cannot be edited, so the settings are not saved.'
        ], logs.output)

    @parameterized.expand([
        ({}, 'Chart value is missing'),
        ({"sort": "ASC"}, 'Chart value is missing'),
        ({"chart": "unknown", "sort": "ASC"}, (
            'Chart value must be in '
            f'{[c[0] for c in report_chart_registry] + ["fakepie"]} '
            '(value=unknown)'
        )),
        ({"chart": "fakepie", "sort": "unknown"}, (
            'Order value must be ASC or DESC (value=unknown)'
        )),
    ])
    def test_update_settings__invalid_argument(self, data, expected):
        user = self.login()
        graph = self._create_documents_rgraph(user=user)

        response = self.assertPOST(
            400,
            path=reverse('reports__update_graph_fetch_settings', args=(graph.pk,)),
            data=data,
        )

        self.assertEqual(response.content.decode(), expected)

    def test_update_settings(self):
        user = self.login()
        graph = self._create_documents_rgraph(user=user)

        self.assertEqual(graph.asc, True)
        self.assertEqual(graph.chart, None)

        response = self.assertPOST200(
            path=reverse('reports__update_graph_fetch_settings', args=(graph.pk,)),
            data={
                "sort": "DESC",
                "chart": 'fakepie',
            }
        )

        self.assertJSONEqual(response.content, {"sort": "DESC", "chart": "fakepie"})

        graph.refresh_from_db()
        self.assertEqual(graph.asc, False)
        self.assertEqual(graph.chart, 'fakepie')

    def test_update_instance_settings__missing_id(self):
        user = self.login()

        self.assertPOST404(
            path=reverse('reports__update_graph_fetch_settings_for_instance', args=(99999, 88888)),
            data={
                "chart": "fakepie",
            }
        )

        graph = self._create_documents_rgraph(user=user)
        config = self._create_graph_instance_brick(graph)

        self.assertPOST404(
            path=reverse(
                'reports__update_graph_fetch_settings_for_instance', args=(99999, graph.pk)
            ),
            data={
                "chart": "fakepie",
            }
        )

        self.assertPOST404(
            path=reverse(
                'reports__update_graph_fetch_settings_for_instance', args=(config.pk, 888888)
            ),
            data={
                "chart": "fakepie",
            }
        )

    @parameterized.expand([
        ({}, 'Chart value is missing'),
        ({"sort": "ASC"}, 'Chart value is missing'),
        ({"chart": "unknown", "sort": "ASC"}, (
            'Chart value must be in '
            f'{[c[0] for c in report_chart_registry] + ["fakepie"]} '
            '(value=unknown)'
        )),
        ({"chart": "fakepie", "sort": "unknown"}, (
            'Order value must be ASC or DESC (value=unknown)'
        )),
    ])
    def test_update_instance_settings__invalid_argument(self, data, expected):
        user = self.login()
        graph = self._create_documents_rgraph(user=user)
        config = self._create_graph_instance_brick(graph)

        response = self.assertPOST(
            400,
            path=reverse(
                'reports__update_graph_fetch_settings_for_instance', args=(config.pk, graph.pk)
            ),
            data=data
        )

        self.assertEqual(response.content.decode(), expected)

    def test_update_instance_settings(self):
        user = self.login()
        graph = self._create_documents_rgraph(user=user)
        config = self._create_graph_instance_brick(graph)

        self.assertEqual(graph.asc, True)
        self.assertEqual(graph.chart, None)

        response = self.assertPOST200(
            path=reverse(
                'reports__update_graph_fetch_settings_for_instance', args=(config.pk, graph.pk,)
            ),
            data={
                "sort": "DESC",
                "chart": 'fakepie',
            }
        )

        self.assertJSONEqual(response.content, {"sort": "DESC", "chart": "fakepie"})

        graph.refresh_from_db()
        self.assertEqual(graph.asc, False)
        self.assertEqual(graph.chart, 'fakepie')
