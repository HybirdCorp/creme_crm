# -*- coding: utf-8 -*-

try:
    from copy import deepcopy
    from datetime import date
    from decimal import Decimal
    from functools import partial

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.utils.formats import date_format, number_format
    from django.utils.timezone import localtime
    from django.utils.translation import gettext as _

    from ..base import CremeTestCase

    from creme.creme_core.core.entity_cell import (
        EntityCell,
        CELLS_MAP, EntityCellsRegistry,
        EntityCellRegularField,
        EntityCellCustomField,
        EntityCellFunctionField,
        EntityCellRelation,
    )
    from creme.creme_core.core.function_field import (
        FunctionField,
        FunctionFieldResult,
        function_field_registry,
    )
    from creme.creme_core.models import (
        RelationType,
        FieldsConfig,
        CustomField, CustomFieldEnumValue,
        FakeContact, FakeDocument, FakeFolder,
    )
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class EntityCellTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.contact_ct = ContentType.objects.get_for_model(FakeContact)

    def test_registry01(self):
        "Global singleton."
        self.assertEqual(EntityCellRegularField,  CELLS_MAP[EntityCellRegularField.type_id])
        self.assertEqual(EntityCellCustomField,   CELLS_MAP[EntityCellCustomField.type_id])
        self.assertEqual(EntityCellFunctionField, CELLS_MAP[EntityCellFunctionField.type_id])
        self.assertEqual(EntityCellRelation,      CELLS_MAP[EntityCellRelation.type_id])

    def test_registry02(self):
        "Register."
        registry = EntityCellsRegistry()

        with self.assertRaises(KeyError):
            __ = registry[EntityCellRegularField.type_id]

        registry(EntityCellRegularField)
        self.assertEqual(EntityCellRegularField, registry[EntityCellRegularField.type_id])

    def test_registry03(self):
        "Deepcopy."
        registry1 = EntityCellsRegistry()
        registry1(EntityCellRegularField)
        registry1(EntityCellCustomField)

        registry2 = deepcopy(registry1)
        registry2(EntityCellFunctionField)

        with self.assertNoException():
            __ = registry1[EntityCellRegularField.type_id]
            __ = registry2[EntityCellRegularField.type_id]

            __ = registry1[EntityCellCustomField.type_id]
            __ = registry2[EntityCellCustomField.type_id]

            __ = registry2[EntityCellFunctionField.type_id]

        with self.assertRaises(KeyError):
            __ = registry1[EntityCellFunctionField.type_id]

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
        # self.assertIs(cell.has_a_filter, True)
        # self.assertIs(cell.editable, True)
        # self.assertIs(cell.sortable, True)
        self.assertIs(cell.is_excluded, False)
        self.assertIs(cell.is_multiline, False)
        # self.assertEqual('first_name__icontains', cell.filter_string)

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

        loves = RelationType.create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by')
        )[0]
        cell = EntityCellRelation(model=FakeContact, rtype=loves)
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(FakeContact,     cell.model)
        self.assertEqual(str(loves.id),   cell.value)
        self.assertEqual(loves.predicate, cell.title)
        self.assertEqual(f'relation-{loves.id}', cell.key)
        self.assertIs(cell.is_multiline, True)
        self.assertEqual(loves, cell.relation_type)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

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