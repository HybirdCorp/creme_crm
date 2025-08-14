from uuid import uuid4

from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.models import (
    FakeContact,
    FakeImage,
    FakeOrganisation,
    FieldsConfig,
    InstanceBrickConfigItem,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_constants import (
    FAKE_REL_SUB_BILL_ISSUED,
    FAKE_REL_SUB_EMPLOYED_BY,
)
from creme.reports.bricks import ReportChartInstanceBrick
from creme.reports.constants import AbscissaGroup, OrdinateAggregator
from creme.reports.core.chart.fetcher import (
    ChartFetcher,
    ChartFetcherRegistry,
    RegularFieldLinkedChartFetcher,
    RelationLinkedChartFetcher,
    SimpleChartFetcher,
)
from creme.reports.models import ReportChart
from creme.reports.tests.base import Report


# TODO: test fetch() ??
class ChartFetcherTestCase(CremeTestCase):
    def test_simple(self):
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            # user=user,
            name='Field Test', linked_report=report,
            abscissa_cell_value='created', abscissa_type=AbscissaGroup.YEAR,
            ordinate_type=OrdinateAggregator.COUNT,
        )

        fetcher1 = SimpleChartFetcher(chart=chart)
        self.assertIsNone(fetcher1.error)
        self.assertEqual(_('No volatile column'), fetcher1.verbose_name)

        ibci = fetcher1.create_brick_config_item()
        self.assertIsInstance(ibci, InstanceBrickConfigItem)
        self.assertEqual(chart.linked_report_id, ibci.entity_id)
        self.assertEqual(ReportChartInstanceBrick.id, ibci.brick_class_id)
        # self.assertEqual(RGF_NOLINK, ibci.get_extra_data('type'))
        self.assertEqual(SimpleChartFetcher.type_id, ibci.get_extra_data('type'))
        self.assertIsNone(ibci.get_extra_data('value'))
        self.assertUUIDEqual(chart.uuid, ibci.get_extra_data('chart'))

        # ---
        fetcher2 = SimpleChartFetcher(chart=chart, value='last_name')
        self.assertEqual(_('No value is needed.'), fetcher2.error)

        self.assertListEqual(
            [('', pgettext('reports-volatile_choice', 'None'))],
            [*SimpleChartFetcher.choices(FakeContact)],
        )

        # ----
        # TODO: move to test for bricks?
        brick = ReportChartInstanceBrick(ibci)
        self.assertIsNone(brick.errors)
        self.assertEqual(
            '{} - {}'.format(chart.name, _('No volatile column')),
            brick.verbose_name,
        )
        self.assertListEqual([], brick.target_ctypes)

        b_fetcher = brick.fetcher
        self.assertIsInstance(b_fetcher, SimpleChartFetcher)
        self.assertIsNone(b_fetcher.error)
        self.assertEqual(chart, b_fetcher.chart)

    def test_fk01(self):
        "ForeignKey ; UUID parameter."
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            # user=user,
            name='Field Test', linked_report=report,
            abscissa_cell_value='created', abscissa_type=AbscissaGroup.YEAR,
            ordinate_type=OrdinateAggregator.COUNT,
        )

        fname = 'image'
        fetcher1 = RegularFieldLinkedChartFetcher(chart=chart, value=fname)
        self.assertIsNone(fetcher1.error)
        self.assertEqual(
            _('{field} (Field)').format(field=_('Photograph')),
            fetcher1.verbose_name,
        )

        uid = uuid4()
        ibci = fetcher1.create_brick_config_item(uuid=uid)
        self.assertEqual(uid, ibci.uuid)
        # self.assertEqual(RGF_FK, ibci.get_extra_data('type'))
        self.assertEqual(
            RegularFieldLinkedChartFetcher.type_id, ibci.get_extra_data('type'),
        )
        self.assertEqual(fname, ibci.get_extra_data('value'))

        fetcher2 = RegularFieldLinkedChartFetcher(chart=chart)
        self.assertEqual(_('No field given.'), fetcher2.error)
        self.assertEqual('??', fetcher2.verbose_name)

        fetcher3 = RegularFieldLinkedChartFetcher(chart=chart, value='invalid')
        self.assertEqual(_('The field is invalid.'), fetcher3.error)

        fetcher4 = RegularFieldLinkedChartFetcher(chart=chart, value='last_name')
        self.assertEqual(
            _('The field is invalid (not a foreign key).'),
            fetcher4.error,
        )

        fetcher5 = RegularFieldLinkedChartFetcher(chart=chart, value='position')
        self.assertEqual(
            _('The field is invalid (not a foreign key to CremeEntity).'),
            fetcher5.error,
        )

        self.assertListEqual(
            [('image', _('Photograph'))],
            [*RegularFieldLinkedChartFetcher.choices(FakeContact)],
        )

        # ----
        # TODO: move to test for bricks ?
        brick = ReportChartInstanceBrick(ibci)
        self.assertIsNone(brick.errors)
        self.assertEqual(
            '{} - {}'.format(
                chart.name,
                _('{field} (Field)').format(field=_('Photograph')),
            ),
            brick.verbose_name,
        )
        self.assertListEqual([FakeImage], brick.target_ctypes)

        b_fetcher = brick.fetcher
        self.assertIsInstance(b_fetcher, RegularFieldLinkedChartFetcher)
        self.assertIsNone(b_fetcher.error)
        self.assertEqual(fname, b_fetcher._field.name)

    def test_fk02(self):
        "Hidden field."
        hidden_fname = 'image'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart(name='Field Test', linked_report=report)

        fetcher = RegularFieldLinkedChartFetcher(chart=chart, value=hidden_fname)
        self.assertEqual(_('The field is hidden.'), fetcher.error)

    def test_relation(self):
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value='created', abscissa_type=AbscissaGroup.YEAR,
            ordinate_type=OrdinateAggregator.COUNT,
        )

        fetcher1 = RelationLinkedChartFetcher(chart=chart, value=FAKE_REL_SUB_EMPLOYED_BY)
        self.assertIsNone(fetcher1.error)
        self.assertEqual(
            _('{rtype} (Relationship)').format(rtype='is an employee of — employs'),
            fetcher1.verbose_name,
        )

        ibci = fetcher1.create_brick_config_item()
        # self.assertEqual(RGF_RELATION, ibci.get_extra_data('type'))
        self.assertEqual(RelationLinkedChartFetcher.type_id, ibci.get_extra_data('type'))
        self.assertEqual(FAKE_REL_SUB_EMPLOYED_BY, ibci.get_extra_data('value'))

        fetcher2 = RelationLinkedChartFetcher(chart=chart)
        self.assertEqual(_('No relationship type given.'), fetcher2.error)
        self.assertEqual('??', fetcher2.verbose_name)

        fetcher3 = RelationLinkedChartFetcher(chart=chart, value='invalid')
        self.assertEqual(_('The relationship type is invalid.'), fetcher3.error)

        fetcher4 = RelationLinkedChartFetcher(chart=chart, value=FAKE_REL_SUB_BILL_ISSUED)
        self.assertEqual(
            _('The relationship type is not compatible with «{}».').format(
                'Test Contact',
            ),
            fetcher4.error
        )

        choices = [*RelationLinkedChartFetcher.choices(FakeContact)]
        self.assertInChoices(
            value=f'{FAKE_REL_SUB_EMPLOYED_BY}',
            label='is an employee of — employs',
            choices=choices,
        )
        self.assertNotInChoices(
            value=f'{FAKE_REL_SUB_BILL_ISSUED}',
            choices=choices,
        )

        # ----
        # TODO: move to test for bricks?
        brick = ReportChartInstanceBrick(ibci)
        self.assertIsNone(brick.errors)
        self.assertListEqual([FakeOrganisation], brick.target_ctypes)

    def test_create_brick_config_item(self):
        "Other brick class."
        class OtherReportChartBrick(ReportChartInstanceBrick):
            id = ReportChartInstanceBrick.generate_id('reports', 'other_chart')

        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            # user=user,
            name='Field Test', linked_report=report,
            abscissa_cell_value='created', abscissa_type=AbscissaGroup.YEAR,
            ordinate_type=OrdinateAggregator.COUNT,
        )

        ibci = SimpleChartFetcher(chart=chart).create_brick_config_item(
            brick_class=OtherReportChartBrick,
        )
        self.assertEqual(OtherReportChartBrick.id, ibci.brick_class_id)


class ChartFetcherRegistryTestCase(CremeTestCase):
    def test_default_class(self):
        registry = ChartFetcherRegistry(SimpleChartFetcher)
        self.assertEqual(SimpleChartFetcher, registry.default_class)

        class OtherSimpleChartFetcher(ChartFetcher):
            pass

        registry.default_class = OtherSimpleChartFetcher
        self.assertEqual(OtherSimpleChartFetcher, registry.default_class)

    def test_register01(self):
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart(name='Field Test', linked_report=report)

        registry = ChartFetcherRegistry(SimpleChartFetcher)
        self.assertFalse([*registry.fetcher_classes])
        fetcher_dict = {
            # 'type': RGF_FK,
            'type': RegularFieldLinkedChartFetcher.type_id,
            'value': 'image',
        }

        with self.assertLogs(level='WARNING') as logs_manager1:
            fetcher1 = registry.get(chart=chart, fetcher_dict=fetcher_dict)

        self.assertIsInstance(fetcher1, SimpleChartFetcher)
        self.assertEqual(
            _('Invalid volatile link; please contact your administrator.'),
            fetcher1.error
        )
        self.assertIn(
            'invalid ID "reports-fk" for fetcher (basic fetcher is used)',
            logs_manager1.output[0]
        )

        # -----
        registry.register(
            RegularFieldLinkedChartFetcher,
            RelationLinkedChartFetcher,
        )
        self.assertCountEqual(
            [
                RegularFieldLinkedChartFetcher,
                RelationLinkedChartFetcher,
            ],
            [*registry.fetcher_classes]
        )
        fetcher2 = registry.get(chart=chart, fetcher_dict=fetcher_dict)
        self.assertIsInstance(fetcher2, RegularFieldLinkedChartFetcher)
        self.assertIsNone(fetcher2.error)

        # Invalid dict (no type) --
        with self.assertLogs(level='WARNING') as logs_manager2:
            fetcher3 = registry.get(chart=chart, fetcher_dict={'value': 'image'})

        self.assertIsInstance(fetcher3, SimpleChartFetcher)
        self.assertEqual(
            _('Invalid volatile link; please contact your administrator.'),
            fetcher3.error
        )
        self.assertIn(
            'no fetcher ID given (basic fetcher is used)',
            logs_manager2.output[0]
        )

    def test_register02(self):
        "Duplicates."
        registry = ChartFetcherRegistry(SimpleChartFetcher).register(
            RegularFieldLinkedChartFetcher,
            RelationLinkedChartFetcher,
        )

        class OtherFKChartFetcher(RegularFieldLinkedChartFetcher):
            pass

        with self.assertRaises(ChartFetcherRegistry.RegistrationError):
            registry.register(OtherFKChartFetcher)
