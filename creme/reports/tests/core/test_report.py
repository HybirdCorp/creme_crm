# -*- coding: utf-8 -*-

try:
    from parameterized import parameterized

    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import gettext as _

    from creme.creme_core.models import (
        RelationType,
        CustomField,
        FieldsConfig,
        FakeContact, FakeOrganisation,
        FakeImage,
        FakeEmailCampaign, FakeMailingList,
    )
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_constants import FAKE_REL_SUB_EMPLOYED_BY
    from creme.creme_core.utils.meta import FieldInfo

    from ..base import (
        skipIfCustomReport,
        Report,
    )

    from creme.reports.constants import (
        RFT_FIELD,
        RFT_CUSTOM,
        RFT_RELATION,
        RFT_FUNCTION,
        RFT_AGG_FIELD,
        RFT_AGG_CUSTOM,
        RFT_RELATED,
    )
    from creme.reports.models import (
        Field,
        FakeReportsFolder, FakeReportsDocument,
    )
    from creme.reports.core.report import (
        ReportHandRegistry,
        ReportHand,
        RHRegularField,
        RHForeignKey,
        RHManyToManyField,
        RHCustomField,
        RHRelation,
        RHFunctionField,
        RHAggregateRegularField,
        RHAggregateCustomField,
        RHRelated,
    )
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


# TODO: complete:
#   - get_value()
@skipIfCustomReport
class ReportHandTestCase(CremeTestCase):
    def test_regular_field01(self):
        fname = 'first_name'
        rfield = Field(report=Report(ct=FakeContact), type=RFT_FIELD, name=fname)
        hand = RHRegularField(rfield)
        self.assertIsInstance(hand, RHRegularField)
        self.assertEqual(_('Regular field'), hand.verbose_name)
        self.assertEqual(_('First name'),    hand.title)
        self.assertIs(hand.hidden, False)
        self.assertIsNone(hand.get_linkable_ctypes())

        finfo = hand.field_info
        self.assertIsInstance(finfo, FieldInfo)
        self.assertEqual(FakeContact, finfo.model)
        self.assertEqual(1, len(finfo))
        self.assertEqual(fname, finfo[0].name)

    def test_regular_field02(self):
        "Hidden field."
        fname = 'capital'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[
                (fname, {FieldsConfig.HIDDEN: True}),
            ],
        )

        rfield = Field(report=Report(ct=FakeOrganisation), type=RFT_FIELD, name=fname)
        hand = RHRegularField(rfield)
        self.assertEqual(_('Capital'), hand.title)
        self.assertIs(hand.hidden, True)

    def test_regular_field_error01(self):
        "Invalid field."
        fname = 'invalid'
        rfield = Field(report=Report(ct=FakeContact), type=RFT_FIELD, name=fname)

        with self.assertRaises(ReportHand.ValueError) as cm:
            __ = RHRegularField(rfield)

        self.assertEqual(
            f'Invalid field: "{fname}" (does not exist)',
            str(cm.exception)
        )

    def test_regular_field_error02(self):
        "Field too deep."
        fname = 'image__user__username'
        rfield = Field(report=Report(ct=FakeContact), type=RFT_FIELD, name=fname)

        with self.assertRaises(ReportHand.ValueError) as cm:
            __ = RHRegularField(rfield)

        self.assertEqual(
            f'Invalid field: "{fname}" (too deep)',
            str(cm.exception)
        )

    def test_regular_field_fk01(self):
        rfield = Field(report=Report(ct=FakeContact), type=RFT_FIELD, name='sector')
        hand = RHRegularField(rfield)
        self.assertIsInstance(hand, RHForeignKey)
        self.assertIsNone(hand.get_linkable_ctypes())
        self.assertIs(hand.linked2entity, False)

    def test_regular_field_fk02(self):
        "Related to entity."
        rfield = Field(report=Report(ct=FakeContact), type=RFT_FIELD, name='image')
        hand = RHForeignKey(rfield)
        self.assertEqual(
            [ContentType.objects.get_for_model(FakeImage)],
            [*hand.get_linkable_ctypes()]
        )
        self.assertIs(hand.linked2entity, True)

    def test_regular_field_m2m01(self):
        rfield = Field(report=Report(ct=FakeContact), type=RFT_FIELD, name='languages')
        hand = RHRegularField(rfield)
        self.assertIsInstance(hand, RHManyToManyField)
        self.assertIsNone(hand.get_linkable_ctypes())

    def test_regular_field_m2m05(self):
        "Related to entity."
        rfield = Field(
            report=Report(ct=FakeEmailCampaign),
            type=RFT_FIELD, name='mailing_lists',
        )
        hand = RHManyToManyField(rfield)
        self.assertEqual(
            [ContentType.objects.get_for_model(FakeMailingList)],
            [*hand.get_linkable_ctypes()]
        )

    def test_custom_field(self):
        cfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=FakeContact,
        )

        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_CUSTOM, name=str(cfield.id),
        )
        hand = RHCustomField(rfield)
        self.assertEqual(_('Custom field'), hand.verbose_name)
        self.assertEqual(cfield.name,  hand.title)
        self.assertIs(hand.hidden, False)

    def test_custom_field_error(self):
        cf_id = '1024'
        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_CUSTOM, name=cf_id,
        )
        with self.assertRaises(ReportHand.ValueError) as cm:
            __ = RHCustomField(rfield)

        self.assertEqual(
            f'Invalid custom field: "{cf_id}"',
            str(cm.exception)
        )

    def test_relation(self):
        rtype = RelationType.objects.get(id=FAKE_REL_SUB_EMPLOYED_BY)

        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_RELATION, name=rtype.id,
        )
        hand = RHRelation(rfield)
        self.assertEqual(_('Relationship'), hand.verbose_name)
        self.assertEqual(rtype.predicate,   hand.title)
        self.assertFalse(hand.hidden)
        self.assertEqual(rtype, hand.relation_type)
        self.assertListEqual(
            [ContentType.objects.get_for_model(FakeOrganisation)],
            [*hand.get_linkable_ctypes()]
        )

    def test_relation_error(self):
        rtype_id = 'unknown'
        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_RELATION, name=rtype_id,
        )
        with self.assertRaises(ReportHand.ValueError) as cm:
            __ = RHRelation(rfield)

        self.assertEqual(
            f'Invalid relation type: "{rtype_id}"',
            str(cm.exception)
        )

    def test_function_field(self):
        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_FUNCTION, name='get_pretty_properties',
        )
        hand = RHFunctionField(rfield)
        self.assertEqual(_('Computed field'), hand.verbose_name)
        self.assertEqual(_('Properties'),     hand.title)
        self.assertFalse(hand.hidden)
        self.assertIsNone(hand.get_linkable_ctypes())

    def test_function_field_error(self):
        name = 'unknown'
        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_FUNCTION, name=name,
        )

        with self.assertRaises(ReportHand.ValueError) as cm:
            __ = RHFunctionField(rfield)

        self.assertEqual(
            f'Invalid function field: "{name}"',
            str(cm.exception)
        )

    def test_regular_aggregate(self):
        rfield = Field(
            report=Report(ct=FakeOrganisation),
            type=RFT_AGG_FIELD, name='capital__avg',
        )
        hand = RHAggregateRegularField(rfield)
        self.assertEqual(_('Aggregated value'), hand.verbose_name)
        self.assertEqual(
            f"{_('Average')} - {_('Capital')}",
            hand.title
        )
        self.assertFalse(hand.hidden)
        self.assertIsNone(hand.get_linkable_ctypes())

    def test_regular_aggregate_error01(self):
        fname = 'unknown'
        rfield = Field(
            report=Report(ct=FakeOrganisation),
            type=RFT_AGG_FIELD, name=f'{fname}__avg',
        )

        with self.assertRaises(ReportHand.ValueError) as cm:
            __ = RHAggregateRegularField(rfield)

        self.assertEqual(
            f'Unknown field: "{fname}"',
            str(cm.exception)
        )

    def test_regular_aggregate_error02(self):
        aggname = 'unknown'
        rfield = Field(
            report=Report(ct=FakeOrganisation),
            type=RFT_AGG_FIELD, name=f'capital__{aggname}',
        )

        with self.assertRaises(ReportHand.ValueError) as cm:
            __ = RHAggregateRegularField(rfield)

        self.assertEqual(
            f'Invalid aggregation: "{aggname}"',
            str(cm.exception)
        )

    def test_regular_aggregate_error03(self):
        fname = 'name'
        rfield = Field(
            report=Report(ct=FakeOrganisation),
            type=RFT_AGG_FIELD, name=f'{fname}__avg',
        )

        with self.assertRaises(ReportHand.ValueError) as cm:
            __ = RHAggregateRegularField(rfield)

        self.assertEqual(
            f'This type of field can not be aggregated: "{fname}"',
            str(cm.exception)
        )

    def test_custom_aggregate(self):
        cfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=FakeContact,
        )

        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_AGG_CUSTOM, name=f'{cfield.id}__avg',
        )
        hand = RHAggregateCustomField(rfield)
        self.assertEqual(_('Aggregated value (custom field)'), hand.verbose_name)
        self.assertEqual(
            f"{_('Average')} - {cfield.name}",
            hand.title
        )
        self.assertIs(hand.hidden, False)

    def test_custom_aggregate_error01(self):
        cf_id = 'unknown'
        rfield = Field(
            report=Report(ct=FakeOrganisation),
            type=RFT_AGG_FIELD, name=f'{cf_id}__avg',
        )

        with self.assertRaises(ReportHand.ValueError) as cm:
            __ = RHAggregateCustomField(rfield)

        self.assertEqual(
            f'Invalid custom field aggregation: "{cf_id}"',
            str(cm.exception)
        )

    def test_custom_aggregate_error02(self):
        cfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=FakeContact,
        )

        agg_id = 'unknown'
        rfield = Field(
            report=Report(ct=FakeOrganisation),
            type=RFT_AGG_FIELD, name=f'{cfield.id}__{agg_id}',
        )

        with self.assertRaises(ReportHand.ValueError) as cm:
            __ = RHAggregateCustomField(rfield)

        self.assertEqual(
            f'Invalid aggregation: "{agg_id}"',
            str(cm.exception)
        )

    def test_custom_aggregate_error03(self):
        cfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.STR,
            content_type=FakeContact,
        )

        rfield = Field(
            report=Report(ct=FakeOrganisation),
            type=RFT_AGG_FIELD, name=f'{cfield.id}__avg',
        )

        with self.assertRaises(ReportHand.ValueError) as cm:
            __ = RHAggregateCustomField(rfield)

        self.assertEqual(
            f'This type of custom field can not be aggregated: "{cfield.id}"',
            str(cm.exception)
        )

    def test_related(self):
        rfield = Field(
            report=Report(ct=FakeReportsFolder),
            type=RFT_RELATED, name='fakereportsdocument',
        )
        hand = RHRelated(rfield)
        self.assertEqual(_('Related field'), hand.verbose_name)
        self.assertEqual(
            FakeReportsDocument._meta.verbose_name,
            hand.title
        )
        self.assertFalse(hand.hidden)
        self.assertListEqual(
            [ContentType.objects.get_for_model(FakeReportsDocument)],
            [*hand.get_linkable_ctypes()]
        )

    @parameterized.expand([
        ('title', ),  # Not ForeignKey
        ('unknown', ),
    ])
    def test_related_error(self, fname):
        rfield = Field(
            report=Report(ct=FakeReportsFolder),
            type=RFT_RELATED, name=fname,
        )

        with self.assertRaises(ReportHand.ValueError) as cm:
            __ = RHRelated(rfield)

        self.assertEqual(
            f'Invalid related field: "{fname}"',
            str(cm.exception)
        )


class ReportHandRegistryTestCase(CremeTestCase):
    def test_empty(self):
        registry = ReportHandRegistry()

        with self.assertRaises(KeyError):
            __ = registry[RFT_FIELD]

        self.assertIsNone(registry.get(RFT_FIELD))
        self.assertFalse([*registry])

    def test_register(self):
        registry = ReportHandRegistry()
        registry(RFT_FIELD)(RHRegularField)

        self.assertEqual(RHRegularField, registry[RFT_FIELD])
        self.assertEqual(RHRegularField, registry.get(RFT_FIELD))
        self.assertEqual([RFT_FIELD], [*registry])

    # TODO: test collision ('true' exception?)

# TODO: test ExpandableLine
