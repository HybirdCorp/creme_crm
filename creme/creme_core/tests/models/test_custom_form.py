# -*- coding: utf-8 -*-

from functools import partial

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils.translation import gettext as _

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
from creme.creme_core.models import (
    CustomField,
    FakeContact,
    FakeOrganisation,
    UserRole,
)
from creme.creme_core.models.custom_form import (
    CustomFormConfigItem,
    CustomFormConfigItemManager,
)

from ..base import CremeTestCase
from ..fake_custom_forms import FAKEACTIVITY_CREATION_CFORM


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
        # self.assertEqual(desc.id, cfci.cform_id)
        self.assertEqual(desc.id, cfci.descriptor_id)
        # self.assertEqual(desc.id, cfci.pk)
        self.assertIsNone(cfci.role)
        self.assertIs(cfci.superuser, False)
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
        "Other model, other fields, layout, super-user."
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
        # self.assertEqual(desc.id, cfci.cform_id)
        self.assertEqual(desc.id, cfci.descriptor_id)
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
            cfci.groups_as_dicts(),
        )

    def test_create_if_needed03(self):
        "No overriding."
        desc = CustomFormDescriptor(
            id='creme_core-fakecontact',
            model=FakeContact,
            verbose_name='Creation form for FakeContact',
        )

        mngr = CustomFormConfigItemManager()
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

    def test_create_if_needed04(self):
        "Super-user."
        desc = CustomFormDescriptor(
            id='creme_core-tests_fakeorga',
            model=FakeOrganisation,
            verbose_name='Creation form for FakeOrganisation',
        )

        mngr = CustomFormConfigItemManager()
        mngr.model = CustomFormConfigItem

        group_name = 'Regular fields'
        groups_desc = [
            {
                'name': group_name,
                'layout': LAYOUT_DUAL_FIRST,
                'cells': [
                    (EntityCellRegularField, {'name': 'name'}),
                    (EntityCellRegularField, {'name': 'description'}),
                ],
            },
        ]

        # Default Item
        mngr.create_if_needed(
            descriptor=desc,
            groups_desc=[
                {
                    'name': group_name,
                    'cells': [(EntityCellRegularField, {'name': 'name'})],
                },
            ],
        )

        cfci01 = mngr.create_if_needed(
            descriptor=desc,
            groups_desc=groups_desc,
            role='superuser',
        )
        self.assertEqual(desc.id, cfci01.descriptor_id)
        self.assertIsNone(cfci01.role)
        self.assertTrue(cfci01.superuser)

        groups_as_dict = [
            {
                'name': group_name,
                'layout': LAYOUT_DUAL_FIRST,
                'cells': [
                    {'type': 'regular_field', 'value': 'name'},
                    {'type': 'regular_field', 'value': 'description'},
                ],
            },
        ]
        self.assertListEqual(groups_as_dict, cfci01.groups_as_dicts())

        # No overriding ---
        groups_desc[0]['cells'] = [
            (EntityCellRegularField, {'name': 'name'}),
            (EntityCellRegularField, {'name': 'phone'}),
        ]
        cfci02 = mngr.create_if_needed(
            descriptor=desc,
            groups_desc=groups_desc,
            role='superuser',
        )
        self.assertEqual(cfci01.id, cfci02.id)
        self.assertEqual(desc.id, cfci02.descriptor_id)
        self.assertIsNone(cfci02.role)
        self.assertTrue(cfci02.superuser)
        self.assertListEqual(groups_as_dict, cfci02.groups_as_dicts())

    def test_create_if_needed05(self):
        "Role."
        desc = CustomFormDescriptor(
            id='creme_core-tests_fakeorga',
            model=FakeOrganisation,
            verbose_name='Creation form for FakeOrganisation',
        )

        role = UserRole.objects.create(name='CEO')

        mngr = CustomFormConfigItemManager()
        mngr.model = CustomFormConfigItem

        group_name = 'Regular fields'
        groups_desc = [
            {
                'name': group_name,
                'layout': LAYOUT_DUAL_FIRST,
                'cells': [
                    (EntityCellRegularField, {'name': 'name'}),
                    (EntityCellRegularField, {'name': 'description'}),
                ],
            },
        ]

        # Default Item
        mngr.create_if_needed(
            descriptor=desc,
            groups_desc=[
                {
                    'name': group_name,
                    'cells': [(EntityCellRegularField, {'name': 'name'})],
                },
            ],
        )

        cfci01 = mngr.create_if_needed(
            descriptor=desc,
            groups_desc=groups_desc,
            role=role,
        )
        self.assertEqual(desc.id, cfci01.descriptor_id)
        self.assertEqual(role, cfci01.role)
        self.assertFalse(cfci01.superuser)

        groups_as_dict = [
            {
                'name': group_name,
                'layout': LAYOUT_DUAL_FIRST,
                'cells': [
                    {'type': 'regular_field', 'value': 'name'},
                    {'type': 'regular_field', 'value': 'description'},
                ],
            },
        ]
        self.assertListEqual(groups_as_dict, cfci01.groups_as_dicts())

        # No overriding ---
        groups_desc[0]['cells'] = [
            (EntityCellRegularField, {'name': 'name'}),
            (EntityCellRegularField, {'name': 'phone'}),
        ]
        cfci02 = mngr.create_if_needed(
            descriptor=desc,
            groups_desc=groups_desc,
            role=role,
        )
        self.assertEqual(cfci01.id, cfci02.id)
        self.assertEqual(desc.id, cfci02.descriptor_id)
        self.assertEqual(role, cfci02.role)
        self.assertFalse(cfci02.superuser)
        self.assertListEqual(groups_as_dict, cfci01.groups_as_dicts())

    def test_get_for_user01(self):
        "No item for role."
        user = self.login()

        with self.assertNoException():
            cfci01 = CustomFormConfigItem.objects.get_for_user(
                descriptor=FAKEACTIVITY_CREATION_CFORM,
                user=user,
            )

        self.assertIsInstance(cfci01, CustomFormConfigItem)
        self.assertEqual(FAKEACTIVITY_CREATION_CFORM.id, cfci01.descriptor_id)
        self.assertIsNone(cfci01.role)
        self.assertIs(cfci01.superuser, False)

        # ---
        with self.assertNoException():
            cfci02 = CustomFormConfigItem.objects.get_for_user(
                descriptor=FAKEACTIVITY_CREATION_CFORM,
                user=self.other_user,
            )

        self.assertEqual(cfci01.id, cfci02.id)

        # ---
        with self.assertRaises(CustomFormConfigItem.DoesNotExist):
            CustomFormConfigItem.objects.get_for_user(
                descriptor=CustomFormDescriptor(
                    id='creme_core-test_invalid',
                    model=FakeContact,
                    verbose_name='Invalid form for FakeContact',
                ),
                user=user,
            )

    def test_get_for_user02(self):
        "Super-user's form & role's form."
        user = self.login()
        role2 = UserRole.objects.create(name='CEO')

        desc = FAKEACTIVITY_CREATION_CFORM
        default_cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=desc.id, role=None, superuser=False,
        )

        create_cfci = partial(CustomFormConfigItem.objects.create, descriptor_id=desc.id)
        super_cfci = create_cfci(role=None, superuser=True)
        create_cfci(role=role2, superuser=False)

        with self.assertNoException():
            cfci01 = CustomFormConfigItem.objects.get_for_user(
                descriptor=FAKEACTIVITY_CREATION_CFORM,
                user=user,
            )
        self.assertEqual(super_cfci.id, cfci01.id)

        # ---
        other_user = self.other_user

        with self.assertNoException():
            cfci02 = CustomFormConfigItem.objects.get_for_user(
                descriptor=FAKEACTIVITY_CREATION_CFORM,
                user=other_user,
            )

        self.assertEqual(default_cfci.id, cfci02.id)

        # ---
        role1_cfci = create_cfci(role=other_user.role, superuser=False)

        with self.assertNoException():
            cfci03 = CustomFormConfigItem.objects.get_for_user(
                descriptor=FAKEACTIVITY_CREATION_CFORM,
                user=other_user,
            )

        self.assertEqual(role1_cfci.id, cfci03.id)

    def test_get_for_user03(self):
        "Descriptor ID passed."
        user = self.login()
        desc_id = FAKEACTIVITY_CREATION_CFORM.id

        with self.assertNoException():
            cfci01 = CustomFormConfigItem.objects.get_for_user(descriptor=desc_id, user=user)

        self.assertIsInstance(cfci01, CustomFormConfigItem)
        self.assertEqual(desc_id, cfci01.descriptor_id)
        self.assertIsNone(cfci01.role)
        self.assertIs(cfci01.superuser, False)


class CustomFormConfigItemTestCase(CremeTestCase):
    def test_uniqueness(self):
        role = UserRole.objects.create(name='Basic')
        kwargs = {
            'descriptor_id': FAKEACTIVITY_CREATION_CFORM.id,
            'role': role,
            'superuser': False,
        }
        CustomFormConfigItem.objects.create(**kwargs)

        cfci02 = CustomFormConfigItem(**kwargs)

        with self.assertRaises(ValidationError) as cm1:
            cfci02.full_clean()

        self.assertDictEqual(
            {
                '__all__': [
                    _('%(model_name)s with this %(field_labels)s already exists.') % {
                        'model_name': _('Custom form'),
                        'field_labels': f"{_('Type of form')} {_('and')} {_('Related role')}",
                    }
                ],
            },
            cm1.exception.message_dict,
        )

        with self.assertRaises(IntegrityError):
            cfci02.save()

    # TODO: when uniqueness with None values for role ar not skipped
    # def test_uniqueness02(self):
    #     kwargs = {
    #         'descriptor_id': FAKEACTIVITY_CREATION_CFORM.id,
    #         'role': None,
    #         'superuser': False,
    #     }
    #     ...

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
