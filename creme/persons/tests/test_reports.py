from datetime import date
from functools import partial

from django.apps import apps
from django.db.models.query_utils import Q
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import (
    BrickDetailviewLocation,
    FakeInvoice,
    InstanceBrickConfigItem,
)
from creme.creme_core.tests.base import CremeTestCase, skipIfNotInstalled
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.queries import QSerializer
from creme.persons.constants import RGF_OWNED
from creme.persons.reports import OwnedGraphFetcher

from .base import Contact, Organisation

if apps.is_installed('creme.reports'):
    from creme.reports.bricks import ReportGraphChartInstanceBrick
    from creme.reports.core.graph.fetcher import GraphFetcher
    from creme.reports.tests.base import (
        Report,
        ReportGraph,
        skipIfCustomReport,
        skipIfCustomRGraph,
    )
else:
    from unittest import skipIf

    def skipIfCustomReport(test_func):
        return skipIf(True, 'Reports app not installed')(test_func)

    skipIfCustomRGraph = skipIfCustomReport


@skipIfNotInstalled('creme.reports')
class PersonsReportsTestCase(BrickTestCaseMixin, CremeTestCase):
    @skipIfCustomReport
    @skipIfCustomRGraph
    def test_report_graph_fetcher01(self):
        "Contact-user."
        user = self.login()
        report = Report.objects.create(user=user, name='Fetcher Test', ct=Organisation)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value='creation_date', abscissa_type=ReportGraph.Group.YEAR,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        url = reverse('reports__create_instance_brick', args=(graph.id,))
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = [*response.context['form'].fields['fetcher'].widget.choices]

        vname = _('Belongs to the Contact/User')
        self.assertInChoices(
            value=f'{RGF_OWNED}|',
            label=vname,
            choices=choices,
        )

        self.assertNoFormError(self.client.post(url, data={'fetcher': RGF_OWNED}))

        ibci = self.get_object_or_fail(InstanceBrickConfigItem, entity=graph.id)
        self.assertEqual('instanceblock_reports-graph', ibci.brick_class_id)
        self.assertEqual(RGF_OWNED, ibci.get_extra_data('type'))
        self.assertIsNone(ibci.get_extra_data('value'))

        brick = ReportGraphChartInstanceBrick(ibci)
        self.assertEqual(
            f'{graph.name} - {vname}',
            brick.verbose_name,
        )
        self.assertListEqual([Contact], brick.target_ctypes)

        # Display on detail-view
        create_orga = partial(Organisation.objects.create, user=user)
        create_orga(name='Orga#1', creation_date=date(year=2015, month=1, day=1))
        create_orga(name='Orga#2', creation_date=date(year=2015, month=2, day=2))
        create_orga(
            name='Orga#3', creation_date=date(year=2015, month=3, day=3), user=self.other_user,
        )
        create_orga(name='Orga#4', creation_date=date(year=2016, month=4, day=4))

        fetcher = brick.fetcher
        self.assertIsInstance(fetcher, OwnedGraphFetcher)
        self.assertIsNone(fetcher.error)
        self.assertEqual(vname, fetcher.verbose_name)

        x, y = fetcher.fetch_4_entity(entity=user.linked_contact, user=user)
        self.assertListEqual(['2015', '2016'], x)

        qfilter_serializer = QSerializer()
        lv_url = reverse('persons__list_organisations')

        def build_url(year):
            return '{}?q_filter={}'.format(
                lv_url,
                qfilter_serializer.dumps(
                    Q(user=user.id) & Q(creation_date__year=year)
                ),
            )

        self.assertListEqual([[2, build_url(2015)], [1, build_url(2016)]], y)

        # ---
        ibci = fetcher.create_brick_config_item()
        BrickDetailviewLocation.objects.create_if_needed(
            brick=ibci.brick_id,
            order=1,
            zone=BrickDetailviewLocation.RIGHT, model=Contact,
        )

        contact = user.linked_contact
        response = self.assertGET200(contact.get_absolute_url())
        dom = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(dom, brick=ibci.brick_id)
        self.assertBrickHasNotClass(brick_node, 'is-empty')

        volatile_span = self.get_html_node_or_fail(
            brick_node, './/span[@class="graph-volatile-value"]',
        )
        self.assertEqual(vname, volatile_span.text)

        # --
        self.assertGET200(
            reverse('reports__fetch_graph_from_brick', args=(ibci.id, contact.id))
        )

    @skipIfCustomReport
    @skipIfCustomRGraph
    def test_report_graph_fetcher02(self):
        "Basic Contact (is_user=None)."
        user = self.login()
        report = Report.objects.create(user=user, name='Fetcher Test', ct=Organisation)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value='creation_date', abscissa_type=ReportGraph.Group.YEAR,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        fetcher = OwnedGraphFetcher(graph=graph)
        self.assertIsNone(fetcher.error)

        contact = Contact.objects.create(
            user=user,
            first_name='Spike',
            last_name='Spiegel',
        )

        with self.assertRaises(GraphFetcher.UselessResult) as cm:
            fetcher.fetch_4_entity(entity=contact, user=user)

        self.assertEqual(
            'OwnedGraphFetcher is only useful for Contacts representing users '
            '(see field "is_user")',
            str(cm.exception)
        )

        # ---
        ibci = fetcher.create_brick_config_item()
        BrickDetailviewLocation.objects.create_if_needed(
            brick=ibci.brick_id,
            order=1,
            zone=BrickDetailviewLocation.RIGHT, model=Contact,
        )

        response1 = self.assertGET200(contact.get_absolute_url())
        dom = self.get_html_tree(response1.content)
        brick_node = self.get_brick_node(dom, brick=ibci.brick_id)
        self.assertBrickHasClass(brick_node, 'is-empty')

        # --
        response2 = self.assertGET200(
            reverse('reports__fetch_graph_from_brick', args=(ibci.id, contact.id))
        )

        result = response2.json()
        self.assertIsInstance(result, dict)
        self.assertIsNone(result.get('x'))
        self.assertIsNone(result.get('y'))

    @skipIfCustomReport
    @skipIfCustomRGraph
    def test_report_graph_fetcher03(self):
        "Entity is not even a Contact."
        user = self.login()
        report = Report.objects.create(user=user, name='Fetcher Test', ct=Organisation)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value='creation_date', abscissa_type=ReportGraph.Group.YEAR,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        fetcher = OwnedGraphFetcher(graph=graph)
        invoice = FakeInvoice.objects.create(user=user, name='SwordFish II')

        with self.assertRaises(GraphFetcher.IncompatibleContentType) as cm:
            fetcher.fetch_4_entity(entity=invoice, user=user)

        error_msg = _(
            "The volatile link «Belongs to the Contact/User» is only compatible with Contacts ; "
            "you should fix your blocks' configuration."
        )
        self.assertEqual(error_msg, str(cm.exception))

        # ---
        ibci = fetcher.create_brick_config_item()
        BrickDetailviewLocation.objects.create_if_needed(
            brick=ibci.brick_id,
            order=1,
            zone=BrickDetailviewLocation.RIGHT, model=FakeInvoice,
        )

        with self.assertLogs(level='WARNING') as logs_manager:
            response1 = self.assertGET200(invoice.get_absolute_url())

        self.assertNoBrick(self.get_html_tree(response1.content), brick_id=ibci.brick_id)
        self.assertIn(
            f'WARNING:creme.creme_core.views.generic.detailview:'
            f'This brick cannot be displayed on this content type '
            f'(you have a config problem): {ibci.brick_id}',
            logs_manager.output,
        )

        # --
        response2 = self.assertGET200(
            reverse('reports__fetch_graph_from_brick', args=(ibci.id, invoice.id))
        )

        result = response2.json()
        self.assertIsInstance(result, dict)
        self.assertIsNone(result.get('x'))
        self.assertIsNone(result.get('y'))

    def test_fetcher_init(self):
        "No value is needed."
        user = self.create_user()
        report = Report.objects.create(user=user, name='Fetcher Test', ct=Organisation)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value='created', abscissa_type=ReportGraph.Group.YEAR,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        fetcher = OwnedGraphFetcher(graph=graph, value='whatever')
        self.assertEqual(_('No value is needed.'), fetcher.error)
