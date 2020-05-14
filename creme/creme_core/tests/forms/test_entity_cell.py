# -*- coding: utf-8 -*-

try:
    from copy import deepcopy
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import gettext as _

    from .base import FieldTestCase
    from creme.creme_core.core.entity_cell import (
        EntityCellRegularField,
        EntityCellCustomField,
        EntityCellFunctionField,
        EntityCellRelation,
    )
    from creme.creme_core.core.function_field import function_field_registry
    from creme.creme_core.forms.header_filter import EntityCellsField
    from creme.creme_core.models import (
        CremeEntity,
        RelationType,
        CustomField,
        FieldsConfig,
        FakeContact, FakeOrganisation, FakeAddress,
    )

    from .. import fake_constants
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class EntityCellsFieldTestCase(FieldTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ct_contact = ContentType.objects.get_for_model(FakeContact)

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
        self.assertFieldValidationError(
            EntityCellsField, 'invalid', field.clean,
            'regular_field-first_name,regular_field-unknown',
        )

    def test_choices_regularfields01(self):
        field = EntityCellsField()
        self.assertListEqual([], field.non_hiddable_cells)
        self.assertFalse(field.widget.model_fields)

    def test_choices_regularfields02(self):
        field = EntityCellsField(content_type=self.ct_contact)
        self.assertListEqual([], field.non_hiddable_cells)

        choices = field.widget.model_fields
        self.assertInChoices(
            value='regular_field-last_name',
            label=_('Last name'),
            choices=choices,
        )
        self.assertInChoices(
            value='regular_field-first_name',
            label=_('First name'),
            choices=choices,
        )
        self.assertInChoices(
            value='regular_field-sector',
            label=_('Line of business'),
            choices=choices,
        )
        self.assertInChoices(
            value='regular_field-civility',
            label=_('Civility'),
            choices=choices,
        )
        self.assertInChoices(
            value='regular_field-address',
            label=_('Billing address'),
            choices=choices,
        )

        sub_choices = field.widget.model_subfields
        self.assertInChoices(
            value='regular_field-sector__title',
            label=_('Title'),
            choices=sub_choices['regular_field-sector'],
        )
        self.assertInChoices(
            value='regular_field-civility__shortcut',
            label=_('Shortcut'),
            choices=sub_choices['regular_field-civility'],
        )

        addr_choices = sub_choices['regular_field-address']
        self.assertInChoices(
            value='regular_field-address__city',
            label=_('City'),
            choices=addr_choices,
        )
        self.assertInChoices(
            value='regular_field-address__country',
            label=_('Country'),
            choices=addr_choices,
        )

    def test_choices_regularfields03(self):
        "Property <content_type>."
        field = EntityCellsField()
        self.assertIsNone(field.content_type)
        self.assertIs(field.widget.model, CremeEntity)

        ct = self.ct_contact
        field.content_type = ct
        self.assertEqual(ct, field.content_type)

        widget = field.widget
        self.assertIs(widget.model, FakeContact)
        self.assertInChoices(
            value='regular_field-last_name',
            label=_('Last name'),
            choices=widget.model_fields,
        )

    def test_choices_regularfields04(self):
        "Hidden fields."
        hidden_fname1 = 'first_name'
        hidden_fname2 = 'city'
        FieldsConfig.objects.create(
            content_type=self.ct_contact,
            descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True})],
        )
        FieldsConfig.objects.create(
            content_type=FakeAddress,
            descriptions=[(hidden_fname2, {FieldsConfig.HIDDEN: True})],
        )

        field = EntityCellsField(content_type=self.ct_contact)
        choices = field.widget.model_fields
        self.assertInChoices(
            value='regular_field-last_name',
            label=_('Last name'),
            choices=choices,
        )
        self.assertNotInChoices(
            value=f'regular_field-{hidden_fname1}',
            choices=choices,
        )

        addr_choices = field.widget.model_subfields['regular_field-address']
        self.assertInChoices(
            value='regular_field-address__country',
            label=_('Country'),
            choices=addr_choices,
        )
        self.assertNotInChoices(
            value=f'regular_field-address__{hidden_fname2}',
            choices=addr_choices,
        )

    def test_choices_regularfields05(self):
        "Hidden fields + selected cells."
        hidden_fname1 = 'first_name'
        hidden_fname2 = 'city'
        FieldsConfig.objects.create(
            content_type=self.ct_contact,
            descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True})],
        )
        FieldsConfig.objects.create(
            content_type=FakeAddress,
            descriptions=[(hidden_fname2, {FieldsConfig.HIDDEN: True})],
        )

        field = EntityCellsField()
        cells = [
            EntityCellRegularField.build(FakeContact, hidden_fname1),
            EntityCellRegularField.build(FakeContact, f'address__{hidden_fname2}'),
        ]
        field.non_hiddable_cells = cells
        field.content_type = self.ct_contact
        self.assertListEqual(cells, field.non_hiddable_cells)

        choices = field.widget.model_fields
        self.assertInChoices(
            value='regular_field-last_name',
            label=_('Last name'),
            choices=choices,
        )
        self.assertInChoices(
            value=f'regular_field-{hidden_fname1}',
            label=_('First name'),
            choices=choices,
        )

        addr_choices = field.widget.model_subfields['regular_field-address']
        self.assertInChoices(
            value='regular_field-address__country',
            label=_('Country'),
            choices=addr_choices,
        )
        self.assertInChoices(
            value=f'regular_field-address__{hidden_fname2}',
            label=_('City'),
            choices=addr_choices,
        )

    def test_choices_regularfields06(self):
        """Hidden fields + selected cells.
        (<non_hiddable_cells> called after setting content type).
        """
        hidden_fname1 = 'first_name'
        hidden_fname2 = 'city'
        FieldsConfig.objects.create(
            content_type=self.ct_contact,
            descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True})],
        )
        FieldsConfig.objects.create(
            content_type=FakeAddress,
            descriptions=[(hidden_fname2, {FieldsConfig.HIDDEN: True})],
        )

        field = EntityCellsField(content_type=self.ct_contact)
        cells = [
            EntityCellRegularField.build(FakeContact, hidden_fname1),
            EntityCellRegularField.build(FakeContact, f'address__{hidden_fname2}'),
        ]
        field.non_hiddable_cells = cells
        self.assertListEqual(cells, field.non_hiddable_cells)

        choices = field.widget.model_fields
        self.assertInChoices(
            value='regular_field-last_name',
            label=_('Last name'),
            choices=choices,
        )
        self.assertInChoices(
            value=f'regular_field-{hidden_fname1}',
            label=_('First name'),
            choices=choices,
        )

        addr_choices = field.widget.model_subfields['regular_field-address']
        self.assertInChoices(
            value='regular_field-address__country',
            label=_('Country'),
            choices=addr_choices,
        )
        self.assertInChoices(
            value=f'regular_field-address__{hidden_fname2}',
            label=_('City'),
            choices=addr_choices,
        )

    def test_choices_customfields01(self):
        create_cf = partial(
            CustomField.objects.create,
            content_type=self.ct_contact,
        )
        cf1 = create_cf(field_type=CustomField.BOOL, name='Pilots?')
        cf2 = create_cf(field_type=CustomField.STR,  name='Dog tag')
        cf3 = create_cf(
            field_type=CustomField.BOOL, name='Operational?',
            content_type=FakeOrganisation,
        )

        field1 = EntityCellsField(content_type=self.ct_contact)
        custom_fields = {cf1, cf2}
        self.assertSetEqual(custom_fields, {*field1._custom_fields})

        choices = field1.widget.custom_fields
        self.assertInChoices(
            value=f'custom_field-{cf1.id}',
            label=cf1.name,
            choices=choices,
        )
        self.assertInChoices(
            value=f'custom_field-{cf2.id}',
            label=cf2.name,
            choices=choices,
        )
        self.assertNotInChoices(
            value=f'custom_field-{cf3.id}',
            choices=choices,
        )

        # ---
        field2 = EntityCellsField()
        field2.content_type = self.ct_contact
        self.assertSetEqual(custom_fields, {*field2._custom_fields})

    def test_choices_customfields02(self):
        "Deleted fields."
        create_cf = partial(
            CustomField.objects.create,
            content_type=self.ct_contact,
            field_type=CustomField.STR,
        )
        cf1 = create_cf(name='Dog tag')
        cf2 = create_cf(name='Old dog tag', is_deleted=True)

        field = EntityCellsField(content_type=self.ct_contact)
        self.assertListEqual([cf1], [*field._custom_fields])

        choices = field.widget.custom_fields
        self.assertInChoices(
            value=f'custom_field-{cf1.id}',
            label=cf1.name,
            choices=choices,
        )
        self.assertNotInChoices(
            value=f'custom_field-{cf2.id}',
            choices=choices,
        )

    def test_choices_customfields03(self):
        "Deleted fields  + selected cells."
        create_cf = partial(
            CustomField.objects.create,
            content_type=self.ct_contact,
            field_type=CustomField.STR,
        )
        cf1 = create_cf(name='Dog tag')
        cf2 = create_cf(name='Old dog tag', is_deleted=True)

        field = EntityCellsField(content_type=self.ct_contact)
        field.non_hiddable_cells = [EntityCellCustomField(cf2)]
        self.assertSetEqual({cf1, cf2}, {*field._custom_fields})

    def test_choices_functionfields(self):
        field = EntityCellsField(content_type=self.ct_contact)
        self.assertInChoices(
            value='function_field-get_pretty_properties',
            label=_('Properties'),
            choices=field.widget.function_fields,
        )

    def test_choices_relations(self):
        rtype1 = self.get_object_or_fail(
            RelationType,
            id=fake_constants.FAKE_REL_SUB_EMPLOYED_BY,
        )
        rtype2 = self.get_object_or_fail(
            RelationType,
            id=fake_constants.FAKE_REL_OBJ_EMPLOYED_BY,
        )
        rtype3 = self.get_object_or_fail(
            RelationType,
            id=fake_constants.FAKE_REL_SUB_BILL_ISSUED,
        )

        field1 = EntityCellsField(content_type=self.ct_contact)
        rtypes1 = {*field1._relation_types}
        self.assertIn(rtype1, rtypes1)
        self.assertNotIn(rtype2, rtypes1)
        self.assertNotIn(rtype3, rtypes1)

        self.assertInChoices(
            value=f'relation-{rtype1.id}',
            label=rtype1.predicate,
            choices=field1.widget.relation_types,
        )

        # ---
        field2 = EntityCellsField()
        field2.content_type = self.ct_contact
        rtypes2 = {*field2._relation_types}
        self.assertIn(rtype1, rtypes2)
        self.assertNotIn(rtype2, rtypes2)

    def test_ok01(self):
        "One regular field."
        field = EntityCellsField(content_type=self.ct_contact)
        cells = field.clean('regular_field-first_name')
        self.assertEqual(1, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(FakeContact,  cell.model)
        self.assertEqual('first_name', cell.value)
        self.assertIs(cell.is_hidden, False)

    def assertCellOK(self, cell, expected_cls, expected_value):
        self.assertIsInstance(cell, expected_cls)
        self.assertEqual(expected_value, cell.value)

    def test_ok02(self):
        "All types of columns."
        loves = RelationType.create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by')
        )[0]
        customfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=self.ct_contact,
        )
        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')

        field = EntityCellsField(content_type=self.ct_contact)
        cells = field.clean(
            f'relation-{loves.id},'
            f'regular_field-last_name,'
            f'function_field-{funcfield.name},'
            f'custom_field-{customfield.id},'
            f'regular_field-first_name'
        )

        self.assertEqual(5, len(cells))
        self.assertCellOK(cells[0], EntityCellRelation,     loves.id)
        self.assertCellOK(cells[1], EntityCellRegularField, 'last_name')
        self.assertCellOK(cells[2], EntityCellFunctionField, funcfield.name)
        self.assertCellOK(cells[3], EntityCellCustomField,   str(customfield.id))
        self.assertCellOK(cells[4], EntityCellRegularField, 'first_name')

    def test_copy(self):
        field1 = EntityCellsField(content_type=self.ct_contact)
        field2 = deepcopy(field1)

        field1.non_hiddable_cells = [
            EntityCellRegularField.build(FakeContact, 'first_name'),
        ]
        self.assertListEqual([], field2.non_hiddable_cells)
