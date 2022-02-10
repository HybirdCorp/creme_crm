# -*- coding: utf-8 -*-

from functools import partial
from json import loads as json_load

from django.contrib.contenttypes.models import ContentType
from django.forms import IntegerField
from django.urls import NoReverseMatch, reverse
# from django.utils.html import escape
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_config.forms.custom_form import (
    CFormCellExtraFieldsField,
    CustomFormCellsField,
)
from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
    EntityCellsRegistry,
)
from creme.creme_core.forms import (
    LAYOUT_DUAL_FIRST,
    LAYOUT_DUAL_SECOND,
    LAYOUT_REGULAR,
)
from creme.creme_core.gui.custom_form import (
    CustomFormDescriptor,
    CustomFormDescriptorRegistry,
    CustomFormExtraSubCell,
    EntityCellCustomFormExtra,
    EntityCellCustomFormSpecial,
    FieldGroup,
    FieldGroupList,
)
from creme.creme_core.models import (
    BrickState,
    CustomField,
    CustomFormConfigItem,
    FakeActivity,
    FakeOrganisation,
    FieldsConfig,
    UserRole,
)
from creme.creme_core.tests import fake_forms
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_custom_forms import (
    FAKEACTIVITY_CREATION_CFORM,
    FAKEACTIVITY_EDITION_CFORM,
    FAKEORGANISATION_CREATION_CFORM,
)
from creme.creme_core.tests.fake_forms import FakeAddressGroup
from creme.creme_core.tests.forms.test_entity_cell import (
    EntityCellsFieldTestCaseMixin,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from .. import bricks
from ..bricks import CustomFormsBrick
from ..constants import BRICK_STATE_SHOW_CFORMS_DETAILS


class CustomFormCellsFieldTestCase(EntityCellsFieldTestCaseMixin, CremeTestCase):
    def test_regularfields01(self):
        field = CustomFormCellsField(model=FakeOrganisation)
        self.assertListEqual([], field.non_hiddable_cells)

        choices = self._find_sub_widget(field, 'regular_field').choices
        fname1 = 'user'
        value = f'regular_field-{fname1}'
        self.assertCellInChoices(value, choices=choices)

        self.assertCellNotInChoices('regular_field-created',        choices=choices)
        self.assertCellNotInChoices('regular_field-entity_type',    choices=choices)
        self.assertCellNotInChoices('regular_field-user__username', choices=choices)

        self.assertCellInChoices('regular_field-name',   choices=choices)
        self.assertCellInChoices('regular_field-sector', choices=choices)

        self.assertListEqual(
            [EntityCellRegularField.build(FakeOrganisation, fname1)],
            field.clean(value),
        )

    def test_regularfields02(self):
        "With ignored cells."
        model = FakeOrganisation
        field = CustomFormCellsField(model=model)
        self.assertListEqual([], [*field.ignored_cells])

        ignored = 'name'
        field.ignored_cells = [EntityCellRegularField.build(model, ignored)]

        choices = self._find_sub_widget(field, 'regular_field').choices
        self.assertCellInChoices('regular_field-user',   choices=choices)
        self.assertCellInChoices('regular_field-sector', choices=choices)

        self.assertCellNotInChoices('regular_field-name', choices=choices)

    def test_customfields(self):
        model = FakeOrganisation
        create_cf = partial(
            CustomField.objects.create,
            content_type=model, field_type=CustomField.STR,
        )
        cf1 = create_cf(name='Headline')
        cf2 = create_cf(name='Color')

        field = CustomFormCellsField(model=model)
        field.ignored_cells = [EntityCellCustomField(cf1)]

        choices = self._find_sub_widget(field, 'custom_field').choices
        self.assertCellInChoices(f'custom_field-{cf2.id}', choices=choices)
        self.assertCellNotInChoices(f'custom_field-{cf1.id}', choices=choices)

    def test_specialfields(self):
        model = FakeOrganisation
        field = CustomFormCellsField(model=model)
        choices1 = self._find_sub_widget(field, 'cform_special').choices
        self.assertCellInChoices('cform_special-regularfields', choices=choices1)
        self.assertCellInChoices('cform_special-customfields',  choices=choices1)

        field.ignored_cells = [
            EntityCellCustomFormSpecial(
                model=model,
                name=EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS,
            ),
        ]
        choices2 = self._find_sub_widget(field, 'cform_special').choices
        self.assertCellInChoices('cform_special-customfields',  choices=choices2)
        self.assertCellNotInChoices('cform_special-regularfields', choices=choices2)

    def test_extrafields(self):
        model = FakeOrganisation
        sub_type_id01 = 'test01'
        sub_type_id02 = 'test05'

        class BaseTestSubCell(CustomFormExtraSubCell):
            def __init__(self, model=FakeOrganisation):
                super().__init__(model=model)

            def formfield(self, instance, user, **kwargs):
                return IntegerField(**kwargs)

        class TestSubCell01(BaseTestSubCell):
            sub_type_id = sub_type_id01
            verbose_name = 'Test01 (test_extrafields)'

        class TestSubCell02(BaseTestSubCell):
            sub_type_id = sub_type_id02
            verbose_name = 'Test02 (test_form_extra_cells01)'

        class TestCellCustomFormExtra(EntityCellCustomFormExtra):
            allowed_sub_cell_classes = [TestSubCell01, TestSubCell02]

        registry = EntityCellsRegistry().register(
            EntityCellRegularField,
            EntityCellCustomField,
            EntityCellCustomFormSpecial,
            TestCellCustomFormExtra,
        )

        class TestCellExtraFieldsField(CFormCellExtraFieldsField):
            cell_class = TestCellCustomFormExtra

        field = CustomFormCellsField(model=model)
        field.field_classes = {*field.field_classes, TestCellExtraFieldsField}
        field.cell_registry = registry

        choices1 = self._find_sub_widget(field, 'cform_extra').choices
        self.assertCellInChoices(f'cform_extra-{sub_type_id01}', choices=choices1)
        self.assertCellInChoices(f'cform_extra-{sub_type_id02}', choices=choices1)

        field.ignored_cells = [TestCellCustomFormExtra(TestSubCell01())]
        choices2 = self._find_sub_widget(field, 'cform_extra').choices
        self.assertCellInChoices(f'cform_extra-{sub_type_id02}', choices=choices2)
        self.assertCellNotInChoices(f'cform_extra-{sub_type_id01}', choices=choices2)


class CustomFormTestCase(BrickTestCaseMixin, CremeTestCase):
    def test_portal(self):
        self.login()

        response = self.assertGET200(reverse('creme_config__custom_forms'))
        # self.assertTemplateUsed(response, 'creme_config/custom_form_portal.html')
        self.assertTemplateUsed(response, 'creme_config/portals/custom-form.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url')
        )
        self.get_brick_node(
            self.get_html_tree(response.content),
            bricks.CustomFormsBrick.id_,
        )

    def test_form_creation_for_role01(self):
        "No copy."
        self.login()
        role = self.role

        # These instances should not be used to compute roles choices
        CustomFormConfigItem.objects.create(
            descriptor_id=FAKEACTIVITY_EDITION_CFORM.id,
            role=role, superuser=False,
        )
        CustomFormConfigItem.objects.create(
            descriptor_id=FAKEACTIVITY_EDITION_CFORM.id,
            role=None, superuser=True,
        )

        descriptor = FAKEACTIVITY_CREATION_CFORM
        item = self.get_object_or_fail(
            CustomFormConfigItem, descriptor_id=descriptor.id, role=None, superuser=False,
        )

        url = reverse('creme_config__create_custom_form', args=(descriptor.id,))
        response1 = self.assertGET200(url)
        context1 = response1.context
        self.assertEqual(
            _('Add a configuration to «{descriptor.verbose_name}» for a role').format(
                descriptor=descriptor,
            ),
            context1.get('title'),
        )
        self.assertEqual(_('Save the custom form'), context1.get('submit_label'))

        with self.assertNoException():
            role_f1 = context1['form'].fields['role']

        self.assertInChoices(value=role.id, label=role.name, choices=role_f1.choices)
        self.assertEqual('*{}*'.format(_('Superuser')), role_f1.empty_label)

        # POST #1 (role)
        self.assertNoFormError(self.client.post(url, data={'role': role.id}))

        new_item1 = self.get_object_or_fail(
            CustomFormConfigItem, descriptor_id=descriptor.id, role=role, superuser=False,
        )
        self.assertFalse(new_item1.groups_as_dicts())
        self.assertNotEqual(item.id, new_item1.id)

        # ---
        response3 = self.assertGET200(url)

        with self.assertNoException():
            role_f2 = response3.context['form'].fields['role']

        self.assertNotInChoices(value=role.id, choices=role_f2.choices)
        self.assertEqual('*{}*'.format(_('Superuser')), role_f2.empty_label)

        # POST #2 (super-user)
        self.assertNoFormError(self.client.post(url, data={}))

        new_item2 = self.get_object_or_fail(
            CustomFormConfigItem, descriptor_id=descriptor.id, role=None, superuser=True,
        )
        self.assertFalse(new_item2.groups_as_dicts())
        self.assertNotEqual(new_item1.id, new_item2.id)

        # ---
        response5 = self.assertGET200(url)

        with self.assertNoException():
            role_f3 = response5.context['form'].fields['role']

        self.assertIsNone(role_f3.empty_label)

    def test_form_creation_for_role02(self):
        "Copy existing instance."
        self.login()
        role1 = self.role
        role2 = UserRole.objects.create(name='Salesman')

        descriptor_id = FAKEACTIVITY_CREATION_CFORM.id
        item1 = self.get_object_or_fail(
            CustomFormConfigItem, descriptor_id=descriptor_id, role=None, superuser=False,
        )
        create_cfci = partial(CustomFormConfigItem.objects.create, descriptor_id=descriptor_id)
        item2 = create_cfci(role=None, superuser=True)
        item3 = create_cfci(role=role2, superuser=False)

        # Excluded from choices (not same descriptor)
        other_item = create_cfci(
            descriptor_id=FAKEACTIVITY_EDITION_CFORM.id,
            role=role1, superuser=False,
        )

        url = reverse('creme_config__create_custom_form', args=(descriptor_id,))
        response1 = self.assertGET200(url)

        with self.assertNoException():
            copy_f = response1.context['form'].fields['instance_to_copy']
            choices = copy_f.choices

        self.assertInChoices(
            value=item1.id, label=_('Default form'), choices=choices,
        )
        self.assertInChoices(
            value=item2.id, label=_('Form for super-user'), choices=choices,
        )
        self.assertInChoices(
            value=item3.id,
            label=_('Form for role «{role}»').format(role=role2.name),
            choices=choices,
        )
        self.assertInChoices(
            value=item3.id,
            label=_('Form for role «{role}»').format(role=role2.name),
            choices=choices,
        )
        self.assertNotInChoices(value=other_item.id, choices=choices)
        self.assertIsNotNone(copy_f.empty_label)

        # POST #1
        response2 = self.client.post(
            url,
            data={
                'role': role1.id,
                'instance_to_copy': item1.id,
            }
        )
        self.assertNoFormError(response2)

        new_item = self.get_object_or_fail(
            CustomFormConfigItem, descriptor_id=descriptor_id, role=role1, superuser=False,
        )
        self.assertEqual(
            json_load(item1.json_groups),
            json_load(new_item.json_groups),
        )

    def test_form_creation_for_role_error(self):
        self.login()
        self.assertGET409(
            reverse('creme_config__create_custom_form', args=('invalid',))
        )

    def test_form_deletion01(self):
        "Super-user's form."
        self.login()
        cfci = CustomFormConfigItem.objects.create(
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=True,
        )
        url = reverse('creme_config__delete_custom_form')
        self.assertGET405(url)

        self.assertPOST200(url, data={'id': cfci.id})
        self.assertDoesNotExist(cfci)

    def test_form_deletion02(self):
        "Role's form."
        self.login()
        cfci = CustomFormConfigItem.objects.create(
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=self.role, superuser=False,
        )

        self.assertPOST200(reverse('creme_config__delete_custom_form'), data={'id': cfci.id})
        self.assertDoesNotExist(cfci)

    def test_form_deletion03(self):
        "Default form => error."
        self.login()
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )

        self.assertPOST409(reverse('creme_config__delete_custom_form'), data={'id': cfci.id})
        self.assertStillExists(cfci)

    def test_group_edition01(self):
        self.login()

        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )

        # url = reverse('creme_config__edit_custom_form_group', args=(cform_id, 0))
        url = reverse('creme_config__edit_custom_form_group', args=(cfci.id, 0))
        response1 = self.assertGET200(url)
        context = response1.context
        self.assertEqual(
            _('Edit the group «{group}»').format(group='General'),
            context.get('title'),
        )
        self.assertEqual(_('Save the configuration'), context.get('submit_label'))

        with self.assertNoException():
            fields = response1.context['form'].fields
            name_f = fields['name']
            cells_f = fields['cells']

        self.assertEqual('General', name_f.initial)

        build_4_field = partial(EntityCellRegularField.build, model=FakeActivity)
        self.assertListEqual(
            [
                build_4_field(name='user'),
                build_4_field(name='title'),
                build_4_field(name='type'),
                # build_4_field(name='minutes'),
                # build_4_field(name='description'),
            ],
            cells_f.initial,
        )

        # --
        group_name1 = 'General information'
        field_names = ['user', 'type', 'title']

        def post(*fnames):
            return self.client.post(
                url,
                data={
                    'name': group_name1,
                    'cells': ','.join(f'regular_field-{fname}' for fname in fnames),
                    'layout': 'not-used',
                },
            )

        excluded = 'description'  # see FAKEACTIVITY_CFORM
        response2 = post(*field_names, excluded)
        self.assertFormError(
            response2, 'form', 'cells',
            _('This value is invalid: %(value)s') % {'value': excluded},
        )

        response3 = post(*field_names)
        self.assertNoFormError(response3)

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)
        self.assertIsNone(cfci.role)
        self.assertIs(cfci.superuser, False)
        self.assertListEqual(
            [
                {
                    'name': group_name1,
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        {'type': 'regular_field', 'value': name}
                        for name in field_names
                    ],
                }, {
                    'name': 'Where & when',
                    'layout': LAYOUT_DUAL_SECOND,
                    'cells': [
                        {'type': 'regular_field', 'value': 'place'},
                        {'type': 'cform_extra',   'value': 'fakeactivity_start'},
                        {'type': 'cform_extra',   'value': 'fakeactivity_end'},
                    ],
                }, {
                    'name': 'Custom fields',
                    'layout': LAYOUT_REGULAR,
                    'cells': [
                        {
                            'type': 'cform_special',
                            'value': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS,
                        },
                    ],
                },
            ],
            self.refresh(cfci).groups_as_dicts(),
        )

    def test_group_edition02(self):
        "Other group (id=1), extra cells."
        self.login()

        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        url = reverse(
            'creme_config__edit_custom_form_group',
            # args=(FAKEACTIVITY_CREATION_CFORM.id, 1),
            args=(cfci.id, 1),
        )
        response1 = self.assertGET200(url)
        context = response1.context
        self.assertEqual(
            _('Edit the group «{group}»').format(group='Where & when'),
            context.get('title'),
        )

        with self.assertNoException():
            fields = response1.context['form'].fields
            name_f = fields['name']
            cells_f = fields['cells']

        self.assertEqual('Where & when', name_f.initial)

        extra_cell1 = fake_forms.FakeActivityStartSubCell().into_cell()
        extra_cell2 = fake_forms.FakeActivityEndSubCell().into_cell()
        self.assertListEqual(
            [
                'regular_field-place',
                extra_cell1.key,
                extra_cell2.key,
            ],
            [c.key for c in cells_f.initial],
        )

        # --
        group_name2 = 'Other information'
        response2 = self.client.post(
            url,
            data={
                'name': group_name2,
                'cells': f'regular_field-place,{extra_cell1.key}',
            },
        )
        self.assertNoFormError(response2)

        # cfci = self.get_object_or_fail(
        #     CustomFormConfigItem, cform_id=FAKEACTIVITY_CREATION_CFORM.id,
        # )
        cfci = self.refresh(cfci)
        self.assertListEqual(
            [
                {
                    'name': 'General',
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        {'type': 'regular_field', 'value': 'user'},
                        {'type': 'regular_field', 'value': 'title'},
                        {'type': 'regular_field', 'value': 'type'},
                        # {'type': 'regular_field', 'value': 'minutes'},
                        # {'type': 'regular_field', 'value': 'description'},
                    ],
                }, {
                    'name': group_name2,
                    'layout': LAYOUT_DUAL_SECOND,
                    'cells': [
                        {'type': 'regular_field', 'value': 'place'},
                        {'type': 'cform_extra', 'value': 'fakeactivity_start'},
                    ],
                }, {
                    'name': 'Custom fields',
                    'layout': LAYOUT_REGULAR,
                    'cells': [
                        {
                            'type': 'cform_special',
                            'value': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS,
                        },
                    ],
                },
            ],
            cfci.groups_as_dicts(),
        )

    def test_group_edition03(self):
        "Layout is not modified."
        self.login()

        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )

        old_groups = iter(FAKEACTIVITY_CREATION_CFORM.groups(item=cfci))
        group1 = next(old_groups)
        group2 = next(old_groups)
        cfci.store_groups(
            FieldGroupList(
                model=FakeActivity,
                cell_registry=FAKEACTIVITY_CREATION_CFORM.build_cell_registry(),
                groups=[
                    FieldGroup(
                        name=group1.name,
                        layout=LAYOUT_DUAL_FIRST,
                        cells=group1.cells,
                    ),
                    group2,
                    *old_groups,
                ],
            )
        )
        cfci.save()

        group_name2 = f'{group2.name} edited'
        response = self.client.post(
            # reverse('creme_config__edit_custom_form_group', args=(cform_id, 1)),
            reverse('creme_config__edit_custom_form_group', args=(cfci.id, 1)),
            data={
                'name': group_name2,
                'cells': ','.join(cell.key for cell in group2.cells),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(
            LAYOUT_DUAL_FIRST,
            self.refresh(cfci).groups_as_dicts()[0]['layout'],
        )

    def test_group_edition04(self):
        "Edition form => no <properties>/<relations> fields."
        self.login()
        prop_cell = EntityCellCustomFormSpecial(
            model=FakeActivity, name=EntityCellCustomFormSpecial.CREME_PROPERTIES,
        )
        rel_cell = EntityCellCustomFormSpecial(
            model=FakeActivity, name=EntityCellCustomFormSpecial.RELATIONS,
        )

        creation_cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        response1 = self.assertGET200(reverse(
            # 'creme_config__edit_custom_form_group', args=(FAKEACTIVITY_CREATION_CFORM.id, 1)
            'creme_config__edit_custom_form_group', args=(creation_cfci.id, 1)
        ))

        with self.assertNoException():
            ignored_cells1 = [*response1.context['form'].fields['cells'].ignored_cells]

        self.assertNotIn(prop_cell, ignored_cells1)
        self.assertNotIn(rel_cell, ignored_cells1)

        # ---
        edition_cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_EDITION_CFORM.id, role=None, superuser=False,
        )
        response2 = self.assertGET200(reverse(
            # 'creme_config__edit_custom_form_group', args=(FAKEACTIVITY_EDITION_CFORM.id, 1)
            'creme_config__edit_custom_form_group', args=(edition_cfci.id, 1)
        ))

        with self.assertNoException():
            ignored_cells2 = [*response2.context['form'].fields['cells'].ignored_cells]

        self.assertIn(prop_cell, ignored_cells2)
        self.assertIn(rel_cell, ignored_cells2)

    def test_group_edition05(self):
        "Non hiddable fields (because already selected)."
        self.login()
        desc = FAKEORGANISATION_CREATION_CFORM
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=desc.id, role=None, superuser=False,
        )

        hidden = 'sector'

        # See fake_populate in core
        self.assertIn(
            hidden,
            [
                cell.value
                # for cell in getattr(desc.groups()[0], 'cells', ())
                for cell in getattr(desc.groups(cfci)[0], 'cells', ())
                if isinstance(cell, EntityCellRegularField)
            ],
        )

        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden, {FieldsConfig.HIDDEN: True})],
        )

        response = self.assertGET200(reverse(
            # 'creme_config__edit_custom_form_group', args=(desc.id, 0)
            'creme_config__edit_custom_form_group', args=(cfci.id, 0)
        ))

        with self.assertNoException():
            non_hiddable_cells = [
                *response.context['form'].fields['cells'].non_hiddable_cells
            ]

        self.assertIn(
            EntityCellRegularField.build(model=FakeOrganisation, name=hidden),
            non_hiddable_cells,
        )

    def test_group_edition_error01(self):
        "Invalid groups."
        self.login()

        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )

        def build_url(group_id):
            return reverse(
                'creme_config__edit_custom_form_group',
                # args=(FAKEACTIVITY_CREATION_CFORM.id, group_id),
                args=(cfci.id, group_id),
            )

        with self.assertRaises(NoReverseMatch):
            self.assertGET404(build_url(group_id='notanint'))

        with self.assertRaises(NoReverseMatch):
            self.assertGET404(build_url(group_id=-1))

        self.assertContains(
            self.client.get(build_url(group_id=3)),
            'The group ID "3" is invalid.',
            status_code=409,
            html=True,
        )
        self.assertContains(
            self.client.get(build_url(group_id=4)),
            'The group ID "4" is invalid.',
            status_code=409,
            html=True,
        )

    def test_group_edition_error02(self):
        "Not registered id."
        self.login()

        # cform_id = 'creme_core-invalid'
        descriptor_id = 'creme_core-invalid'
        # cfci = CustomFormConfigItem.objects.create(cform_id=cform_id)
        cfci = CustomFormConfigItem.objects.create(descriptor_id=descriptor_id)

        self.assertContains(
            self.client.get(
                # reverse('creme_config__edit_custom_form_group', args=(cform_id, 0)),
                reverse('creme_config__edit_custom_form_group', args=(cfci.id, 0)),
            ),
            # escape(f'The custom form "{cform_id}" is invalid.'),
            f'The custom form "{descriptor_id}" is invalid.',
            status_code=409,
            html=True,
        )

    def test_group_edition_error03(self):
        "Bad type of cell."
        self.login()

        base_cell_keys = [
            f'regular_field-{name}' for name in ('user', 'type', 'title')
        ]
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        url = reverse(
            'creme_config__edit_custom_form_group',
            # args=(FAKEACTIVITY_CREATION_CFORM.id, 0),
            args=(cfci.id, 0),
        )

        def post(extra_cell):
            response = self.assertPOST200(
                url,
                data={
                    'name': 'General information',
                    'cells': ','.join([*base_cell_keys, extra_cell.key]),
                },
            )
            self.assertFormError(
                response, 'form', 'cells',
                'The type of cell in invalid: %(type_id)s.' % {
                    'type_id': extra_cell.type_id,
                },
            )

        post(EntityCellFunctionField.build(FakeActivity, 'get_pretty_properties'))
        post(EntityCellRelation.build(FakeActivity, REL_SUB_HAS))

    @parameterized.expand([
        ('user__username', ),  # Deep field
        ('place', ),  # Used field
        ('created', ),  # Not editable field
    ])
    def test_group_edition_regularfields_error(self, fname):
        self.login()

        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        response = self.assertPOST200(
            reverse(
                'creme_config__edit_custom_form_group',
                # args=(FAKEACTIVITY_CREATION_CFORM.id, 0),
                args=(cfci.id, 0),
            ),
            data={
                'name': 'General information',
                'cells': ','.join(
                    f'regular_field-{name}' for name in ('user', 'type', 'title', fname)
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'cells',
            _('This value is invalid: %(value)s') % {'value': fname},
        )

    def test_group_edition_customfield(self):
        self.login()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=FakeActivity, field_type=CustomField.INT,
        )
        cfields = [
            create_cfield(name=name) for name in ('Importance', 'Cost', 'Hardness')
        ]

        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        # url = reverse('creme_config__edit_custom_form_group', args=(cform_id, 1))
        url = reverse('creme_config__edit_custom_form_group', args=(cfci.id, 1))

        # TODO: test available cfields ?

        rfield_name = 'place'
        response = self.client.post(
            url,
            data={
                'name': 'Other information',
                'cells': ','.join([
                    f'regular_field-{rfield_name}',
                    f'custom_field-{cfields[1].id}',
                    f'custom_field-{cfields[0].id}',
                ]),
            },
        )
        self.assertNoFormError(response)

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)
        self.assertDictEqual(
            {
                'name': 'Other information',
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    {'type': 'regular_field', 'value': rfield_name},
                    {'type': 'custom_field', 'value': str(cfields[1].id)},
                    {'type': 'custom_field', 'value': str(cfields[0].id)},
                ],
            },
            cfci.groups_as_dicts()[1],
        )

    def test_group_edition_customfield_error(self):
        "Used custom field."
        self.login()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=FakeActivity, field_type=CustomField.INT,
        )
        cfields = [
            create_cfield(name=name) for name in ('Importance', 'Cost', 'Hardness')
        ]

        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )

        old_groups = [*FAKEACTIVITY_CREATION_CFORM.groups(item=cfci)]
        cfci.store_groups(
            FieldGroupList(
                model=FakeActivity,
                cell_registry=FAKEACTIVITY_CREATION_CFORM.build_cell_registry(),
                groups=[
                    *old_groups,
                    FieldGroup(
                        name='Custom fields#1',
                        cells=[EntityCellCustomField(cfields[0])],
                    ),
                    FieldGroup(
                        name='Custom fields#2',
                        cells=[EntityCellCustomField(cfields[1])],
                    ),
                ],
            )
        )
        cfci.save()

        response = self.assertPOST200(
            reverse(
                'creme_config__edit_custom_form_group',
                # args=(cform_id, len(old_groups) - 1),
                args=(cfci.id, len(old_groups) - 1),
            ),
            data={
                'name': 'Custom fields#2',
                'cells': ','.join([
                    f'custom_field-{cfields[0].id}',
                    f'custom_field-{cfields[2].id}',
                ]),
            },
        )
        self.assertFormError(
            response, 'form', 'cells',
            _('This value is invalid: %(value)s') % {'value': cfields[0].id},
        )

    def test_group_edition_extrafield(self):
        self.login()

        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        # url = reverse('creme_config__edit_custom_form_group', args=(cform_id, 1))
        url = reverse('creme_config__edit_custom_form_group', args=(cfci.id, 1))

        # First step: we remove the extra fields 'start' & 'end'
        response = self.client.post(
            url,
            data={
                'name': 'Where',
                'cells': 'regular_field-place',
            },
        )
        self.assertNoFormError(response)

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)
        self.assertDictEqual(
            {
                'name': 'Where',
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    {'type': 'regular_field', 'value': 'place'},
                    # {'type': 'cform_extra', 'value': 'fakeactivity_start'},
                    # {'type': 'cform_extra', 'value': 'fakeactivity_end'},
                ],
            },
            cfci.groups_as_dicts()[1],
        )

        # Second step: we add the extra fields 'start'
        response = self.client.post(
            url,
            data={
                'name': 'Where',
                'cells': 'regular_field-place,cform_extra-fakeactivity_start',
            },
        )
        self.assertNoFormError(response)

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)
        self.assertDictEqual(
            {
                'name': 'Where',
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    {'type': 'regular_field', 'value': 'place'},
                    {'type': 'cform_extra', 'value': 'fakeactivity_start'},
                ],
            },
            cfci.groups_as_dicts()[1],
        )

    def test_group_edition_extrafield_error(self):
        "Used extra field."
        self.login()

        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        response = self.client.post(
            reverse(
                'creme_config__edit_custom_form_group',
                # args=(FAKEACTIVITY_CREATION_CFORM.id, 0),
                args=(cfci.id, 0),
            ),
            data={
                'name': 'General',
                'cells': ','.join([
                    'regular_field-user',
                    'regular_field-title',
                    'regular_field-type',
                    'cform_extra-fakeactivity_start',
                ]),
            },
        )
        self.assertFormError(
            response, 'form', 'cells',
            _('This value is invalid: %(value)s') % {'value': 'fakeactivity_start'},
        )

    def test_group_edition_specialfield01(self):
        "Remaining regular fields."
        self.login()

        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        response = self.client.post(
            # reverse('creme_config__edit_custom_form_group', args=(cform_id, 0)),
            reverse('creme_config__edit_custom_form_group', args=(cfci.id, 0)),
            data={
                'name': 'Main',
                'cells': 'cform_special-regularfields',
            },
        )
        self.assertNoFormError(response)

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)
        self.assertDictEqual(
            {
                'name': 'Main',
                'layout': LAYOUT_DUAL_FIRST,
                'cells': [
                    {
                        'type': 'cform_special',
                        'value': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS,
                    },
                ],
            },
            cfci.groups_as_dicts()[0],
        )

    def test_group_edition_specialfield02(self):
        "Remaining custom fields."
        self.login()

        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        # url = reverse('creme_config__edit_custom_form_group', args=(cform_id, 2))
        url = reverse('creme_config__edit_custom_form_group', args=(cfci.id, 2))

        # First step: we remove the special fields 'remaining custom-fields'
        response = self.client.post(
            url,
            data={
                'name': 'Custom fields',
                'cells': 'regular_field-minutes',  # Group cannot be empty...
            },
        )
        self.assertNoFormError(response)

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)
        self.assertDictEqual(
            {
                'name': 'Custom fields',
                'layout': LAYOUT_REGULAR,
                'cells': [
                    {'type': 'regular_field', 'value': 'minutes'},
                ],
            },
            cfci.groups_as_dicts()[2],
        )

        # Second step: we add the special fields 'customfields'
        response = self.client.post(
            url,
            data={
                'name': 'All custom fields',
                'cells': 'cform_special-customfields',
            },
        )
        self.assertNoFormError(response)

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)
        self.assertDictEqual(
            {
                'name': 'All custom fields',
                'layout': LAYOUT_REGULAR,
                'cells': [
                    {
                        'type': 'cform_special',
                        'value': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS,
                    },
                ],
            },
            cfci.groups_as_dicts()[2],
        )

    def test_group_edition_specialfield_error(self):
        "Used special field."
        self.login()

        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        response = self.client.post(
            reverse(
                'creme_config__edit_custom_form_group',
                # args=(FAKEACTIVITY_CREATION_CFORM.id, 0),
                args=(cfci.id, 0),
            ),
            data={
                'name': 'General',
                'cells': ','.join([
                    'regular_field-user',
                    'regular_field-title',
                    'regular_field-type',
                    'cform_special-customfields',
                ]),
            },
        )
        self.assertFormError(
            response, 'form', 'cells',
            _('This value is invalid: %(value)s') % {'value': 'customfields'},
        )

    def test_group_edition_extra_group(self):
        "Extra group has no cells => no error when computing ignored cells."
        self.login()

        desc = FAKEORGANISATION_CREATION_CFORM
        # cform_id = desc.id
        descriptor_id = desc.id
        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.get_object_or_fail(CustomFormConfigItem, descriptor_id=descriptor_id)
        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cfci.store_groups(
            FieldGroupList(
                model=FakeActivity,
                cell_registry=desc.build_cell_registry(),
                groups=[
                    FieldGroup(
                        name='General',
                        cells=[build_cell(name='user'), build_cell(name='name')],
                    ),
                    FakeAddressGroup(model=FakeOrganisation),
                ],
            )
        )
        cfci.save()

        self.assertGET200(reverse(
            # 'creme_config__edit_custom_form_group', args=(cform_id, 0)
            'creme_config__edit_custom_form_group', args=(cfci.id, 0)
        ))

    def test_group_creation_regularfields01(self):
        self.login()

        group_name1 = 'Required fields'
        fields1 = ('user', 'title', 'place', 'type')

        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        build_cell = partial(EntityCellRegularField.build, model=FakeActivity)
        cfci.store_groups(
            FieldGroupList(
                model=FakeActivity,
                cell_registry=FAKEACTIVITY_CREATION_CFORM.build_cell_registry(),
                groups=[
                    FieldGroup(
                        name=group_name1,
                        cells=[build_cell(name=name) for name in fields1],
                    ),
                ],
            )
        )
        cfci.save()

        # url = reverse('creme_config__add_custom_form_group', args=(cform_id,))
        url = reverse('creme_config__add_custom_form_group', args=(cfci.id,))
        response1 = self.assertGET200(url)
        context = response1.context
        self.assertEqual(
            _('Add a group to «{form}»').format(form=FAKEACTIVITY_CREATION_CFORM.verbose_name),
            context.get('title')
        )
        self.assertEqual(_('Save the configuration'), context.get('submit_label'))

        # TODO: test that used fields are not proposed

        # --
        group_name2 = 'Other information'
        # fields2 = ['start', 'end']
        fields2 = ['minutes']

        def post(*fnames):
            return self.client.post(
                url,
                data={
                    'name': group_name2,
                    'cells': ','.join(f'regular_field-{name}' for name in fnames),
                },
            )

        excluded = 'description'  # see FAKEACTIVITY_CFORM
        response2 = post(*fields2, excluded)
        self.assertFormError(
            response2, 'form', 'cells',
            _('This value is invalid: %(value)s') % {'value': excluded},
        )

        response3 = post(*fields2)
        self.assertNoFormError(response3)
        self.assertListEqual(
            [
                {
                    'name': group_name1,
                    'layout': LAYOUT_REGULAR,
                    'cells': [
                        {'type': 'regular_field', 'value': name}
                        for name in fields1
                    ],
                }, {
                    'name': group_name2,
                    'layout': LAYOUT_REGULAR,
                    'cells': [
                        {'type': 'regular_field', 'value': name}
                        for name in fields2
                    ],
                },
            ],
            self.refresh(cfci).groups_as_dicts(),
        )

    def test_group_creation_regularfields02(self):
        "Empty group."
        self.login()

        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )

        group_name3 = 'Empty group'
        response = self.client.post(
            # reverse('creme_config__add_custom_form_group', args=(cform_id,)),
            reverse('creme_config__add_custom_form_group', args=(cfci.id,)),
            data={
                'name': group_name3,
                # 'cells': ...,
            },
        )
        self.assertNoFormError(response)

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)

        dict_groups = cfci.groups_as_dicts()
        self.assertEqual(4, len(dict_groups))

        dict_group = dict_groups[-1]
        self.assertEqual(group_name3, dict_group['name'])
        self.assertListEqual([], dict_group['cells'])

    def test_group_creation_customfields(self):
        self.login()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=FakeActivity, field_type=CustomField.INT,
        )
        cfields = [
            create_cfield(name=name) for name in ('Importance', 'Cost', 'Hardness')
        ]

        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        descriptor_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=descriptor_id, role=None, superuser=False,
        )

        group_name = 'Custom Fields'
        # url = reverse('creme_config__add_custom_form_group', args=(cform_id,))
        url = reverse('creme_config__add_custom_form_group', args=(cfci.id,))
        response = self.client.post(
            url,
            data={
                'name': group_name,
                'cells': ','.join([
                    f'custom_field-{cfields[1].id}',
                    f'custom_field-{cfields[0].id}',
                ]),
            },
        )
        self.assertNoFormError(response)

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)
        self.assertDictEqual(
            {
                'name': group_name,
                'layout': LAYOUT_REGULAR,
                'cells': [
                    {'type': 'custom_field', 'value': str(cfields[1].id)},
                    {'type': 'custom_field', 'value': str(cfields[0].id)},
                ],
            },
            cfci.groups_as_dicts()[-1],
        )

        # Cannot used same fields in another group ---
        response = self.assertPOST200(
            url,
            data={
                'name': 'Another group',
                'cells': ','.join([
                    f'custom_field-{cfields[1].id}',
                    f'custom_field-{cfields[2].id}',
                ]),
            },
        )
        self.assertFormError(
            response, 'form', 'cells',
            _('This value is invalid: %(value)s') % {'value': cfields[1].id},
        )

    def test_group_creation_customfields_error(self):
        "CustomField for another ContentType."
        self.login()

        cfield = CustomField.objects.create(
            content_type=FakeOrganisation, field_type=CustomField.INT, name='Cost',
        )

        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        response = self.assertPOST200(
            reverse(
                # 'creme_config__add_custom_form_group', args=(FAKEACTIVITY_CREATION_CFORM.id,)
                'creme_config__add_custom_form_group', args=(cfci.id,)
            ),
            data={
                'name': 'Custom Fields',
                'cells': f'custom_field-{cfield.id}',
            },
        )
        self.assertFormError(
            response, 'form', 'cells',
            _('This value is invalid: %(value)s') % {'value': cfield.id},
        )

    def test_group_creation_properties(self):
        "Edition form => no <properties>/<relations> fields."
        self.login()
        prop_cell = EntityCellCustomFormSpecial(
            model=FakeActivity, name=EntityCellCustomFormSpecial.CREME_PROPERTIES,
        )
        rel_cell = EntityCellCustomFormSpecial(
            model=FakeActivity, name=EntityCellCustomFormSpecial.RELATIONS,
        )

        creation_cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        response1 = self.assertGET200(reverse(
            # 'creme_config__add_custom_form_group', args=[FAKEACTIVITY_CREATION_CFORM.id],
            'creme_config__add_custom_form_group', args=[creation_cfci.id],
        ))

        with self.assertNoException():
            ignored_cells1 = [*response1.context['form'].fields['cells'].ignored_cells]

        self.assertNotIn(prop_cell, ignored_cells1)
        self.assertNotIn(rel_cell, ignored_cells1)

        # ---
        edition_cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_EDITION_CFORM.id, role=None, superuser=False,
        )
        response2 = self.assertGET200(reverse(
            # 'creme_config__add_custom_form_group', args=[FAKEACTIVITY_EDITION_CFORM.id],
            'creme_config__add_custom_form_group', args=[edition_cfci.id],
        ))

        with self.assertNoException():
            ignored_cells2 = [*response2.context['form'].fields['cells'].ignored_cells]

        self.assertIn(prop_cell, ignored_cells2)
        self.assertIn(rel_cell, ignored_cells2)

    def test_extra_group01(self):
        "Adding extra group."
        self.login()

        # cform_id = FAKEORGANISATION_CREATION_CFORM.id
        descriptor_id = FAKEORGANISATION_CREATION_CFORM.id
        cfci = self.get_object_or_fail(
            CustomFormConfigItem, descriptor_id=descriptor_id, role=None, superuser=False,
        )

        # See fake_populate
        self.assertFalse(
            [
                group
                # for group in FAKEORGANISATION_CREATION_CFORM.groups()
                for group in FAKEORGANISATION_CREATION_CFORM.groups(cfci)
                if isinstance(group, FakeAddressGroup)
            ]
        )

        # url = reverse('creme_config__add_custom_form_extra_group', args=[cform_id])
        url = reverse('creme_config__add_custom_form_extra_group', args=[cfci.id])
        response1 = self.assertGET200(url)

        with self.assertNoException():
            group_f1 = response1.context['form'].fields['group']

        group_id = FakeAddressGroup.extra_group_id
        self.assertInChoices(
            value=group_id,
            label=FakeAddressGroup.name,
            choices=group_f1.choices,
        )
        self.assertFalse(group_f1.help_text)

        # ---
        response2 = self.client.post(
            url, follow=True, data={'group': group_id},
        )
        self.assertNoFormError(response2)

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)
        dict_groups = cfci.groups_as_dicts()
        self.assertEqual(2, len(dict_groups))
        self.assertDictEqual({'group_id': group_id}, dict_groups[-1])

        # No choices available
        response3 = self.assertGET200(url)

        with self.assertNoException():
            group_f3 = response3.context['form'].fields['group']

        self.assertFalse(group_f3.choices)
        self.assertEqual(
            _('Sorry no extra group is available any more.'),
            group_f3.help_text,
        )

        # Cannot edit this group
        self.assertGET409(
            # reverse('creme_config__edit_custom_form_group', args=(cform_id, 1))
            reverse('creme_config__edit_custom_form_group', args=(cfci.id, 1))
        )
        # Adding a group does not crash (extra group has no cell)
        self.assertGET200(
            # reverse('creme_config__add_custom_form_group', args=(cform_id,))
            reverse('creme_config__add_custom_form_group', args=(cfci.id,))
        )

    def test_extra_group02(self):
        "Descriptor without extra group class."
        self.login()

        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        self.assertGET409(reverse(
            'creme_config__add_custom_form_extra_group',
            # args=[FAKEACTIVITY_CREATION_CFORM.id],
            args=[cfci.id],
        ))

    @parameterized.expand([
        (0, ['Where & when', 'Custom fields']),
        (1, ['General', 'Custom fields']),
    ])
    def test_group_deletion(self, deleted_group_id, remaining_group_names):
        self.login()
        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )

        # url = reverse('creme_config__delete_custom_form_group', args=(cform_id,))
        url = reverse('creme_config__delete_custom_form_group', args=(cfci.id,))
        self.assertGET405(url)
        self.assertPOST200(url, data={'group_id': deleted_group_id})

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)

        dict_groups = cfci.groups_as_dicts()
        self.assertEqual(len(remaining_group_names), len(dict_groups))
        self.assertListEqual(
            remaining_group_names,
            [dict_group['name'] for dict_group in dict_groups],
        )

    def test_group_deletion_error(self):
        "Invalid ID."
        self.login()
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )

        url = reverse(
            'creme_config__delete_custom_form_group',
            # args=[FAKEACTIVITY_CREATION_CFORM.id],
            args=[cfci.id],
        )
        self.assertPOST404(url, data={'group_id': 'notanint'})
        self.assertContains(
            self.client.post(url, data={'group_id': 3}),
            'The group ID "3" is invalid.',
            status_code=409,
            html=True,
        )

    def test_delete_cell01(self):
        self.login()
        desc = FAKEACTIVITY_CREATION_CFORM
        # cform_id = desc.id
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=desc.id, role=None, superuser=False,
        )

        cell_key = 'regular_field-place'

        # See fake_populate in core
        # group1 = desc.groups()[1]
        group1 = desc.groups(cfci)[1]
        self.assertIn(cell_key, [cell.key for cell in group1.cells])
        self.assertEqual(LAYOUT_DUAL_SECOND, group1.layout)

        # url = reverse('creme_config__delete_custom_form_cell', args=(cform_id,))
        url = reverse('creme_config__delete_custom_form_cell', args=(cfci.id,))
        self.assertGET405(url)

        data = {'cell_key': cell_key}
        self.assertPOST200(url, data=data)

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)
        group_dict1 = cfci.groups_as_dicts()[1]
        self.assertListEqual(
            [
                {'type': 'cform_extra', 'value': 'fakeactivity_start'},
                {'type': 'cform_extra', 'value': 'fakeactivity_end'},
            ],
            group_dict1['cells']
        )
        # Layout must remain the same
        self.assertEqual(group_dict1['layout'], LAYOUT_DUAL_SECOND)

        self.assertPOST404(url, data=data)  # Cell is not used anymore

    def test_delete_cell02(self):
        "Extra group has no cells => no error when searching ignored cells."
        self.login()

        desc = FAKEORGANISATION_CREATION_CFORM
        # cform_id = desc.id
        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=desc.id, role=None, superuser=False,
        )
        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cell_to_dell = build_cell(name='sector')
        cfci.store_groups(
            FieldGroupList(
                model=FakeActivity,
                cell_registry=desc.build_cell_registry(),
                groups=[
                    FieldGroup(
                        name='General',
                        cells=[
                            build_cell(name='user'), build_cell(name='name'),
                            cell_to_dell,
                        ],
                    ),
                    FakeAddressGroup(model=FakeOrganisation),
                ],
            )
        )
        cfci.save()

        self.assertPOST200(
            # reverse('creme_config__delete_custom_form_cell', args=(cform_id,)),
            reverse('creme_config__delete_custom_form_cell', args=(cfci.id,)),
            data={'cell_key': cell_to_dell.key},
        )

    @parameterized.expand([
        (0, LAYOUT_DUAL_FIRST),
        (1, LAYOUT_DUAL_SECOND),
    ])
    def test_group_set_layout(self, group_id, layout):
        self.login()
        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )

        # url = reverse('creme_config__setlayout_custom_form_group', args=(cform_id, group_id))
        url = reverse('creme_config__setlayout_custom_form_group', args=(cfci.id, group_id))
        self.assertGET405(url)
        self.assertPOST200(url, data={'layout': layout})

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)
        self.assertEqual(layout, cfci.groups_as_dicts()[group_id]['layout'])

    def test_group_set_layout_extra_group(self):
        self.login()

        desc = FAKEORGANISATION_CREATION_CFORM
        # cform_id = desc.id
        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=desc.id, role=None, superuser=False,
        )
        build_cell = partial(EntityCellRegularField.build, model=FakeOrganisation)
        cfci.store_groups(
            FieldGroupList(
                model=FakeActivity,
                cell_registry=desc.build_cell_registry(),
                groups=[
                    FieldGroup(
                        name='General',
                        cells=[build_cell(name='user'), build_cell(name='name')],
                    ),
                    FakeAddressGroup(model=FakeOrganisation),
                ],
            )
        )
        cfci.save()

        group_id = 1
        layout = LAYOUT_DUAL_FIRST
        self.assertPOST200(
            # reverse('creme_config__setlayout_custom_form_group', args=(cform_id, group_id)),
            reverse('creme_config__setlayout_custom_form_group', args=(cfci.id, group_id)),
            data={'layout': layout},
        )

        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.refresh(cfci)
        self.assertEqual(layout, cfci.groups_as_dicts()[group_id]['layout'])

    def test_group_set_layout_error(self):
        "Invalid group, invalid layout."
        self.login()
        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )

        self.assertPOST409(
            # reverse('creme_config__setlayout_custom_form_group', args=(cform_id, 3)),
            reverse('creme_config__setlayout_custom_form_group', args=(cfci.id, 3)),
            data={'layout': LAYOUT_DUAL_SECOND},
        )
        self.assertPOST409(
            # reverse('creme_config__setlayout_custom_form_group', args=(cform_id, 1)),
            reverse('creme_config__setlayout_custom_form_group', args=(cfci.id, 1)),
            data={'layout': 'INVALID'},
        )

    def test_group_reorder(self):
        self.login()

        group_id = 0
        target = 1

        # cform_id = FAKEACTIVITY_CREATION_CFORM.id
        # cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=FAKEACTIVITY_CREATION_CFORM.id, role=None, superuser=False,
        )
        old_groups = cfci.groups_as_dicts()

        # url = reverse('creme_config__reorder_custom_form_group', args=(cform_id, group_id))
        url = reverse('creme_config__reorder_custom_form_group', args=(cfci.id, group_id))
        self.assertGET405(url)
        self.assertPOST200(url, data={'target': target})

        cfci = self.refresh(cfci)
        self.assertEqual(old_groups[group_id], cfci.groups_as_dicts()[target])

        # Errors
        self.assertPOST409(
            # Bad group ID
            # reverse('creme_config__reorder_custom_form_group', args=(cform_id, 123)),
            reverse('creme_config__reorder_custom_form_group', args=(cfci.id, 123)),
            data={'target': target},
        )
        self.assertPOST404(url, data={'target': 'notanint'})  # Bad target type
        self.assertPOST409(url, data={'target': 123})  # Bad target value

    def test_brick(self):
        customfield = CustomField.objects.create(
            content_type=FakeOrganisation,
            name='Rate', field_type=CustomField.INT, is_required=True,
        )

        desc1 = CustomFormDescriptor(
            id='test-fakeactivity_creation',
            model=FakeActivity,
            verbose_name='Creation form for FakeActivity',
        )
        desc2 = CustomFormDescriptor(
            id='test-fakeactivity_edition',
            model=FakeActivity,
            verbose_name='Edition form for FakeActivity',
        )
        desc3 = CustomFormDescriptor(
            id='test-fakeorga_creation',
            model=FakeOrganisation,
            verbose_name='Creation form for FakeOrganisation',
        )

        cfci1_base = CustomFormConfigItem.objects.create_if_needed(
            descriptor=desc1,
            groups_desc=[
                {
                    'name': 'General',
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),
                        (EntityCellRegularField, {'name': 'type'}),
                    ],
                }, {
                    'name': 'Where',
                    'cells': [(EntityCellRegularField, {'name': 'place'})],
                },
            ],
        )
        cfci1_super = CustomFormConfigItem.objects.create_if_needed(
            descriptor=desc1,
            groups_desc=[
                {
                    'name': 'General',
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),
                        (EntityCellRegularField, {'name': 'type'}),
                    ],
                },
            ],
            role='superuser',
        )
        role = UserRole.objects.create(name='Basic')
        cfci1_role = CustomFormConfigItem.objects.create_if_needed(
            descriptor=desc1,
            groups_desc=[
                {
                    'name': 'Main',
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),
                        (EntityCellRegularField, {'name': 'type'}),
                    ],
                },
            ],
            role=role,
        )

        cfci2 = CustomFormConfigItem.objects.create_if_needed(
            descriptor=desc2,
            groups_desc=[{
                'name': 'Misc',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'title'}),
                    (EntityCellRegularField, {'name': 'type'}),
                    (EntityCellRegularField, {'name': 'place'}),
                ],
            }],
        )
        cfci3 = CustomFormConfigItem.objects.create_if_needed(
            descriptor=desc3,
            groups_desc=[{
                'name': 'General',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                    EntityCellCustomField(customfield),
                ],
            }],
        )

        registry = CustomFormDescriptorRegistry().register(desc1, desc2, desc3)

        user = self.create_user()

        brick = bricks.CustomFormsBrick()
        brick.registry = registry

        get_ct = ContentType.objects.get_for_model

        desc_data = brick.get_ctype_descriptors(
            user=user,
            expanded_ctype_id=get_ct(FakeActivity).id,
        )
        self.assertIsList(desc_data, length=2)

        def get_ct_wrapper(model):
            ct = get_ct(model)
            for ct_wrapper in desc_data:
                if ct_wrapper.ctype == ct:
                    return ct_wrapper

            self.fail(f'No descriptor found for {ct}')

        activity_wrapper = get_ct_wrapper(FakeActivity)
        self.assertFalse(activity_wrapper.collapsed)

        # activity_descriptors = activity_wrapper.descriptors
        # self.assertEqual(2, len(activity_descriptors))
        #
        # act_desc1 = activity_descriptors[0]
        # self.assertEqual(desc1.id,           act_desc1.id)
        # self.assertEqual(desc1.verbose_name, act_desc1.verbose_name)
        # self.assertListEqual(
        #     ['General', 'Where'],
        #     [g.name for g in act_desc1.groups],
        # )
        # self.assertListEqual([], act_desc1.errors)
        #
        # act_desc2 = activity_descriptors[1]
        # self.assertEqual(desc2.id,           act_desc2.id)
        # self.assertEqual(desc2.verbose_name, act_desc2.verbose_name)
        # self.assertListEqual(['Misc'], [g.name for g in act_desc2.groups])
        # self.assertListEqual([], act_desc2.errors)
        #
        # orga_wrapper = get_ct_wrapper(FakeOrganisation)
        # self.assertTrue(orga_wrapper.collapsed)
        #
        # orga_descriptors = orga_wrapper.descriptors
        # self.assertEqual(1, len(orga_descriptors))
        #
        # orga_desc = orga_descriptors[0]
        # self.assertEqual(desc3.id,           orga_desc.id)
        # self.assertEqual(desc3.verbose_name, orga_desc.verbose_name)
        # self.assertListEqual(['General'], [g.name for g in orga_desc.groups])
        # self.assertListEqual([], orga_desc.errors)
        activity_descriptors = activity_wrapper.descriptors
        self.assertEqual(2, len(activity_descriptors))

        # ---
        act_creation_descriptor = activity_descriptors[0]
        self.assertEqual(desc1.verbose_name, act_creation_descriptor.verbose_name)
        self.assertIsList(act_creation_descriptor.items, length=3)

        act_item11 = act_creation_descriptor.items[0]
        self.assertEqual(cfci1_base.id,     act_item11.id)
        self.assertEqual(_('Default form'), act_item11.verbose_name)
        self.assertListEqual(
            ['General', 'Where'],
            [g.name for g in act_item11.groups],
        )
        self.assertListEqual([], act_item11.errors)

        act_item12 = act_creation_descriptor.items[1]
        self.assertEqual(cfci1_super.id,           act_item12.id)
        self.assertEqual(_('Form for super-user'), act_item12.verbose_name)
        self.assertListEqual(['General'], [g.name for g in act_item12.groups])

        act_item13 = act_creation_descriptor.items[2]
        self.assertEqual(cfci1_role.id, act_item13.id)
        self.assertEqual(
            _('Form for role «{role}»').format(role=role),
            act_item13.verbose_name,
        )

        # ---
        act_edition_descriptor = activity_descriptors[1]
        self.assertEqual(desc2.verbose_name, act_edition_descriptor.verbose_name)
        self.assertIsList(act_edition_descriptor.items, length=1)

        act_item21 = act_edition_descriptor.items[0]
        self.assertEqual(cfci2.id,          act_item21.id)
        self.assertEqual(_('Default form'), act_item21.verbose_name)
        self.assertListEqual(['Misc'], [g.name for g in act_item21.groups])
        self.assertListEqual([], act_item21.errors)

        # ---
        orga_wrapper = get_ct_wrapper(FakeOrganisation)
        self.assertTrue(orga_wrapper.collapsed)

        orga_descriptors = orga_wrapper.descriptors
        self.assertEqual(1, len(orga_descriptors))

        orga_creation_descriptor = orga_descriptors[0]
        self.assertIsList(orga_creation_descriptor.items, length=1)

        orga_item = orga_creation_descriptor.items[0]
        self.assertEqual(cfci3.id, orga_item.id)
        self.assertListEqual(['General'], [g.name for g in orga_item.groups])
        self.assertListEqual([], orga_item.errors)

    def test_brick_error01(self):
        "Missing regular field."
        desc = CustomFormDescriptor(
            id='test-fakeactivity_creation',
            model=FakeActivity,
            verbose_name='Creation form for FakeActivity',
            excluded_fields=['place'],
        )
        cfci = CustomFormConfigItem.objects.create_if_needed(
            descriptor=desc,
            groups_desc=[{
                'name': 'General',
                'cells': [
                    # (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'title'}),
                    # (EntityCellRegularField, {'name': 'type'}),
                    # (EntityCellRegularField, {'name': 'place'}),
                ],
            }],
        )
        registry = CustomFormDescriptorRegistry().register(desc)

        user = self.create_user()

        brick = bricks.CustomFormsBrick()
        brick.registry = registry

        # act_desc1 = brick.get_ctype_descriptors(
        #     user=user, expanded_ctype_id=None,
        # )[0].descriptors[0]
        act_item1 = brick.get_ctype_descriptors(
            user=user, expanded_ctype_id=None,
        )[0].descriptors[0].items[0]
        # self.assertEqual(desc.id, act_desc1.id)
        self.assertEqual(cfci.id, act_item1.id)

        fmt = _('Missing required field: {}').format
        self.assertListEqual(
            [fmt(_('Owner user')), fmt(_('Activity type'))],  # Not 'place'
            # act_desc1.errors,
            act_item1.errors,
        )

    def test_brick_error02(self):
        "Missing required custom-field."
        customfield = CustomField.objects.create(
            content_type=FakeOrganisation,
            name='Rate', field_type=CustomField.INT, is_required=True,
        )

        desc = CustomFormDescriptor(
            id='test-fakeorga_creation',
            model=FakeOrganisation,
            verbose_name='Creation form for FakeOrganisation',
        )
        cfci = CustomFormConfigItem.objects.create_if_needed(
            descriptor=desc,
            groups_desc=[{
                'name': 'General',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                    # EntityCellCustomField(customfield),
                ],
            }],
        )
        registry = CustomFormDescriptorRegistry().register(desc)

        user = self.create_user()

        brick = bricks.CustomFormsBrick()
        brick.registry = registry

        # act_desc1 = brick.get_ctype_descriptors(
        #     user=user, expanded_ctype_id=None,
        # )[0].descriptors[0]
        act_item1 = brick.get_ctype_descriptors(
            user=user, expanded_ctype_id=None,
        )[0].descriptors[0].items[0]
        # self.assertEqual(desc.id, act_desc1.id)
        self.assertEqual(cfci.id, act_item1.id)
        self.assertListEqual(
            [_('Missing required custom field: {}').format(customfield.name)],
            # act_desc1.errors,
            act_item1.errors,
        )

    def test_brick_error03(self):
        "Missing required extra field."
        desc = CustomFormDescriptor(
            id='test-fakeactivity_creation',
            model=FakeActivity,
            verbose_name='Creation form for FakeActivity',
            excluded_fields=['start', 'end'],
            extra_sub_cells=[
                fake_forms.FakeActivityStartSubCell(),
                fake_forms.FakeActivityEndSubCell(),
            ],
        )
        cfci = CustomFormConfigItem.objects.create_if_needed(
            descriptor=desc,
            groups_desc=[{
                'name': 'General',
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'title'}),
                    (EntityCellRegularField, {'name': 'type'}),
                    (EntityCellRegularField, {'name': 'place'}),
                ],
            }],
        )
        registry = CustomFormDescriptorRegistry().register(desc)

        user = self.create_user()

        brick = bricks.CustomFormsBrick()
        brick.registry = registry

        # act_desc1 = brick.get_ctype_descriptors(
        #     user=user, expanded_ctype_id=None,
        # )[0].descriptors[0]
        act_item1 = brick.get_ctype_descriptors(
            user=user, expanded_ctype_id=None,
        )[0].descriptors[0].items[0]
        # self.assertEqual(desc.id, act_desc1.id)
        self.assertEqual(cfci.id, act_item1.id)
        self.assertListEqual(
            [
                _('Missing required special field: {}').format('Start'),
            ],
            # act_desc1.errors,
            act_item1.errors,
        )

    def test_brick_show_details(self):
        user = self.login()

        def get_state():
            return BrickState.objects.get_for_brick_id(
                user=user, brick_id=CustomFormsBrick.id_,
            )

        self.assertIsNone(get_state().pk)

        url = reverse('creme_config__customforms_brick_show_details')
        self.assertGET405(url)

        # ---
        key = 'ct_id'
        get_ct = ContentType.objects.get_for_model
        ct_id01 = get_ct(FakeActivity).id
        self.assertPOST200(url, data={key: ct_id01})
        state1 = get_state()
        self.assertIsNotNone(state1.pk)
        self.assertEqual(
            state1.get_extra_data(BRICK_STATE_SHOW_CFORMS_DETAILS),
            ct_id01,
        )

        # ---
        ct_id02 = get_ct(FakeOrganisation).id
        self.assertPOST200(url, data={key: ct_id02})
        self.assertEqual(
            get_state().get_extra_data(BRICK_STATE_SHOW_CFORMS_DETAILS),
            ct_id02,
        )

        # Invalid ID
        self.assertPOST404(url, data={key: 1024})

        # ID==0 => clear
        self.assertPOST200(url, data={key: '0'})
        # TODO: has_extra_data() ??
        self.assertIsNone(
            get_state().get_extra_data(BRICK_STATE_SHOW_CFORMS_DETAILS),
        )

        # Check does not crash
        self.assertPOST200(url, data={key: '0'})

    # TODO: test credentials for views
