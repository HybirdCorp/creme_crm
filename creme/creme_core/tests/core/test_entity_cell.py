# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext as _

    from ..base import CremeTestCase

    from creme.creme_core.core.entity_cell import (CELLS_MAP, EntityCellsRegistry,
            EntityCellRegularField, EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.core.function_field import (FunctionField,
            FunctionFieldResult, function_field_registry)
    from creme.creme_core.models import (RelationType,
            CustomField, CustomFieldEnumValue, FakeContact, FakeDocument)
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


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

    def test_build_4_field01(self):
        field_name = 'first_name'
        cell = EntityCellRegularField.build(model=FakeContact, name=field_name)
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_name,      cell.value)
        self.assertEqual(_('First name'), cell.title)
        self.assertEqual('regular_field-first_name', cell.key)
        # self.assertIs(cell.has_a_filter, True)
        # self.assertIs(cell.editable, True)
        # self.assertIs(cell.sortable, True)
        self.assertIs(cell.is_multiline, False)
        # self.assertEqual('first_name__icontains', cell.filter_string)

    def test_build_4_field02(self):
        "Date field."
        cell = EntityCellRegularField.build(model=FakeContact, name='birthday')
        # self.assertEqual('birthday__range', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_field03(self):
        "Boolean field."
        cell = EntityCellRegularField.build(model=FakeContact, name='is_a_nerd')
        # self.assertEqual('is_a_nerd__creme-boolean', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

    def test_build_4_field04(self):
        "ForeignKey."
        cell = EntityCellRegularField.build(model=FakeContact, name='position')
        self.assertEqual('regular_field-position', cell.key)
        # self.assertEqual('position', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

        cell = EntityCellRegularField.build(model=FakeContact, name='image')
        # self.assertEqual('image__header_filter_search_field__icontains',
        #                  cell.filter_string
        #                 )
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW, cell.listview_css_class)

    def test_build_4_field05(self):
        "Basic ForeignKey subfield."
        cell = EntityCellRegularField.build(model=FakeContact, name='position__title')
        self.assertEqual('regular_field-position__title', cell.key)
        # self.assertEqual('position__title__icontains', cell.filter_string)

        cell = EntityCellRegularField.build(model=FakeContact, name='image__name')
        self.assertEqual('regular_field-image__name', cell.key)
        # self.assertEqual('image__name__icontains', cell.filter_string)

    def test_build_4_field06(self):
        "Date ForeignKey subfield."
        cell = EntityCellRegularField.build(model=FakeContact, name='image__created')
        self.assertEqual('{} - {}'.format(_('Photograph'), _('Creation date')), cell.title)
        # self.assertEqual('image__created__range', cell.filter_string)

    def test_build_4_field07(self):
        "ForeignKey subfield is a FK."
        cell = EntityCellRegularField.build(model=FakeDocument, name='linked_folder__category')
        self.assertEqual('regular_field-linked_folder__category', cell.key)
        # self.assertTrue(cell.has_a_filter)
        # self.assertEqual('linked_folder__category', cell.filter_string)

    def test_build_4_field08(self):
        "ManyToMany."
        cell = EntityCellRegularField.build(model=FakeContact, name='languages')
        # self.assertTrue(cell.has_a_filter)
        # self.assertFalse(cell.sortable)
        self.assertTrue(cell.is_multiline)
        # self.assertEqual('languages', cell.filter_string)

        cell = EntityCellRegularField.build(model=FakeContact, name='languages__name')
        # self.assertTrue(cell.has_a_filter)
        # self.assertFalse(cell.sortable)
        self.assertTrue(cell.is_multiline)
        # self.assertEqual('languages__name__icontains', cell.filter_string)

    def test_build_4_field_errors(self):
        build = partial(EntityCellRegularField.build, model=FakeContact)
        self.assertIsNone(build(name='unknown_field'))
        self.assertIsNone(build(name='user__unknownfield'))

    def test_build_4_customfield01(self):
        "INT CustomField"
        name = 'Size (cm)'
        customfield = CustomField.objects.create(name=name, field_type=CustomField.INT,
                                                 content_type=self.contact_ct,
                                                )

        cell = EntityCellCustomField(customfield)
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(str(customfield.id), cell.value)
        self.assertEqual(name,                cell.title)
        self.assertEqual('custom_field-{}'.format(customfield.id), cell.key)
        # self.assertIs(cell.has_a_filter, True)
        # self.assertIs(cell.editable,     False)
        # self.assertIs(cell.sortable,     False)
        self.assertIs(cell.is_multiline, False)
        # self.assertEqual('customfieldinteger__value__icontains', cell.filter_string)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,           cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW,   cell.header_listview_css_class)

        cell = EntityCellCustomField.build(FakeContact, customfield.id)
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(str(customfield.id), cell.value)

        self.assertIsNone(EntityCellCustomField.build(FakeContact, 1000))

    def test_build_4_customfield02(self):
        "FLOAT CustomField."
        customfield = CustomField.objects.create(name='Weight', field_type=CustomField.FLOAT,
                                                 content_type=self.contact_ct,
                                                )

        cell = EntityCellCustomField(customfield)
        # self.assertEqual('customfieldfloat__value__icontains', cell.filter_string)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,         cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_customfield03(self):
        "DATE CustomField."
        customfield = CustomField.objects.create(name='Day', field_type=CustomField.DATETIME,
                                                 content_type=self.contact_ct,
                                                )

        cell = EntityCellCustomField(customfield)
        # self.assertEqual('customfielddatetime__value__range', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,     cell.listview_css_class)
        self.assertEqual(settings.CSS_DATE_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_customfield04(self):
        "BOOL CustomField."
        customfield = CustomField.objects.create(name='Is fun ?', field_type=CustomField.BOOL,
                                                 content_type=self.contact_ct,
                                                )

        cell = EntityCellCustomField(customfield)
        # self.assertEqual('customfieldboolean__value__creme-boolean', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_customfield05(self):
        "ENUM CustomField."
        customfield = CustomField.objects.create(name='Eva', field_type=CustomField.ENUM,
                                                 content_type=self.contact_ct,
                                                )

        create_enumvalue = partial(CustomFieldEnumValue.objects.create, custom_field=customfield)
        create_enumvalue(value='Eva-00')
        create_enumvalue(value='Eva-01')

        cell = EntityCellCustomField(customfield)
        # self.assertEqual('customfieldenum__value__exact',      cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_customfield06(self):
        "MULTI_ENUM CustomField."
        customfield = CustomField.objects.create(name='Eva', field_type=CustomField.MULTI_ENUM,
                                                 content_type=self.contact_ct,
                                                )

        create_enumvalue = partial(CustomFieldEnumValue.objects.create, custom_field=customfield)
        create_enumvalue(value='Eva-00')
        create_enumvalue(value='Eva-01')

        cell = EntityCellCustomField(customfield)
        # self.assertEqual('customfieldmultienum__value__exact', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_relation(self):
        loves = RelationType.create(('test-subject_love', 'Is loving'),
                                    ('test-object_love',  'Is loved by')
                                   )[0]
        cell = EntityCellRelation(model=FakeContact, rtype=loves)
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(FakeContact,     cell.model)
        self.assertEqual(str(loves.id),   cell.value)
        self.assertEqual(loves.predicate, cell.title)
        self.assertEqual('relation-{}'.format(loves.id), cell.key)
        # self.assertIs(cell.has_a_filter, True)
        # self.assertIs(cell.editable,     False)
        # self.assertIs(cell.sortable,     False)
        self.assertIs(cell.is_multiline, True)
        # self.assertEqual('',    cell.filter_string)
        self.assertEqual(loves, cell.relation_type)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_build_4_functionfield01(self):
        name = 'get_pretty_properties'
        funfield = function_field_registry.get(FakeContact, name)
        self.assertIsNotNone(funfield)

        cell = EntityCellFunctionField(model=FakeContact, func_field=funfield)
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(name,            cell.value)
        self.assertEqual(str(funfield.verbose_name), cell.title)
        self.assertEqual('function_field-{}'.format(funfield.name), cell.key)
        # self.assertIs(cell.has_a_filter, True)
        # self.assertIs(cell.editable,     False)
        # self.assertIs(cell.sortable,     False)
        self.assertIs(cell.is_hidden,    False)
        self.assertIs(cell.is_multiline, True)
        # self.assertEqual('', cell.filter_string)
        self.assertEqual(settings.CSS_DEFAULT_LISTVIEW,        cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

        cell = EntityCellFunctionField.build(FakeContact, func_field_name=name)
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(name, cell.value)

        self.assertIsNone(EntityCellFunctionField.build(FakeContact, func_field_name='invalid'))

    def test_build_4_functionfield02(self):
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
