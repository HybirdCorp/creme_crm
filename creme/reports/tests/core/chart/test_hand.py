from uuid import uuid4

from django.utils.translation import gettext as _
from django.utils.translation import override as override_language

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.models import (
    CustomField,
    FakeContact,
    FakeEmailCampaign,
    FakeOrganisation,
    FieldsConfig,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_constants import FAKE_REL_OBJ_EMPLOYED_BY
from creme.reports.core.chart.aggregator import ChartCount, ChartSum
from creme.reports.core.chart.hand import (
    ChartHandChoices,
    ChartHandCustomDay,
    ChartHandCustomFK,
    ChartHandCustomMonth,
    ChartHandCustomRange,
    ChartHandCustomYear,
    ChartHandDay,
    ChartHandForeignKey,
    ChartHandMonth,
    ChartHandRange,
    ChartHandRegistry,
    ChartHandRelation,
    ChartHandYear,
    _generate_date_format,
)
from creme.reports.models import ReportChart
from creme.reports.tests.base import Report

# TODO: complete
#  - fetch
#  ...


class ReportChartHandTestCase(CremeTestCase):
    def test_generate_date_format(self):
        with override_language('en'):
            self.assertEqual(
                '%Y-%m-%d', _generate_date_format(year=True, month=True, day=True),
            )

        with override_language('fr'):
            self.assertEqual(
                '%d/%m/%Y', _generate_date_format(year=True, month=True, day=True),
            )

    def test_regular_field_day(self):
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value='created', abscissa_type=ReportChart.Group.DAY,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandDay(chart)
        self.assertEqual(ReportChart.Group.DAY, hand.hand_id)
        self.assertEqual(_('By days'),          hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertEqual(_('Creation date'), hand.verbose_abscissa)

        ordinate = hand.ordinate
        self.assertIsInstance(ordinate, ChartCount)
        self.assertIsNone(ordinate.error)

    def test_regular_field_month(self):
        ordinate_cell = EntityCellRegularField.build(FakeOrganisation, 'capital')

        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeOrganisation)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value='modified', abscissa_type=ReportChart.Group.MONTH,
            ordinate_type=ReportChart.Aggregator.SUM,
            ordinate_cell_key=ordinate_cell.portable_key,
        )

        hand = ChartHandMonth(chart)
        self.assertEqual(ReportChart.Group.MONTH, hand.hand_id)
        self.assertEqual(_('By months'),          hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertEqual(_('Last modification'), hand.verbose_abscissa)

        ordinate = hand.ordinate
        self.assertIsInstance(ordinate, ChartSum)
        self.assertIsNone(ordinate.error)

    def test_regular_field_year(self):
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value='created', abscissa_type=ReportChart.Group.YEAR,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandYear(chart)
        self.assertEqual(ReportChart.Group.YEAR, hand.hand_id)
        self.assertEqual(_('By years'),          hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)

    def test_regular_field_date_range(self):
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value='created', abscissa_type=ReportChart.Group.RANGE,
            abscissa_parameter='90',
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandRange(chart)
        self.assertEqual(ReportChart.Group.RANGE, hand.hand_id)
        self.assertEqual(_('By X days'),          hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)

    def test_regular_field_fk(self):
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value='sector', abscissa_type=ReportChart.Group.FK,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandForeignKey(chart)
        self.assertEqual(ReportChart.Group.FK, hand.hand_id)
        self.assertEqual(_('By values'),       hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)

    def test_regular_field_choices(self):
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeEmailCampaign)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value='type', abscissa_type=ReportChart.Group.CHOICES,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandChoices(chart)
        self.assertEqual(ReportChart.Group.CHOICES, hand.hand_id)
        self.assertEqual(_('By values'),            hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)

    def test_regular_field_error01(self):
        "Invalid field."
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value='invalid', abscissa_type=ReportChart.Group.DAY,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandDay(chart)
        self.assertEqual(ReportChart.Group.DAY, hand.hand_id)
        self.assertEqual(
            _('the field does not exist any more.'),
            hand.abscissa_error,
        )
        self.assertEqual('??', hand.verbose_abscissa)

    def test_regular_field_error02(self):
        "Hidden field."
        hidden_fname = 'sector'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname, {FieldsConfig.HIDDEN: True}),
            ],
        )

        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value=hidden_fname, abscissa_type=ReportChart.Group.FK,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandDay(chart)
        self.assertEqual(
            _('this field should be hidden.'),
            hand.abscissa_error
        )
        self.assertEqual(_('Line of business'), hand.verbose_abscissa)

    def test_relation(self):
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value=FAKE_REL_OBJ_EMPLOYED_BY,
            abscissa_type=ReportChart.Group.RELATION,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandRelation(chart)
        self.assertEqual(ReportChart.Group.RELATION, hand.hand_id)
        self.assertEqual(_('By values (of related entities)'), hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertEqual('employs', hand.verbose_abscissa)

    def test_relation_error01(self):
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value='invalid',
            abscissa_type=ReportChart.Group.RELATION,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandRelation(chart)
        self.assertEqual(
            _('the relationship type does not exist any more.'),
            hand.abscissa_error,
        )
        self.assertEqual('??', hand.verbose_abscissa)

    def test_relation_error02(self):
        "The RelationType is disabled."
        user = self.get_root_user()

        rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='[disabled]',
            enabled=False,  # <==
        ).symmetric(id='test-object_disabled', predicate='what ever').get_or_create()[0]

        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value=rtype.id,
            abscissa_type=ReportChart.Group.RELATION,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandRelation(chart)
        self.assertEqual(
            _('the relationship type is disabled.'),
            hand.abscissa_error,
        )
        self.assertEqual(rtype.predicate, hand.verbose_abscissa)

    def test_custom_field_day(self):
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.DATETIME,
            name='First fight',
        )

        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value=str(cfield.uuid),
            abscissa_type=ReportChart.Group.CUSTOM_DAY,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandCustomDay(chart)
        self.assertEqual(ReportChart.Group.CUSTOM_DAY, hand.hand_id)
        self.assertEqual(_('By days'), hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertEqual(cfield.name, hand.verbose_abscissa)

    def test_custom_field_month(self):
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.DATETIME,
            name='First fight',
        )

        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value=str(cfield.uuid),
            abscissa_type=ReportChart.Group.CUSTOM_MONTH,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandCustomMonth(chart)
        self.assertEqual(ReportChart.Group.CUSTOM_MONTH, hand.hand_id)
        self.assertEqual(_('By months'), hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertEqual(cfield.name, hand.verbose_abscissa)

    def test_custom_field_year(self):
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.DATETIME,
            name='First fight',
        )

        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value=str(cfield.uuid),
            abscissa_type=ReportChart.Group.CUSTOM_YEAR,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandCustomYear(chart)
        self.assertEqual(ReportChart.Group.CUSTOM_YEAR, hand.hand_id)
        self.assertEqual(_('By years'), hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertEqual(cfield.name, hand.verbose_abscissa)

    def test_custom_field_date_range(self):
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.DATETIME,
            name='First fight',
        )

        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value=str(cfield.uuid),
            abscissa_type=ReportChart.Group.CUSTOM_RANGE,
            abscissa_parameter='90',
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandCustomRange(chart)
        self.assertEqual(ReportChart.Group.CUSTOM_RANGE, hand.hand_id)
        self.assertEqual(_('By X days'), hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)

    def test_custom_field_enum(self):
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.ENUM,
            name='Sport',
        )

        user = self.get_root_user()
        chart = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=chart,
            abscissa_cell_value=str(cfield.uuid),
            abscissa_type=ReportChart.Group.CUSTOM_FK,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandCustomFK(chart)
        self.assertEqual(ReportChart.Group.CUSTOM_FK, hand.hand_id)
        self.assertEqual(_('By values (of custom choices)'), hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)

    def test_custom_field_error01(self):
        "Field does not exist."
        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value=str(uuid4()),  # < ==
            abscissa_type=ReportChart.Group.CUSTOM_DAY,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandCustomDay(chart)
        self.assertEqual(ReportChart.Group.CUSTOM_DAY, hand.hand_id)
        self.assertEqual(_('By days'), hand.verbose_name)
        self.assertEqual(
            _('the custom field does not exist any more.'),
            hand.abscissa_error,
        )
        self.assertEqual('??', hand.verbose_abscissa)

    def test_custom_field_error02(self):
        "Field is marked as deleted."
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.ENUM,
            name='Sport',
            is_deleted=True,
        )

        user = self.get_root_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        chart = ReportChart.objects.create(
            name='Field Test', linked_report=report,
            abscissa_cell_value=str(cfield.uuid),
            abscissa_type=ReportChart.Group.CUSTOM_FK,
            ordinate_type=ReportChart.Aggregator.COUNT,
        )

        hand = ChartHandCustomFK(chart)
        self.assertEqual(_('the custom field is deleted.'), hand.abscissa_error)
        self.assertEqual(cfield.name, hand.verbose_abscissa)


class ChartHandRegistryTestCase(CremeTestCase):
    def test_empty(self):
        registry = ChartHandRegistry()

        with self.assertRaises(KeyError):
            registry[ReportChart.Group.FK]  # NOQA

        self.assertIsNone(registry.get(ReportChart.Group.FK))
        self.assertListEqual([], [*registry])

    def test_register(self):
        registry = ChartHandRegistry()
        registry(ReportChart.Group.FK)(ChartHandForeignKey)

        self.assertEqual(ChartHandForeignKey, registry[ReportChart.Group.FK])
        self.assertEqual(ChartHandForeignKey, registry.get(ReportChart.Group.FK))
        self.assertListEqual([ReportChart.Group.FK], [*registry])

# TODO: collision exception ??
