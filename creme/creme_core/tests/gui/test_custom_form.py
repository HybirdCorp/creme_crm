from copy import deepcopy
from decimal import Decimal
from functools import partial

from django import forms
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.forms import ModelMultipleChoiceField
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellRegistry,
    EntityCellRegularField,
)
from creme.creme_core.forms.base import (
    LAYOUT_DUAL_FIRST,
    LAYOUT_DUAL_SECOND,
    LAYOUT_REGULAR,
    CremeEntityForm,
)
from creme.creme_core.forms.fields import (
    CremeUserEnumerableField,
    EnhancedModelMultipleChoiceField,
    MultiRelationEntityField,
)
from creme.creme_core.gui.custom_form import (
    CustomFormDefault,
    CustomFormDescriptor,
    CustomFormDescriptorRegistry,
    CustomFormExtraSubCell,
    EntityCellCustomFormExtra,
    EntityCellCustomFormSpecial,
    ExtraFieldGroup,
    FieldGroup,
    FieldGroupList,
    base_cell_registry,
)
from creme.creme_core.models import (
    CremePropertyType,
    CustomField,
    CustomFormConfigItem,
    FakeAddress,
    FakeContact,
    FakeOrganisation,
    FakePosition,
    FieldsConfig,
    Relation,
    RelationType,
    SemiFixedRelationType,
)

from ..base import CremeTestCase


class EntityCellCustomFormSpecialTestCase(CremeTestCase):
    def test_build_regular_fields(self):
        value = EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS
        cell = EntityCellCustomFormSpecial.build(FakeOrganisation, value)
        self.assertIsInstance(cell, EntityCellCustomFormSpecial)
        self.assertEqual(FakeOrganisation, cell.model)
        self.assertEqual(value,            cell.value)

        self.assertEqual(_('*Remaining regular fields*'), cell.title)

    def test_build_custom_fields(self):
        value = EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS
        cell = EntityCellCustomFormSpecial.build(FakeOrganisation, value)
        self.assertIsInstance(cell, EntityCellCustomFormSpecial)
        self.assertEqual(FakeOrganisation, cell.model)
        self.assertEqual(value,            cell.value)

        self.assertEqual(_('*Remaining custom fields*'), cell.title)

    def test_build_relationships(self):
        cell = EntityCellCustomFormSpecial.build(
            FakeOrganisation,
            EntityCellCustomFormSpecial.RELATIONS,
        )

        self.assertEqual(_('*Relationships*'), cell.title)

    def test_build_properties(self):
        cell = EntityCellCustomFormSpecial.build(
            FakeOrganisation,
            EntityCellCustomFormSpecial.CREME_PROPERTIES,
        )

        self.assertEqual(_('Properties'), cell.title)

    def test_build_error(self):
        with self.assertLogs(level='WARNING'):
            cell = EntityCellCustomFormSpecial.build(FakeOrganisation, 'invalid')

        self.assertIsNone(cell)


class CustomFormExtraSubCellTestCase(CremeTestCase):
    def test_init(self):
        stype_id = 'test01'
        vname = 'Test01 (test_init)'

        class TestSubCell(CustomFormExtraSubCell):
            sub_type_id = stype_id
            verbose_name = vname

        sub_cell = TestSubCell(model=FakeOrganisation)
        self.assertEqual(FakeOrganisation, sub_cell.model)
        self.assertIs(sub_cell.is_required, True)
        self.assertEqual(stype_id, sub_cell.sub_type_id)
        self.assertEqual(vname, sub_cell.verbose_name)

    def test_eq(self):
        class TestSubCell01(CustomFormExtraSubCell):
            sub_type_id = 'test01'
            verbose_name = 'Test01 (test_eq)'

        class TestSubCell02(CustomFormExtraSubCell):
            sub_type_id = 'test02'
            verbose_name = 'Test02 (test_eq)'

        self.assertEqual(
            TestSubCell01(model=FakeOrganisation),
            TestSubCell01(model=FakeOrganisation),
        )
        self.assertNotEqual(
            TestSubCell01(model=FakeOrganisation),
            TestSubCell01(model=FakeContact),
        )
        self.assertNotEqual(
            TestSubCell01(model=FakeOrganisation),
            TestSubCell02(model=FakeOrganisation),
        )

    def test_into_cell(self):
        class TestSubCell(CustomFormExtraSubCell):
            sub_type_id = 'test01'
            verbose_name = 'Test01 (test_eq)'

        sub_cell = TestSubCell(model=FakeOrganisation)
        cell = sub_cell.into_cell()
        self.assertIsInstance(cell, EntityCellCustomFormExtra)
        self.assertIs(sub_cell, cell.sub_cell)


class CustomFormExtraEntityCellTestCase(CremeTestCase):
    def test_init(self):
        vname = 'Test (test_init)'

        class TestSubCell(CustomFormExtraSubCell):
            sub_type_id = 'test'
            verbose_name = vname

            def formfield(self, instance, user, **kwargs):
                f = forms.CharField(label=str(instance), **kwargs)
                f.user = user

                return f

        sub_cell = TestSubCell(model=FakeOrganisation)
        cell = EntityCellCustomFormExtra(sub_cell)
        self.assertEqual(sub_cell, cell.sub_cell)
        self.assertEqual(vname, cell.title)

        user = self.get_root_user()
        orga = FakeOrganisation(user=user, name='Nerv')
        ffield = cell.formfield(instance=orga, user=user)
        self.assertIsInstance(ffield, forms.CharField)
        self.assertEqual(user, ffield.user)
        self.assertEqual(orga.name, ffield.label)
        self.assertTrue(ffield.required)

    def test_required(self):
        class TestSubCell(CustomFormExtraSubCell):
            sub_type_id = 'test'
            verbose_name = 'Test (test_required)'
            is_required = False

            def formfield(self, instance, user, **kwargs):
                return forms.CharField(label=str(instance), **kwargs)

        cell = EntityCellCustomFormExtra(TestSubCell(model=FakeOrganisation))

        user = self.get_root_user()
        ffield = cell.formfield(
            instance=FakeOrganisation(user=user, name='Nerv'),
            user=user,
        )
        self.assertFalse(ffield.required)

    def test_build(self):
        class TestSubCell01(CustomFormExtraSubCell):
            sub_type_id = 'test01'
            verbose_name = 'Test01 (test_build)'

        class TestSubCell02(CustomFormExtraSubCell):
            sub_type_id = 'test02'
            verbose_name = 'Test02 (test_build)'

        class TestSubCell03(CustomFormExtraSubCell):
            sub_type_id = 'test03'
            verbose_name = 'Test03 (test_build)'

        class ExtraCell(EntityCellCustomFormExtra):
            allowed_sub_cell_classes = [TestSubCell01, TestSubCell03]

        cell1 = ExtraCell.build(FakeOrganisation, TestSubCell01.sub_type_id)
        self.assertIsInstance(cell1, ExtraCell)
        self.assertIsInstance(cell1.sub_cell, TestSubCell01)

        cell3 = ExtraCell.build(FakeOrganisation, TestSubCell03.sub_type_id)
        self.assertIsInstance(cell3, ExtraCell)
        self.assertIsInstance(cell3.sub_cell, TestSubCell03)

        self.assertIsNone(ExtraCell.build(FakeOrganisation, TestSubCell02.sub_type_id))


class ExtraFieldGroupTestCase(CremeTestCase):
    def test_init_base(self):
        group = ExtraFieldGroup(model=FakeOrganisation)
        self.assertEqual(FakeOrganisation, group.model)
        self.assertEqual(LAYOUT_REGULAR, group.layout)

        self.assertFalse(
            [*group.formfields(user=self.get_root_user(), instance=FakeOrganisation())],
        )

        with self.assertRaises(ValueError) as cm:
            group.as_dict()

        self.assertEqual(
            'ExtraFieldGroup.group_id is empty.',
            str(cm.exception),
        )

    def test_as_dict01(self):
        class ChildGroup(ExtraFieldGroup):
            extra_group_id = 'creme_core-child'

        self.assertDictEqual(
            {'group_id': ChildGroup.extra_group_id},
            ChildGroup(model=FakeOrganisation).as_dict(),
        )

    def test_as_dict02(self):
        "With layout."
        class ChildGroup(ExtraFieldGroup):
            extra_group_id = 'creme_core-child'

        self.assertDictEqual(
            {
                'group_id': ChildGroup.extra_group_id,
                'layout': LAYOUT_DUAL_SECOND,
            },
            ChildGroup(model=FakeOrganisation, layout=LAYOUT_DUAL_SECOND).as_dict(),
        )


class FieldGroupListTestCase(CremeTestCase):
    def test_from_cells01(self):
        group_name = 'General'
        fields_groups = FieldGroupList.from_cells(
            model=FakeContact,
            cell_registry=base_cell_registry,
            data=[{
                'name': group_name,
                'cells': [
                    EntityCellRegularField.build(model=FakeContact, name='first_name'),
                    (EntityCellRegularField, {'name': 'last_name'}),
                ],
            }],
        )
        self.assertIsInstance(fields_groups, FieldGroupList)
        self.assertEqual(FakeContact, fields_groups.model)
        self.assertIs(base_cell_registry, fields_groups.cell_registry)

        group = self.get_alone_element(fields_groups)
        self.assertIsInstance(group, FieldGroup)
        self.assertEqual(group_name, group.name)
        self.assertEqual(LAYOUT_REGULAR, group.layout)
        self.assertListEqual(
            [
                EntityCellRegularField.build(model=FakeContact, name=name)
                for name in ('first_name', 'last_name')
            ],
            [*group.cells],
        )

    def test_from_cells02(self):
        "Other model, other fields, layout, registry."
        customfield = CustomField.objects.create(
            name='Rate', field_type=CustomField.INT, content_type=FakeOrganisation,
        )

        my_registry = deepcopy(base_cell_registry)
        group_name1 = 'Regular fields'
        group_name2 = 'Custom fields'
        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            data=[
                {
                    'name': group_name1,
                    'layout': LAYOUT_REGULAR,
                    'cells': [
                        (EntityCellRegularField, {'name': 'name'}),
                    ],
                }, {
                    'name': group_name2,
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        EntityCellCustomField(customfield=customfield),
                    ],
                },
            ],
            cell_registry=my_registry,
        )
        self.assertEqual(2, len(fields_groups))
        self.assertIs(my_registry, fields_groups.cell_registry)

        group1 = fields_groups[0]
        self.assertEqual(group_name1, group1.name)
        self.assertEqual(LAYOUT_REGULAR, group1.layout)
        self.assertListEqual(
            [EntityCellRegularField.build(model=FakeOrganisation, name='name')],
            [*group1.cells],
        )

        group2 = fields_groups[1]
        self.assertEqual(group_name2, group2.name)
        self.assertEqual(LAYOUT_DUAL_FIRST, group2.layout)
        self.assertListEqual([EntityCellCustomField(customfield)], [*group2.cells])

        self.assertListEqual([group1, group2], [*fields_groups])

    def test_from_cells03(self):
        "None cells are ignored."
        group_name = 'General'
        fields_groups = FieldGroupList.from_cells(
            model=FakeContact,
            cell_registry=base_cell_registry,
            data=[
                {
                    'name': group_name,
                    'cells': [
                        None,  # EntityCellRegularField.build() + invalid field name
                        (EntityCellRegularField, {'name': 'last_name'}),
                        (EntityCellRegularField, {'name': 'invalid'}),
                    ],
                },
            ],
        )
        self.assertListEqual(
            [EntityCellRegularField.build(model=FakeContact, name='last_name')],
            [*fields_groups[0].cells],
        )

    def test_from_cells04(self):
        "Extra groups."
        class AddressGroup(ExtraFieldGroup):
            extra_group_id = 'creme_core-address'

        group_name = 'General'
        fields_groups = FieldGroupList.from_cells(
            model=FakeContact,
            cell_registry=base_cell_registry,
            allowed_extra_group_classes=[AddressGroup],
            data=[
                {
                    'name': group_name,
                    'cells': [
                        (EntityCellRegularField, {'name': 'last_name'}),
                        (EntityCellRegularField, {'name': 'first_name'}),
                    ],
                },
                AddressGroup(model=FakeContact),
            ],
        )
        self.assertEqual(2, len(fields_groups))
        self.assertEqual(group_name, fields_groups[0].name)
        self.assertIsInstance(fields_groups[1], AddressGroup)

        # Not allowed group
        class CorporateGroup(ExtraFieldGroup):
            extra_group_id = 'creme_core-corporate'

        with self.assertLogs(level='WARNING') as logs_manager:
            FieldGroupList.from_cells(
                model=FakeContact,
                cell_registry=base_cell_registry,
                allowed_extra_group_classes=[CorporateGroup],  # < ===
                data=[AddressGroup(model=FakeContact)],
            )
        self.assertEqual(
            logs_manager.output[0],
            'WARNING:creme.creme_core.gui.custom_form:FieldGroupList.from_cells(): '
            'invalid group class "AddressGroup" (available: [CorporateGroup])',
        )

    def test_from_cells_errors(self):
        "Other errors."
        with self.assertLogs(level='WARNING') as logs_manager:
            fields_groups = FieldGroupList.from_cells(
                model=FakeOrganisation,
                data=[
                    {
                        'name': 'Regular fields',
                        'layout': 'invalid',  # <====
                        'cells': [
                            (EntityCellRegularField, {'name': 'name'}),
                        ],
                    }
                ],
                cell_registry=base_cell_registry,
            )

        fields_group = self.get_alone_element(fields_groups)
        self.assertEqual(LAYOUT_REGULAR, fields_group.layout)

        message = self.get_alone_element(logs_manager.output)
        self.assertStartsWith(
            message,
            'WARNING:creme.creme_core.gui.custom_form:FieldGroupList.from_cells(): '
            'invalid layout "invalid" ',
        )

    def test_from_dicts01(self):
        group_name = 'General'
        cells = [
            EntityCellRegularField.build(model=FakeContact, name=name)
            for name in ('first_name', 'last_name')
        ]
        fields_groups = FieldGroupList.from_dicts(
            model=FakeContact,
            data=[
                {
                    'name': group_name,
                    'cells': [cell.to_dict() for cell in cells],
                    'layout': LAYOUT_REGULAR,
                },
            ],
            cell_registry=base_cell_registry,
        )
        self.assertIsInstance(fields_groups, FieldGroupList)
        self.assertEqual(FakeContact, fields_groups.model)

        group = self.get_alone_element(fields_groups)
        self.assertIsInstance(group, FieldGroup)
        self.assertEqual(group_name, group.name)
        self.assertEqual(LAYOUT_REGULAR, group.layout)
        self.assertListEqual(cells, [*group.cells])

    def test_from_dicts02(self):
        "Other model, other fields, layout."
        customfield = CustomField.objects.create(
            name='Rate', field_type=CustomField.INT, content_type=FakeOrganisation,
        )

        group_name1 = 'Regular fields'
        cell1 = EntityCellRegularField.build(model=FakeOrganisation, name='name')
        group_name2 = 'Custom fields'
        cell2 = EntityCellCustomField(customfield=customfield)
        fields_groups = FieldGroupList.from_dicts(
            model=FakeOrganisation,
            data=[
                {
                    'name': group_name1,
                    'layout': LAYOUT_REGULAR,
                    'cells': [cell1.to_dict()],
                }, {
                    'name': group_name2,
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [cell2.to_dict()],
                },
            ],
            cell_registry=base_cell_registry,
        )
        self.assertEqual(2, len(fields_groups))

        group1 = fields_groups[0]
        self.assertEqual(group_name1, group1.name)
        self.assertEqual(LAYOUT_REGULAR, group1.layout)
        self.assertListEqual([cell1], [*group1.cells])

        group2 = fields_groups[1]
        self.assertEqual(group_name2, group2.name)
        self.assertEqual(LAYOUT_DUAL_FIRST, group2.layout)
        self.assertListEqual([cell2], [*group2.cells])

    def test_from_dicts03(self):
        "Extra groups."
        class AddressGroup(ExtraFieldGroup):
            extra_group_id = 'creme_core-address'

        class CorporateGroup(ExtraFieldGroup):
            extra_group_id = 'creme_core-corporate'

        fields_groups1 = FieldGroupList.from_dicts(
            model=FakeContact,
            cell_registry=base_cell_registry,
            allowed_extra_group_classes=[AddressGroup, CorporateGroup],
            data=[
                {'group_id': AddressGroup.extra_group_id},
                {
                    'group_id': CorporateGroup.extra_group_id,
                    'layout': LAYOUT_DUAL_SECOND,
                },
            ],
        )
        self.assertEqual(2, len(fields_groups1))

        group1 = fields_groups1[0]
        self.assertIsInstance(group1, AddressGroup)
        self.assertEqual(LAYOUT_REGULAR, group1.layout)

        group2 = fields_groups1[1]
        self.assertIsInstance(group2, CorporateGroup)
        self.assertEqual(LAYOUT_DUAL_SECOND, group2.layout)

        # Not allowed group
        with self.assertLogs(level='WARNING') as logs_manager:
            fields_groups2 = FieldGroupList.from_dicts(
                model=FakeContact,
                cell_registry=base_cell_registry,
                allowed_extra_group_classes=[AddressGroup],
                data=[
                    {'group_id': AddressGroup.extra_group_id},
                    {'group_id': CorporateGroup.extra_group_id},  # <===
                ],
            )
        self.assertEqual(1, len(fields_groups2))
        self.assertIn(
            f'WARNING:creme.creme_core.gui.custom_form:FieldGroupList.from_dicts(): '
            f'invalid data (not allowed group ID "{CorporateGroup.extra_group_id}").',
            logs_manager.output,
        )

    def test_from_dicts_errors(self):
        "Errors."
        cell = EntityCellRegularField.build(model=FakeOrganisation, name='name')

        with self.assertLogs(level='WARNING') as logs_manager1:
            groups1 = FieldGroupList.from_dicts(
                model=FakeOrganisation,
                data=[('cells', [cell])],
                cell_registry=base_cell_registry,
            )
        self.assertIsInstance(groups1, FieldGroupList)
        self.assertIn(
            'WARNING:creme.creme_core.gui.custom_form:FieldGroupList.from_dicts(): '
            'invalid data ("tuple indices must be integers or slices, not str").',
            logs_manager1.output,
        )

        with self.assertLogs(level='WARNING') as logs_manager2:
            groups2 = FieldGroupList.from_dicts(
                model=FakeOrganisation,
                data=[{'cells': ['I am not a dict']}],
                cell_registry=base_cell_registry,
            )
        self.assertIsInstance(groups2, FieldGroupList)
        self.assertIn(
            'WARNING:creme.creme_core.gui.custom_form:FieldGroupList.from_dicts(): '
            'invalid data (missing key "\'name\'").',
            logs_manager2.output,
        )

    def test_form_regular_fields01(self):
        user = self.get_root_user()
        group_name = 'General'
        mfields = ['user', 'last_name', 'first_name', 'is_a_nerd']
        fields_groups = FieldGroupList.from_cells(
            model=FakeContact,
            cell_registry=base_cell_registry,
            data=[{
                'name': group_name,
                'cells': [
                    (EntityCellRegularField, {'name': name}) for name in mfields
                ],
            }],
        )

        form_cls = fields_groups.form_class()
        self.assertIsSubclass(form_cls, CremeEntityForm)

        form1 = form_cls(user=user)
        self.assertIs(FakeContact, form1._meta.model)
        formfields1 = form1.fields

        lname_field = formfields1.get('last_name')
        self.assertIsInstance(lname_field, forms.CharField)
        self.assertEqual(100, lname_field.max_length)
        self.assertEqual(_('Last name'), lname_field.label)
        self.assertTrue(lname_field.required)

        fname_field = formfields1.get('first_name')
        self.assertIsInstance(fname_field, forms.CharField)
        self.assertEqual(100, fname_field.max_length)
        self.assertEqual(_('First name'), fname_field.label)
        self.assertFalse(fname_field.required)

        user_field = formfields1.get('user')
        self.assertIsInstance(user_field, CremeUserEnumerableField)
        self.assertEqual(_('Owner user'), user_field.label)

        self.assertIsInstance(formfields1.get('is_a_nerd'), forms.BooleanField)

        self.assertNotIn('created',     formfields1)  # Not editable
        self.assertNotIn('description', formfields1)  # Not in FieldGroupList
        self.assertNotIn('position',    formfields1)  # Idem

        self.assertNotIn('property_types',   formfields1)
        self.assertNotIn('relation_types',   formfields1)
        self.assertNotIn('semifixed_rtypes', formfields1)

        block = self.get_alone_element(form1.get_blocks())
        self.assertEqual(group_name,     block.label)
        self.assertEqual(LAYOUT_REGULAR, block.layout)

        block_fields = block.bound_fields
        self.assertEqual(4, len(block_fields))

        bound_field1 = block_fields[0]
        self.assertEqual(mfields[0],      bound_field1.name)
        self.assertEqual(_('Owner user'), bound_field1.label)

        self.assertEqual(mfields[1], block_fields[1].name)
        self.assertEqual(mfields[2], block_fields[2].name)
        self.assertEqual(mfields[3], block_fields[3].name)

        # ---
        lname = 'Turtle'
        fname = 'Donatello'
        form2 = form_cls(
            user=user,
            data={
                'user':       user.id,
                'first_name': fname,
                'last_name':  lname,
                'is_a_nerd':  'on',
                'description': 'Should not be used',
                'position': FakePosition.objects.first().id,
            },
        )
        self.assertTrue(form2.is_valid(), form2.errors)

        instance = form2.save()
        self.assertIsInstance(instance, FakeContact)
        self.assertIsNotNone(instance.pk)
        self.assertEqual(user,  instance.user)
        self.assertEqual(lname, instance.last_name)
        self.assertEqual(fname, instance.first_name)
        self.assertIs(instance.is_a_nerd, True)
        self.assertFalse(instance.description)
        self.assertIsNone(instance.position)

    def test_form_regular_fields02(self):
        "Other models, other fields, layout, base form class."
        class MyFormBase(CremeEntityForm):
            pass

        user = self.get_root_user()
        group_name = 'Regular fields'
        mfields = ['user', 'name', 'description']
        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=base_cell_registry,
            data=[{
                'name': group_name,
                'cells': [
                    (EntityCellRegularField, {'name': name}) for name in mfields
                ],
                'layout': LAYOUT_DUAL_FIRST,
            }],
        )

        form_cls = fields_groups.form_class(base_form_class=MyFormBase)
        self.assertIsSubclass(form_cls, MyFormBase)

        form = form_cls(user=user)
        self.assertIs(FakeOrganisation, form._meta.model)

        fields = form.fields
        self.assertIn(mfields[0], fields)
        self.assertIn(mfields[1], fields)
        self.assertIn(mfields[2], fields)

        self.assertNotIn('modified', fields)
        self.assertNotIn('sector',   fields)
        self.assertNotIn('address',  fields)

        block = self.get_alone_element(form.get_blocks())
        self.assertEqual(group_name,        block.label)
        self.assertEqual(LAYOUT_DUAL_FIRST, block.layout)
        self.assertListEqual(mfields, [bfield.name for bfield in block.bound_fields])

    def test_form_regular_fields03(self):
        "Missing required fields."
        user = self.get_root_user()

        fields_groups1 = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=base_cell_registry,
            data=[{
                'name': 'Regular fields',
                'cells': [
                    # (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                ],
            }],
        )

        form1 = fields_groups1.form_class()(user=user)
        fields1 = form1.fields
        self.assertIn('name', fields1)
        self.assertIn('user', fields1)
        self.assertNotIn('description', fields1)

        blocks = [*form1.get_blocks()]
        self.assertEqual(2, len(blocks))  # There's a special block for missing required

        block = blocks[1]
        self.assertEqual(
            _('Missing required fields (update your configuration)'),
            block.label,
        )
        self.assertListEqual(['user'], [bfield.name for bfield in block.bound_fields])

        # Other model, other fields ----
        fields_groups2 = FieldGroupList.from_cells(
            model=FakeContact,
            cell_registry=base_cell_registry,
            data=[{
                'name': 'Regular fields',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    # (EntityCellRegularField, {'name': 'last_name'}),
                ],
            }],
        )

        form2 = fields_groups2.form_class()(user=user)
        fields2 = form2.fields
        self.assertIn('user',      fields2)
        self.assertIn('last_name', fields2)

    def test_form_regular_fields04(self):
        "Exclude required fields."
        user = self.get_root_user()

        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=base_cell_registry,
            data=[{
                'name': 'Regular fields',
                'cells': [
                    # (EntityCellRegularField, {'name': 'user'}),
                    # (EntityCellRegularField, {'name': 'name'}),
                    (EntityCellRegularField, {'name': 'phone'}),
                ],
            }],
        )

        form_class = fields_groups.form_class(exclude_fields=['user', 'name'])
        form = form_class(user=user)

        fields = form.fields
        self.assertIn('phone', fields)
        self.assertNotIn('name', fields)
        self.assertNotIn('user', fields)

        blocks = [*form.get_blocks()]
        self.assertEqual(1, len(blocks))  # No special block for missing required

    def test_form_regular_fields_not_editable(self):
        user = self.get_root_user()

        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=base_cell_registry,
            data=[{
                'name': 'Regular fields',
                'cells': [
                    (EntityCellRegularField, {'name': 'created'}),
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                ],
            }],
        )

        with self.assertLogs(level='WARNING') as logs_manager:
            fields = fields_groups.form_class()(user=user).fields

        self.assertIn('user', fields)
        self.assertIn('name', fields)
        self.assertNotIn('created', fields)

        self.assertEqual(
            logs_manager.output,
            [
                'WARNING:creme.creme_core.gui.custom_form:'
                'A not editable field is used by the configuration '
                '& will be ignored: created',
            ],
        )

    def test_form_regular_fields_too_deep(self):
        user = self.get_root_user()

        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=base_cell_registry,
            data=[{
                'name': 'Regular fields',
                'cells': [
                    (EntityCellRegularField, {'name': 'sector__title'}),
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                ],
            }],
        )

        with self.assertLogs(level='WARNING') as logs_manager:
            fields = fields_groups.form_class()(user=user).fields

        self.assertIn('user', fields)
        self.assertIn('name', fields)
        self.assertNotIn('sector__title', fields)
        self.assertNotIn('sector', fields)
        self.assertNotIn('title', fields)

        self.assertEqual(
            logs_manager.output,
            [
                'WARNING:creme.creme_core.gui.custom_form:'
                'A deep field is used by the configuration '
                '& will be ignored: sector__title',
            ],
        )

    def test_form_regular_fields_hidden_fields(self):
        user = self.get_root_user()

        hidden = 'description'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden, {FieldsConfig.HIDDEN: True})],
        )

        mfields = ['user', 'name', hidden]
        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=base_cell_registry,
            data=[{
                'name': 'Regular fields',
                'cells': [
                    (EntityCellRegularField, {'name': name}) for name in mfields
                ],
            }],
        )

        fields = fields_groups.form_class()(user=user).fields
        self.assertIn(mfields[0], fields)
        self.assertIn(mfields[1], fields)
        self.assertNotIn(hidden, fields)

    def test_form_regular_fields_required_fields(self):
        user = self.get_root_user()

        required1 = 'email'
        required2 = 'phone'
        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[
                (required1, {FieldsConfig.REQUIRED: True}),
                (required2, {FieldsConfig.REQUIRED: True}),
            ],
        )

        mfields = ['user', 'name', required1]
        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=base_cell_registry,
            data=[{
                'name': 'Regular fields',
                'cells': [
                    (EntityCellRegularField, {'name': name}) for name in mfields
                ],
            }],
        )

        fields = fields_groups.form_class()(user=user).fields
        self.assertIn(mfields[0], fields)
        self.assertIn(mfields[1], fields)

        required_field1 = fields.get(required1)
        self.assertIsNotNone(required_field1)
        self.assertTrue(required_field1.required)

        # This field is present because it is required
        required_field2 = fields.get(required2)
        self.assertIsNotNone(required_field2)
        self.assertTrue(required_field2.required)

    def test_form_custom_fields01(self):
        user = self.get_root_user()

        create_cfield = partial(CustomField.objects.create, content_type=FakeContact)
        cfield1 = create_cfield(name='IQ',       field_type=CustomField.INT, is_required=True)
        cfield2 = create_cfield(name='Strength', field_type=CustomField.FLOAT)
        cfield3 = create_cfield(name='Unused',   field_type=CustomField.STR)

        group_name1 = 'Regular fields'
        group_name2 = 'CustomField fields'
        fields_groups = FieldGroupList.from_cells(
            model=FakeContact,
            cell_registry=base_cell_registry,
            data=[
                {
                    'name': group_name1,
                    'cells': [
                        (EntityCellRegularField, {'name': name})
                        for name in ['user', 'last_name', 'first_name']
                    ],
                }, {
                    'name': group_name2,
                    'cells': [
                        EntityCellCustomField(cfield1),
                        EntityCellCustomField(cfield2),
                    ],
                },
            ],
        )

        form_cls = fields_groups.form_class()

        form1 = form_cls(user=user)
        fields1 = form1.fields

        iq_field = fields1.get(f'custom_field-{cfield1.id}')
        self.assertIsInstance(iq_field, forms.IntegerField)
        self.assertEqual(cfield1.name, iq_field.label)
        self.assertTrue(iq_field.required)

        strong_field = fields1.get(f'custom_field-{cfield2.id}')
        self.assertIsInstance(strong_field, forms.DecimalField)
        self.assertEqual(cfield2.name, strong_field.label)
        self.assertFalse(strong_field.required)

        self.assertNotIn(f'custom_field-{cfield3.id}', fields1)

        blocks = form1.get_blocks()
        listified_blocks = [*blocks]
        self.assertEqual(2, len(listified_blocks))

        block = listified_blocks[1]
        self.assertEqual('group_1', block.id)
        self.assertEqual(group_name2, block.label)

        block_fields = block.bound_fields
        self.assertEqual(2, len(block_fields))
        self.assertEqual(f'custom_field-{cfield1.id}', block_fields[0].name)
        self.assertEqual(f'custom_field-{cfield2.id}', block_fields[1].name)

        self.assertEqual(group_name2, blocks['group_1'].label)

        # ---
        iq = 130
        strength = '72.50'
        form2 = form_cls(
            user=user,
            data={
                'user':       user.id,
                'first_name': 'Turtle',
                'last_name':  'Donatello',

                f'custom_field-{cfield1.id}': iq,
                f'custom_field-{cfield2.id}': strength,
                f'custom_field-{cfield3.id}': 'Should not be used',
            },
        )
        self.assertTrue(form2.is_valid(), form2.errors)

        instance = form2.save()

        cf_value1 = self.get_object_or_fail(
            cfield1.value_class, custom_field=cfield1, entity=instance,
        )
        self.assertEqual(iq, cf_value1.value)

        cf_value2 = self.get_object_or_fail(
            cfield2.value_class, custom_field=cfield2, entity=instance,
        )
        self.assertEqual(Decimal(strength), cf_value2.value)

        self.assertFalse(cfield2.value_class.objects.filter(custom_field=cfield3))

    def test_form_custom_fields02(self):
        "Missing required fields."
        user = self.get_root_user()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=FakeContact, field_type=CustomField.INT,
        )
        cfield1 = create_cfield(name='IQ', is_required=True)
        cfield2 = create_cfield(name='Strength', field_type=CustomField.FLOAT)
        cfield3 = create_cfield(name='Unused', field_type=CustomField.STR)
        cfield4 = create_cfield(name='Costs', content_type=FakeOrganisation, is_required=True)

        fields_groups = FieldGroupList.from_cells(
            model=FakeContact,
            cell_registry=base_cell_registry,
            data=[
                {
                    'name': 'Regular fields',
                    'cells': [
                        (EntityCellRegularField, {'name': name})
                        for name in ('user', 'last_name')
                    ],
                }, {
                    'name': 'CustomField fields',
                    'cells': [
                        # EntityCellCustomField(cfield1),
                        EntityCellCustomField(cfield2),
                        # EntityCellCustomField(cfield3),
                    ],
                },
            ],
        )

        form = fields_groups.form_class()(user=user)

        fields = form.fields
        self.assertNotIn(f'custom_field-{cfield3.id}', fields)
        self.assertIn(f'custom_field-{cfield2.id}', fields)
        self.assertIn(f'custom_field-{cfield1.id}', fields)
        self.assertNotIn(f'custom_field-{cfield4.id}', fields)

        blocks = [*form.get_blocks()]
        self.assertEqual(3, len(blocks))  # There's a special block for missing required

        block = blocks[2]
        self.assertEqual(
            _('Missing required custom fields (update your configuration)'),
            block.label,
        )
        self.assertListEqual(
            [f'custom_field-{cfield1.id}'],
            [bfield.name for bfield in block.bound_fields],
        )

    def test_form_custom_fields03(self):
        "Deleted custom fields."
        user = self.get_root_user()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=FakeContact, field_type=CustomField.INT,
        )
        cfield1 = create_cfield(name='IQ')
        cfield2 = create_cfield(name='Strength')

        fields_groups = FieldGroupList.from_cells(
            model=FakeContact,
            cell_registry=base_cell_registry,
            data=[
                {
                    'name': 'Regular fields',
                    'cells': [
                        (EntityCellRegularField, {'name': name})
                        for name in ('user', 'last_name')
                    ],
                }, {
                    'name': 'CustomField fields',
                    'cells': [
                        EntityCellCustomField(cfield1),
                        EntityCellCustomField(cfield2),
                    ],
                },
            ],
        )

        cfield1.is_deleted = True
        cfield1.save()

        form = fields_groups.form_class()(user=user)

        fields = form.fields
        self.assertIn(f'custom_field-{cfield2.id}', fields)
        self.assertNotIn(f'custom_field-{cfield1.id}', fields)

        listified_blocks = [*form.get_blocks()]
        self.assertEqual(2, len(listified_blocks))

        # Not cfield1.id
        block_field = self.get_alone_element(listified_blocks[1].bound_fields)
        self.assertEqual(f'custom_field-{cfield2.id}', block_field.name)

    def test_form_custom_fields04(self):
        "Deleted missing required fields."
        user = self.get_root_user()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=FakeContact, field_type=CustomField.INT,
        )
        cfield1 = create_cfield(name='IQ', is_required=True, is_deleted=True)
        cfield2 = create_cfield(name='Strength')

        group_name1 = 'Regular fields'
        group_name2 = 'CustomField fields'
        fields_groups = FieldGroupList.from_cells(
            model=FakeContact,
            cell_registry=base_cell_registry,
            data=[
                {
                    'name': 'Regular fields',
                    'cells': [
                        (EntityCellRegularField, {'name': name})
                        for name in ('user', 'last_name')
                    ],
                }, {
                    'name': group_name2,
                    'cells': [
                        # EntityCellCustomField(cfield1),
                        EntityCellCustomField(cfield2),
                    ],
                },
            ],
        )

        form = fields_groups.form_class()(user=user)

        fields = form.fields
        self.assertIn(f'custom_field-{cfield2.id}', fields)
        self.assertNotIn(f'custom_field-{cfield1.id}', fields)

        self.assertListEqual(
            [group_name1, group_name2],
            [block.label for block in form.get_blocks()]
        )

    def test_form_remaining_regular_fields(self):
        user = self.get_root_user()

        model = FakeContact
        hidden = 'first_name'
        excluded = 'sector'

        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[(hidden, {FieldsConfig.HIDDEN: True})],
        )

        group_name1 = 'Main fields'
        group_name2 = 'Other fields'
        field_names1 = ['user', 'last_name']
        fields_groups = FieldGroupList.from_cells(
            model=model,
            cell_registry=base_cell_registry,
            data=[
                {
                    'name': group_name1,
                    'cells': [
                        *(
                            (EntityCellRegularField, {'name': name})
                            for name in field_names1
                        ),
                    ],
                }, {
                    'name': group_name2,
                    'cells': [
                        (EntityCellRegularField, {'name': 'phone'}),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
            ],
        )

        form_cls = fields_groups.form_class(exclude_fields=(excluded,))

        form = form_cls(user=user)
        formfields = form.fields

        # 1rst group
        for fname in field_names1:
            self.assertIn(fname, formfields)

        # 2nd group (explicit)
        self.assertIn('phone', formfields)

        # 2nd group (remaining)
        mobile_field = formfields.get('mobile')
        self.assertIsInstance(mobile_field, forms.CharField)
        self.assertEqual(_('Mobile'), mobile_field.label)
        self.assertFalse(mobile_field.required)

        self.assertIn('position', formfields)

        self.assertNotIn('id',              formfields)
        self.assertNotIn('cremeentity_ptr', formfields)
        self.assertNotIn(excluded,          formfields)
        self.assertNotIn(hidden,            formfields)

        blocks = form.get_blocks()
        listified_blocks = [*blocks]
        self.assertEqual(2, len(listified_blocks))

        self.assertListEqual(
            field_names1,
            [bfield.name for bfield in listified_blocks[0].bound_fields],
        )
        self.assertListEqual(
            [
                'phone',  # Explicit
                'description',
                'civility',
                'is_a_nerd',
                'loves_comics',
                'mobile',
                'email',
                'url_site',
                'position',
                'birthday',
                'image',
                'languages',
                'preferred_countries',
            ],
            [bfield.name for bfield in listified_blocks[1].bound_fields],
        )

    def test_form_remaining_custom_fields(self):
        user = self.get_root_user()

        create_cfield = partial(
            CustomField.objects.create, content_type=FakeContact, field_type=CustomField.INT,
        )
        cfield1 = create_cfield(name='IQ', is_required=True)
        cfield2 = create_cfield(name='Strength', field_type=CustomField.FLOAT)
        cfield3 = create_cfield(name='Nickname', field_type=CustomField.STR)
        create_cfield(name='Deleted', is_deleted=True)  # Should not be used

        group_name1 = 'Main fields'
        group_name2 = 'Other Custom fields'
        fields_groups = FieldGroupList.from_cells(
            model=FakeContact,
            cell_registry=base_cell_registry,
            data=[
                {
                    'name': group_name1,
                    'cells': [
                        *(
                            (EntityCellRegularField, {'name': name})
                            for name in ['user', 'last_name', 'first_name']
                        ),
                        EntityCellCustomField(cfield2),
                    ],
                }, {
                    'name': group_name2,
                    'cells': [
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS},
                        ),
                    ],
                },
            ],
        )

        form_cls = fields_groups.form_class()

        form = form_cls(user=user)
        fields1 = form.fields

        strong_field = fields1.get(f'custom_field-{cfield2.id}')
        self.assertIsInstance(strong_field, forms.DecimalField)
        self.assertEqual(cfield2.name, strong_field.label)
        self.assertFalse(strong_field.required)

        iq_field = fields1.get(f'custom_field-{cfield1.id}')
        self.assertIsInstance(iq_field, forms.IntegerField)
        self.assertEqual(cfield1.name, iq_field.label)
        self.assertTrue(iq_field.required)

        nick_field = fields1.get(f'custom_field-{cfield3.id}')
        self.assertIsInstance(nick_field, forms.CharField)
        self.assertEqual(cfield3.name, nick_field.label)
        self.assertFalse(nick_field.required)

        blocks = form.get_blocks()
        listified_blocks = [*blocks]
        self.assertEqual(2, len(listified_blocks))

        block1 = listified_blocks[0]
        self.assertEqual(group_name1, block1.label)
        self.assertIn(
            f'custom_field-{cfield2.id}',
            [bfield.name for bfield in block1.bound_fields],
        )

        block2 = listified_blocks[1]
        self.assertEqual(group_name2, block2.label)

        block_fields2 = block2.bound_fields
        self.assertEqual(2, len(block_fields2))
        self.assertEqual(f'custom_field-{cfield1.id}', block_fields2[0].name)
        self.assertEqual(f'custom_field-{cfield3.id}', block_fields2[1].name)

    def test_form_properties(self):
        user = self.get_root_user()
        model = FakeContact

        create_ptype = CremePropertyType.objects.create
        ptype01 = create_ptype(text='Smokes')
        ptype02 = create_ptype(text='Wears glasses')
        ptype03 = create_ptype(text='Has a gun').set_subject_ctypes(model)
        ptype04 = create_ptype(text='Is a ship').set_subject_ctypes(FakeOrganisation)

        group_name1 = 'Main fields'
        group_name2 = 'Properties'
        fields_groups = FieldGroupList.from_cells(
            model=model,
            cell_registry=base_cell_registry,
            data=[
                {
                    'name': group_name1,
                    'cells': [
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                }, {
                    'name': group_name2,
                    'cells': [
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.CREME_PROPERTIES},
                        ),
                    ],
                },
            ],
        )

        form_cls = fields_groups.form_class()

        form1 = form_cls(user=user)
        formfields = form1.fields

        # 1rst group
        self.assertIn('user', formfields)
        self.assertIn('phone', formfields)

        # 2nd group
        prop_field = formfields.get('property_types')
        self.assertIsInstance(prop_field, EnhancedModelMultipleChoiceField)
        self.assertEqual(_('Properties'), prop_field.label)
        self.assertFalse(prop_field.required)

        # Choices are sorted with 'text'
        choices = [(choice[0].value, choice[1]) for choice in prop_field.choices]
        i1 = self.assertIndex((ptype03.id, ptype03.text), choices)
        i2 = self.assertIndex((ptype01.id, ptype01.text), choices)
        i3 = self.assertIndex((ptype02.id, ptype02.text), choices)
        self.assertLess(i1, i2)
        self.assertLess(i2, i3)

        self.assertNotIn((ptype04.id, ptype04.text), choices)

        listified_blocks = [*form1.get_blocks()]
        self.assertEqual(2, len(listified_blocks))
        self.assertListEqual(
            ['property_types'],
            [bfield.name for bfield in listified_blocks[1].bound_fields],
        )

        # ---
        form2 = form_cls(
            user=user,
            data={
                'user':       user.id,
                'first_name': 'Turtle',
                'last_name':  'Donatello',

                'property_types': [ptype01.id, ptype03.id],
            },
        )
        self.assertTrue(form2.is_valid(), form2.errors)

        instance = form2.save()
        self.assertIsInstance(instance, model)
        self.assertSetEqual(
            {ptype01, ptype03},
            {p.type for p in instance.properties.all()},
        )

        # Edition ---
        form3 = form_cls(user=user, instance=instance)
        self.assertNotIn('property_types', form3.fields)

        form4 = form_cls(
            user=user,
            instance=instance,
            data={
                'user':        user.id,
                'first_name':  'Turtle',
                'last_name':   'Donatello',
                'description': 'Nerd',

                'property_types': [ptype02.id],  # Should not be used
            },
        )
        self.assertTrue(form4.is_valid(), form2.errors)

        edited_instance = form4.save()
        self.assertSetEqual(
            {ptype01, ptype03},
            {p.type for p in edited_instance.properties.all()},
        )

    @staticmethod
    def _build_basic_relations_groups():
        return FieldGroupList.from_cells(
            model=FakeContact,
            cell_registry=base_cell_registry,
            data=[
                {
                    'name': 'Main fields',
                    'cells': [
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                }, {
                    'name': 'Relations',
                    'cells': [
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.RELATIONS},
                        ),
                    ],
                },
            ],
        )

    def test_form_relations01(self):
        user = self.get_root_user()
        model = FakeContact

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Splinter', last_name='Hamato')
        contact2 = create_contact(first_name='Yoshi',    last_name='Hamato')

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name="'Turtle's lair'")
        orga2 = create_orga(user=user, name="'April's apartment")

        rtype1 = RelationType.objects.builder(
            id='test-subject_sensei', predicate='has sensei',
        ).symmetric(id='test-object_sensei', predicate='is the sensei of').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_lives', predicate='lives in', models=[FakeContact],
        ).symmetric(
            id='test-object_lives', predicate='is occupied by', models=[FakeOrganisation],
        ).get_or_create()[0]

        create_strt = SemiFixedRelationType.objects.create
        sfrt1 = create_strt(
            predicate='Lives at April',
            relation_type=rtype2,
            real_object=orga2,
        )
        sfrt2 = create_strt(
            predicate='Hamato Yoshi is a sensei',
            relation_type=rtype1,
            real_object=contact2,
        )
        create_strt(
            predicate='Do not use me',
            relation_type=rtype2.symmetric_type,
            real_object=contact2,
        )

        fields_groups = self._build_basic_relations_groups()
        form_cls = fields_groups.form_class()

        form1 = form_cls(user=user)
        formfields = form1.fields

        # 1rst group
        self.assertIn('user', formfields)
        self.assertIn('phone', formfields)

        # 2nd group
        rtypes_field = formfields.get('relation_types')
        self.assertIsInstance(rtypes_field, MultiRelationEntityField)
        self.assertEqual(_('Relationships to add'), rtypes_field.label)
        self.assertFalse(rtypes_field.required)
        self.assertCountEqual(
            [*RelationType.objects.compatible(model)],
            [*rtypes_field.allowed_rtypes],
        )

        semirtypes_field = formfields.get('semifixed_rtypes')
        self.assertIsInstance(semirtypes_field, ModelMultipleChoiceField)
        self.assertEqual(
            _('Semi-fixed types of relationship'), semirtypes_field.label,
        )
        self.assertFalse(semirtypes_field.required)
        self.assertCountEqual(
            [sfrt1, sfrt2],
            [*semirtypes_field.queryset],
        )

        listified_blocks = [*form1.get_blocks()]
        self.assertEqual(2, len(listified_blocks))
        self.assertListEqual(
            ['relation_types', 'semifixed_rtypes'],
            [bfield.name for bfield in listified_blocks[1].bound_fields],
        )

        # ---
        form2 = form_cls(
            user=user,
            data={
                'user':       user.id,
                'first_name': 'Turtle',
                'last_name':  'Donatello',

                'relation_types': self.formfield_value_multi_relation_entity(
                    (rtype1, contact1),
                    (rtype2, orga1),
                    (rtype2, orga1),  # Duplicates
                ),
                'semifixed_rtypes': [sfrt1.id, sfrt2.id],
            },
        )
        self.assertTrue(form2.is_valid(), form2.errors)

        instance = form2.save()
        self.assertIsInstance(instance, model)

        self.assertEqual(4, instance.relations.count())
        self.assertHaveRelation(subject=instance, type=rtype1, object=contact1)
        self.assertHaveRelation(subject=instance, type=rtype1, object=contact2)
        self.assertHaveRelation(subject=instance, type=rtype2, object=orga1)
        self.assertHaveRelation(subject=instance, type=rtype2, object=orga2)

        # Edition ---
        form3 = form_cls(user=user, instance=instance)
        self.assertNotIn('relation_types', form3.fields)
        self.assertNotIn('semifixed_rtypes', form3.fields)

        form4 = form_cls(
            user=user,
            instance=instance,
            data={
                'user':        user.id,
                'first_name':  'Turtle',
                'last_name':   'Donatello',
                'description': 'Nerd',

                'relation_types': self.formfield_value_multi_relation_entity(
                    (rtype2, orga2),
                ),  # Should not be used
            },
        )
        self.assertTrue(form4.is_valid(), form2.errors)

        edited_instance = form4.save()
        self.assertEqual(4, edited_instance.relations.count())

    def test_form_relations02(self):
        "No semi-fixed available."
        user = self.get_root_user()

        fields_groups = self._build_basic_relations_groups()
        form_cls = fields_groups.form_class()

        formfields = form_cls(user=user).fields
        self.assertIn('relation_types', formfields)
        self.assertNotIn('semifixed_rtypes', formfields)

    def test_form_relations03(self):
        "Forced relationships."
        user = self.get_root_user()

        orga = FakeOrganisation.objects.create(user=user, name='Technodrome')
        rtype = RelationType.objects.builder(
            id='test-subject_leads', predicate='leads',
        ).symmetric(id='test-object_leads', predicate='is lead by').get_or_create()[0]
        forced_relations = [Relation(type=rtype, object_entity=orga)]

        fields_groups = self._build_basic_relations_groups()
        form_cls = fields_groups.form_class()
        form1 = form_cls(user=user, forced_relations=forced_relations)

        formfields = form1.fields
        self.assertIn('relation_types', formfields)
        self.assertNotIn('semifixed_rtypes', formfields)

        info_f = formfields.get('rtypes_info')
        self.assertIsInstance(info_f, forms.CharField)
        self.assertEqual(_('Information on relationships'), info_f.label)
        self.assertHTMLEqual(
            _('This relationship will be added: {predicate} «{entity}»').format(
                predicate=rtype.predicate,
                entity=orga,
            ),
            info_f.initial
        )

        listified_blocks = [*form1.get_blocks()]
        self.assertEqual(2, len(listified_blocks))
        self.assertListEqual(
            ['rtypes_info', 'relation_types'],
            [bfield.name for bfield in listified_blocks[1].bound_fields],
        )

        # ---
        form2 = form_cls(
            user=user,
            forced_relations=forced_relations,
            data={
                'user':       user.id,
                'first_name': 'Krang',
                'last_name':  'BigBrain',
            },
        )
        self.assertFalse(form2.errors)

        instance = form2.save()
        self.assertHaveRelation(subject=instance, type=rtype, object=orga)

    def test_form_relations04(self):
        "Properties constraints."
        user = self.get_root_user()

        ptype = CremePropertyType.objects.create(text='Is bad')

        orga = FakeOrganisation.objects.create(user=user, name='Technodrome')
        rtype = RelationType.objects.builder(
            id='test-subject_leads', predicate='leads', properties=[ptype],
        ).symmetric(id='test-object_leads', predicate='is lead by').get_or_create()[0]

        fields_groups = self._build_basic_relations_groups()
        form_cls = fields_groups.form_class()

        first_name = 'Krang'
        last_name = 'BigBrain'
        form = form_cls(
            user=user,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,

                'relation_types': self.formfield_value_multi_relation_entity((rtype, orga)),
            },
        )
        self.assertFormInstanceErrors(
            form,
            (
                'relation_types',
                Relation.error_messages['missing_subject_property'] % {
                    'entity': FakeContact(last_name=last_name, first_name=first_name),
                    'property': ptype,
                    'predicate': rtype.predicate,
                },
            ),
        )

    def test_form_extra_cells01(self):
        label1 = 'My extra field #1'
        label2 = 'My extra field #2'

        saved_form_ids = set()
        cleaned_form_ids = set()

        class BaseTestSubCell(CustomFormExtraSubCell):
            def __init__(this, model=FakeOrganisation):
                super().__init__(model=model)

        class TestSubCell01(BaseTestSubCell):
            sub_type_id = 'test01'
            verbose_name = 'Weapons'

            def formfield(this, instance, user, **kwargs):
                f = forms.CharField(label=label1, **kwargs)
                f.user = user

                return f

            def post_save_instance(this, *, instance, value, form):
                saved_form_ids.add(id(form))
                instance.description += f'\nWeapons: {value}'

                return True

        class TestSubCell02(BaseTestSubCell):
            sub_type_id = 'test02'
            verbose_name = 'Size'
            is_required = False

            def post_clean_instance(this, *, instance, value, form):
                cleaned_form_ids.add(id(form))
                instance.description += f'Size: {value}'

            def formfield(this, instance, user, **kwargs):
                return forms.IntegerField(label=label2, **kwargs)

        class ExtraCells(EntityCellCustomFormExtra):
            allowed_sub_cell_classes = [TestSubCell01, TestSubCell02]

        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=deepcopy(base_cell_registry).register(ExtraCells),
            data=[{
                'name': 'Main',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                    EntityCellCustomFormExtra(TestSubCell01()),
                    EntityCellCustomFormExtra(TestSubCell02()),
                ],
            }],
        )

        form_class = fields_groups.form_class()
        user = self.get_root_user()
        form1 = form_class(user=user)

        fields = form1.fields
        self.assertIn('name', fields)
        self.assertIn('user', fields)
        self.assertNotIn('phone', fields)

        key1 = f'cform_extra-{TestSubCell01.sub_type_id}'
        key2 = f'cform_extra-{TestSubCell02.sub_type_id}'
        self.assertEqual(key1, form1.subcell_key(TestSubCell01))
        self.assertEqual(key2, form1.subcell_key(TestSubCell02))

        with self.assertNoException():
            my_field1 = fields[key1]
            my_field2 = fields[key2]

        self.assertIsInstance(my_field1, forms.CharField)
        self.assertEqual(label1, my_field1.label)
        self.assertIs(my_field1.required, True)
        self.assertEqual(user, my_field1.user)

        self.assertIsInstance(my_field2, forms.IntegerField)
        self.assertEqual(label2, my_field2.label)
        self.assertIs(my_field2.required, False)

        block_fields = self.get_alone_element(form1.get_blocks()).bound_fields
        self.assertEqual(4, len(block_fields))
        self.assertEqual('user', block_fields[0].name)
        self.assertEqual('name', block_fields[1].name)

        bfield1 = block_fields[2]
        self.assertEqual(key1, bfield1.name)
        self.assertEqual(label1, bfield1.label)

        bfield2 = block_fields[3]
        self.assertEqual(key2, bfield2.name)
        self.assertEqual(label2, bfield2.label)

        # ---
        name = 'Technodrome'
        extra_value1 = 'Laser'
        extra_value2 = 100
        form2 = form_class(
            user=user,
            data={
                'user': user.id,
                'name': name,
                key1: extra_value1,
                key2: extra_value2,
            },
        )
        self.assertFalse(form2.errors)

        orga = self.refresh(form2.save())
        self.assertEqual(name, orga.name)
        self.assertEqual(
            f'Size: {extra_value2}\nWeapons: {extra_value1}',
            orga.description,
        )

        form_ids = {id(form2)}
        self.assertSetEqual(form_ids, saved_form_ids)
        self.assertSetEqual(form_ids, cleaned_form_ids)

    def test_form_extra_cells02(self):
        "Missing required fields."
        class BaseSubCell(CustomFormExtraSubCell):
            def __init__(this, model=FakeOrganisation):
                super().__init__(model=model)

            def formfield(this, instance, user, **kwargs):
                return forms.CharField(label=this.verbose_name, **kwargs)

        class TestSubCell01(BaseSubCell):
            sub_type_id = 'test01'
            verbose_name = 'Weapons'

            def post_clean_instance(this, *, instance, value, form):
                instance.description += 'Weapons: '

            def post_save_instance(this, *, instance, value, form):
                instance.description += value
                return True

        class TestSubCell02(BaseSubCell):
            sub_type_id = 'test02'
            verbose_name = 'Size'
            is_required = False

        class ExtraCells(EntityCellCustomFormExtra):
            allowed_sub_cell_classes = [TestSubCell01, TestSubCell02]

        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            data=[{
                'name': 'Main',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                    # MyCell01(),
                ],
            }],
            cell_registry=deepcopy(base_cell_registry).register(ExtraCells),
        )

        user = self.get_root_user()
        form_class = fields_groups.form_class()
        form1 = form_class(user=user)

        fields = form1.fields
        key1 = f'cform_extra-{TestSubCell01.sub_type_id}'
        self.assertIn(key1, fields)

        self.assertNotIn(f'cform_extra-{TestSubCell02.sub_type_id}', fields)

        blocks = [*form1.get_blocks()]
        self.assertEqual(2, len(blocks))  # There's a special block for missing required

        block = blocks[1]
        self.assertEqual(
            _('Missing required special fields (update your configuration)'),
            block.label,
        )
        self.assertListEqual(
            [key1],
            [bfield.name for bfield in block.bound_fields],
        )

        # ---
        name = 'Technodrome'
        extra_value = 'Laser'
        form2 = form_class(
            user=user,
            data={
                'user': user.id,
                'name': name,
                key1: extra_value,
            },
        )
        self.assertFalse(form2.errors)

        orga = self.refresh(form2.save())
        self.assertEqual(name, orga.name)
        self.assertEqual(f'Weapons: {extra_value}', orga.description)

    def test_form_extra_cells03(self):
        "post_save_instance() returns <False>."

        class TestSubCell(CustomFormExtraSubCell):
            sub_type_id = 'test'
            verbose_name = 'Weapons'

            def formfield(this, instance, user, **kwargs):
                return forms.CharField(label=this.verbose_name, **kwargs)

            def post_save_instance(this, *, instance, value, form):
                instance.description += f'Weapons: {value}'

                return False

        class ExtraCells(EntityCellCustomFormExtra):
            allowed_sub_cell_classes = [TestSubCell]

        extra_cell = TestSubCell(model=FakeOrganisation).into_cell()
        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=deepcopy(base_cell_registry).register(ExtraCells),
            data=[{
                'name': 'Main',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                    extra_cell,
                ],
            }],
        )

        user = self.get_root_user()
        name = 'Technodrome'
        form = fields_groups.form_class()(
            user=user,
            data={
                'user': user.id,
                'name': name,
                extra_cell.key: 'Laser',
            },
        )
        self.assertFalse(form.errors)

        orga = self.refresh(form.save())
        self.assertEqual(name, orga.name)
        self.assertFalse(orga.description)

    def test_form_extra_cells04(self):
        "post_clean_instance() raises ValidationError."
        error_msg = 'On fire!'

        class TestSubCell(CustomFormExtraSubCell):
            sub_type_id = 'test'
            verbose_name = 'Weapons'

            def formfield(this, instance, user, **kwargs):
                return forms.CharField(label=this.verbose_name, **kwargs)

            def post_clean_instance(this, *, instance, value, form):
                raise ValidationError(error_msg)

        class ExtraCells(EntityCellCustomFormExtra):
            allowed_sub_cell_classes = [TestSubCell]

        extra_cell = TestSubCell(model=FakeOrganisation).into_cell()
        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=deepcopy(base_cell_registry).register(ExtraCells),
            data=[{
                'name': 'Main',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                    extra_cell,
                ],
            }],
        )

        user = self.get_root_user()
        form_instance = fields_groups.form_class()(
            user=user,
            data={
                'user': user.id,
                'name': 'Technodrome',
                extra_cell.key: 'Laser',
            },
        )
        self.assertFormInstanceErrors(form_instance, (extra_cell.key, error_msg))

    def test_form_extra_groups01(self):
        logger_user = self.get_root_user()
        group_fname = 'city'

        class AddressGroup(ExtraFieldGroup):
            name = 'Address'
            extra_group_id = 'creme_core-address'

            def formfields(this, instance, user):
                self.assertIsInstance(instance, FakeOrganisation)
                self.assertEqual(logger_user, user)

                yield (
                    f'address__{group_fname}',
                    FakeAddress._meta.get_field(group_fname).formfield(),
                )

            def save(this, form):
                get_data = form.cleaned_data.get
                instance = form.instance
                instance.address = FakeAddress.objects.create(
                    entity=instance,
                    **{group_fname: get_data(f'address__{group_fname}')},
                )

                return True

        corporate_ctxt = {'some': 'data'}

        class CorporateGroup(ExtraFieldGroup):
            name = 'Corporate'
            extra_group_id = 'creme_core-corporate'
            template_name = 'creme_core/generics/blockform/field-block-EXTRA.html'

            def get_context(this):
                return corporate_ctxt

        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=base_cell_registry,
            allowed_extra_group_classes=[AddressGroup, CorporateGroup],
            data=[
                {
                    'name': 'Regular fields',
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                    ],
                },
                AddressGroup(model=FakeOrganisation),
                CorporateGroup(model=FakeOrganisation),
            ],
        )

        form_cls = fields_groups.form_class()

        form1 = form_cls(user=logger_user)

        fields = form1.fields
        self.assertIn('user', fields)
        self.assertIn('name', fields)
        self.assertIn(f'address__{group_fname}', fields)

        blocks = [*form1.get_blocks()]
        self.assertEqual(3, len(blocks))

        block2 = blocks[1]
        self.assertEqual(AddressGroup.name, block2.label)
        self.assertEqual(LAYOUT_REGULAR,    block2.layout)
        self.assertFalse(block2.bound_fields)
        self.assertEqual(
            'creme_core/generics/blockform/field-block.html',
            block2.template_name,
        )
        self.assertFalse(block2.template_context)

        block3 = blocks[2]
        self.assertEqual(CorporateGroup.template_name, block3.template_name)
        self.assertDictEqual(corporate_ctxt, block3.template_context)

        # ---
        city = 'NewYork'
        form2 = form_cls(
            user=logger_user,
            data={
                'user': logger_user.id,
                'name': 'Technodrome',

                f'address__{group_fname}': city,
            },
        )
        self.assertFalse(form2.errors)

        orga = self.refresh(form2.save())
        address = orga.address
        self.assertIsInstance(address, FakeAddress)
        self.assertEqual(city, address.city)

    def test_form_extra_groups02(self):
        "clean() method + error."
        user = self.get_root_user()
        error_msg = 'Error caused by the extra group'

        class AddressGroup(ExtraFieldGroup):
            name = 'Address'
            extra_group_id = 'address'

            def clean(this, form):
                form.add_error('user', error_msg)

        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=base_cell_registry,
            allowed_extra_group_classes=[AddressGroup],
            data=[
                {
                    'name': 'Regular fields',
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                    ],
                },
                AddressGroup(model=FakeOrganisation),
            ],
        )
        self.assertFormInstanceErrors(
            fields_groups.form_class()(
                user=user,
                data={
                    'user': user.id,
                    'name': 'Technodrome',
                },
            ),
            ('user', error_msg)
        )

    def test_form_extra_groups03(self):
        "save() returns <False>."
        user = self.get_root_user()

        class AddressGroup(ExtraFieldGroup):
            name = 'Address'
            extra_group_id = 'address'

            def save(this, form):
                form.instance.description = 'A string'
                return False

        fields_groups = FieldGroupList.from_cells(
            model=FakeOrganisation,
            cell_registry=base_cell_registry,
            allowed_extra_group_classes=[AddressGroup],
            data=[
                {
                    'name': 'Regular fields',
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                    ],
                },
                AddressGroup(model=FakeOrganisation),
            ],
        )
        form2 = fields_groups.form_class()(
            user=user,
            data={
                'user': user.id,
                'name': 'Technodrome',
            },
        )
        self.assertFalse(form2.errors)
        self.assertFalse(self.refresh(form2.save()).description)


class CustomFormDefaultTestCase(CremeTestCase):
    def test_creation_type(self):
        form_desc = CustomFormDescriptor(
            id='creme_core-fakecontact_creation',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )

        cfd = CustomFormDefault(descriptor=form_desc)
        groups_desc = cfd.groups_desc()
        self.assertIsList(groups_desc, length=5)

        # self.maxDiff = None
        self.assertDictEqual(
            {
                'name': _('General information'),
                'layout': LAYOUT_DUAL_FIRST,
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    ),
                ],
            },
            groups_desc[0],
        )
        self.assertDictEqual(
            {
                'name': _('Description'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [(EntityCellRegularField, {'name': 'description'})],
            },
            groups_desc[1],
        )
        self.assertDictEqual(
            {
                'name': _('Description'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [(EntityCellRegularField, {'name': 'description'})],
            },
            groups_desc[1],
        )
        self.assertDictEqual(
            {
                'name': _('Custom fields'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [(
                    EntityCellCustomFormSpecial,
                    {'name': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS},
                )],
            },
            groups_desc[2],
        )
        self.assertDictEqual(
            {
                'name': _('Properties'),
                'cells': [(
                    EntityCellCustomFormSpecial,
                    {'name': EntityCellCustomFormSpecial.CREME_PROPERTIES},
                )],
            },
            groups_desc[3],
        )
        self.assertDictEqual(
            {
                'name': _('Relationships'),
                'cells': [(
                    EntityCellCustomFormSpecial,
                    {'name': EntityCellCustomFormSpecial.RELATIONS},
                )],
            },
            groups_desc[4],
        )

    def test_edition_type(self):
        form_desc = CustomFormDescriptor(
            id='creme_core-fakecontact_edition',
            model=FakeContact,
            form_type=CustomFormDescriptor.EDITION_FORM,
            verbose_name='Edition form for FakeContact',
        )

        cfd = CustomFormDefault(descriptor=form_desc)

        self.assertListEqual(
            [
                _('General information'),
                _('Description'),
                _('Custom fields'),
                # _('Properties'),
                # _('Relationships'),
            ],
            [d.get('name') for d in cfd.groups_desc()],
        )

    def test_fields(self):
        form_desc = CustomFormDescriptor(
            id='creme_core-fakecontact_creation',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )

        cfd = CustomFormDefault(descriptor=form_desc)
        self.assertDictEqual(
            {
                'name': _('General information'),
                'layout': LAYOUT_DUAL_FIRST,
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    ),
                ],
            },
            cfd.groups_desc()[0],
        )

    def test_main_fields(self):
        form_desc = CustomFormDescriptor(
            id='creme_core-fakecontact_creation',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )

        class MyCustomFormDefault(CustomFormDefault):
            main_fields = ['user', 'first_name', 'last_name']

        cfd = MyCustomFormDefault(descriptor=form_desc)
        self.assertDictEqual(
            {
                'name': _('General information'),
                'layout': LAYOUT_DUAL_FIRST,
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'first_name'}),
                    (EntityCellRegularField, {'name': 'last_name'}),
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    ),
                ],
            },
            cfd.groups_desc()[0],
        )


class CustomFormDescriptorTestCase(CremeTestCase):
    def test_init(self):
        id_value1 = 'creme_core-fakecontact_creation'
        verbose_name1 = 'Creation form for FakeContact'

        form_desc1 = CustomFormDescriptor(
            id=id_value1,
            model=FakeContact,
            verbose_name=verbose_name1,
        )
        self.assertEqual(id_value1, form_desc1.id)
        self.assertIs(FakeContact, form_desc1.model)
        self.assertEqual(CustomFormDescriptor.CREATION_FORM, form_desc1.form_type)
        self.assertEqual(verbose_name1, form_desc1.verbose_name)
        self.assertIs(CremeEntityForm, form_desc1.base_form_class)
        self.assertListEqual([], [*form_desc1.excluded_fields])
        self.assertListEqual([], [*form_desc1.extra_sub_cells])
        self.assertListEqual([], [*form_desc1.extra_group_classes])
        self.assertListEqual(
            [
                _('General information'),
                _('Description'),
                _('Custom fields'),
                _('Properties'),
                _('Relationships'),
            ],
            [d.get('name') for d in form_desc1.default_groups_desc],
        )

        registry1 = form_desc1.build_cell_registry()
        self.assertIsInstance(registry1, EntityCellRegistry)
        self.assertIsNot(registry1, CustomFormDescriptor.base_cell_registry)
        cell_classes1 = {*registry1.cell_classes}
        self.assertIn(EntityCellRegularField, cell_classes1)
        self.assertIn(EntityCellCustomField,  cell_classes1)
        self.assertIn(EntityCellCustomFormSpecial,  cell_classes1)

        extra_class1 = registry1[EntityCellCustomFormExtra.type_id]
        self.assertIsSubclass(extra_class1, EntityCellCustomFormExtra)
        self.assertIsNot(extra_class1, EntityCellCustomFormExtra)
        self.assertListEqual([], extra_class1.allowed_sub_cell_classes)

        # ---
        class TestBaseForm(CremeEntityForm):
            pass

        class TestSubCell1(CustomFormExtraSubCell):
            sub_type_id = 'test01'

        class TestSubCell2(CustomFormExtraSubCell):
            sub_type_id = 'test02'

        id_value2 = 'creme_core-fakeorga_creation'
        verbose_name2 = 'Creation form for FakeOrganisation'

        default_groups_desc2 = [
            {
                'name': 'General',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                    (EntityCellRegularField, {'name': 'description'}),
                ],
            },
        ]

        class FakeOrgaFormDefault(CustomFormDefault):
            def groups_desc(this, fields=()):
                return default_groups_desc2

        form_desc2 = CustomFormDescriptor(
            id=id_value2,
            model=FakeOrganisation,
            verbose_name=verbose_name2,
            form_type=CustomFormDescriptor.EDITION_FORM,
            base_form_class=TestBaseForm,
            excluded_fields=['name'],
            extra_sub_cells=[
                TestSubCell1(model=FakeOrganisation),
                TestSubCell2(model=FakeOrganisation),
            ],
            default=FakeOrgaFormDefault,
        )
        self.assertEqual(id_value2, form_desc2.id)
        self.assertIs(FakeOrganisation, form_desc2.model)
        self.assertEqual(verbose_name2, form_desc2.verbose_name)
        self.assertIs(TestBaseForm, form_desc2.base_form_class)
        self.assertListEqual(['name'], [*form_desc2.excluded_fields])
        self.assertListEqual(
            [TestSubCell1(model=FakeOrganisation), TestSubCell2(model=FakeOrganisation)],
            [*form_desc2.extra_sub_cells],
        )
        self.assertListEqual(
            default_groups_desc2,
            form_desc2.default_groups_desc,
        )

        registry2 = form_desc2.build_cell_registry()
        self.assertListEqual(
            [TestSubCell1, TestSubCell2],
            registry2[EntityCellCustomFormExtra.type_id].allowed_sub_cell_classes
        )

    def test_property_excluded_fields(self):
        form_desc = CustomFormDescriptor(
            id='creme_core-fakecontact_creation',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )

        form_desc.excluded_fields = ('user', 'last_name')
        self.assertListEqual(['user', 'last_name'], [*form_desc.excluded_fields])

        with self.assertRaises(FieldDoesNotExist):
            form_desc.excluded_fields = ('invalid',)

    def test_property_form_types(self):
        form_desc = CustomFormDescriptor(
            id='creme_core-fakecontact_creation',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )

        with self.assertRaises(ValueError):
            form_desc.form_type = 3

    def test_property_extra_sub_cells(self):
        form_desc = CustomFormDescriptor(
            id='creme_core-fakecontact_creation',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )

        class BaseTestSubCell(CustomFormExtraSubCell):
            def __init__(self):
                super().__init__(model=FakeContact)

        class TestSubCell1(BaseTestSubCell):
            sub_type_id = 'test01'

        class TestSubCell2(BaseTestSubCell):
            sub_type_id = 'test02'

        form_desc.extra_sub_cells = (TestSubCell1(), TestSubCell2())
        self.assertListEqual([TestSubCell1(), TestSubCell2()], [*form_desc.extra_sub_cells])

        # Must inherit CustomFormExtraSubCell ---
        class InvalidClass01:
            sub_type_id = 'invalid'

        with self.assertRaises(ValueError) as cm:
            form_desc.extra_sub_cells = (InvalidClass01(),)

        self.assertIn(
            "is not an instance of <CustomFormExtraSubCell>.",
            str(cm.exception),
        )

        # Type_id must be set ---
        class InvalidClass02(CustomFormExtraSubCell):
            # sub_type_id = '...'
            pass

        with self.assertRaises(ValueError) as cm:
            form_desc.extra_sub_cells = (InvalidClass02(model=FakeContact),)

        self.assertEqual(
            "CustomFormDescriptor.extra_cells: <InvalidClass02> has no sub_type_id.",
            str(cm.exception),
        )

    def test_property_extra_groups(self):
        class AddressGroup(ExtraFieldGroup):
            pass

        form_desc = CustomFormDescriptor(
            id='creme_core-fakecontact_creation',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
            extra_group_classes=[AddressGroup],
        )
        self.assertListEqual([AddressGroup], [*form_desc.extra_group_classes])

        class FooGroup(FieldGroup):
            pass

        class BarGroup(FieldGroup):
            pass

        form_desc.extra_group_classes = (FooGroup, BarGroup)
        self.assertListEqual([FooGroup, BarGroup], [*form_desc.extra_group_classes])

    def test_groups01(self):
        form_desc = CustomFormDescriptor(
            id='creme_core-tests_fakecontact',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )

        group_name = 'General'
        cfci = CustomFormConfigItem.objects.create_if_needed(
            descriptor=form_desc,
            groups_desc=[{
                'name': group_name,
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'last_name'}),
                    (EntityCellRegularField, {'name': 'first_name'}),
                ],
            }],
        )

        groups = form_desc.groups(item=cfci)

        self.assertIsInstance(groups, FieldGroupList)
        self.assertEqual(FakeContact, groups.model)

        group = self.get_alone_element(groups)
        self.assertEqual(group_name, group.name)
        self.assertEqual(LAYOUT_REGULAR, group.layout)
        self.assertListEqual(
            [
                EntityCellRegularField.build(model=FakeContact, name=name)
                for name in ('user', 'last_name', 'first_name')
            ],
            [*group.cells],
        )

    def test_groups02(self):
        "Other model, several groups, layout, extra_cells."
        class BaseTestSubCell(CustomFormExtraSubCell):
            def __init__(self, model=FakeOrganisation):
                super().__init__(model=model)

            def formfield(self, instance, *args, **kwargs):
                return forms.CharField(label='Extra field', *args, **kwargs)

        class TestSubCell1(BaseTestSubCell):
            sub_type_id = 'test01'

        class TestSubCell2(BaseTestSubCell):
            sub_type_id = 'test02'

        form_desc = CustomFormDescriptor(
            id='creme_core-tests_fakeorga',
            model=FakeOrganisation,
            verbose_name='Creation form for FakeOrganisation',
            excluded_fields=['user'],
            extra_sub_cells=[TestSubCell1(), TestSubCell2()],
        )

        group_name1 = 'General'
        group_name2 = 'Details'
        cfci = CustomFormConfigItem.objects.create_if_needed(
            descriptor=form_desc,
            groups_desc=[
                {
                    'name': group_name1,
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                    ],
                }, {
                    'name': group_name2,
                    'layout': LAYOUT_DUAL_SECOND,
                    'cells': [
                        (EntityCellRegularField, {'name': 'email'}),
                        TestSubCell1().into_cell(),
                        TestSubCell2().into_cell(),
                    ],
                },
            ],
        )

        with self.assertNumQueries(0):
            groups = form_desc.groups(cfci)

        self.assertIsInstance(groups, FieldGroupList)
        self.assertEqual(2, len(groups))
        self.assertEqual(FakeOrganisation, groups.model)

        group1 = groups[0]
        self.assertEqual(group_name1, group1.name)
        self.assertEqual(LAYOUT_DUAL_FIRST, group1.layout)
        self.assertListEqual(
            [
                EntityCellRegularField.build(model=FakeOrganisation, name=name)
                for name in ('user', 'name')
            ],
            [*group1.cells],
        )

        group2 = groups[1]
        self.assertEqual(group_name2, group2.name)
        self.assertEqual(LAYOUT_DUAL_SECOND, group2.layout)

        # NB: we cannot compare cells directly because extra cells use an odd inner class
        self.assertListEqual(
            [
                EntityCellRegularField.build(model=FakeOrganisation, name='email').key,
                TestSubCell1().into_cell().key,
                TestSubCell2().into_cell().key,
            ],
            [c.key for c in group2.cells],
        )

    def test_groups03(self):
        "With extra groups."
        class AddressGroup(ExtraFieldGroup):
            extra_group_id = 'creme_core-address'

        class CorporateGroup(ExtraFieldGroup):
            extra_group_id = 'creme_core-corporate'

        form_desc = CustomFormDescriptor(
            id='creme_core-tests_fakecontact',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
            extra_group_classes=[AddressGroup, CorporateGroup],
        )

        group_name = 'General'
        cfci = CustomFormConfigItem.objects.create_if_needed(
            descriptor=form_desc,
            groups_desc=[
                {
                    'name': group_name,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'last_name'}),
                        (EntityCellRegularField, {'name': 'first_name'}),
                    ],
                },
                AddressGroup(model=FakeContact),
                CorporateGroup(model=FakeContact, layout=LAYOUT_DUAL_FIRST),
            ],
        )

        groups = form_desc.groups(item=cfci)
        self.assertEqual(3, len(groups))

        self.assertEqual(group_name, groups[0].name)

        group2 = groups[1]
        self.assertIsInstance(group2, AddressGroup)
        self.assertEqual(LAYOUT_REGULAR, group2.layout)

        group3 = groups[2]
        self.assertIsInstance(group3, CorporateGroup)
        self.assertEqual(LAYOUT_DUAL_FIRST, group3.layout)

    def test_form_class01(self):
        user = self.get_root_user()
        form_desc = CustomFormDescriptor(
            id='creme_core-tests_fakecontact',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )

        cfci = CustomFormConfigItem.objects.create_if_needed(
            descriptor=form_desc,
            groups_desc=[{
                'name': 'General',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'last_name'}),
                    (EntityCellRegularField, {'name': 'first_name'}),
                ],
            }],
        )

        with self.assertNumQueries(1):  # CustomFields
            form_cls = form_desc.build_form_class(cfci)

        self.assertIsSubclass(form_cls, CremeEntityForm)

        fields = form_cls(user=user).fields
        self.assertIn('user',       fields)
        self.assertIn('last_name',  fields)
        self.assertIn('first_name', fields)

        self.assertNotIn('description', fields)

    def test_form_class02(self):
        "Base class, excluded fields, extra cells."
        class TestBaseForm(CremeEntityForm):
            pass

        class BaseTestSubCell(CustomFormExtraSubCell):
            def __init__(self, model=FakeContact):
                super().__init__(model=model)

            def formfield(self, instance, user, **kwargs):
                return forms.CharField(label='Extra field', **kwargs)

        class TestSubCell1(BaseTestSubCell):
            sub_type_id = 'test01'

        class TestSubCell2(BaseTestSubCell):
            sub_type_id = 'test02'

        user = self.get_root_user()
        form_desc = CustomFormDescriptor(
            id='creme_core-tests_fakecontact',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
            base_form_class=TestBaseForm,
            excluded_fields=['user'],
            extra_sub_cells=[TestSubCell1(), TestSubCell2()],
        )

        cfci = CustomFormConfigItem.objects.create_if_needed(
            descriptor=form_desc,
            groups_desc=[{
                'name': 'General',
                'cells': [
                    # (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'last_name'}),
                    (EntityCellRegularField, {'name': 'first_name'}),
                    TestSubCell1().into_cell(),
                    TestSubCell2().into_cell(),
                ],
            }],
        )
        with self.assertNumQueries(1):  # CustomFields
            form_cls = form_desc.build_form_class(cfci)

        self.assertIsSubclass(form_cls, TestBaseForm)

        fields = form_cls(user=user).fields
        self.assertIn('last_name',  fields)
        self.assertIn('first_name', fields)
        self.assertNotIn('user', fields)

        self.assertIn(f'cform_extra-{TestSubCell1.sub_type_id}', fields)
        self.assertIn(f'cform_extra-{TestSubCell2.sub_type_id}', fields)

    def test_registry01(self):
        form_desc1 = CustomFormDescriptor(
            id='creme_core-fakecontact_creation',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )
        form_desc2 = CustomFormDescriptor(
            id='creme_core-fakecontact_edition',
            model=FakeContact,
            verbose_name='Edition form for FakeContact',
        )
        form_desc3 = CustomFormDescriptor(
            id='creme_core-fakeorga_creation',
            model=FakeOrganisation,
            verbose_name='Creation form for FakeOrganisation',
        )

        registry = CustomFormDescriptorRegistry()
        registry.register(form_desc1, form_desc3).register(form_desc2)

        self.assertEqual(form_desc1, registry.get(form_desc1.id))
        self.assertEqual(form_desc2, registry.get(form_desc2.id))
        self.assertEqual(form_desc3, registry.get(form_desc3.id))

        self.assertCountEqual([form_desc1, form_desc2, form_desc3], registry)

        # --
        registry.unregister(form_desc1, form_desc3)
        self.assertListEqual([form_desc2], [*registry])

        with self.assertRaises(CustomFormDescriptorRegistry.UnRegistrationError) as cm:
            registry.unregister(form_desc2, form_desc3)
        self.assertEqual(
            f"Invalid CustomFormDescriptor's id (already unregistered?): {form_desc3.id}",
            str(cm.exception),
        )

    def test_registry02(self):
        "ID collision."
        form_desc1 = CustomFormDescriptor(
            id='creme_core-fakecontact_creation',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )
        form_desc2 = CustomFormDescriptor(
            id=form_desc1.id,  # <===
            model=FakeContact,
            verbose_name='Edition form for FakeContact',
        )

        registry = CustomFormDescriptorRegistry()

        with self.assertRaises(CustomFormDescriptorRegistry.RegistrationError) as cm:
            registry.register(form_desc1, form_desc2)
        self.assertEqual(
            f"Duplicated CustomFormDescriptor's id: {form_desc1.id}",
            str(cm.exception),
        )
