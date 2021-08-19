# -*- coding: utf-8 -*-

from copy import deepcopy
from functools import partial

# from django.contrib.contenttypes.models import ContentType
from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
    EntityCellsRegistry,
)
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.forms.header_filter import (
    EntityCellCustomFieldsField,
    EntityCellCustomFieldsWidget,
    EntityCellFunctionFieldsWidget,
    EntityCellRegularFieldsField,
    EntityCellRelationsField,
    EntityCellsField,
    UniformEntityCellsField,
)
from creme.creme_core.models import (
    CremeEntity,
    CustomField,
    FakeAddress,
    FakeContact,
    FakeImage,
    FakeOrganisation,
    FieldsConfig,
    RelationType,
)

from .. import fake_constants
from .base import FieldTestCase


class EntityCellsFieldTestCaseMixin:
    def _find_sub_widget(self, field, cell_class_type_id):
        available = []

        for sub_widget in field.widget.sub_widgets:
            current_type_id = sub_widget.type_id

            if current_type_id == cell_class_type_id:
                return sub_widget

            available.append(current_type_id)

        self.fail(f'Sub-widget "{cell_class_type_id}" not found in {available}.')

    def assertCellInChoices(self, cell_key, choices):
        for choice_cell_key, choice_cell in choices:
            if cell_key == choice_cell_key:
                if choice_cell.key != cell_key:
                    self.fail(
                        'The cell has been found, but choice Id does not match the cell key.'
                    )

                return

        self.fail(
            f'The choice for cell-key="{cell_key}" has not been found in '
            f'{[choice_cell_key for choice_cell_key, choice_cell in choices]}'
        )

    def assertCellNotInChoices(self, cell_key, choices):
        for choice_cell_key, choice_cell in choices:
            if cell_key == choice_cell_key:
                self.fail(
                    f'The choice for cell-key="{cell_key}" has been unexpectedly found.'
                )


class EntityCellsFieldTestCase(EntityCellsFieldTestCaseMixin, FieldTestCase):
    def test_clean_empty_required(self):
        clean = EntityCellsField(required=True, model=FakeContact).clean
        self.assertFieldValidationError(EntityCellsField, 'required', clean, None)
        self.assertFieldValidationError(EntityCellsField, 'required', clean, '')

    def test_clean_empty_not_required(self):
        field = EntityCellsField(required=False, model=FakeContact)

        with self.assertNoException():
            value = field.clean(None)

        self.assertListEqual([], value)

    def test_regularfields01(self):
        field = EntityCellsField()
        self.assertListEqual([], field.non_hiddable_cells)

        choices = self._find_sub_widget(field, 'regular_field').choices
        fname1 = 'created'
        value = f'regular_field-{fname1}'
        self.assertCellInChoices(value, choices=choices)
        self.assertCellNotInChoices('regular_field-entity_type', choices=choices)
        self.assertCellInChoices('regular_field-user',           choices=choices)
        self.assertCellInChoices('regular_field-user__username', choices=choices)
        self.assertCellNotInChoices('regular_field-user__role',  choices=choices)

        self.assertListEqual(
            [EntityCellRegularField.build(CremeEntity, fname1)],
            field.clean(value),
        )

        fname2 = 'unknown'
        self.assertFieldValidationError(
            UniformEntityCellsField, 'invalid_value', field.clean,
            f'regular_field-{fname2}',
            message_args={'value': fname2},
        )

        self.assertFieldValidationError(
            EntityCellRegularFieldsField, 'invalid_value', field.clean,
            'regular_field-entity_type',
            message_args={'value': 'entity_type'},
        )

    def test_regularfields02(self):
        field = EntityCellsField(model=FakeContact)
        self.assertListEqual([], field.non_hiddable_cells)

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices('regular_field-created', choices=choices)
        self.assertCellInChoices('regular_field-last_name', choices=choices)
        self.assertCellInChoices('regular_field-first_name', choices=choices)
        self.assertCellInChoices('regular_field-sector', choices=choices)
        self.assertCellInChoices('regular_field-civility', choices=choices)
        self.assertCellInChoices('regular_field-address', choices=choices)

        self.assertCellInChoices('regular_field-sector__title', choices=choices)
        self.assertCellNotInChoices('regular_field-sector__is_custom', choices=choices)
        self.assertCellInChoices('regular_field-civility__shortcut', choices=choices)

        self.assertCellInChoices('regular_field-address__city', choices=choices)
        self.assertCellInChoices('regular_field-address__country', choices=choices)

        self.assertCellInChoices('regular_field-image',             choices=choices)
        self.assertCellInChoices('regular_field-image__name',       choices=choices)
        self.assertCellInChoices('regular_field-image__user',       choices=choices)
        self.assertCellInChoices('regular_field-image__categories', choices=choices)
        self.assertCellNotInChoices('regular_field-image__user__username',   choices=choices)
        self.assertCellNotInChoices('regular_field-image__categories__name', choices=choices)

        # ----
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, 'first_name'),
                EntityCellRegularField.build(FakeContact, 'sector__title'),
                EntityCellRegularField.build(FakeContact, 'address__city'),
                EntityCellRegularField.build(FakeContact, 'image__user'),
                EntityCellRegularField.build(FakeContact, 'image__categories'),
            ],
            field.clean(
                'regular_field-first_name,'
                'regular_field-sector__title,'
                'regular_field-address__city,'
                'regular_field-image__user,'
                'regular_field-image__categories'
            )
        )

        self.assertFieldValidationError(
            EntityCellRegularFieldsField, 'invalid_value', field.clean,
            'regular_field-sector__is_custom',
            message_args={'value': 'sector__is_custom'},
        )
        self.assertFieldValidationError(
            EntityCellRegularFieldsField, 'invalid_value', field.clean,
            'regular_field-image__user__username',
            message_args={'value': 'image__user__username'},
        )
        self.assertFieldValidationError(
            EntityCellRegularFieldsField, 'invalid_value', field.clean,
            'regular_field-image__categories__name',
            message_args={'value': 'image__categories__name'},
        )

    def test_regularfields03(self):
        "Property <model>."
        field = EntityCellsField()
        self.assertIs(field.model,        CremeEntity)
        self.assertIs(field.widget.model, CremeEntity)

        field.model = FakeContact
        self.assertEqual(FakeContact, field.model)

        widget = field.widget
        self.assertIs(widget.model, FakeContact)

        fname = 'last_name'
        value = f'regular_field-{fname}'
        self.assertCellInChoices(
            value,
            choices=self._find_sub_widget(field, 'regular_field').choices,
        )
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, fname)],
            field.clean(value)
        )

    def test_regularfields04(self):
        "Hidden fields."
        hidden_fname1 = 'first_name'
        hidden_fname2 = 'description'  # NB: in CremeEntity
        hidden_addr_fname = 'city'
        hidden_img_fname1 = 'exif_date'
        hidden_img_fname2 = 'description'  # NB: in CremeEntity

        create_fconf = FieldsConfig.objects.create
        create_fconf(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )
        create_fconf(
            content_type=FakeAddress,
            descriptions=[(hidden_addr_fname, {FieldsConfig.HIDDEN: True})],
        )
        create_fconf(
            content_type=FakeImage,
            descriptions=[
                (hidden_img_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_img_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        field = EntityCellsField(model=FakeContact)
        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices('regular_field-last_name', choices=choices)
        self.assertCellNotInChoices(f'regular_field-{hidden_fname1}', choices=choices)
        self.assertCellNotInChoices(f'regular_field-{hidden_fname2}', choices=choices)

        self.assertCellInChoices('regular_field-address__country', choices=choices)
        self.assertCellNotInChoices(
            f'regular_field-address__{hidden_addr_fname}',
            choices=choices,
        )

        self.assertCellInChoices('regular_field-image__categories', choices=choices)
        self.assertCellNotInChoices(
            f'regular_field-image__{hidden_img_fname1}',
            choices=choices,
        )
        self.assertCellNotInChoices(
            f'regular_field-image__{hidden_img_fname2}',
            choices=choices,
        )

        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, 'last_name')],
            field.clean('regular_field-last_name')
        )
        self.assertFieldValidationError(
            UniformEntityCellsField, 'invalid_value', field.clean,
            f'regular_field-{hidden_fname1}',
            message_args={'value': hidden_fname1},
        )
        self.assertFieldValidationError(
            UniformEntityCellsField, 'invalid_value', field.clean,
            f'regular_field-address__{hidden_addr_fname}',
            message_args={'value': f'address__{hidden_addr_fname}'},
        )

    def test_regularfields05(self):
        "Hidden fields + selected cells."
        hidden_fname1 = 'first_name'
        hidden_fname2 = 'description'  # Nb: in CremeEntity
        hidden_addr_fname = 'city'
        hidden_img_fname1 = 'exif_date'
        hidden_img_fname2 = 'description'  # NB: in CremeEntity

        create_fconf = FieldsConfig.objects.create
        create_fconf(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )
        create_fconf(
            content_type=FakeAddress,
            descriptions=[(hidden_addr_fname, {FieldsConfig.HIDDEN: True})],
        )
        create_fconf(
            content_type=FakeImage,
            descriptions=[
                (hidden_img_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_img_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        field = EntityCellsField()
        cells = [
            EntityCellRegularField.build(FakeContact, hidden_fname1),
            EntityCellRegularField.build(FakeContact, hidden_fname2),
            EntityCellRegularField.build(FakeContact, f'address__{hidden_addr_fname}'),
            EntityCellRegularField.build(FakeContact, f'image__{hidden_img_fname1}'),
            EntityCellRegularField.build(FakeContact, f'image__{hidden_img_fname2}'),
        ]
        field.non_hiddable_cells = cells
        field.model = FakeContact
        self.assertListEqual(cells, field.non_hiddable_cells)

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices('regular_field-last_name', choices=choices)
        self.assertCellInChoices(f'regular_field-{hidden_fname1}', choices=choices)
        self.assertCellInChoices(f'regular_field-{hidden_fname2}', choices=choices)

        self.assertCellInChoices('regular_field-address__country', choices=choices)
        self.assertCellInChoices(
            f'regular_field-address__{hidden_addr_fname}',
            choices=choices,
        )

        self.assertCellInChoices(
            f'regular_field-image__{hidden_img_fname1}',
            choices=choices,
        )
        self.assertCellInChoices(
            f'regular_field-image__{hidden_img_fname2}',
            choices=choices,
        )

        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, 'last_name'),
                EntityCellRegularField.build(FakeContact, hidden_fname1),
                EntityCellRegularField.build(FakeContact, f'address__{hidden_addr_fname}'),
            ],
            field.clean(
                'regular_field-last_name,'
                f'regular_field-{hidden_fname1},'
                f'regular_field-address__{hidden_addr_fname}'
            )
        )

    def test_regularfields06(self):
        """Hidden fields + selected cells.
        (<non_hiddable_cells> called after setting content type).
        """
        hidden_fname1 = 'first_name'
        hidden_fname2 = 'city'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True})],
        )
        FieldsConfig.objects.create(
            content_type=FakeAddress,
            descriptions=[(hidden_fname2, {FieldsConfig.HIDDEN: True})],
        )

        field = EntityCellsField(model=FakeContact)
        cells = [
            EntityCellRegularField.build(FakeContact, hidden_fname1),
            EntityCellRegularField.build(FakeContact, f'address__{hidden_fname2}'),
        ]
        field.non_hiddable_cells = cells
        self.assertListEqual(cells, field.non_hiddable_cells)

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices('regular_field-last_name', choices=choices)
        self.assertCellInChoices(f'regular_field-{hidden_fname1}', choices=choices)

        self.assertCellInChoices('regular_field-address__country', choices=choices)
        self.assertCellInChoices(f'regular_field-address__{hidden_fname2}', choices=choices)

    def test_regularfields_only_leaves(self):
        class OnlyLeavesRegularFields(EntityCellRegularFieldsField):
            only_leaves = True

        class OnlyLeavesEntityCellsField(EntityCellsField):
            field_classes = {OnlyLeavesRegularFields}

        field = OnlyLeavesEntityCellsField(model=FakeContact)

        fname1 = 'first_name'
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, fname1)],
            field.clean(f'regular_field-{fname1}'),
        )

        fname2 = 'sector__title'
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, fname2)],
            field.clean(f'regular_field-{fname2}'),
        )

        fname3 = 'sector'
        self.assertFieldValidationError(
            EntityCellRegularFieldsField, 'not_leaf', field.clean,
            f'regular_field-{fname3}',
            message_args={'value': fname3},
        )

    def test_customfields01(self):
        create_cf = partial(
            CustomField.objects.create, content_type=FakeContact,
        )
        cf1 = create_cf(field_type=CustomField.BOOL, name='Pilots?')
        cf2 = create_cf(field_type=CustomField.STR,  name='Dog tag')
        cf3 = create_cf(
            field_type=CustomField.BOOL, name='Operational?',
            content_type=FakeOrganisation,
        )

        field1 = EntityCellsField(model=FakeContact)

        choices1 = self._find_sub_widget(field1, 'custom_field').choices
        self.assertCellInChoices(f'custom_field-{cf1.id}', choices=choices1)
        self.assertCellInChoices(f'custom_field-{cf2.id}', choices=choices1)
        self.assertCellNotInChoices(f'custom_field-{cf3.id}', choices=choices1)

        # ---
        field2 = EntityCellsField()
        field2.model = FakeContact

        choices2 = self._find_sub_widget(field2, 'custom_field').choices
        self.assertCellInChoices(f'custom_field-{cf1.id}', choices=choices2)

        # ----
        self.assertListEqual(
            [EntityCellCustomField(cf1), EntityCellCustomField(cf2)],
            field2.clean(f'custom_field-{cf1.id},custom_field-{cf2.id}')
        )

        value = '1024'
        self.assertFieldValidationError(
            UniformEntityCellsField, 'invalid_value', field2.clean, f'custom_field-{value}',
            message_args={'value': value},
        )

    def test_customfields02(self):
        "Deleted fields."
        create_cf = partial(
            CustomField.objects.create,
            content_type=FakeContact,
            field_type=CustomField.STR,
        )
        cf1 = create_cf(name='Dog tag')
        cf2 = create_cf(name='Old dog tag', is_deleted=True)

        field = EntityCellsField(model=FakeContact)

        choices = self._find_sub_widget(field, 'custom_field').choices
        self.assertCellInChoices(f'custom_field-{cf1.id}', choices=choices)
        self.assertCellNotInChoices(f'custom_field-{cf2.id}', choices=choices)

        self.assertListEqual(
            [EntityCellCustomField(cf1)],
            field.clean(f'custom_field-{cf1.id}')
        )
        self.assertFieldValidationError(
            EntityCellCustomFieldsField, 'invalid_value', field.clean,
            f'custom_field-{cf2.id}',
            message_args={'value': cf2.id},
        )

    def test_customfields03(self):
        "Deleted fields  + selected cells."
        create_cf = partial(
            CustomField.objects.create,
            content_type=FakeContact,
            field_type=CustomField.STR,
        )
        cf1 = create_cf(name='Dog tag')
        cf2 = create_cf(name='Old dog tag', is_deleted=True)

        field = EntityCellsField(model=FakeContact)
        field.non_hiddable_cells = [EntityCellCustomField(cf2)]

        choices = self._find_sub_widget(field, 'custom_field').choices
        self.assertCellInChoices(f'custom_field-{cf1.id}', choices=choices)
        self.assertCellInChoices(f'custom_field-{cf2.id}', choices=choices)

        # ----
        self.assertListEqual(
            [EntityCellCustomField(cf1), EntityCellCustomField(cf2)],
            field.clean(f'custom_field-{cf1.id},custom_field-{cf2.id}')
        )

    def test_functionfields(self):
        field = EntityCellsField(model=FakeContact)
        name1 = 'get_pretty_properties'
        value = f'function_field-{name1}'
        self.assertCellInChoices(
            value,
            choices=self._find_sub_widget(field, 'function_field').choices,
        )
        self.assertListEqual(
            [EntityCellFunctionField.build(FakeContact, name1)],
            field.clean(value)
        )

        name2 = 'invalid'
        self.assertFieldValidationError(
            UniformEntityCellsField, 'invalid_value', field.clean, f'function_field-{name2}',
            message_args={'value': name2},
        )

    def test_relations(self):
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

        field1 = EntityCellsField(model=FakeContact)

        choices1 = self._find_sub_widget(field1, 'relation').choices
        self.assertCellInChoices(f'relation-{rtype1.id}', choices=choices1)
        self.assertCellNotInChoices(f'relation-{rtype2.id}', choices=choices1)
        self.assertCellNotInChoices(f'relation-{rtype3.id}', choices=choices1)

        # ---
        field2 = EntityCellsField()
        field2.model = FakeContact

        choices2 = self._find_sub_widget(field2, 'relation').choices
        self.assertCellInChoices(f'relation-{rtype1.id}', choices=choices2)
        self.assertCellNotInChoices(f'relation-{rtype2.id}', choices=choices2)

        self.assertListEqual(
            [EntityCellRelation(model=FakeContact, rtype=rtype1)],
            field2.clean(f'relation-{rtype1.id}')
        )
        self.assertFieldValidationError(
            EntityCellRelationsField, 'incompatible', field2.clean, f'relation-{rtype2.id}',
            message_args={'model': 'Test Contact'},
        )

    def test_ok01(self):
        "One regular field."
        field = EntityCellsField(model=FakeContact)
        fname = 'first_name'
        cells = field.clean(f'regular_field-{fname}')
        self.assertEqual(1, len(cells))

        cell = cells[0]
        self.assertEqual(EntityCellRegularField.build(FakeContact, fname), cell)
        self.assertIs(cell.is_hidden, False)

    def assertCellOK(self, cell, expected_cls, expected_value):
        self.assertIsInstance(cell, expected_cls)
        self.assertEqual(expected_value, cell.value)

    def test_ok02(self):
        "All types of columns."
        loves = RelationType.objects.smart_update_or_create(
            ('test-subject_love', 'Is loving'),
            ('test-object_love',  'Is loved by')
        )[0]
        customfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            # content_type=self.ct_contact,
            content_type=FakeContact,
        )
        funcfield = function_field_registry.get(FakeContact, 'get_pretty_properties')

        field = EntityCellsField(model=FakeContact)
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

    def test_error(self):
        "Invalid type id."
        field = EntityCellsField(model=FakeContact, required=False)
        self.assertFieldValidationError(
            EntityCellsField, 'invalid_type', field.clean, 'unknown-donotcare',
            message_args={'type_id': 'unknown'},
        )

    def test_cell_registry01(self):
        field = EntityCellsField()

        registry1 = field.cell_registry
        self.assertIsInstance(registry1, EntityCellsRegistry)
        self.assertIn(EntityCellRegularField.type_id,  registry1)
        self.assertIn(EntityCellCustomField.type_id,   registry1)
        self.assertIn(EntityCellFunctionField.type_id, registry1)
        self.assertIn(EntityCellRelation.type_id,      registry1)

        registry2 = EntityCellsRegistry()
        registry2(EntityCellRegularField)
        registry2(EntityCellRelation)

        field.cell_registry = registry2
        self.assertIs(registry2, field.cell_registry)

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices('regular_field-created', choices=choices)

        self._find_sub_widget(field, 'regular_field')

        def assertNoSubWidget(widget_class):
            for sub_widget in field.widget.sub_widgets:
                if isinstance(sub_widget, widget_class):
                    self.fail(f'Sub-widget unexpectedly found: {widget_class}.')

        assertNoSubWidget(EntityCellCustomFieldsWidget)
        assertNoSubWidget(EntityCellFunctionFieldsWidget)

        self.assertFieldValidationError(
            EntityCellsField, 'invalid_type', field.clean,
            'function_field-get_pretty_properties',
            message_args={'type_id': 'function_field'},
        )

    def test_cell_registry02(self):
        "Set non_hiddable cells BEFORE."
        fname = 'first_name'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(fname, {FieldsConfig.HIDDEN: True})],
        )

        field = EntityCellsField(model=FakeContact)
        field.non_hiddable_cells = [
            EntityCellRegularField.build(FakeContact, fname),
        ]

        registry = EntityCellsRegistry()
        registry(EntityCellRegularField)
        registry(EntityCellRelation)

        field.cell_registry = registry

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices(f'regular_field-{fname}', choices=choices)

    def test_copy01(self):
        "Attribute <non_hiddable_cells>."
        field1 = EntityCellsField(model=FakeContact)
        field2 = deepcopy(field1)

        field1.non_hiddable_cells = [
            EntityCellRegularField.build(FakeContact, 'first_name'),
        ]
        self.assertListEqual([], field2.non_hiddable_cells)

    def test_copy02(self):
        "Attribute <_sub_fields> (container)."
        field1 = EntityCellsField(model=FakeContact)
        field2 = deepcopy(field1)

        registry = EntityCellsRegistry()
        registry(EntityCellRegularField)
        registry(EntityCellRelation)

        field1.cell_registry = registry

        ffield_name = 'get_pretty_properties'
        value = f'function_field-{ffield_name}'
        self.assertFieldValidationError(
            EntityCellsField, 'invalid_type', field1.clean, value,
            message_args={'type_id': 'function_field'},
        )
        self.assertListEqual(
            [EntityCellFunctionField.build(FakeContact, ffield_name)],
            field2.clean(value)
        )

    def test_copy03(self):
        "Attribute <_sub_fields> (content) & sub-widgets' choices."
        field1 = EntityCellsField(model=FakeContact)
        field2 = deepcopy(field1)

        field1.model = FakeOrganisation
        self.assertIsNot(field1._sub_fields[0], field2._sub_fields[0])
        self.assertIsNot(field1._sub_fields[0].widget, field2._sub_fields[0].widget)
        self.assertIsNot(field1.widget, field2.widget)
        self.assertIsNot(field1.widget._sub_widgets[0], field2.widget._sub_widgets[0])

        self.assertEqual(FakeOrganisation, field1.model)
        self.assertEqual(FakeOrganisation, field1.widget.model)
        self.assertEqual(FakeContact,      field2.model)
        self.assertEqual(FakeContact,      field2.widget.model)

        contact_fname = 'first_name'
        contact_value = f'regular_field-{contact_fname}'
        self.assertFieldValidationError(
            UniformEntityCellsField, 'invalid_value', field1.clean, contact_value,
            message_args={'value': contact_fname},
        )
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, contact_fname)],
            field2.clean(contact_value)
        )

        choices1 = self._find_sub_widget(field1, 'regular_field').choices
        choices2 = self._find_sub_widget(field2, 'regular_field').choices
        self.assertCellInChoices(contact_value, choices=choices2)
        self.assertCellNotInChoices(contact_value, choices=choices1)

        orga_fname = 'capital'
        orga_value = f'regular_field-{orga_fname}'
        self.assertFieldValidationError(
            UniformEntityCellsField, 'invalid_value', field2.clean, orga_value,
            message_args={'value': orga_fname},
        )
        self.assertListEqual(
            [EntityCellRegularField.build(FakeOrganisation, orga_fname)],
            field1.clean(orga_value)
        )
        self.assertCellInChoices(orga_value, choices=choices1)
        self.assertCellNotInChoices(orga_value, choices=choices2)

    # def test_content_type(self):  # DEPRECATED
    #     field = EntityCellsField()
    #     self.assertIs(field.content_type.model_class(), CremeEntity)
    #     self.assertIs(field.widget.model, CremeEntity)
    #
    #     ct = ContentType.objects.get_for_model(FakeContact)
    #     field.content_type = ct
    #     self.assertEqual(ct, field.content_type)
    #     self.assertEqual(FakeContact, field.model)
