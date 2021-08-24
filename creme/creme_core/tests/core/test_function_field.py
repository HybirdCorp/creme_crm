# -*- coding: utf-8 -*-

from decimal import Decimal
from functools import partial

from django.db.models import Q
from django.urls import reverse
from django.utils.formats import number_format
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellFunctionField
from creme.creme_core.core.function_field import (
    FunctionField,
    FunctionFieldDecimal,
    FunctionFieldLink,
    FunctionFieldResult,
    FunctionFieldResultsList,
    _FunctionFieldRegistry,
)
from creme.creme_core.forms.listview import SelectLVSWidget
from creme.creme_core.function_fields import PropertiesField
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    FakeContact,
)

from ..base import CremeTestCase
from ..fake_models import FakeOrganisation


class FunctionFieldsTestCase(CremeTestCase):
    def test_registry01(self):
        class Klass1:
            pass

        class Klass2(Klass1):
            pass

        registry = _FunctionFieldRegistry()

        fname11 = 'name11'
        fname12 = 'name12'
        fname13 = 'name13'
        fname2  = 'name2'

        class TestFunctionField11(FunctionField):
            name = fname11
            verbose_name = 'Verbose name 11'

        class TestFunctionField12(FunctionField):
            name = fname12
            verbose_name = 'Verbose name 12'

        class TestFunctionField13(FunctionField):
            name = fname13
            verbose_name = 'Verbose name 13'

        class TestFunctionField2(FunctionField):
            name = fname2
            verbose_name = 'Verbose name 2'

        registry.register(
            Klass1, TestFunctionField11, TestFunctionField12, TestFunctionField13,
        ).register(
            Klass2, TestFunctionField2,
        )
        self.assertIsInstance(registry.get(Klass1, fname11), TestFunctionField11)
        self.assertIsInstance(registry.get(Klass1, fname12), TestFunctionField12)
        self.assertIsInstance(registry.get(Klass1, fname13), TestFunctionField13)
        self.assertIsNone(registry.get(Klass1, 'unknown'))
        self.assertIsNone(registry.get(Klass1, fname2))

        self.assertIsInstance(registry.get(Klass2, fname11), TestFunctionField11)
        self.assertIsInstance(registry.get(Klass2, fname12), TestFunctionField12)
        self.assertIsInstance(registry.get(Klass2, fname2),  TestFunctionField2)

        self.assertIsNone(registry.get(Klass1, fname2))

        # Function fields
        self.assertSetEqual(
            {TestFunctionField11, TestFunctionField12, TestFunctionField13},
            {ff.__class__ for ff in registry.fields(Klass1)},
        )
        self.assertSetEqual(
            {TestFunctionField11, TestFunctionField12, TestFunctionField13, TestFunctionField2},
            {ff.__class__ for ff in registry.fields(Klass2)},
        )

        # Unregister -----
        registry.unregister(Klass1, TestFunctionField11, TestFunctionField12)
        self.assertIsNone(registry.get(Klass1, fname11))
        self.assertIsNone(registry.get(Klass1, fname12))
        self.assertIsInstance(registry.get(Klass1, fname13), TestFunctionField13)

        self.assertIsNone(registry.get(Klass2, fname11))

    def test_registry02(self):
        "Duplicates error."
        class Klass:
            pass

        registry = _FunctionFieldRegistry()

        class TestFunctionField1(FunctionField):
            name = 'name1'
            verbose_name = 'Verbose name 1'

        class TestFunctionField2(FunctionField):
            name = TestFunctionField1.name  # <==
            verbose_name = 'Verbose name 2'

        registry.register(Klass, TestFunctionField1)

        with self.assertRaises(_FunctionFieldRegistry.RegistrationError):
            registry.register(Klass, TestFunctionField2)

    def test_registry03(self):
        "Overridden field."
        class Klass1:
            pass

        class Klass2(Klass1):
            pass

        registry = _FunctionFieldRegistry()

        fname1 = 'name1'
        fname2 = 'name2'

        class TestFunctionField1(FunctionField):
            name = fname1
            verbose_name = 'Verbose name 1'

        class TestFunctionField2(FunctionField):
            name = fname2
            verbose_name = 'Verbose name 2'

        class TestFunctionField22(FunctionField):
            name = TestFunctionField2.name  # <== Override
            verbose_name = 'Verbose name 2'

        registry.register(Klass1, TestFunctionField1, TestFunctionField2)
        registry.register(Klass2, TestFunctionField22)
        self.assertIsInstance(registry.get(Klass2, fname1), TestFunctionField1)

        # Not TestFunctionField2
        self.assertIsInstance(registry.get(Klass2, fname2), TestFunctionField22)

        # Function fields
        self.assertSetEqual(
            {TestFunctionField1, TestFunctionField2},
            {ff.__class__ for ff in registry.fields(Klass1)},
        )
        self.assertSetEqual(
            {TestFunctionField1, TestFunctionField22},
            {ff.__class__ for ff in registry.fields(Klass2)},
        )

    def test_registry04(self):
        "Unregister() error."
        class Klass:
            pass

        registry = _FunctionFieldRegistry()

        class TestFunctionField(FunctionField):
            name = 'name'
            verbose_name = 'Verbose name'

        with self.assertRaises(_FunctionFieldRegistry.RegistrationError):
            registry.unregister(Klass, TestFunctionField)

    def test_result(self):
        value = 'My value'
        result = FunctionFieldResult(value)
        self.assertEqual(value, result.for_csv())
        self.assertEqual(value, result.for_html())

    def test_result_decimal(self):
        value = Decimal('1234.45')
        result = FunctionFieldDecimal(value)
        self.assertEqual(
            number_format(value, use_l10n=True, force_grouping=True),
            result.for_html(),
        )
        self.assertEqual(
            number_format(value, use_l10n=True),
            result.for_csv(),
        )

    def test_result_link(self):
        label = 'My Contacts'
        url = reverse('creme_core__list_fake_contacts')
        result = FunctionFieldLink(label=label, url=url)
        self.assertEqual(label, result.for_csv())
        self.assertHTMLEqual(f'<a href="{url}">{label}</a>', result.for_html())

    def test_result_list(self):
        value1 = 'My value #1'
        value2 = 'My value #2'
        result = FunctionFieldResultsList([
            FunctionFieldResult(value1),
            FunctionFieldResult(value2),
        ])
        self.assertEqual(f'{value1}/{value2}', result.for_csv())
        self.assertHTMLEqual(
            f'<ul><li>{value1}</li><li>{value2}</li></ul>',
            result.for_html(),
        )

    def test_field(self):
        fname = 'get_delete_absolute_url'
        label = 'URL'

        class TestFunctionField(FunctionField):
            name = fname
            verbose_name = label

        ffield = TestFunctionField()
        self.assertEqual(fname, ffield.name)
        self.assertEqual(label, ffield.verbose_name)
        self.assertIs(False, ffield.is_hidden)

        user = self.create_user()
        entity = CremeEntity.objects.create(user=user)
        result = ffield(entity, user)
        self.assertIsInstance(result, FunctionFieldResult)
        self.assertEqual(entity.get_delete_absolute_url(), result.for_csv())

    def test_properties_field(self):
        user = self.create_user()

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_foo', text='Foo')
        ptype2 = create_ptype(
            str_pk='test-prop_bar', text='Bar',
            subject_ctypes=[FakeContact, FakeOrganisation],
        )

        ptype3 = create_ptype(str_pk='test-prop_del', text='Deleted')
        ptype3.enabled = False
        ptype3.save()

        ptype4 = create_ptype(
            str_pk='test-prop_baz', text='Baz', subject_ctypes=[FakeOrganisation],
        )

        # --
        create_contact = partial(FakeContact.objects.create, user=user)
        entity1 = create_contact(first_name='Spike', last_name='Spiegel')
        entity2 = create_contact(first_name='Faye',  last_name='Valentine')

        create_prop = CremeProperty.objects.create
        create_prop(creme_entity=entity1, type=ptype1)
        create_prop(creme_entity=entity1, type=ptype2)
        create_prop(creme_entity=entity1, type=ptype3)
        create_prop(creme_entity=entity2, type=ptype1)

        ffield = PropertiesField()

        with self.assertNumQueries(1):
            result1 = ffield(entity1, user)

        self.assertIsInstance(result1, FunctionFieldResultsList)
        # self.assertEqual(f'{ptype1.text}/{ptype2.text}', result1.for_csv())
        self.assertEqual(
            f'{ptype2.text}/{ptype3.text}/{ptype1.text}',
            result1.for_csv(),
        )
        self.assertHTMLEqual(
            f'<ul>'
            f' <li><a href="{ptype2.get_absolute_url()}">{ptype2.text}</a></li>'
            f' <li>'
            f'  <a href="{ptype3.get_absolute_url()}" class="is_deleted">{ptype3.text}</a>'
            f' </li>'
            f' <li><a href="{ptype1.get_absolute_url()}">{ptype1.text}</a></li>'
            f'</ul>',
            result1.for_html(),
        )

        with self.assertNumQueries(0):
            ffield(entity1, user)

        # ---
        with self.assertNumQueries(1):
            ffield(entity2, user)

        # ---
        # NB: clean internal caches
        entity1 = self.refresh(entity1)
        entity2 = self.refresh(entity2)

        with self.assertNumQueries(1):
            ffield.populate_entities([entity1, entity2], user)

        with self.assertNumQueries(0):
            ffield(entity1, user)
            ffield(entity2, user)

        # ---
        field_class = ffield.search_field_builder
        self.assertIsNotNone(field_class)

        field = field_class(
            cell=EntityCellFunctionField(model=FakeContact, func_field=ffield),
            user=user,
        )
        self.assertIsInstance(field.widget, SelectLVSWidget)

        choices = field.widget.choices
        self.assertIn({'value': 'NULL',    'label': _('* no property *')}, choices)

        index1 = self.assertIndex({'value': ptype1.id, 'label': ptype1.text}, choices)
        index2 = self.assertIndex({'value': ptype2.id, 'label': ptype2.text}, choices)
        self.assertLess(index2, index1)

        self.assertNotIn({'value': ptype4.id, 'label': ptype4.text}, choices)
        self.assertNotIn({'value': ptype3.id, 'label': ptype3.text}, choices)

        to_python = field.to_python
        self.assertQEqual(Q(), to_python(value=None))
        self.assertQEqual(Q(), to_python(value=''))

        value = ptype1.id
        self.assertQEqual(Q(properties__type=value), to_python(value=value))

        self.assertQEqual(Q(properties__isnull=True), to_python(value='NULL'))
