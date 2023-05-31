from datetime import date
from functools import partial
from unittest import mock
from unittest.case import skipIf

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
# from django.contrib.sessions.backends.base import SessionBase
from django.db.models.query_utils import Q
# from django.test.client import RequestFactory
from django.urls.base import reverse
from django.utils.timezone import datetime, make_aware
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.auth.entity_credentials import EntityCredentials
# from creme.creme_core.gui.bricks import BricksManager
from creme.creme_core.models.auth import SetCredentials
from creme.creme_core.models.bricks import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    InstanceBrickConfigItem,
)
from creme.creme_core.models.relation import Relation, RelationType
from creme.creme_core.tests import fake_constants
from creme.creme_core.tests.fake_models import (
    FakeContact,
    FakeInvoice,
    FakeOrganisation,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.queries import QSerializer
from creme.reports.bricks import (
    InstanceBricksInfoBrick,
    ReportGraphChartBrick,
    ReportGraphChartInstanceBrick,
    ReportGraphChartListBrick,
)
from creme.reports.constants import RGF_FK, RGF_NOLINK, RGF_RELATION
from creme.reports.core.graph.fetcher import (
    RegularFieldLinkedGraphFetcher,
    SimpleGraphFetcher,
)
from creme.reports.core.graph.hand import _generate_date_format
from creme.reports.report_chart_registry import report_chart_registry
from creme.reports.tests.base import BaseReportsTestCase
from creme.reports.tests.fake_models import (
    FakeReportsDocument,
    FakeReportsFolder,
)

from .base import Report, ReportGraph, skipIfCustomReport, skipIfCustomRGraph

# def detailview_display_context(entity, user):
#     request = RequestFactory().get(entity.get_absolute_url())
#     request.session = SessionBase()
#     request.user = user
#
#     return {
#         'object': entity,
#         'request': request,
#         'user': user,
#         BricksManager.var_name: BricksManager(),
#     }


# def home_display_context(user):
#     request = RequestFactory().get(reverse('creme_core__home'))
#     request.session = SessionBase()
#     request.user = user
#
#     return {
#         'request': request,
#         'user': user,
#         BricksManager.var_name: BricksManager(),
#     }


def create_fake_docs(user):
    create_folder = partial(FakeReportsFolder.objects.create, user=user)
    folder1 = create_folder(title='Internal', created=make_aware(datetime(2022, 5, 1)))
    folder2 = create_folder(title='External', created=make_aware(datetime(2022, 5, 1)))

    create_doc = partial(FakeReportsDocument.objects.create, user=user)
    return (
        create_doc(
            title='Doc#1.1',
            linked_folder=folder1,
            created=make_aware(datetime(2022, 5, 10)),
        ),
        create_doc(
            title='Doc#1.2',
            linked_folder=folder1,
            created=make_aware(datetime(2022, 5, 30)),
        ),
        create_doc(
            title='Doc#2',
            linked_folder=folder2,
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


@skipIf(settings.USE_JQPLOT, "Reports are using JQPlot charts")
@mock.patch('creme.reports.bricks.ReportGraphChartBrick._render')
class D3ReportGraphChartBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    def test_detailview_display__no_data(self, mock_brick_render):
        user = self.get_root_user()
        graph = self._create_documents_rgraph(user=user)

        # context = detailview_display_context(graph, user)
        context = self.build_context(user=user, instance=graph)

        brick = ReportGraphChartBrick()
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
            },
        })

    def test_detailview_display(self, mock_brick_render):
        user = self.get_root_user()
        graph = self._create_documents_rgraph(user=user)

        create_fake_docs(user)

        # context = detailview_display_context(graph, user)
        context = self.build_context(user=user, instance=graph)
        data = [
            {
                'x': '2022',
                'y': 3,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}],
                ),
            },
        ]

        brick = ReportGraphChartBrick()
        brick.detailview_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'graph': graph,
            'data': data,
            'settings_update_url': reverse(
                'reports__update_graph_fetch_settings', args=(graph.id,),
            ),
            'charts': [chart for _, chart in report_chart_registry],
            'props': {
                name: chart.props(graph, data) for name, chart in report_chart_registry
            }
        })


@skipIf(settings.USE_JQPLOT, "Reports are using JQPlot charts")
@mock.patch('creme.reports.bricks.ReportGraphChartListBrick._render')
class D3ReportGraphChartListBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
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
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)

        # context = detailview_display_context(report, user)
        context = self.build_context(user=user, instance=report)

        brick = ReportGraphChartListBrick()
        brick.detailview_display(context)

        mock_brick_render.assert_called_once()
        render_context = mock_brick_render.call_args[0][0]

        self.assertEqual(
            render_context['charts'],
            [chart for _, chart in report_chart_registry],
        )

        self.assertEqual(render_context['rows'], [])

    def test_detailview_display__no_data(self, mock_brick_render):
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)
        graph_by_year, graph_by_month = self._create_report_graphs(report)

        # context = detailview_display_context(report, user)
        context = self.build_context(user=user, instance=report)

        brick = ReportGraphChartListBrick()
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
                },
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
                },
            },
        ])

    def test_detailview_display(self, mock_brick_render):
        user = self.get_root_user()
        report = self._create_simple_documents_report(user=user)
        graph_by_year, graph_by_month = self._create_report_graphs(report)

        create_fake_docs(user)

        brick = ReportGraphChartListBrick()
        # brick.detailview_display(detailview_display_context(report, user))
        brick.detailview_display(self.build_context(user=user, instance=report))

        graph_by_year_data = [
            {
                'x': '2022',
                'y': 3,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}],
                ),
            },
        ]

        by_month_format = _generate_date_format(year=True, month=True)

        graph_by_month_data = [
            {
                'x': datetime(2022, 5, 1).strftime(by_month_format),  # 05-2022
                'y': 2,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[
                        {"created__year": 2022, 'created__month': 5},
                    ]
                ),
            },
            {
                'x': datetime(2022, 8, 1).strftime(by_month_format),  # 08-2022
                'y': 1,
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
                    'reports__update_graph_fetch_settings', args=(graph_by_year.id,),
                ),
                'props': {
                    name: chart.props(graph_by_year, graph_by_year_data)
                    for name, chart in report_chart_registry
                },
            },
            {
                'graph': graph_by_month,
                'data': graph_by_month_data,
                'instance_brick_count': 0,
                'settings_update_url': reverse(
                    'reports__update_graph_fetch_settings', args=(graph_by_month.id,),
                ),
                'props': {
                    name: chart.props(graph_by_month, graph_by_month_data)
                    for name, chart in report_chart_registry
                }
            },
        ])


@skipIf(settings.USE_JQPLOT, "Reports are using JQPlot charts")
@mock.patch('creme.reports.bricks.ReportGraphChartInstanceBrick._render')
class D3ReportGraphChartInstanceBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    def test_detailview_display__no_data(self, mock_brick_render):
        # user = self.login()
        user = self.login_as_root_and_get()
        graph = self._create_documents_rgraph(user=user)
        instance = self._create_graph_instance_brick(graph)

        # context = detailview_display_context(graph, user)
        context = self.build_context(user=user, instance=graph)

        brick = ReportGraphChartInstanceBrick(instance)
        brick.detailview_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'graph': graph,
            'data': [],
            'settings_update_url': reverse(
                'reports__update_graph_fetch_settings_for_instance',
                args=(instance.id, graph.id,),
            ),
            'charts': [chart for _, chart in report_chart_registry],
            'props': {
                name: chart.props(graph, []) for name, chart in report_chart_registry
            },
        })

    def test_detailview_display(self, mock_brick_render):
        # user = self.login()
        user = self.login_as_root_and_get()
        graph = self._create_documents_rgraph(user=user)
        instance = self._create_graph_instance_brick(graph)

        create_fake_docs(user)

        # context = detailview_display_context(graph, user)
        context = self.build_context(user=user, instance=graph)
        data = [
            {
                'x': '2022',
                'y': 3,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}],
                ),
            },
        ]

        brick = ReportGraphChartInstanceBrick(instance)
        brick.detailview_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'graph': graph,
            'data': data,
            'settings_update_url': reverse(
                'reports__update_graph_fetch_settings_for_instance',
                args=(instance.id, graph.id,),
            ),
            'charts': [chart for _, chart in report_chart_registry],
            'props': {
                name: chart.props(graph, data) for name, chart in report_chart_registry
            }
        })

    def test_home_display__no_data(self, mock_brick_render):
        # user = self.login()
        user = self.login_as_root_and_get()
        graph = self._create_documents_rgraph(user=user)
        instance = self._create_graph_instance_brick(graph)

        # context = home_display_context(user)
        context = self.build_context(user=user)

        brick = ReportGraphChartInstanceBrick(instance)
        brick.home_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'graph': graph,
            'data': [],
            'settings_update_url': reverse(
                'reports__update_graph_fetch_settings_for_instance',
                args=(instance.id, graph.id,),
            ),
            'charts': [chart for _, chart in report_chart_registry],
            'props': {
                name: chart.props(graph, []) for name, chart in report_chart_registry
            },
        })

    def test_home_display(self, mock_brick_render):
        # user = self.login()
        user = self.login_as_root_and_get()
        graph = self._create_documents_rgraph(user=user)
        instance = self._create_graph_instance_brick(graph)

        create_fake_docs(user)

        # context = home_display_context(user)
        context = self.build_context(user=user)
        data = [
            {
                'x': '2022',
                'y': 3,
                'url': reverse_listview(
                    'reports__list_fake_documents', q_filters=[{"created__year": 2022}],
                ),
            },
        ]

        brick = ReportGraphChartInstanceBrick(instance)
        brick.home_display(context)

        mock_brick_render.assert_called_once_with({
            **context,
            'graph': graph,
            'data': data,
            'settings_update_url': reverse(
                'reports__update_graph_fetch_settings_for_instance',
                args=(instance.id, graph.id,),
            ),
            'charts': [chart for _, chart in report_chart_registry],
            'props': {
                name: chart.props(graph, data) for name, chart in report_chart_registry
            },
        })


@skipIf(not settings.USE_JQPLOT, "Reports are using D3 charts")
@skipIfCustomReport
@skipIfCustomRGraph
class JQplotReportGraphChartInstanceBrickTestCase(BrickTestCaseMixin, BaseReportsTestCase):
    @staticmethod
    def _build_add_brick_url(rgraph):
        return reverse('reports__create_instance_brick', args=(rgraph.id,))

    @staticmethod
    def _build_fetchfrombrick_url(ibi, entity, order='ASC', chart=None, save_settings=None):
        uri = '{}?order={}'.format(
            reverse('reports__fetch_graph_from_brick', args=(ibi.id, entity.id)),
            order,
        )

        if chart is not None:
            uri += f'&chart={chart}'

        if save_settings is not None:
            uri += f'&save_settings={save_settings}'

        return uri

    def test_fetchfrombrick_save_settings(self):
        # user = self.login()
        user = self.login_as_root_and_get()
        folder = FakeReportsFolder.objects.create(title='my Folder', user=user)
        rgraph = self._create_documents_rgraph(user=user)

        fetcher = RegularFieldLinkedGraphFetcher(graph=rgraph, value='linked_folder')
        self.assertIsNone(fetcher.error)

        ibci = fetcher.create_brick_config_item()

        chart = 'piechart'
        url = self._build_fetchfrombrick_url
        self.assertGET200(url(ibci, folder, 'ASC', chart=chart))
        rgraph = self.refresh(rgraph)
        self.assertIsNone(rgraph.chart)
        self.assertTrue(rgraph.asc)

        self.assertGET200(url(ibci, folder, 'ASC', chart=chart, save_settings='false'))
        self.assertIsNone(self.refresh(rgraph).chart)

        self.assertGET404(url(ibci, folder, 'ASC', chart=chart, save_settings='invalid'))
        self.assertIsNone(self.refresh(rgraph).chart)

        self.assertGET404(url(ibci, folder, 'ASC', chart='invalid', save_settings='true'))
        self.assertIsNone(self.refresh(rgraph).chart)

        self.assertGET200(url(ibci, folder, 'ASC', chart=chart, save_settings='true'))
        rgraph = self.refresh(rgraph)
        self.assertEqual(chart, rgraph.chart)
        self.assertTrue(rgraph.asc)

        self.assertGET200(url(ibci, folder, 'DESC', save_settings='true'))
        rgraph = self.refresh(rgraph)
        self.assertEqual(chart, rgraph.chart)
        self.assertFalse(rgraph.asc)

    def test_add_graph_instance_brick01(self):
        # user = self.login()
        user = self.login_as_root_and_get()
        rgraph = self._create_invoice_report_n_graph(user=user)
        self.assertFalse(
            InstanceBrickConfigItem.objects.filter(entity=rgraph.id).exists()
        )

        url = self._build_add_brick_url(rgraph)
        response_get = self.assertGET200(url)
        self.assertTemplateUsed(
            response_get,
            'creme_core/generics/blockform/add-popup.html',
        )

        get_ctxt1 = response_get.context.get
        self.assertEqual(
            _('Create an instance block for «{entity}»').format(entity=rgraph),
            get_ctxt1('title'),
        )
        self.assertEqual(_('Save the block'), get_ctxt1('submit_label'))

        # ---
        response_post_error = self.assertPOST200(url)
        self.assertFormError(
            response_post_error.context['form'],
            field='fetcher',
            errors=_('This field is required.'),
        )

        self.assertNoFormError(self.client.post(url, data={'fetcher': RGF_NOLINK}))

        item = self.get_alone_element(
            InstanceBrickConfigItem.objects.filter(entity=rgraph.id)
        )
        self.assertEqual('instanceblock_reports-graph', item.brick_class_id)
        self.assertEqual(RGF_NOLINK, item.get_extra_data('type'))
        self.assertIsNone(item.get_extra_data('value'))
        self.assertIsNone(item.brick.errors)

        brick_id = item.brick_id
        self.assertEqual(f'instanceblock-{item.id}', brick_id)

        title = '{} - {}'.format(rgraph.name, _('No volatile column'))
        self.assertEqual(title, ReportGraphChartInstanceBrick(item).verbose_name)

        brick = item.brick
        self.assertIsInstance(brick, ReportGraphChartInstanceBrick)
        self.assertEqual(item,  brick.config_item)
        self.assertEqual(title, brick.verbose_name)
        self.assertEqual(
            _(
                'This block displays the graph «{graph}», contained by the report «{report}».\n'
                'App: Reports'
            ).format(graph=rgraph.name, report=rgraph.linked_report.name),
            brick.description,
        )

        # ----------------------------------------------------------------------
        response_duplicate = self.assertPOST200(url, data={'fetcher': RGF_NOLINK})
        self.assertFormError(
            response_duplicate.context['form'],
            field='fetcher',
            errors=_(
                'The instance block for «{graph}» with these parameters already exists!'
            ).format(graph=rgraph.name),
        )

        # ----------------------------------------------------------------------
        response_info = self.assertGET200(
            reverse('reports__instance_bricks_info', args=(rgraph.id,))
        )
        self.assertTemplateUsed(response_info, 'reports/bricks/instance-bricks-info.html')
        self.assertEqual(rgraph, response_info.context.get('object'))
        brick_node = self.get_brick_node(
            self.get_html_tree(response_info.content),
            brick=InstanceBricksInfoBrick,
        )
        vname_node = self.get_html_node_or_fail(brick_node, './/td[@data-table-primary-column]')
        self.assertEqual(_('No volatile column'), vname_node.text)

        # ----------------------------------------------------------------------
        # Display on home
        BrickHomeLocation.objects.all().delete()
        BrickHomeLocation.objects.create(brick_id=brick_id, order=1)
        response_home = self.assertGET200('/')
        self.assertTemplateUsed(response_home, 'reports/bricks/graph.html')
        self.get_brick_node(self.get_html_tree(response_home.content), brick_id)

        # ----------------------------------------------------------------------
        # Display on detailview
        ct_invoice = ContentType.objects.get_for_model(FakeInvoice)
        BrickDetailviewLocation.objects.filter(content_type=ct_invoice).delete()
        BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_id,
            order=1,
            zone=BrickDetailviewLocation.RIGHT, model=FakeInvoice,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='BullFrog')
        orga2 = create_orga(name='Maxis')
        orga3 = create_orga(name='Bitmap brothers')

        invoice = self._create_invoice(orga1, orga2, issuing_date=date(2014, 10, 16))
        self._create_invoice(orga1, orga3, issuing_date=date(2014, 11, 3))

        response_dview = self.assertGET200(invoice.get_absolute_url())
        self.assertTemplateUsed(response_dview, 'reports/bricks/graph.html')
        self.get_brick_node(self.get_html_tree(response_dview.content), brick_id)

        # ASC ------------------------------------------------------------------
        url_fetch_asc = self._build_fetchfrombrick_url(item, invoice, 'ASC')
        with self.settings(USE_L10N=False, DATE_INPUT_FORMATS=['%d/%m/%Y']):
            result_asc = self.assertGET200(url_fetch_asc).json()
            self.assertIsDict(result_asc, length=2)
            self.assertListEqual(['10/2014', '11/2014'], result_asc.get('x'))

            y_asc = result_asc.get('y')
            self.assertEqual(0, y_asc[0][0])
            self.assertListviewURL(
                y_asc[0][1],
                FakeInvoice,
                Q(issuing_date__month=10, issuing_date__year=2014),
            )

            result_asc2 = self.assertGET200(url_fetch_asc).json()
            self.assertEqual(result_asc, result_asc2)

        # DESC -----------------------------------------------------------------
        with self.settings(USE_L10N=False, DATE_INPUT_FORMATS=['%d-%m-%Y']):
            result_desc = self.assertGET200(
                self._build_fetchfrombrick_url(item, invoice, 'DESC'),
            ).json()

        self.assertListEqual(['11-2014', '10-2014'], result_desc.get('x'))

        y_desc = result_desc.get('y')
        self.assertEqual(0, y_desc[0][0])
        self.assertListviewURL(
            y_desc[0][1],
            FakeInvoice,
            Q(issuing_date__month=11, issuing_date__year=2014),
        )

        # ----------------------------------------------------------------------
        self.assertGET404(self._build_fetchfrombrick_url(item, invoice, 'FOOBAR'))

    def test_add_graph_instance_brick02(self):
        "Volatile column (RGF_FK)."
        # user = self.login()
        user = self.login_as_root_and_get()
        rgraph = self._create_documents_rgraph(user=user)

        url = self._build_add_brick_url(rgraph)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = [*response.context['form'].fields['fetcher'].widget.choices]

        self.assertGreaterEqual(len(choices), 3)
        self.assertInChoices(
            value=f'{RGF_NOLINK}|',
            label=pgettext('reports-volatile_choice', 'None'),
            choices=choices,
        )

        fk_name = 'linked_folder'
        folder_choice = f'{RGF_FK}|{fk_name}'
        field_choices = self.get_choices_group_or_fail(label=_('Fields'), choices=choices)
        self.assertInChoices(
            value=folder_choice,
            label=_('Folder'),
            choices=field_choices,
        )

        self.assertNoFormError(self.client.post(url, data={'fetcher': folder_choice}))

        item = self.get_alone_element(
            InstanceBrickConfigItem.objects.filter(entity=rgraph.id)
        )
        self.assertEqual('instanceblock_reports-graph', item.brick_class_id)
        self.assertEqual(RGF_FK, item.get_extra_data('type'))
        self.assertEqual(fk_name, item.get_extra_data('value'))

        title = '{} - {}'.format(rgraph.name, _('{field} (Field)').format(field=_('Folder')))
        self.assertEqual(title, ReportGraphChartInstanceBrick(item).verbose_name)
        self.assertEqual(title, str(item))

        # Display on detail-view
        create_folder = partial(FakeReportsFolder.objects.create, user=user)
        folder1 = create_folder(title='Internal')
        folder2 = create_folder(title='External')

        create_doc = partial(FakeReportsDocument.objects.create, user=user)
        doc1 = create_doc(title='Doc#1.1', linked_folder=folder1)
        create_doc(title='Doc#1.2', linked_folder=folder1)
        create_doc(title='Doc#2',   linked_folder=folder2)

        ct = folder1.entity_type
        BrickDetailviewLocation.objects.filter(content_type=ct).delete()
        BrickDetailviewLocation.objects.create_if_needed(
            brick=item.brick_id,
            order=1,
            zone=BrickDetailviewLocation.RIGHT, model=FakeReportsFolder,
        )

        response = self.assertGET200(folder1.get_absolute_url())
        self.assertTemplateUsed(response, 'reports/bricks/graph.html')

        fetcher = ReportGraphChartInstanceBrick(item).fetcher
        self.assertIsNone(fetcher.error)

        x, y = fetcher.fetch_4_entity(entity=folder1, user=user)  # TODO: order

        year = doc1.created.year
        self.assertListEqual([str(year)], x)
        qfilter = [{'linked_folder': folder1.id}, {'created__year': year}]
        self.assertListEqual(
            [[
                2,
                reverse_listview('reports__list_fake_documents', qfilter),
            ]],
            y,
        )

    def test_add_graph_instance_brick_not_superuser01(self):
        apps = ['reports']
        # user = self.login(is_superuser=False, allowed_apps=apps, admin_4_apps=apps)
        user = self.login_as_standard(allowed_apps=apps, admin_4_apps=apps)
        rgraph = self._create_invoice_report_n_graph(user=user)
        self.assertGET200(self._build_add_brick_url(rgraph))

    def test_add_graph_instance_brick_not_superuser02(self):
        "Admin permission needed."
        # user = self.login(
        user = self.login_as_standard(
            # is_superuser=False,
            allowed_apps=['reports'],  # admin_4_apps=['reports'],
        )
        rgraph = self._create_invoice_report_n_graph(user=user)
        self.assertGET403(self._build_add_brick_url(rgraph))

    def test_add_graph_instance_brick02_error01(self):
        "Volatile column (RFT_FIELD): invalid field."
        # user = self.login()
        user = self.login_as_root_and_get()
        rgraph = self._create_documents_rgraph(user=user)

        # We create voluntarily an invalid item
        fname = 'invalid'
        ibci = InstanceBrickConfigItem.objects.create(
            entity=rgraph,
            # brick_class_id=ReportGraphChartInstanceBrick.id_,
            brick_class_id=ReportGraphChartInstanceBrick.id,
        )
        ibci.set_extra_data(key='type',  value=RGF_FK)
        ibci.set_extra_data(key='value', value=fname)

        folder = FakeReportsFolder.objects.create(user=user, title='My folder')

        fetcher = ReportGraphChartInstanceBrick(ibci).fetcher
        x, y = fetcher.fetch_4_entity(entity=folder, user=user)

        self.assertEqual([], x)
        self.assertEqual([], y)
        self.assertEqual(_('The field is invalid.'), fetcher.error)
        self.assertEqual('??',                       fetcher.verbose_name)

        self.assertEqual([_('The field is invalid.')], ibci.brick.errors)

    def test_add_graph_instance_brick02_error02(self):
        "Volatile column (RFT_FIELD): field is not a FK to CremeEntity."
        # user = self.login()
        user = self.login_as_root_and_get()
        rgraph = self._create_documents_rgraph(user=user)

        # We create voluntarily an invalid item
        fname = 'description'
        ibci = InstanceBrickConfigItem(
            entity=rgraph,
            # brick_class_id=ReportGraphChartInstanceBrick.id_,
            brick_class_id=ReportGraphChartInstanceBrick.id,
        )
        ibci.set_extra_data(key='type',  value=RGF_FK)
        ibci.set_extra_data(key='value', value=fname)
        ibci.save()

        folder = FakeReportsFolder.objects.create(user=user, title='My folder')

        fetcher = ReportGraphChartInstanceBrick(ibci).fetcher
        x, y = fetcher.fetch_4_entity(entity=folder, user=user)

        self.assertEqual([], x)
        self.assertEqual([], y)
        self.assertEqual(_('The field is invalid (not a foreign key).'), fetcher.error)

    def test_add_graph_instance_brick02_error03(self):
        "Volatile column (RGF_FK): field is not a FK to the given Entity type."
        # user = self.login()
        user = self.login_as_root_and_get()
        rgraph = self._create_documents_rgraph(user=user)

        fetcher = RegularFieldLinkedGraphFetcher(graph=rgraph, value='linked_folder')
        self.assertIsNone(fetcher.error)

        ibci = fetcher.create_brick_config_item()
        self.assertIsNotNone(ibci)

        x, y = fetcher.fetch_4_entity(entity=user.linked_contact, user=user)
        self.assertListEqual([], x)
        self.assertListEqual([], y)
        self.assertIsNone(fetcher.error)

    def test_add_graph_instance_brick03(self):
        "Volatile column (RGF_RELATION)."
        # user = self.login()
        user = self.login_as_root_and_get()
        report = self._create_simple_contacts_report(user=user)
        rtype = RelationType.objects.get(pk=fake_constants.FAKE_REL_SUB_EMPLOYED_BY)
        incompatible_rtype = RelationType.objects.smart_update_or_create(
            ('reports-subject_related_doc', 'is related to doc',   [Report]),
            ('reports-object_related_doc',  'is linked to report', [FakeReportsDocument]),
        )[0]

        rgraph = ReportGraph.objects.create(
            user=user, linked_report=report,
            name='Number of created contacts / year',
            abscissa_cell_value='created', abscissa_type=ReportGraph.Group.YEAR,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        url = self._build_add_brick_url(rgraph)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = [*response.context['form'].fields['fetcher'].widget.choices]

        rel_choices = self.get_choices_group_or_fail(label=_('Relationships'), choices=choices)

        choice_id = f'{RGF_RELATION}|{rtype.id}'
        self.assertInChoices(value=choice_id, label=str(rtype), choices=rel_choices)
        self.assertNotInChoices(value=f'rtype-{incompatible_rtype.id}', choices=rel_choices)

        self.assertNoFormError(self.client.post(url, data={'fetcher': choice_id}))

        item = self.get_alone_element(
            InstanceBrickConfigItem.objects.filter(entity=rgraph.id)
        )
        self.assertEqual('instanceblock_reports-graph', item.brick_class_id)
        self.assertEqual(RGF_RELATION, item.get_extra_data('type'))
        self.assertEqual(rtype.id,     item.get_extra_data('value'))

        self.assertEqual(
            '{} - {}'.format(
                rgraph.name,
                _('{rtype} (Relationship)').format(rtype=rtype),
            ),
            ReportGraphChartInstanceBrick(item).verbose_name,
        )

        create_contact = partial(FakeContact.objects.create, user=user)
        sonsaku = create_contact(first_name='Sonsaku', last_name='Hakufu')
        ryomou  = create_contact(first_name='Ryomou',  last_name='Shimei')
        create_contact(first_name='Kan-u', last_name='Unchô')

        nanyo = FakeOrganisation.objects.create(user=user, name='Nanyô')

        create_rel = partial(Relation.objects.create, user=user, type=rtype, object_entity=nanyo)
        create_rel(subject_entity=sonsaku)
        create_rel(subject_entity=ryomou)

        fetcher = ReportGraphChartInstanceBrick(item).fetcher
        self.assertIsNone(fetcher.error)

        x, y = fetcher.fetch_4_entity(entity=nanyo, user=user)

        year = sonsaku.created.year
        self.assertListEqual([str(year)], x)

        qfilter = [
            {'relations__object_entity': nanyo.id},
            {'relations__type': rtype},
            {'created__year': year},
        ]

        self.assertListEqual(
            [[
                2,
                get_listview_url('/tests/contacts', qfilter),
            ]],
            y,
        )

        # Invalid choice
        choice = 'invalid'
        response = self.assertPOST200(url, data={'fetcher': choice})
        self.assertFormError(
            response.context['form'],
            field='fetcher',
            error=_(
                'Select a valid choice. %(value)s is not one of the available choices.'
            ) % {'value': choice},
        )

    def test_add_graph_instance_brick03_error(self):
        "Volatile column (RFT_RELATION): invalid relation type."
        # user = self.login()
        user = self.login_as_root_and_get()
        rgraph = self._create_documents_rgraph(user=user)

        # We create voluntarily an invalid item
        rtype_id = 'invalid'
        ibci = InstanceBrickConfigItem.objects.create(
            entity=rgraph,
            # brick_class_id=ReportGraphChartInstanceBrick.id_,
            brick_class_id=ReportGraphChartInstanceBrick.id,
        )
        ibci.set_extra_data(key='type',  value=RGF_RELATION)
        ibci.set_extra_data(key='value', value=rtype_id)

        fetcher = ReportGraphChartInstanceBrick(ibci).fetcher
        x, y = fetcher.fetch_4_entity(entity=user.linked_contact, user=user)
        self.assertListEqual([], x)
        self.assertListEqual([], y)
        self.assertEqual(_('The relationship type is invalid.'), fetcher.error)
        self.assertEqual('??',                                   fetcher.verbose_name)

    def test_get_fetcher_from_instance_brick(self):
        "Invalid type."
        # self.login()
        user = self.login_as_root_and_get()
        rgraph = self._create_documents_rgraph(user=user)

        ibci = InstanceBrickConfigItem.objects.create(
            # brick_class_id=ReportGraphChartInstanceBrick.id_,
            brick_class_id=ReportGraphChartInstanceBrick.id,
            entity=rgraph,
        )

        # No extra data
        fetcher1 = ReportGraphChartInstanceBrick(ibci).fetcher
        self.assertIsInstance(fetcher1, SimpleGraphFetcher)
        msg = _('Invalid volatile link ; please contact your administrator.')
        self.assertEqual(msg, fetcher1.error)

        # Invalid type
        ibci.set_extra_data(key='type', value='invalid')
        fetcher2 = ReportGraphChartInstanceBrick(ibci).fetcher
        self.assertIsInstance(fetcher2, SimpleGraphFetcher)
        self.assertEqual(msg, fetcher2.error)

    def test_fetch_with_credentials(self):
        "Filter retrieved entities with permission (brick + regular field version)."
        # user = self.login(is_superuser=False, allowed_apps=['creme_core', 'reports'])
        user = self.login_as_standard(allowed_apps=['creme_core', 'reports'])
        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_OWN,
        )

        folder = FakeReportsFolder.objects.create(title='my Folder', user=user)

        create_doc = partial(FakeReportsDocument.objects.create, linked_folder=folder)
        doc1 = create_doc(title='Doc#1', user=user)
        create_doc(title='Doc#2', user=user)
        # Cannot be seen => should not be used to compute aggregate
        # doc3 = create_doc(title='Doc#3', user=self.other_user)
        doc3 = create_doc(title='Doc#3', user=self.get_root_user())
        self.assertEqual(doc1.created.year, doc3.created.year)

        rgraph = self._create_documents_rgraph(user=user)
        fetcher = RegularFieldLinkedGraphFetcher(graph=rgraph, value='linked_folder')
        self.assertIsNone(fetcher.error)

        ibci = fetcher.create_brick_config_item()
        response = self.assertGET200(self._build_fetchfrombrick_url(ibci, folder, 'ASC'))

        result = response.json()
        self.assertListEqual([str(doc1.created.year)], result.get('x'))
        self.assertEqual(2, result.get('y')[0][0])
