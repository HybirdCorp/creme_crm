# -*- coding: utf-8 -*-

from functools import partial

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellRegularField,
)
from creme.creme_core.forms.base import (
    LAYOUT_DUAL_FIRST,
    LAYOUT_DUAL_SECOND,
    LAYOUT_REGULAR,
)
from creme.creme_core.gui.custom_form import (
    CustomFormDescriptor,
    FieldGroup,
    FieldGroupList,
    base_cell_registry,
)
from creme.creme_core.models import CustomField, FakeContact, FakeOrganisation
from creme.creme_core.models.custom_form import (
    CustomFormConfigItem,
    CustomFormConfigItemManager,
)

from ..base import CremeTestCase


class CustomFormConfigItemManagerTestCase(CremeTestCase):
    def test_create_if_needed01(self):
        desc = CustomFormDescriptor(
            id='creme_core-fakecontact',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )

        mngr = CustomFormConfigItemManager()
        self.assertIsNone(mngr.model)
        mngr.model = CustomFormConfigItem

        group_name = 'General'
        cfci = mngr.create_if_needed(
            descriptor=desc,
            groups_desc=[{
                'name': group_name,
                'cells': [
                    EntityCellRegularField.build(model=FakeContact, name='first_name'),
                    (EntityCellRegularField, {'name': 'last_name'}),
                ],
            }],
        )
        self.assertIsInstance(cfci, CustomFormConfigItem)
        self.assertEqual(desc.id, cfci.cform_id)
        self.assertEqual(desc.id, cfci.pk)
        self.assertListEqual(
            [
                {
                    'name': group_name,
                    'layout': LAYOUT_REGULAR,
                    'cells': [
                        {'type': 'regular_field', 'value': 'first_name'},
                        {'type': 'regular_field', 'value': 'last_name'},
                    ],
                },
            ],
            self.refresh(cfci).groups_as_dicts(),
        )

    def test_create_if_needed02(self):
        "Other model, other fields, layout."
        customfield = CustomField.objects.create(
            name='Rate', field_type=CustomField.INT, content_type=FakeOrganisation,
        )

        desc = CustomFormDescriptor(
            id='creme_core-tests_fakeorga',
            model=FakeOrganisation,
            verbose_name='Creation form for FakeOrganisation',
        )

        mngr = CustomFormConfigItemManager()
        mngr.model = CustomFormConfigItem

        group_name1 = 'Regular fields'
        group_name2 = 'Custom fields'

        cfci = mngr.create_if_needed(
            descriptor=desc,
            groups_desc=[
                {
                    'name': group_name1,
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'name'}),
                    ],
                }, {
                    'name': group_name2,
                    'layout': LAYOUT_DUAL_SECOND,
                    'cells': [
                        EntityCellCustomField(customfield=customfield),
                    ],
                },
            ],
        )
        self.assertEqual(desc.id, cfci.cform_id)
        self.assertListEqual(
            [
                {
                    'name': group_name1,
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [{'type': 'regular_field', 'value': 'name'}],
                }, {
                    'name': group_name2,
                    'layout': LAYOUT_DUAL_SECOND,
                    'cells': [{'type': 'custom_field', 'value': str(customfield.id)}],
                },
            ],
            self.refresh(cfci).groups_as_dicts(),
        )

    def test_create_if_needed03(self):
        "No overriding."
        desc = CustomFormDescriptor(
            id='creme_core-fakecontact',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )

        mngr = CustomFormConfigItemManager()
        self.assertIsNone(mngr.model)
        mngr.model = CustomFormConfigItem

        group_name = 'General'
        groups_desc = [{
            'name': group_name,
            'cells': [
                (EntityCellRegularField, {'name': 'last_name'}),
                (EntityCellRegularField, {'name': 'first_name'}),
            ],
        }]

        mngr.create_if_needed(
            descriptor=desc,
            groups_desc=groups_desc,
        )

        groups_desc[0]['cells'] = [(EntityCellRegularField, {'name': 'last_name'})]
        cfci = mngr.create_if_needed(descriptor=desc, groups_desc=groups_desc)
        self.assertListEqual(
            [
                {
                    'name': group_name,
                    'layout': LAYOUT_REGULAR,
                    'cells': [
                        {'type': 'regular_field', 'value': 'last_name'},
                        {'type': 'regular_field', 'value': 'first_name'},
                    ],
                },
            ],
            self.refresh(cfci).groups_as_dicts(),
        )


class CustomFormConfigItemTestCase(CremeTestCase):
    def test_json(self):
        cfci = CustomFormConfigItem()

        group_name1 = 'Main'
        group_name2 = 'Details'
        build_cell = partial(EntityCellRegularField.build, model=FakeContact)
        cfci.store_groups(
            FieldGroupList(
                model=FakeContact,
                cell_registry=base_cell_registry,
                groups=[
                    FieldGroup(
                        name=group_name1,
                        cells=(
                            build_cell(name='user'),
                            build_cell(name='description'),
                        ),
                    ),
                    FieldGroup(
                        name=group_name2,
                        layout=LAYOUT_DUAL_FIRST,
                        cells=(
                            build_cell(name='first_name'),
                            build_cell(name='last_name'),
                        ),
                    ),
                ]
            )
        )
        cfci.save()
        self.assertListEqual(
            [
                {
                    'name': group_name1,
                    'layout': LAYOUT_REGULAR,
                    'cells': [
                        {'type': 'regular_field', 'value': 'user'},
                        {'type': 'regular_field', 'value': 'description'},
                    ],
                }, {
                    'name': group_name2,
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        {'type': 'regular_field', 'value': 'first_name'},
                        {'type': 'regular_field', 'value': 'last_name'},
                    ],
                },
            ],
            self.refresh(cfci).groups_as_dicts(),
        )
