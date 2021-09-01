# -*- coding: utf-8 -*-

from copy import deepcopy
from datetime import date
from decimal import Decimal
from functools import partial

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.formats import date_format, number_format
from django.utils.timezone import localtime
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import (
    CELLS_MAP,
    EntityCell,
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
    EntityCellsRegistry,
)
from creme.creme_core.core.function_field import (
    FunctionField,
    FunctionFieldResult,
    function_field_registry,
)
from creme.creme_core.models import (
    CremeEntity,
    CustomField,
    CustomFieldEnumValue,
    FakeCivility,
    FakeContact,
    FakeDocument,
    FakeFolder,
    FakePosition,
    FieldsConfig,
    Relation,
    RelationType,
)

from ..base import CremeTestCase


class EntityCellTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.contact_ct = ContentType.objects.get_for_model(FakeContact)

    def test_registry_global(self):
        self.assertEqual(EntityCellRegularField,  CELLS_MAP[EntityCellRegularField.type_id])
        self.assertEqual(EntityCellCustomField,   CELLS_MAP[EntityCellCustomField.type_id])
        self.assertEqual(EntityCellFunctionField, CELLS_MAP[EntityCellFunctionField.type_id])
        self.assertEqual(EntityCellRelation,      CELLS_MAP[EntityCellRelation.type_id])

    def test_registry_register01(self):
        registry = EntityCellsRegistry()

        with self.assertRaises(KeyError):
            registry[EntityCellRegularField.type_id]  # NOQA

        self.assertNotIn(EntityCellFunctionField.type_id, registry)
        self.assertListEqual([], [*registry.cell_classes])

        res = registry.register(EntityCellRegularField, EntityCellFunctionField)
        self.assertIs(res, registry)

        self.assertEqual(EntityCellRegularField,  registry[EntityCellRegularField.type_id])
        self.assertEqual(EntityCellFunctionField, registry[EntityCellFunctionField.type_id])

        self.assertIn(EntityCellRegularField.type_id,  registry)
        self.assertIn(EntityCellFunctionField.type_id, registry)

        self.assertCountEqual(
            [EntityCellRegularField, EntityCellFunctionField],
            [*registry.cell_classes],
        )

    def test_registry_register02(self):
        "Duplicate."
        registry = EntityCellsRegistry().register(EntityCellRegularField)

        class DuplicatedIdCell(EntityCell):
            type_id = EntityCellRegularField.type_id

        with self.assertRaises(EntityCellsRegistry.RegistrationError):
            registry.register(DuplicatedIdCell)

    def test_registry_call(self):
        registry = EntityCellsRegistry()

        with self.assertRaises(KeyError):
            registry[EntityCellRegularField.type_id]  # NOQA

        self.assertNotIn(EntityCellRegularField.type_id, registry)

        res = registry(EntityCellRegularField)
        self.assertIs(res, EntityCellRegularField)
        self.assertEqual(EntityCellRegularField, registry[EntityCellRegularField.type_id])

        self.assertIn(EntityCellRegularField.type_id, registry)

    def test_registry_deepcopy(self):
        registry1 = EntityCellsRegistry()
        registry1(EntityCellRegularField)
        registry1(EntityCellCustomField)

        registry2 = deepcopy(registry1)
        registry2(EntityCellFunctionField)

        with self.assertNoException():
            registry1[EntityCellRegularField.type_id]
            registry2[EntityCellRegularField.type_id]

            registry1[EntityCellCustomField.type_id]
            registry2[EntityCellCustomField.type_id]

            registry2[EntityCellFunctionField.type_id]

        with self.assertRaises(KeyError):
            registry1[EntityCellFunctionField.type_id]

    def test_registry_build_cells_from_dicts01(self):
        "No error."
        cells, errors = CELLS_MAP.build_cells_from_dicts(
            model=FakeContact,
            dicts=[
                {'type': EntityCellRegularField.type_id,  'value': 'first_name'},
                {'type': EntityCellFunctionField.type_id, 'value': 'get_pretty_properties'},
            ],
        )
        self.assertIs(errors, False)
        self.assertEqual(2, len(cells))

        cell1 = cells[0]
        self.assertIsInstance(cell1, EntityCellRegularField)
        self.assertEqual(FakeContact,  cell1.model)
        self.assertEqual('first_name', cell1.value)

        cell2 = cells[1]
        self.assertIsInstance(cell2, EntityCellFunctionField)
        self.assertEqual(FakeContact,             cell2.model)
        self.assertEqual('get_pretty_properties', cell2.value)

    def test_registry_build_cells_from_dicts02(self):
        "Error."
        cells, errors = CELLS_MAP.build_cells_from_dicts(
            model=FakeDocument,
            dicts=[
                {'type': EntityCellRegularField.type_id,  'value': 'invalid'},
                {'type': EntityCellFunctionField.type_id, 'value': 'get_pretty_properties'},
            ],
        )
        self.assertIs(errors, True)
        self.assertEqual(1, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(FakeDocument,            cell.model)
        self.assertEqual('get_pretty_properties', cell.value)

    def test_regular_field01(self):
        self.assertEqual(_('Fields'), EntityCellRegularField.verbose_name)

        field_name = 'first_name'
        cell = EntityCellRegularField.build(model=FakeContact, name=field_name)
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_name,      cell.value)
        self.assertEqual(_('First name'), cell.title)
        self.assertEqual(f'regular_field-{field_name}', cell.key)
        self.assertIs(cell.is_excluded, False)
        self.assertIs(cell.is_multiline, False)

    def test_regular_field_date(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='birthday')
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_regular_field_bool(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='is_a_nerd')
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

    def test_regular_field_fk(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='position')
        self.assertEqual('regular_field-position', cell.key)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

        cell = EntityCellRegularField.build(model=FakeContact, name='image')
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

    def test_regular_field_fk_subfield01(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='position__title')
        self.assertEqual('regular_field-position__title', cell.key)

        cell = EntityCellRegularField.build(model=FakeContact, name='image__name')
        self.assertEqual('regular_field-image__name', cell.key)

    def test_regular_field_fk_subfield02(self):
        "Date ForeignKey subfield."
        cell = EntityCellRegularField.build(model=FakeContact, name='image__created')
        self.assertEqual('{} - {}'.format(_('Photograph'), _('Creation date')), cell.title)

    def test_regular_field_fk_subfield03(self):
        "ForeignKey subfield is a FK."
        cell = EntityCellRegularField.build(model=FakeDocument, name='linked_folder__category')
        self.assertEqual('regular_field-linked_folder__category', cell.key)

    def test_regular_field_m2m(self):
        cell = EntityCellRegularField.build(model=FakeContact, name='languages')
        self.assertTrue(cell.is_multiline)

        cell = EntityCellRegularField.build(model=FakeContact, name='languages__name')
        self.assertTrue(cell.is_multiline)

    def test_regular_field_hidden(self):
        "Hidden field."
        hidden = 'first_name'

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (hidden,  {FieldsConfig.HIDDEN: True}),
            ],
        )

        cell = EntityCellRegularField.build(model=FakeContact, name=hidden)
        self.assertEqual(_('{} [hidden]').format(_('First name')), cell.title)
        self.assertIs(cell.is_excluded, True)

    def test_regular_field_errors(self):
        build = partial(EntityCellRegularField.build, model=FakeContact)
        self.assertIsNone(build(name='unknown_field'))
        self.assertIsNone(build(name='user__unknownfield'))

    def test_customfield_int(self):
        self.assertEqual(_('Custom fields'), EntityCellCustomField.verbose_name)

        name = 'Size (cm)'
        customfield = CustomField.objects.create(
            name=name,
            field_type=CustomField.INT,
            content_type=self.contact_ct,
        )

        cell = EntityCellCustomField(customfield)
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(str(customfield.id),              cell.value)
        self.assertEqual(name,                             cell.title)
        self.assertEqual(f'custom_field-{customfield.id}', cell.key)
        self.assertIs(cell.is_multiline, False)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,         cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        cell = EntityCellCustomField.build(FakeContact, customfield.id)
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(str(customfield.id), cell.value)

        self.assertIsNone(EntityCellCustomField.build(FakeContact, 1000))
        self.assertIsNone(EntityCellCustomField.build(FakeContact, 'notanint'))

        # Render ---
        user = self.create_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        self.assertEqual('', cell.render_html(entity=yoko, user=user))

        customfield.value_class.objects.create(entity=yoko, custom_field=customfield, value=152)
        yoko = self.refresh(yoko)  # Reset caches
        self.assertEqual('152', cell.render_html(entity=yoko, user=user))
        self.assertEqual('152', cell.render_csv(entity=yoko, user=user))

    def test_customfield_decimal(self):
        customfield = CustomField.objects.create(
            name='Weight',
            field_type=CustomField.FLOAT,
            content_type=self.contact_ct,
        )

        cell = EntityCellCustomField(customfield)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,         cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.create_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        value = Decimal('1.52')
        value_str = number_format(value, use_l10n=True)
        customfield.value_class.objects.create(entity=yoko, custom_field=customfield, value=value)
        self.assertEqual(value_str, cell.render_html(entity=yoko, user=user))
        self.assertEqual(value_str, cell.render_csv(entity=yoko, user=user))

    def test_customfield_datetime(self):
        customfield = CustomField.objects.create(
            name='Day & hour',
            field_type=CustomField.DATETIME,
            content_type=self.contact_ct,
        )

        cell = EntityCellCustomField(customfield)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.create_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        dt = self.create_datetime(year=2058, month=3, day=26, hour=12)
        dt_str = date_format(localtime(dt), 'DATETIME_FORMAT')
        customfield.value_class.objects.create(
            entity=yoko, custom_field=customfield, value=dt,
        )
        self.assertEqual(dt_str, cell.render_html(entity=yoko, user=user))
        self.assertEqual(dt_str, cell.render_csv(entity=yoko, user=user))

    def test_customfield_date(self):
        customfield = CustomField.objects.create(
            name='Day',
            field_type=CustomField.DATE,
            content_type=self.contact_ct,
        )

        cell = EntityCellCustomField(customfield)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.create_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        date_obj = date(year=2058, month=3, day=26)
        date_str = date_format(date_obj, 'DATE_FORMAT')
        customfield.value_class.objects.create(
            entity=yoko, custom_field=customfield, value=date_obj,
        )
        self.assertEqual(date_str, cell.render_html(entity=yoko, user=user))
        self.assertEqual(date_str, cell.render_csv(entity=yoko, user=user))

    def test_customfield_bool(self):
        customfield = CustomField.objects.create(
            name='Is fun ?',
            field_type=CustomField.BOOL,
            content_type=self.contact_ct,
        )

        cell = EntityCellCustomField(customfield)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.create_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        customfield.value_class.objects.create(entity=yoko, custom_field=customfield, value=True)
        self.assertEqual(
            f'<input type="checkbox" checked disabled/>{_("Yes")}',
            cell.render_html(entity=yoko, user=user)
        )
        self.assertEqual(_('Yes'), cell.render_csv(entity=yoko, user=user))

    def test_customfield_str(self):
        customfield = CustomField.objects.create(
            name='Nickname',
            field_type=CustomField.STR,
            content_type=self.contact_ct,
        )

        cell = EntityCellCustomField(customfield)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.create_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')

        value = '<i>Sniper</i>'
        customfield.value_class.objects.create(
            entity=yoko, custom_field=customfield, value=value,
        )
        self.assertEqual(
            '&lt;i&gt;Sniper&lt;/i&gt;',
            cell.render_html(entity=yoko, user=user)
        )
        self.assertEqual(value, cell.render_csv(entity=yoko, user=user))

    def test_customfield_text(self):
        customfield = CustomField.objects.create(
            name='Plot',
            field_type=CustomField.TEXT,
            content_type=self.contact_ct,
        )

        cell = EntityCellCustomField(customfield)

        # Render ---
        user = self.create_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')

        value = 'Yoko is a young woman from <i>Littner</i>, a village neighboring Giha.\n' \
                'She helps introduce Simon and Kamina to the surface world.'
        customfield.value_class.objects.create(
            entity=yoko, custom_field=customfield, value=value,
        )
        self.assertHTMLEqual(
            '<p>'
            'Yoko is a young woman from &lt;i&gt;Littner&lt;/i&gt;, a village neighboring Giha.'
            '<br>'
            'She helps introduce Simon and Kamina to the surface world.'
            '</p>',
            cell.render_html(entity=yoko, user=user)
        )
        self.assertEqual(value, cell.render_csv(entity=yoko, user=user))

    def test_customfield_url(self):
        customfield = CustomField.objects.create(
            name='Village URL',
            field_type=CustomField.URL,
            content_type=self.contact_ct,
        )

        cell = EntityCellCustomField(customfield)

        # Render ---
        user = self.create_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')

        value = 'www.littner.org'
        customfield.value_class.objects.create(
            entity=yoko, custom_field=customfield, value=value,
        )
        self.assertHTMLEqual(
            f'<a href="{value}" target="_blank">{value}</a>',
            cell.render_html(entity=yoko, user=user)
        )
        self.assertEqual(value, cell.render_csv(entity=yoko, user=user))

    def test_customfield_enum(self):
        customfield = CustomField.objects.create(
            name='Eva',
            field_type=CustomField.ENUM,
            content_type=self.contact_ct,
        )

        create_enumvalue = partial(
            CustomFieldEnumValue.objects.create,
            custom_field=customfield,
        )
        enum_value1 = create_enumvalue(value='Eva-00<script>')
        create_enumvalue(value='Eva-01')

        cell = EntityCellCustomField(customfield)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.create_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        self.assertEqual('', cell.render_html(entity=yoko, user=user))
        self.assertEqual('', cell.render_csv(entity=yoko, user=user))

        customfield.value_class.objects.create(
            entity=yoko, custom_field=customfield, value=enum_value1,
        )
        yoko = self.refresh(yoko)  # Avoid cache
        self.assertEqual('Eva-00&lt;script&gt;', cell.render_html(entity=yoko, user=user))
        self.assertEqual(enum_value1.value, cell.render_csv(entity=yoko, user=user))

    def test_customfield_mulitenum(self):
        customfield = CustomField.objects.create(
            name='Eva',
            field_type=CustomField.MULTI_ENUM,
            content_type=self.contact_ct,
        )

        create_enumvalue = partial(
            CustomFieldEnumValue.objects.create,
            custom_field=customfield,
        )
        enum_value1 = create_enumvalue(value='Eva-00')
        create_enumvalue(value='Eva-01')
        enum_value3 = create_enumvalue(value='Eva-02<script>')

        cell = EntityCellCustomField(customfield)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.create_user()
        yoko = FakeContact.objects.create(user=user, first_name='Yoko', last_name='Littner')
        self.assertEqual('', cell.render_html(entity=yoko, user=user))
        self.assertEqual('', cell.render_csv(entity=yoko, user=user))

        cf_value = customfield.value_class(entity=yoko, custom_field=customfield)
        cf_value.set_value_n_save([enum_value1.id, enum_value3.id])
        yoko = self.refresh(yoko)  # Avoid cache
        self.assertHTMLEqual(
            f'<ul><li>{enum_value1.value}</li><li>Eva-02&lt;script&gt;</li></ul>',
            cell.render_html(entity=yoko, user=user)
        )
        self.assertEqual(
            f'{enum_value1.value} / {enum_value3.value}',
            cell.render_csv(entity=yoko, user=user)
        )

    def test_customfield_deleted(self):
        name = 'Size (cm)'
        customfield = CustomField.objects.create(
            name=name,
            field_type=CustomField.INT,
            content_type=self.contact_ct,
            is_deleted=True,
        )

        cell = EntityCellCustomField(customfield)
        self.assertEqual(_('{} [deleted]').format(name), cell.title)
        self.assertIs(cell.is_hidden, False)
        self.assertIs(cell.is_excluded, True)

    def test_relation(self):
        self.assertEqual(_('Relationships'), EntityCellRelation.verbose_name)

        loved = RelationType.objects.smart_update_or_create(
            ('test-object_loved', 'Is loved by'),
            ('test-subject_loved', 'Is loving'),
        )[0]
        cell = EntityCellRelation(model=FakeContact, rtype=loved)
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(FakeContact,     cell.model)
        self.assertEqual(str(loved.id),   cell.value)
        self.assertEqual(loved.predicate, cell.title)
        self.assertEqual(f'relation-{loved.id}', cell.key)
        self.assertIs(cell.is_multiline, True)
        self.assertEqual(loved, cell.relation_type)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        # Render ---
        user = self.create_user()
        create_contact = partial(FakeContact.objects.create, user=user)
        contacts = [
            create_contact(first_name='Nagate',  last_name='Tanikaze'),
            create_contact(first_name='Shizuka', last_name='Hoshijiro'),
            create_contact(first_name='Izana',   last_name='Shinatose'),
        ]

        create_rel = partial(
            Relation.objects.create,
            user=user, subject_entity=contacts[0], type=loved,
        )
        create_rel(object_entity=contacts[1])
        create_rel(object_entity=contacts[2])

        self.assertEqual(
            f'{contacts[2]}/{contacts[1]}',
            cell.render_csv(entity=contacts[0], user=user),
        )
        self.assertHTMLEqual(
            f'<ul>'
            f' <li><a href="{contacts[2].get_absolute_url()}">{contacts[2]}</li>'
            f' <li><a href="{contacts[1].get_absolute_url()}">{contacts[1]}</li>'
            f'</ul>',
            cell.render_html(entity=contacts[0], user=user),
        )

    def test_functionfield01(self):
        self.assertEqual(_('Computed fields'), EntityCellFunctionField.verbose_name)

        name = 'get_pretty_properties'
        funfield = function_field_registry.get(FakeContact, name)
        self.assertIsNotNone(funfield)

        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(name,                              cell.value)
        self.assertEqual(str(funfield.verbose_name),        cell.title)
        self.assertEqual(f'function_field-{funfield.name}', cell.key)
        self.assertIs(cell.is_hidden,    False)
        self.assertIs(cell.is_multiline, True)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        cell = EntityCellFunctionField.build(FakeContact, func_field_name=name)
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(name, cell.value)

        self.assertIsNone(EntityCellFunctionField.build(FakeContact, func_field_name='invalid'))

    def test_functionfield02(self):
        class PhoneFunctionField(FunctionField):
            name         = 'phone_or_mobile'
            verbose_name = 'Phone or mobile'

            def __call__(self, entity, user):
                return FunctionFieldResult(entity.phone or entity.mobile)

        funfield = PhoneFunctionField()
        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)
        self.assertEqual(funfield.name,         cell.value)
        self.assertEqual(funfield.verbose_name, cell.title)
        self.assertFalse(cell.is_multiline)

    def test_eq(self):
        cell1 = EntityCellRegularField.build(model=FakeDocument, name='title')

        # Other is not an EntityCell
        self.assertNotEqual(None,       cell1)
        self.assertNotEqual('whatever', cell1)

        self.assertEqual(
            EntityCellRegularField.build(model=FakeDocument, name='title'),
            cell1
        )
        # Value is different
        self.assertNotEqual(
            EntityCellRegularField.build(model=FakeDocument, name='linked_folder'),
            cell1
        )
        # Model is different
        self.assertNotEqual(
            EntityCellRegularField.build(model=FakeFolder, name='title'),
            cell1
        )

        # Class is different
        class TestCell(EntityCell):
            type_id = 'test'

            def __init__(self, model, value):
                super().__init__(model=model, value=value)

        self.assertNotEqual(
            TestCell(model=FakeDocument, value='title'),
            cell1
        )

    def test_mixed_populate_entities01(self):
        "Regular fields: no FK."
        user = self.create_user()

        pos = FakePosition.objects.create(title='Pilot')
        create_contact = partial(FakeContact.objects.create, user=user, position_id=pos.id)
        contacts = [
            create_contact(first_name='Nagate',  last_name='Tanikaze'),
            create_contact(first_name='Shizuka', last_name='Hoshijiro'),
        ]

        build = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [build(name='last_name'), build(name='first_name')]

        with self.assertNumQueries(0):
            EntityCell.mixed_populate_entities(cells=cells, entities=contacts, user=user)

        with self.assertNumQueries(1):
            contacts[0].position  # NOQA

    def test_mixed_populate_entities02(self):
        "Regular fields: FK."
        user = self.create_user()

        pos = FakePosition.objects.all()[0]
        civ = FakeCivility.objects.all()[0]
        create_contact = partial(
            FakeContact.objects.create, user=user, position=pos, civility=civ,
        )
        contact1 = create_contact(first_name='Nagate', last_name='Tanikaze')
        contact2 = create_contact(first_name='Shizuka', last_name='Hoshijiro')
        # NB: we refresh because the __str__() method retrieves the civility
        contacts = [self.refresh(contact1), self.refresh(contact2)]

        build = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [
            build(name='last_name'), build(name='first_name'),
            build(name='position'),
            build(name='civility__title'),
        ]

        with self.assertNumQueries(2):
            EntityCell.mixed_populate_entities(cells=cells, entities=contacts, user=user)

        with self.assertNumQueries(0):
            contacts[0].position  # NOQA
            contacts[1].position  # NOQA
            contacts[0].civility  # NOQA
            contacts[1].civility  # NOQA

    def test_mixed_populate_entities03(self):
        "Relationships."
        user = self.create_user()

        create_rt = RelationType.objects.smart_update_or_create
        loved = create_rt(
            ('test-subject_love', 'Is loving'),
            ('test-object_love', 'Is loved by'),
        )[1]
        hated = create_rt(
            ('test-subject_hate', 'Is hating'),
            ('test-object_hate', 'Is hated by'),
        )[1]

        cells = [
            EntityCellRegularField.build(model=FakeContact, name='last_name'),
            EntityCellRelation(model=FakeContact, rtype=loved),
            EntityCellRelation(model=FakeContact, rtype=hated),
        ]

        create_contact = partial(FakeContact.objects.create, user=user)
        nagate  = create_contact(first_name='Nagate',  last_name='Tanikaze')
        shizuka = create_contact(first_name='Shizuka', last_name='Hoshijiro')
        izana   = create_contact(first_name='Izana',   last_name='Shinatose')
        norio   = create_contact(first_name='Norio',   last_name='Kunato')

        create_rel = partial(Relation.objects.create, user=user)
        create_rel(subject_entity=nagate,  type=loved, object_entity=izana)
        create_rel(subject_entity=nagate,  type=hated, object_entity=norio)
        create_rel(subject_entity=shizuka, type=loved, object_entity=norio)

        # NB: sometimes a query to get this CT is performed when the Relations
        # are retrieved. So we force the cache to be filled has he should be
        ContentType.objects.get_for_model(CremeEntity)

        with self.assertNumQueries(2):
            EntityCell.mixed_populate_entities(cells, [nagate, shizuka], user)

        with self.assertNumQueries(0):
            r1 = nagate.get_relations(loved.id,  real_obj_entities=True)
            r2 = nagate.get_relations(hated.id,  real_obj_entities=True)
            r3 = shizuka.get_relations(loved.id, real_obj_entities=True)
            r4 = shizuka.get_relations(hated.id, real_obj_entities=True)

        with self.assertNumQueries(0):
            objs1 = [r.object_entity.get_real_entity() for r in r1]
            objs2 = [r.object_entity.get_real_entity() for r in r2]
            objs3 = [r.object_entity.get_real_entity() for r in r3]
            objs4 = [r.object_entity.get_real_entity() for r in r4]

        self.assertListEqual([izana], objs1)
        self.assertListEqual([norio], objs2)
        self.assertListEqual([norio], objs3)
        self.assertListEqual([],      objs4)

    def test_mixed_populate_entities04(self):
        "Mixed types."
        user = self.create_user()

        pos = FakePosition.objects.all()[0]
        create_contact = partial(FakeContact.objects.create, user=user)
        contacts = [
            create_contact(first_name='Nagate',  last_name='Tanikaze', position=pos),
            create_contact(first_name='Shizuka', last_name='Hoshijiro'),
            create_contact(first_name='Izana',   last_name='Shinatose'),
        ]

        loved = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love', 'Is loved by'),
        )[1]
        Relation.objects.create(
            user=user, subject_entity=contacts[0], type=loved, object_entity=contacts[2],
        )

        build_rfield = partial(EntityCellRegularField.build, model=FakeContact)
        cells = [
            build_rfield(name='last_name'),
            build_rfield(name='position'),
            EntityCellRelation(model=FakeContact, rtype=loved),
        ]

        # NB: sometimes a query to get this CT is performed when the Relations
        # are retrieved. So we force the cache to be filled has he should be
        ContentType.objects.get_for_model(CremeEntity)

        # Drop caches
        contacts = [self.refresh(c) for c in contacts]

        with self.assertNumQueries(3):
            EntityCell.mixed_populate_entities(cells, contacts, user)

        with self.assertNumQueries(0):
            contacts[0].position  # NOQA

        with self.assertNumQueries(0):
            contacts[0].get_relations(loved.id,  real_obj_entities=True)
