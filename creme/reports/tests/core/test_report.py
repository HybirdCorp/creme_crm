# -*- coding: utf-8 -*-

from datetime import date
from decimal import Decimal
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.utils.formats import date_format, number_format
from django.utils.timezone import localtime
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldEnumValue,
    FakeContact,
    FakeEmailCampaign,
    FakeImage,
    FakeMailingList,
    FakeOrganisation,
    FakeSector,
    FieldsConfig,
    Language,
    Relation,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_constants import FAKE_REL_SUB_EMPLOYED_BY
from creme.creme_core.utils.meta import FieldInfo
from creme.reports.constants import (
    RFT_AGG_CUSTOM,
    RFT_AGG_FIELD,
    RFT_CUSTOM,
    RFT_FIELD,
    RFT_FUNCTION,
    RFT_RELATED,
    RFT_RELATION,
)
from creme.reports.core.report import (
    ExpandableLine,
    ReportHand,
    ReportHandRegistry,
    RHAggregateCustomField,
    RHAggregateRegularField,
    RHCustomField,
    RHForeignKey,
    RHFunctionField,
    RHManyToManyField,
    RHRegularField,
    RHRelated,
    RHRelation,
)
from creme.reports.models import FakeReportsDocument, FakeReportsFolder, Field

from ..base import Report, skipIfCustomReport


# TODO: complete:
#   - get_value() + sub-report
@skipIfCustomReport
class ReportHandTestCase(CremeTestCase):
    def test_regular_field01(self):
        user = self.create_user()

        fname = 'first_name'
        rfield = Field(
            report=Report(user=user, ct=FakeContact), type=RFT_FIELD, name=fname,
        )
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

        aria = FakeContact.objects.create(user=user, first_name='Aria', last_name='Stark')
        self.assertEqual(
            aria.first_name,
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

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
            RHRegularField(rfield)

        self.assertEqual(
            f'Invalid field: "{fname}" (does not exist)',
            str(cm.exception)
        )

    def test_regular_field_error02(self):
        "Field too deep."
        fname = 'image__user__username'
        rfield = Field(report=Report(ct=FakeContact), type=RFT_FIELD, name=fname)

        with self.assertRaises(ReportHand.ValueError) as cm:
            RHRegularField(rfield)

        self.assertEqual(
            f'Invalid field: "{fname}" (too deep)',
            str(cm.exception)
        )

    def test_regular_field_bool(self):
        user = self.create_user()

        rfield = Field(
            report=Report(user=user, ct=FakeContact), type=RFT_FIELD, name='is_a_nerd',
        )
        hand = RHRegularField(rfield)

        aria = FakeContact.objects.create(user=user, first_name='Aria', last_name='Stark')
        self.assertEqual(
            _('No'),
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

    def test_regular_field_datetime(self):
        user = self.create_user()

        rfield = Field(
            report=Report(user=user, ct=FakeContact), type=RFT_FIELD, name='modified',
        )
        hand = RHRegularField(rfield)

        aria = FakeContact.objects.create(user=user, first_name='Aria', last_name='Stark')
        self.assertEqual(
            date_format(localtime(aria.modified), 'DATETIME_FORMAT'),
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

    def test_regular_field_fk01(self):
        user = self.create_user()

        rfield = Field(
            report=Report(user=user, ct=FakeContact), type=RFT_FIELD, name='sector',
        )
        hand = RHRegularField(rfield)
        self.assertIsInstance(hand, RHForeignKey)
        self.assertIsNone(hand.get_linkable_ctypes())
        self.assertIs(hand.linked2entity, False)

        sector = FakeSector.objects.all()[0]
        aria = FakeContact.objects.create(
            user=user, first_name='Aria', last_name='Stark', sector=sector,
        )
        self.assertEqual(
            str(sector),
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

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
        user = self.create_user()

        rfield = Field(
            report=Report(user=user, ct=FakeContact),
            type=RFT_FIELD, name='languages',
        )
        hand = RHRegularField(rfield)
        self.assertIsInstance(hand, RHManyToManyField)
        self.assertIsNone(hand.get_linkable_ctypes())

        languages = [*Language.objects.all()[:2]]
        aria = FakeContact.objects.create(user=user, first_name='Aria', last_name='Stark')
        aria.languages.set(languages)
        self.assertEqual(
            f'{languages[0]}, {languages[1]}',
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

    def test_regular_field_m2m02(self):
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

    def test_custom_field01(self):
        user = self.create_user()
        cfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=FakeContact,
        )

        rfield = Field(
            report=Report(user=user, ct=FakeContact),
            type=RFT_CUSTOM, name=str(cfield.id),
        )
        hand = RHCustomField(rfield)
        self.assertEqual(_('Custom field'), hand.verbose_name)
        self.assertEqual(cfield.name,  hand.title)
        self.assertIs(hand.hidden, False)

        aria = FakeContact.objects.create(user=user, first_name='Aria', last_name='Stark')
        value = 162
        cfield.value_class.objects.create(custom_field=cfield, entity=aria, value=value)

        self.assertEqual(
            str(value),
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

    def test_custom_field02(self):
        "Deleted custom-field."
        cfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=FakeContact,
            is_deleted=True,
        )

        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_CUSTOM, name=str(cfield.id),
        )
        hand = RHCustomField(rfield)
        self.assertEqual(cfield.name,  hand.title)
        self.assertIs(hand.hidden, True)

    def test_custom_field_bool(self):
        user = self.create_user()
        cfield = CustomField.objects.create(
            name='Uses sword',
            field_type=CustomField.BOOL,
            content_type=FakeContact,
        )

        rfield = Field(
            report=Report(user=user, ct=FakeContact),
            type=RFT_CUSTOM, name=str(cfield.id),
        )
        hand = RHCustomField(rfield)

        aria = FakeContact.objects.create(user=user, first_name='Aria', last_name='Stark')
        cfield.value_class.objects.create(custom_field=cfield, entity=aria, value=True)
        self.assertEqual(
            _('Yes'),
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

    def test_custom_field_datetime(self):
        user = self.create_user()
        cfield = CustomField.objects.create(
            name='Knighting',
            field_type=CustomField.DATETIME,
            content_type=FakeContact,
        )

        rfield = Field(
            report=Report(user=user, ct=FakeContact),
            type=RFT_CUSTOM, name=str(cfield.id),
        )
        hand = RHCustomField(rfield)

        aria = FakeContact.objects.create(user=user, first_name='Aria', last_name='Stark')
        dt = self.create_datetime(year=2020, month=5, day=18, hour=15, minute=47)
        cfield.value_class.objects.create(custom_field=cfield, entity=aria, value=dt)
        self.assertEqual(
            date_format(localtime(dt), 'DATETIME_FORMAT'),
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

    def test_custom_field_date(self):
        user = self.create_user()
        cfield = CustomField.objects.create(
            name='Knighting',
            field_type=CustomField.DATE,
            content_type=FakeContact,
        )

        rfield = Field(
            report=Report(user=user, ct=FakeContact),
            type=RFT_CUSTOM, name=str(cfield.id),
        )
        hand = RHCustomField(rfield)

        aria = FakeContact.objects.create(user=user, first_name='Aria', last_name='Stark')
        date_obj = date(year=2020, month=5, day=18)
        cfield.value_class.objects.create(custom_field=cfield, entity=aria, value=date_obj)
        self.assertEqual(
            date_format(date_obj, 'DATE_FORMAT'),
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

    def test_custom_field_decimal(self):
        user = self.create_user()
        cfield = CustomField.objects.create(
            name="Sword's price",
            field_type=CustomField.FLOAT,
            content_type=FakeContact,
        )

        rfield = Field(
            report=Report(user=user, ct=FakeContact),
            type=RFT_CUSTOM, name=str(cfield.id),
        )
        hand = RHCustomField(rfield)

        aria = FakeContact.objects.create(user=user, first_name='Aria', last_name='Stark')
        value = Decimal('235.50')
        cfield.value_class.objects.create(custom_field=cfield, entity=aria, value=value)
        self.assertEqual(
            number_format(value, use_l10n=True),
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

    def test_custom_field_multienum(self):
        user = self.create_user()
        cfield = CustomField.objects.create(
            name='Weapons',
            field_type=CustomField.MULTI_ENUM,
            content_type=FakeContact,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        evalue1 = create_evalue(value='Sword')
        create_evalue(value='Axe')
        evalue3 = create_evalue(value='Bow')

        aria = FakeContact.objects.create(user=user, first_name='Aria', last_name='Stark')
        cfield.value_class(
            entity=aria, custom_field=cfield,
        ).set_value_n_save([evalue1, evalue3])

        rfield = Field(
            report=Report(user=user, ct=FakeContact),
            type=RFT_CUSTOM, name=str(cfield.id),
        )
        hand = RHCustomField(rfield)
        self.assertEqual(
            f'{evalue1.value} / {evalue3.value}',
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

    def test_custom_field_error(self):
        cf_id = str(self.UNUSED_PK)
        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_CUSTOM, name=cf_id,
        )
        with self.assertRaises(ReportHand.ValueError) as cm:
            RHCustomField(rfield)

        self.assertEqual(
            f'Invalid custom field: "{cf_id}"',
            str(cm.exception)
        )

    def test_relation(self):
        user = self.create_user()
        rtype = RelationType.objects.get(id=FAKE_REL_SUB_EMPLOYED_BY)

        rfield = Field(
            report=Report(user=user, ct=FakeContact),
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

        aria = FakeContact.objects.create(
            user=user, first_name='Aria', last_name='Stark',
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        starks    = create_orga(name='Starks')
        assassins = create_orga(name='Assassins')

        create_relation = partial(
            Relation.objects.create, user=user, type=rtype, subject_entity=aria,
        )
        create_relation(object_entity=starks)
        create_relation(object_entity=assassins)

        self.assertEqual(
            f'{starks}, {assassins}',
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

    def test_relation_error(self):
        rtype_id = 'unknown'
        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_RELATION, name=rtype_id,
        )
        with self.assertRaises(ReportHand.ValueError) as cm:
            RHRelation(rfield)

        self.assertEqual(
            f'Invalid relation type: "{rtype_id}"',
            str(cm.exception)
        )

    def test_function_field(self):
        user = self.create_user()
        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_FUNCTION, name='get_pretty_properties',
        )
        hand = RHFunctionField(rfield)
        self.assertEqual(_('Computed field'), hand.verbose_name)
        self.assertEqual(_('Properties'),     hand.title)
        self.assertFalse(hand.hidden)
        self.assertIsNone(hand.get_linkable_ctypes())

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(id='creme_core-sword',   text='Knows sword')
        ptype2 = create_ptype(id='creme_core-costume', text='Knows costume')

        aria = FakeContact.objects.create(
            user=user, first_name='Aria', last_name='Stark',
        )

        create_prop = partial(CremeProperty.objects.create, creme_entity=aria)
        create_prop(type=ptype1)
        create_prop(type=ptype2)

        self.assertCountEqual(
            # f'{ptype1.text}/{ptype2.text}',
            [ptype1.text, ptype2.text],  # TODO: sort alphabetically ??
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all()).split('/')
        )

    def test_function_field_error(self):
        name = 'unknown'
        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_FUNCTION, name=name,
        )

        with self.assertRaises(ReportHand.ValueError) as cm:
            RHFunctionField(rfield)

        self.assertEqual(
            f'Invalid function field: "{name}"',
            str(cm.exception)
        )

    def test_regular_aggregate01(self):
        user = self.create_user()
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

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        starks = create_orga(name='Starks', capital=500)
        create_orga(name='Lannisters', capital=1000)

        self.assertEqual(
            number_format(Decimal('750.0'), use_l10n=True),
            hand.get_value(entity=starks, user=user, scope=FakeOrganisation.objects.all())
        )

    def test_regular_aggregate02(self):
        "Hidden field."
        fname = 'capital'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[
                (fname, {FieldsConfig.HIDDEN: True}),
            ],
        )

        rfield = Field(
            report=Report(ct=FakeOrganisation),
            type=RFT_AGG_FIELD, name=f'{fname}__avg',
        )
        hand = RHAggregateRegularField(rfield)
        self.assertEqual(
            f"{_('Average')} - {_('Capital')}",
            hand.title
        )
        self.assertTrue(hand.hidden)

    def test_regular_aggregate_error01(self):
        fname = 'unknown'
        rfield = Field(
            report=Report(ct=FakeOrganisation),
            type=RFT_AGG_FIELD, name=f'{fname}__avg',
        )

        with self.assertRaises(ReportHand.ValueError) as cm:
            RHAggregateRegularField(rfield)

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
            RHAggregateRegularField(rfield)

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
            RHAggregateRegularField(rfield)

        self.assertEqual(
            f'This type of field can not be aggregated: "{fname}"',
            str(cm.exception)
        )

    def test_custom_aggregate01(self):
        user = self.create_user()
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

        create_contact = partial(FakeContact.objects.create, user=user, last_name='Stark')
        aria  = create_contact(first_name='Aria')
        sansa = create_contact(first_name='Sansa')

        create_cf_value = partial(cfield.value_class.objects.create, custom_field=cfield)
        create_cf_value(entity=aria,  value=Decimal('154.40'))
        create_cf_value(entity=sansa, value=Decimal('175.60'))

        self.assertEqual(
            number_format(Decimal('164.5'), use_l10n=True),
            hand.get_value(entity=aria, user=user, scope=FakeContact.objects.all())
        )

    def test_custom_aggregate02(self):
        "Deleted custom-field."
        cfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=FakeContact,
            is_deleted=True,
        )

        rfield = Field(
            report=Report(ct=FakeContact),
            type=RFT_AGG_CUSTOM, name=f'{cfield.id}__avg',
        )
        hand = RHAggregateCustomField(rfield)
        self.assertEqual(
            f"{_('Average')} - {cfield.name}",
            hand.title
        )
        self.assertTrue(hand.hidden)

    def test_custom_aggregate_error01(self):
        cf_id = 'unknown'
        rfield = Field(
            report=Report(ct=FakeOrganisation),
            type=RFT_AGG_FIELD, name=f'{cf_id}__avg',
        )

        with self.assertRaises(ReportHand.ValueError) as cm:
            RHAggregateCustomField(rfield)

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
            RHAggregateCustomField(rfield)

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
            RHAggregateCustomField(rfield)

        self.assertEqual(
            f'This type of custom field can not be aggregated: "{cfield.id}"',
            str(cm.exception)
        )

    def test_related(self):
        user = self.create_user()
        rfield = Field(
            report=Report(user=user, ct=FakeReportsFolder),
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

        folder = FakeReportsFolder.objects.create(user=user, title='Archives')

        create_doc = partial(FakeReportsDocument.objects.create, user=user, linked_folder=folder)
        doc1 = create_doc(title='Map of Essos')
        doc2 = create_doc(title='Map of Westeros')

        self.assertEqual(
            f'{doc1}, {doc2}',
            hand.get_value(entity=folder, user=user, scope=FakeContact.objects.all())
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
            RHRelated(rfield)

        self.assertEqual(
            f'Invalid related field: "{fname}"',
            str(cm.exception)
        )


class ReportHandRegistryTestCase(CremeTestCase):
    def test_empty(self):
        registry = ReportHandRegistry()

        with self.assertRaises(KeyError):
            registry[RFT_FIELD]

        self.assertIsNone(registry.get(RFT_FIELD))
        self.assertFalse([*registry])

    def test_register(self):
        registry = ReportHandRegistry()
        registry(RFT_FIELD)(RHRegularField)

        self.assertEqual(RHRegularField, registry[RFT_FIELD])
        self.assertEqual(RHRegularField, registry.get(RFT_FIELD))
        self.assertEqual([RFT_FIELD], [*registry])

    # TODO: test collision ('true' exception?)


class ExpandableLineTestCase(CremeTestCase):
    def test_empty(self):
        self.assertListEqual(
            [[]],
            ExpandableLine(values=[]).get_lines()
        )

    def test_flat(self):
        self.assertListEqual(
            [['a', 'b']],
            ExpandableLine(values=['a', 'b']).get_lines()
        )

    def test_expand(self):
        self.assertListEqual(
            [
                ['a', 'b', 'c', 'e'],
                ['a', 'b', 'd', 'e'],
            ],
            ExpandableLine(values=['a', 'b', ['c', 'd'], 'e']).get_lines()
        )
        self.assertListEqual(
            [
                ['a', 'b', 'c', 'd', 'e'],
            ],
            ExpandableLine(values=['a', 'b', [['c', 'd']], 'e']).get_lines()
        )
        self.assertListEqual(
            [
                ['a', 'b', 'c', 'd', 'g'],
                ['a', 'b', 'e', 'f', 'g'],
            ],
            ExpandableLine(values=['a', 'b', [['c', 'd'], ['e', 'f']], 'g']).get_lines()
        )
