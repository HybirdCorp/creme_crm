# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from .base import FieldTestCase
    from creme.creme_core.forms.header_filter import EntityCellsField
    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.models import RelationType, CustomField

    from creme.persons.models import Contact
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('EntityCellsFieldTestCase',)


class EntityCellsFieldTestCase(FieldTestCase):
    @classmethod
    def setUpClass(cls):
        cls.ct_contact = ContentType.objects.get_for_model(Contact)

    def test_clean_empty_required(self):
        clean = EntityCellsField(required=True, content_type=self.ct_contact).clean
        self.assertFieldValidationError(EntityCellsField, 'required', clean, None)
        self.assertFieldValidationError(EntityCellsField, 'required', clean, '')

    def test_clean_empty_not_required(self):
        field = EntityCellsField(required=False, content_type=self.ct_contact)

        with self.assertNoException():
            value = field.clean(None)

        self.assertEqual([], value)

    def test_clean_invalid_choice(self):
        field = EntityCellsField(content_type=self.ct_contact)
        self.assertFieldValidationError(EntityCellsField, 'invalid', field.clean,
                                        'regular_field-first_name,regular_field-unknown'
                                       )

    def test_ok01(self):
        "One regular field"
        field = EntityCellsField(content_type=self.ct_contact)
        cells = field.clean('regular_field-first_name')
        self.assertEqual(1, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual('first_name',            cell.value)
        self.assertEqual('first_name__icontains', cell.filter_string)
        self.assertIs(cell.is_hidden, False)

    def assertCellOK(self, cell, expected_cls, expected_value):
        self.assertIsInstance(cell, expected_cls)
        self.assertEqual(expected_value, cell.value)

    def test_ok02(self):
        "All types of columns"
        loves = RelationType.create(('test-subject_love', u'Is loving'),
                                    ('test-object_love',  u'Is loved by')
                                   )[0]
        customfield = CustomField.objects.create(name=u'Size (cm)',
                                                 field_type=CustomField.INT,
                                                 content_type=self.ct_contact,
                                                )
        funcfield = Contact.function_fields.get('get_pretty_properties')

        field = EntityCellsField(content_type=self.ct_contact)
        cells = field.clean('relation-%s,regular_field-last_name,function_field-%s,custom_field-%s,regular_field-first_name' % (
                                    loves.id, funcfield.name, customfield.id,
                                )
                           )

        self.assertEqual(5, len(cells))
        self.assertCellOK(cells[0], EntityCellRelation,     loves.id)
        self.assertCellOK(cells[1], EntityCellRegularField, 'last_name')
        self.assertCellOK(cells[2], EntityCellFunctionField, funcfield.name)
        self.assertCellOK(cells[3], EntityCellCustomField,   str(customfield.id))
        self.assertCellOK(cells[4], EntityCellRegularField, 'first_name')
