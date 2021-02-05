# -*- coding: utf-8 -*-

from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.models import (
    CustomField,
    FakeContact,
    FakeOrganisation,
    FieldsConfig,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_constants import FAKE_REL_OBJ_EMPLOYED_BY
# from creme.reports.constants import (
#     RGA_COUNT,
#     RGA_SUM,
#     RGT_CUSTOM_DAY,
#     RGT_CUSTOM_FK,
#     RGT_CUSTOM_MONTH,
#     RGT_CUSTOM_RANGE,
#     RGT_CUSTOM_YEAR,
#     RGT_DAY,
#     RGT_FK,
#     RGT_MONTH,
#     RGT_RANGE,
#     RGT_RELATION,
#     RGT_YEAR,
# )
from creme.reports.core.graph.aggregator import RGACount, RGASum
from creme.reports.core.graph.hand import (
    ReportGraphHandRegistry,
    RGHCustomDay,
    RGHCustomFK,
    RGHCustomMonth,
    RGHCustomRange,
    RGHCustomYear,
    RGHDay,
    RGHForeignKey,
    RGHMonth,
    RGHRange,
    RGHRelation,
    RGHYear,
)
from creme.reports.tests.base import Report, ReportGraph

# TODO: complete
#  - fetch
#  ...


class ReportGraphHandTestCase(CremeTestCase):
    def test_regular_field_day(self):
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            # abscissa_cell_value='created', abscissa_type=RGT_DAY,
            abscissa_cell_value='created', abscissa_type=ReportGraph.Group.DAY,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHDay(graph)
        # self.assertEqual(RGT_DAY,      hand.hand_id)
        self.assertEqual(ReportGraph.Group.DAY, hand.hand_id)
        self.assertEqual(_('By days'),          hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertEqual(_('Creation date'), hand.verbose_abscissa)

        ordinate = hand.ordinate
        self.assertIsInstance(ordinate, RGACount)
        self.assertIsNone(ordinate.error)

    def test_regular_field_month(self):
        ordinate_cell = EntityCellRegularField.build(FakeOrganisation, 'capital')

        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeOrganisation)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            # abscissa_cell_value='modified', abscissa_type=RGT_MONTH,
            abscissa_cell_value='modified', abscissa_type=ReportGraph.Group.MONTH,
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=ordinate_cell.key,
        )

        hand = RGHMonth(graph)
        # self.assertEqual(RGT_MONTH,      hand.hand_id)
        self.assertEqual(ReportGraph.Group.MONTH, hand.hand_id)
        self.assertEqual(_('By months'),          hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertEqual(_('Last modification'), hand.verbose_abscissa)

        ordinate = hand.ordinate
        self.assertIsInstance(ordinate, RGASum)
        self.assertIsNone(ordinate.error)

    def test_regular_field_year(self):
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            # abscissa_cell_value='created', abscissa_type=RGT_YEAR,
            abscissa_cell_value='created', abscissa_type=ReportGraph.Group.YEAR,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHYear(graph)
        # self.assertEqual(RGT_YEAR,      hand.hand_id)
        self.assertEqual(ReportGraph.Group.YEAR, hand.hand_id)
        self.assertEqual(_('By years'),          hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)

    def test_regular_field_date_range(self):
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            # abscissa_cell_value='created', abscissa_type=RGT_RANGE,
            abscissa_cell_value='created', abscissa_type=ReportGraph.Group.RANGE,
            abscissa_parameter='90',
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHRange(graph)
        # self.assertEqual(RGT_RANGE,      hand.hand_id)
        self.assertEqual(ReportGraph.Group.RANGE, hand.hand_id)
        self.assertEqual(_('By X days'),          hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)

    def test_regular_field_fk(self):
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            # abscissa_cell_value='sector', abscissa_type=RGT_FK,
            abscissa_cell_value='sector', abscissa_type=ReportGraph.Group.FK,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHForeignKey(graph)
        # self.assertEqual(RGT_FK,         hand.hand_id)
        self.assertEqual(ReportGraph.Group.FK, hand.hand_id)
        self.assertEqual(_('By values'),       hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)

    def test_regular_field_error01(self):
        "Invalid field."
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            # abscissa_cell_value='invalid', abscissa_type=RGT_DAY,
            abscissa_cell_value='invalid', abscissa_type=ReportGraph.Group.DAY,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHDay(graph)
        # self.assertEqual(RGT_DAY, hand.hand_id)
        self.assertEqual(ReportGraph.Group.DAY, hand.hand_id)
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

        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            # abscissa_cell_value=hidden_fname, abscissa_type=RGT_FK,
            abscissa_cell_value=hidden_fname, abscissa_type=ReportGraph.Group.FK,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHDay(graph)
        self.assertEqual(
            _('this field should be hidden.'),
            hand.abscissa_error
        )
        self.assertEqual(_('Line of business'), hand.verbose_abscissa)

    def test_relation(self):
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value=FAKE_REL_OBJ_EMPLOYED_BY,
            # abscissa_type=RGT_RELATION,
            abscissa_type=ReportGraph.Group.RELATION,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHRelation(graph)
        # self.assertEqual(RGT_RELATION, hand.hand_id)
        self.assertEqual(ReportGraph.Group.RELATION, hand.hand_id)
        self.assertEqual(_('By values (of related entities)'), hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertEqual('employs', hand.verbose_abscissa)

    def test_relation_error(self):
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value='invalid',
            # abscissa_type=RGT_RELATION,
            abscissa_type=ReportGraph.Group.RELATION,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHRelation(graph)
        self.assertEqual(
            _('the relationship type does not exist any more.'),
            hand.abscissa_error,
        )
        self.assertEqual('??', hand.verbose_abscissa)

    def test_custom_field_day(self):
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.DATETIME,
            name='First fight',
        )

        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value=str(cfield.id),
            # abscissa_type=RGT_CUSTOM_DAY,
            abscissa_type=ReportGraph.Group.CUSTOM_DAY,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHCustomDay(graph)
        # self.assertEqual(RGT_CUSTOM_DAY, hand.hand_id)
        self.assertEqual(ReportGraph.Group.CUSTOM_DAY, hand.hand_id)
        self.assertEqual(_('By days'), hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertEqual(cfield.name, hand.verbose_abscissa)

    def test_custom_field_month(self):
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.DATETIME,
            name='First fight',
        )

        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value=str(cfield.id),
            # abscissa_type=RGT_CUSTOM_MONTH,
            abscissa_type=ReportGraph.Group.CUSTOM_MONTH,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHCustomMonth(graph)
        # self.assertEqual(RGT_CUSTOM_MONTH, hand.hand_id)
        self.assertEqual(ReportGraph.Group.CUSTOM_MONTH, hand.hand_id)
        self.assertEqual(_('By months'), hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertEqual(cfield.name, hand.verbose_abscissa)

    def test_custom_field_year(self):
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.DATETIME,
            name='First fight',
        )

        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value=str(cfield.id),
            # abscissa_type=RGT_CUSTOM_YEAR,
            abscissa_type=ReportGraph.Group.CUSTOM_YEAR,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHCustomYear(graph)
        # self.assertEqual(RGT_CUSTOM_YEAR, hand.hand_id)
        self.assertEqual(ReportGraph.Group.CUSTOM_YEAR, hand.hand_id)
        self.assertEqual(_('By years'), hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)
        self.assertEqual(cfield.name, hand.verbose_abscissa)

    def test_custom_field_date_range(self):
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.DATETIME,
            name='First fight',
        )

        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value=str(cfield.id),
            # abscissa_type=RGT_CUSTOM_RANGE,
            abscissa_type=ReportGraph.Group.CUSTOM_RANGE,
            abscissa_parameter='90',
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHCustomRange(graph)
        # self.assertEqual(RGT_CUSTOM_RANGE,      hand.hand_id)
        self.assertEqual(ReportGraph.Group.CUSTOM_RANGE, hand.hand_id)
        self.assertEqual(_('By X days'), hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)

    def test_custom_field_enum(self):
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.ENUM,
            name='Sport',
        )

        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value=str(cfield.id),
            # abscissa_type=RGT_CUSTOM_FK,
            abscissa_type=ReportGraph.Group.CUSTOM_FK,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHCustomFK(graph)
        # self.assertEqual(RGT_CUSTOM_FK,         hand.hand_id)
        self.assertEqual(ReportGraph.Group.CUSTOM_FK, hand.hand_id)
        self.assertEqual(_('By values (of custom choices)'), hand.verbose_name)
        self.assertIsNone(hand.abscissa_error)

    def test_custom_field_error01(self):
        "Field does not exist."
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value='1234',  # < ==
            # abscissa_type=RGT_CUSTOM_DAY,
            abscissa_type=ReportGraph.Group.CUSTOM_DAY,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHCustomDay(graph)
        # self.assertEqual(RGT_CUSTOM_DAY, hand.hand_id)
        self.assertEqual(ReportGraph.Group.CUSTOM_DAY, hand.hand_id)
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

        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            abscissa_cell_value=str(cfield.id),
            # abscissa_type=RGT_CUSTOM_FK,
            abscissa_type=ReportGraph.Group.CUSTOM_FK,
            # ordinate_type=RGA_COUNT,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        hand = RGHCustomFK(graph)
        self.assertEqual(
            _('the custom field is deleted.'),
            hand.abscissa_error
        )
        self.assertEqual(cfield.name, hand.verbose_abscissa)


class ReportGraphHandRegistryTestCase(CremeTestCase):
    def test_empty(self):
        registry = ReportGraphHandRegistry()

        with self.assertRaises(KeyError):
            # registry[RGT_FK]  # NOQA
            registry[ReportGraph.Group.FK]  # NOQA

        # self.assertIsNone(registry.get(RGT_FK))
        self.assertIsNone(registry.get(ReportGraph.Group.FK))
        self.assertListEqual([], [*registry])

    def test_register(self):
        registry = ReportGraphHandRegistry()
        # registry(RGT_FK)(RGHForeignKey)
        registry(ReportGraph.Group.FK)(RGHForeignKey)

        # self.assertEqual(RGHForeignKey, registry[RGT_FK])
        self.assertEqual(RGHForeignKey, registry[ReportGraph.Group.FK])
        # self.assertEqual(RGHForeignKey, registry.get(RGT_FK))
        self.assertEqual(RGHForeignKey, registry.get(ReportGraph.Group.FK))
        # self.assertListEqual([RGT_FK], [*registry])
        self.assertListEqual([ReportGraph.Group.FK], [*registry])

# TODO: collision exception ??
