from collections import defaultdict
from datetime import date
from decimal import Decimal
from functools import partial
from uuid import UUID

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet
from django.utils.translation import gettext as _

from creme.creme_config.forms.fields import (
    CreatorCustomEnumerableChoiceField,
    CustomMultiEnumChoiceField,
)
from creme.creme_core.core.history import toggle_history
from creme.creme_core.models import (
    CremeEntity,
    CustomField,
    CustomFieldBoolean,
    CustomFieldDate,
    CustomFieldDateTime,
    CustomFieldEnum,
    CustomFieldEnumValue,
    CustomFieldFloat,
    CustomFieldInteger,
    CustomFieldMultiEnum,
    CustomFieldString,
    CustomFieldText,
    CustomFieldURL,
    CustomFieldValue,
    FakeContact,
    FakeOrganisation,
)

from ..base import CremeTestCase


class CustomFieldManagerTestCase(CremeTestCase):
    def test_compatible(self):
        create_cfield = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        cfield1 = create_cfield(name='Length of ship', field_type=CustomField.INT)
        cfield2 = create_cfield(name='Width of ship',  field_type=CustomField.STR)
        create_cfield(
            name='Weapon', field_type=CustomField.STR, content_type=FakeContact,
        )
        # __ = create_cfield(name='Flag', field_type=CustomField.STR, is_deleted=True) ??

        qs1 = CustomField.objects.compatible(FakeOrganisation)
        self.assertIsInstance(qs1, QuerySet)
        self.assertEqual(CustomField, qs1.model)
        expected = [cfield1, cfield2]
        self.assertCountEqual(expected, [*qs1])

        # ---
        self.assertCountEqual(
            expected,
            [*CustomField.objects.compatible(
                ContentType.objects.get_for_model(FakeOrganisation)
            )],
        )

    def test_get_for_model(self):
        create_cfield = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        cfield1 = create_cfield(name='Length of ship', field_type=CustomField.INT)
        cfield2 = create_cfield(name='Width of ship',  field_type=CustomField.STR)
        create_cfield(
            name='Weapon', field_type=CustomField.STR, content_type=FakeContact,
        )

        with self.assertNumQueries(1):
            cfields1 = CustomField.objects.get_for_model(FakeOrganisation)

        self.assertDictEqual(
            {cfield1.id: cfield1, cfield2.id: cfield2},
            cfields1,
        )

        # Cache ---
        with self.assertNumQueries(0):
            cfields2 = CustomField.objects.get_for_model(FakeOrganisation)

        self.assertDictEqual(cfields1, cfields2)
        self.assertIsNot(cfields2, cfields1)

        # ContentType argument ---
        with self.assertNumQueries(0):
            cfields3 = CustomField.objects.get_for_model(
                ContentType.objects.get_for_model(FakeOrganisation)
            )

        self.assertDictEqual(cfields1, cfields3)


class CustomFieldTestCase(CremeTestCase):
    def assertValueEqual(self, *, cfield, entity, value):
        cf_value = self.get_object_or_fail(
            cfield.value_class,
            custom_field=cfield,
            entity=entity,
        )
        self.assertEqual(value, cf_value.value)

    def _create_orga(self):
        return FakeOrganisation.objects.create(
            user=self.get_root_user(),
            name='Arcadia',
        )

    def test_int(self) -> None:
        name = 'Length of ship'
        cfield: CustomField = CustomField.objects.create(
            name=name,
            field_type=CustomField.INT,
            content_type=FakeOrganisation,
        )
        self.assertEqual(
            ContentType.objects.get_for_model(FakeOrganisation),
            cfield.content_type,
        )
        self.assertTrue(cfield.uuid)
        self.assertIs(cfield.is_required, False)
        self.assertIs(cfield.is_deleted, False)
        self.assertEqual(name, str(cfield))
        self.assertEqual('', cfield.description)
        self.assertEqual(CustomFieldInteger, cfield.value_class)
        self.assertEqual(_('Integer'), CustomFieldInteger.verbose_name)

        self.assertEqual(
            'customfieldinteger',
            CustomFieldInteger.get_related_name(),
        )

        orga = self._create_orga()
        value = 1562
        cf_value = CustomFieldInteger.objects.create(
            custom_field=cfield,
            entity=orga,
            value=value,
        )
        self.assertValueEqual(cfield=cfield, entity=orga, value=value)

        formfield1 = cfield.get_formfield(custom_value=cf_value, user=orga.user)
        self.assertIsInstance(formfield1, forms.IntegerField)
        self.assertFalse(formfield1.required)
        self.assertFalse(formfield1.help_text)
        self.assertEqual(value, formfield1.initial)

        formfield2 = cfield.get_formfield(custom_value=None, user=orga.user)
        self.assertIsInstance(formfield2, forms.IntegerField)
        self.assertIsNone(formfield2.initial)

    def test_int__set_value_n_save(self) -> None:
        cfield = CustomField.objects.create(
            name='Length of ship',
            field_type=CustomField.INT,
            content_type=FakeOrganisation,
        )
        orga = self._create_orga()

        cf_value: CustomFieldInteger = CustomFieldInteger.objects.create(
            custom_field=cfield,
            entity=orga,
            value=456,
        )

        value = cf_value.value + 1

        # 2: value + history
        with self.assertNumQueries(2):
            cf_value.set_value_n_save(value)

        self.assertEqual(value, self.refresh(cf_value).value)

        # ---
        with self.assertNumQueries(0):
            cf_value.set_value_n_save(value)

    def test_str(self):
        cfield = CustomField.objects.create(
            name='Length of ship',
            field_type=CustomField.STR,
            content_type=FakeOrganisation,
            is_required=True,
            description='Metric system bro',
        )
        self.assertEqual(CustomFieldString, cfield.value_class)
        self.assertEqual(_('Short string'), CustomFieldString.verbose_name)

        self.assertEqual(
            'customfieldstring',
            CustomFieldString.get_related_name()
        )

        orga = self._create_orga()
        value = '1562 m'
        cf_value = CustomFieldString.objects.create(
            custom_field=cfield,
            entity=orga,
            value=value,
        )
        self.assertValueEqual(cfield=cfield, entity=orga, value=value)

        formfield = cfield.get_formfield(custom_value=cf_value, user=orga.user)
        self.assertIsInstance(formfield, forms.CharField)
        self.assertTrue(formfield.required)
        self.assertEqual(value, formfield.initial)
        self.assertEqual(cfield.description, formfield.help_text)

    def test_text(self):
        cfield = CustomField.objects.create(
            name='History',
            field_type=CustomField.TEXT,
            content_type=FakeOrganisation,
        )
        self.assertEqual(CustomFieldText, cfield.value_class)
        self.assertEqual(_('Long text'), CustomFieldText.verbose_name)

        orga = self._create_orga()
        value = '''This ship was build a long time ago
by a man named Tochiro.
'''
        cf_value = CustomFieldText.objects.create(
            custom_field=cfield,
            entity=orga,
            value=value,
        )
        self.assertValueEqual(cfield=cfield, entity=orga, value=value)

        formfield = cfield.get_formfield(custom_value=cf_value, user=orga.user)
        self.assertIsInstance(formfield,        forms.CharField)
        self.assertIsInstance(formfield.widget, forms.Textarea)

    def test_url(self):
        cfield = CustomField.objects.create(
            name='History',
            field_type=CustomField.URL,
            content_type=FakeOrganisation,
        )
        self.assertEqual(CustomFieldURL, cfield.value_class)
        self.assertEqual(_('URL (link)'), CustomFieldURL.verbose_name)

        orga = self._create_orga()
        value = 'www.hybird.org'
        cf_value = CustomFieldURL.objects.create(
            custom_field=cfield,
            entity=orga,
            value=value,
        )
        self.assertValueEqual(cfield=cfield, entity=orga, value=value)

        formfield = cfield.get_formfield(custom_value=cf_value, user=orga.user)
        self.assertIsInstance(formfield, forms.CharField)
        self.assertEqual(200, formfield.max_length)

    def test_decimal(self):
        cfield = CustomField.objects.create(
            name='Length of ship',
            field_type=CustomField.FLOAT,
            content_type=FakeOrganisation,
        )
        self.assertEqual(CustomFieldFloat, cfield.value_class)
        self.assertEqual(_('Decimal'), CustomFieldFloat.verbose_name)

        orga = self._create_orga()
        value1 = '1562.50'
        cf_value = CustomFieldFloat.objects.create(
            custom_field=cfield,
            entity=orga,
            value=value1,
        )
        self.assertValueEqual(cfield=cfield, entity=orga, value=Decimal(value1))

        cf_value.value = value2 = Decimal('1562.60')
        cf_value.save()
        self.assertValueEqual(cfield=cfield, entity=orga, value=value2)

        formfield = cfield.get_formfield(custom_value=cf_value, user=orga.user)
        self.assertIsInstance(formfield, forms.DecimalField)

    def test_date(self):
        user = self.create_user()
        cfield = CustomField.objects.create(
            name='Last battle',
            field_type=CustomField.DATE,
            content_type=FakeOrganisation,
        )
        self.assertEqual(CustomFieldDate, cfield.value_class)
        self.assertEqual(_('Date'), CustomFieldDate.verbose_name)

        orga = FakeOrganisation.objects.create(user=user, name='Arcadia')
        value = date(year=2058, month=2, day=15)
        cf_value = CustomFieldDate.objects.create(
            custom_field=cfield,
            entity=orga,
            value=value,
        )
        self.assertValueEqual(cfield=cfield, entity=orga, value=value)

        formfield = cfield.get_formfield(custom_value=cf_value, user=orga.user)
        self.assertIsInstance(formfield, forms.DateField)

    def test_datetime(self):
        user = self.get_root_user()
        cfield = CustomField.objects.create(
            name='Last battle',
            field_type=CustomField.DATETIME,
            content_type=FakeOrganisation,
        )
        self.assertEqual(CustomFieldDateTime, cfield.value_class)
        self.assertEqual(_('Date and time'), CustomFieldDateTime.verbose_name)

        orga = FakeOrganisation.objects.create(user=user, name='Arcadia')
        value = self.create_datetime(year=2058, month=2, day=15, hour=18, minute=32)
        CustomFieldDateTime.objects.create(
            custom_field=cfield,
            entity=orga,
            value=value,
        )
        self.assertValueEqual(cfield=cfield, entity=orga, value=value)

        formfield = cfield.get_formfield(custom_value=None, user=orga.user)
        self.assertIsInstance(formfield, forms.DateTimeField)

    def test_bool(self):
        create_cfield = partial(
            CustomField.objects.create,
            field_type=CustomField.BOOL,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        cfield1 = create_cfield(name='Ship is armed?')
        self.assertEqual(CustomFieldBoolean, cfield1.value_class)
        self.assertEqual(_('Boolean (2 values: Yes/No)'), CustomFieldBoolean.verbose_name)

        orga = self._create_orga()
        value = True
        cf_value = CustomFieldBoolean.objects.create(
            custom_field=cfield1,
            entity=orga,
            value=value,
        )
        self.assertValueEqual(cfield=cfield1, entity=orga, value=value)

        formfield = cfield1.get_formfield(custom_value=cf_value, user=orga.user)
        self.assertIsInstance(formfield, forms.NullBooleanField)
        self.assertFalse(formfield.required)
        self.assertEqual(value, formfield.initial)

        # ---
        cfield2 = create_cfield(name='Pirates?', is_required=True)
        formfield = cfield2.get_formfield(custom_value=None, user=orga.user)
        self.assertIsInstance(formfield, forms.BooleanField)
        self.assertFalse(formfield.required)

    @toggle_history(enabled=False)
    def test_bool__set_value_n_save(self) -> None:
        cfield = CustomField.objects.create(
            name='Ship is armed?',
            field_type=CustomField.BOOL,
            content_type=FakeOrganisation,
        )
        orga = self._create_orga()

        cf_value: CustomFieldBoolean = CustomFieldBoolean.objects.create(
            custom_field=cfield,
            entity=orga,
            value=False,
        )

        with self.assertNumQueries(1):
            cf_value.set_value_n_save(True)

        self.assertIs(self.refresh(cf_value).value, True)

        # ---
        # with self.assertNumQueries(0):  # TODO: beware to False case
        with self.assertNumQueries(1):
            cf_value.set_value_n_save(True)

        # ---
        with self.assertNumQueries(1):
            cf_value.set_value_n_save(False)

        self.assertIs(self.refresh(cf_value).value, False)

        # ---
        with self.assertNumQueries(0):
            cf_value.set_value_n_save(None)

    def test_enum01(self):
        cfield = CustomField.objects.create(
            name='Type of ship',
            field_type=CustomField.ENUM,
            content_type=FakeOrganisation,
        )
        self.assertEqual(CustomFieldEnum, cfield.value_class)
        self.assertEqual(_('Choice list'), CustomFieldEnum.verbose_name)

        enum_value = CustomFieldEnumValue.objects.create(
            custom_field=cfield,
            value='BattleShip',
        )
        self.assertIsInstance(enum_value.uuid, UUID)

        orga = self._create_orga()
        cf_value = CustomFieldEnum.objects.create(
            custom_field=cfield,
            entity=orga,
            value=enum_value,
        )
        self.assertValueEqual(cfield=cfield, entity=orga, value=enum_value)

        formfield = cfield.get_formfield(custom_value=cf_value, user=orga.user)
        self.assertIsInstance(formfield, CreatorCustomEnumerableChoiceField)
        self.assertEqual(orga.user, formfield.user)
        self.assertEqual(cfield,    formfield.custom_field)
        self.assertFalse(formfield.required)

    def test_enum02(self):
        "set_value_n_save()."
        cfield = CustomField.objects.create(
            name='Type of ship',
            field_type=CustomField.ENUM,
            content_type=FakeOrganisation,
        )

        create_enum_value = partial(
            CustomFieldEnumValue.objects.create,
            custom_field=cfield,
        )
        enum_value1 = create_enum_value(value='BattleShip')
        enum_value2 = create_enum_value(value='Transporter')
        self.assertNotEqual(enum_value1.uuid, enum_value2.uuid)

        orga = self._create_orga()
        cf_value = CustomFieldEnum.objects.create(
            custom_field=cfield,
            entity=orga,
            value=enum_value1,
        )

        # 2: value + history
        with self.assertNumQueries(2):
            cf_value.set_value_n_save(str(enum_value2.id))

        self.assertEqual(enum_value2, self.refresh(cf_value).value)

        # ---
        with self.assertNumQueries(0):
            cf_value.set_value_n_save(enum_value2.id)

    def test_multi_enum(self):
        cfield = CustomField.objects.create(
            name='Weapons',
            field_type=CustomField.MULTI_ENUM,
            content_type=FakeOrganisation,
        )
        self.assertEqual(CustomFieldMultiEnum, cfield.value_class)
        self.assertEqual(_('Multiple choice list'), CustomFieldMultiEnum.verbose_name)

        create_enum_value = partial(
            CustomFieldEnumValue.objects.create,
            custom_field=cfield,
        )
        enum_value1 = create_enum_value(value='Lasers')
        enum_value2 = create_enum_value(value='Missiles')
        orga = self._create_orga()
        cf_value = CustomFieldMultiEnum.objects.create(
            custom_field=cfield,
            entity=orga,
        )
        cf_value.value.set([enum_value1, enum_value2])

        self.assertCountEqual(
            [enum_value1, enum_value2],
            self.refresh(cf_value).value.all(),
        )

        formfield = cfield.get_formfield(custom_value=cf_value, user=orga.user)
        self.assertIsInstance(formfield, CustomMultiEnumChoiceField)
        self.assertEqual(orga.user, formfield.user)
        self.assertEqual(cfield,    formfield.custom_field)
        self.assertFalse(formfield.required)
        self.assertListEqual(
            [
                (enum_value1.id, enum_value1.value),
                (enum_value2.id, enum_value2.value),
            ],
            formfield.choices,
        )

    def test_multi_enum__set_value_n_save(self):
        cfield = CustomField.objects.create(
            name='Weapons',
            field_type=CustomField.MULTI_ENUM,
            content_type=FakeOrganisation,
        )

        create_enum_value = partial(
            CustomFieldEnumValue.objects.create,
            custom_field=cfield,
        )
        enum_value1 = create_enum_value(value='Lasers')
        enum_value2 = create_enum_value(value='Missiles')
        orga = self._create_orga()

        cf_value = CustomFieldMultiEnum.objects.create(
            custom_field=cfield,
            entity=orga,
        )

        # 3 queries to select & save the values
        # 1 to create history line
        # 5. SELECT "creme_core_historyconfigitem"."relation_type_id" FROM
        #    "creme_core_historyconfigitem"  => is it OK?
        with self.assertNumQueries(5):
            cf_value.set_value_n_save([enum_value1, enum_value2])

        self.assertCountEqual(
            [enum_value1, enum_value2],
            self.refresh(cf_value).value.all(),
        )

    def test_delete(self):
        create_cfield = partial(
            CustomField.objects.create,
            field_type=CustomField.STR,
            content_type=FakeOrganisation,
        )
        cfield1 = create_cfield(name='Length of ship')
        cfield2 = create_cfield(name='Width of ship')

        def create_value(cfield, value):
            return CustomFieldString.objects.create(
                custom_field=cfield,
                entity=orga,
                value=value,
            )

        orga = self._create_orga()
        cf_value1 = create_value(cfield1, '1562 m')
        cf_value2 = create_value(cfield2, '845 m')

        cfield1.delete()
        self.assertDoesNotExist(cfield1)
        self.assertDoesNotExist(cf_value1)
        self.assertStillExists(cfield2)
        self.assertStillExists(cf_value2)

    def test_delete_entity(self) -> None:
        create_orga = partial(
            FakeOrganisation.objects.create,
            user=self.get_root_user(),
        )
        orga1 = create_orga(name='Arcadia')
        orga2 = create_orga(name='Queen Emeraldas')

        cfield: CustomField = CustomField.objects.create(
            name='Length',
            field_type=CustomField.INT,
            content_type=FakeOrganisation,
        )

        def create_value(entity, value):
            return CustomFieldInteger.objects.create(
                custom_field=cfield,
                entity=entity,
                value=value,
            )

        cf_value1 = create_value(orga1, 1562)
        cf_value2 = create_value(orga2, 1236)

        orga1.delete()
        self.assertDoesNotExist(orga1)
        self.assertStillExists(cfield)
        self.assertDoesNotExist(cf_value1)
        self.assertStillExists(orga2)
        self.assertStillExists(cf_value2)

    def test_save_values_for_entities(self):
        cfield = CustomField.objects.create(
            name='Length of ship',
            field_type=CustomField.INT,
            content_type=FakeOrganisation,
        )
        create_orga = partial(
            FakeOrganisation.objects.create,
            user=self.get_root_user(),
        )
        orga1 = create_orga(name='Arcadia')
        orga2 = create_orga(name='Queen Emeraldas')

        value = 456
        # with self.assertNumQueries(3):
        # NB: 2 queries to create history lines + 1 to retrieve config
        with self.assertNumQueries(6):
            CustomFieldInteger.save_values_for_entities(
                custom_field=cfield,
                entities=[orga1, orga2],
                value=value,
            )

        cf_value1 = self.get_object_or_fail(CustomFieldInteger, custom_field=cfield, entity=orga1)
        self.assertEqual(value, cf_value1.value)

        cf_value2 = self.get_object_or_fail(CustomFieldInteger, custom_field=cfield, entity=orga1)
        self.assertEqual(value, cf_value2.value)

        # Do not save entities with existing same value ---
        orga3 = create_orga(name='Yamato')

        # with self.assertNumQueries(2):
        # NB: 1 query to create history line
        with self.assertNumQueries(3):
            CustomFieldInteger.save_values_for_entities(
                custom_field=cfield,
                entities=[orga1, orga3],
                value=value,
            )

        cf_value3 = self.get_object_or_fail(CustomFieldInteger, custom_field=cfield, entity=orga3)
        self.assertEqual(value, cf_value3.value)

        ContentType.objects.get_for_model(CremeEntity)  # Fill cache

        # Empty value => deletion ---
        # NB1: Django makes a query to retrieve the IDs, then performs a second query...
        # NB2: 2x3 queries for history (get entity, get real entity, update line)
        # with self.assertNumQueries(2):
        with self.assertNumQueries(8):
            CustomFieldInteger.save_values_for_entities(
                custom_field=cfield,
                entities=[orga1, orga2],
                value=None,
            )

        self.assertDoesNotExist(cf_value1)
        self.assertDoesNotExist(cf_value2)
        self.assertStillExists(cf_value3)

    def test_save_values_for_entities__update_cache(self):
        cfield = CustomField.objects.create(
            name='Length of ship',
            field_type=CustomField.INT,
            content_type=FakeOrganisation,
        )
        orga = FakeOrganisation.objects.create(
            user=self.get_root_user(), name='Arcadia',
        )
        self.assertIsNone(orga.get_custom_value(cfield))

        # Edition ---
        value = 456
        CustomFieldValue.save_values_for_entities(
            custom_field=cfield, entities=[orga], value=value,
        )
        cvalue = orga.get_custom_value(cfield)
        self.assertIsInstance(cvalue, CustomFieldInteger)
        self.assertEqual(value, cvalue.value)

        # Empty value => deletion ---
        CustomFieldValue.save_values_for_entities(
            custom_field=cfield, entities=[orga], value=None,
        )
        self.assertIsNone(orga.get_custom_value(cfield))

    def test_get_custom_values_map01(self):
        create_cfield = partial(
            CustomField.objects.create,
            field_type=CustomField.INT,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        cfield1 = create_cfield(name='Length of ship')
        cfield2 = create_cfield(name='Width of ship')

        create_orga = partial(
            FakeOrganisation.objects.create,
            user=self.get_root_user(),
        )
        orga1 = create_orga(name='Arcadia')
        orga2 = create_orga(name='Queen Emeraldas')
        orga3 = create_orga(name='Yamato')

        create_cf_value = CustomFieldInteger.objects.create
        cf_value11 = create_cf_value(custom_field=cfield1, entity=orga1, value=1200)
        cf_value12 = create_cf_value(custom_field=cfield2, entity=orga1, value=450)
        cf_value21 = create_cf_value(custom_field=cfield1, entity=orga2, value=860)

        with self.assertNumQueries(1):
            values_map = CustomField.get_custom_values_map(
                entities=[orga1, orga2, orga3],
                custom_fields=[cfield1, cfield2],
            )

        self.assertIsInstance(values_map, defaultdict)
        self.assertIsInstance(values_map.default_factory(), dict)
        self.assertDictEqual(
            {
                orga1.id: {
                    cfield1.id: cf_value11,
                    cfield2.id: cf_value12,
                },
                orga2.id: {
                    cfield1.id: cf_value21,
                },
                # orga3.id: {}, NOPE
            },
            values_map,
        )

    def test_get_custom_values_map02(self):
        "Several types of fields."
        create_cfield = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        cfield1 = create_cfield(name='Length of ship', field_type=CustomField.INT)
        cfield2 = create_cfield(name='Width of ship',  field_type=CustomField.STR)

        create_orga = partial(
            FakeOrganisation.objects.create,
            user=self.get_root_user(),
        )
        orga1 = create_orga(name='Arcadia')
        orga2 = create_orga(name='Queen Emeraldas')

        create_cf_value1 = partial(CustomFieldInteger.objects.create, custom_field=cfield1)
        create_cf_value2 = partial(CustomFieldString.objects.create,  custom_field=cfield2)
        cf_value11 = create_cf_value1(custom_field=cfield1, entity=orga1, value=1200)
        cf_value12 = create_cf_value2(custom_field=cfield2, entity=orga1, value='450 m')
        cf_value21 = create_cf_value1(custom_field=cfield1, entity=orga2, value=860)

        with self.assertNumQueries(2):
            values_map = CustomField.get_custom_values_map(
                entities=[orga1, orga2],
                custom_fields=[cfield1, cfield2],
            )

        self.assertDictEqual(
            {
                orga1.id: {
                    cfield1.id: cf_value11,
                    cfield2.id: cf_value12,
                },
                orga2.id: {
                    cfield1.id: cf_value21,
                },
                # orga3.id: {}, NOPE
            },
            values_map,
        )
