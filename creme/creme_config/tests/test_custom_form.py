# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.forms import IntegerField
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape
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
    CustomField,
    CustomFormConfigItem,
    FakeActivity,
    FakeOrganisation,
    FieldsConfig,
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
        self.assertTemplateUsed(response, 'creme_config/custom_form_portal.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url')
        )
        self.get_brick_node(
            self.get_html_tree(response.content),
            bricks.CustomFormsBrick.id_,
        )

    def test_group_edition01(self):
        self.login()

        cform_id = FAKEACTIVITY_CREATION_CFORM.id
        url = reverse('creme_config__edit_custom_form_group', args=(cform_id, 0))
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

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
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

        url = reverse(
            'creme_config__edit_custom_form_group',
            args=(FAKEACTIVITY_CREATION_CFORM.id, 1),
        )
        response1 = self.assertGET200(url)
        context = response1.context
        self.assertEqual(
            _('Edit the group «{group}»').format(group='Where & when'),
            context.get('title')
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

        cfci = self.get_object_or_fail(
            CustomFormConfigItem, cform_id=FAKEACTIVITY_CREATION_CFORM.id,
        )
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

        cform_id = FAKEACTIVITY_CREATION_CFORM.id

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)

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
            reverse('creme_config__edit_custom_form_group', args=(cform_id, 1)),
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

        response1 = self.assertGET200(reverse(
            'creme_config__edit_custom_form_group', args=(FAKEACTIVITY_CREATION_CFORM.id, 1)
        ))

        with self.assertNoException():
            ignored_cells1 = [*response1.context['form'].fields['cells'].ignored_cells]

        self.assertNotIn(prop_cell, ignored_cells1)
        self.assertNotIn(rel_cell, ignored_cells1)

        # ---
        response2 = self.assertGET200(reverse(
            'creme_config__edit_custom_form_group', args=(FAKEACTIVITY_EDITION_CFORM.id, 1)
        ))

        with self.assertNoException():
            ignored_cells2 = [*response2.context['form'].fields['cells'].ignored_cells]

        self.assertIn(prop_cell, ignored_cells2)
        self.assertIn(rel_cell, ignored_cells2)

    def test_group_edition05(self):
        "Non hiddable fields (because already selected)."
        self.login()
        desc = FAKEORGANISATION_CREATION_CFORM
        hidden = 'sector'

        # See fake_populate in core
        self.assertIn(
            hidden,
            [
                cell.value
                for cell in getattr(desc.groups()[0], 'cells', ())
                if isinstance(cell, EntityCellRegularField)
            ],
        )

        FieldsConfig.objects.create(
            content_type=FakeOrganisation,
            descriptions=[(hidden, {FieldsConfig.HIDDEN: True})],
        )

        response = self.assertGET200(reverse(
            'creme_config__edit_custom_form_group', args=(desc.id, 0)
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

        def build_url(group_id):
            return reverse(
                'creme_config__edit_custom_form_group',
                args=(FAKEACTIVITY_CREATION_CFORM.id, group_id),
            )

        with self.assertRaises(NoReverseMatch):
            self.assertGET404(build_url(group_id='notanint'))

        with self.assertRaises(NoReverseMatch):
            self.assertGET404(build_url(group_id=-1))

        self.assertContains(
            self.client.get(build_url(group_id=3)),
            escape('The group ID "3" is invalid.'),
            status_code=409,
        )
        self.assertContains(
            self.client.get(build_url(group_id=4)),
            escape('The group ID "4" is invalid.'),
            status_code=409,
        )

    def test_group_edition_error02(self):
        "Not registered id."
        self.login()

        cform_id = 'creme_core-invalid'
        CustomFormConfigItem.objects.create(cform_id=cform_id)

        self.assertContains(
            self.client.get(
                reverse('creme_config__edit_custom_form_group', args=(cform_id, 0)),
            ),
            escape(f'The custom form "{cform_id}" is invalid.'),
            status_code=409,
        )

    def test_group_edition_error03(self):
        "Bad type of cell."
        self.login()

        base_cell_keys = [
            f'regular_field-{name}' for name in ('user', 'type', 'title')
        ]
        url = reverse(
            'creme_config__edit_custom_form_group',
            args=(FAKEACTIVITY_CREATION_CFORM.id, 0),
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

        response = self.assertPOST200(
            reverse(
                'creme_config__edit_custom_form_group',
                args=(FAKEACTIVITY_CREATION_CFORM.id, 0),
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

        cform_id = FAKEACTIVITY_CREATION_CFORM.id
        url = reverse('creme_config__edit_custom_form_group', args=(cform_id, 1))

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

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
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

        cform_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)

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
                args=(cform_id, len(old_groups) - 1),
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

        cform_id = FAKEACTIVITY_CREATION_CFORM.id
        url = reverse('creme_config__edit_custom_form_group', args=(cform_id, 1))

        # First step: we remove the extra fields 'start' & 'end'
        response = self.client.post(
            url,
            data={
                'name': 'Where',
                'cells': 'regular_field-place',
            },
        )
        self.assertNoFormError(response)

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
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

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
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

        response = self.client.post(
            reverse(
                'creme_config__edit_custom_form_group',
                args=(FAKEACTIVITY_CREATION_CFORM.id, 0),
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

        cform_id = FAKEACTIVITY_CREATION_CFORM.id
        response = self.client.post(
            reverse('creme_config__edit_custom_form_group', args=(cform_id, 0)),
            data={
                'name': 'Main',
                'cells': 'cform_special-regularfields',
            },
        )
        self.assertNoFormError(response)

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
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

        cform_id = FAKEACTIVITY_CREATION_CFORM.id
        url = reverse('creme_config__edit_custom_form_group', args=(cform_id, 2))

        # First step: we remove the special fields 'remaining custom-fields'
        response = self.client.post(
            url,
            data={
                'name': 'Custom fields',
                'cells': 'regular_field-minutes',  # Group cannot be empty...
            },
        )
        self.assertNoFormError(response)

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
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

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
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

        response = self.client.post(
            reverse(
                'creme_config__edit_custom_form_group',
                args=(FAKEACTIVITY_CREATION_CFORM.id, 0),
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

    def test_group_creation_regularfields01(self):
        self.login()

        group_name1 = 'Required fields'
        fields1 = ('user', 'title', 'place', 'type')

        cform_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
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

        url = reverse('creme_config__add_custom_form_group', args=(cform_id,))
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

        cform_id = FAKEACTIVITY_CREATION_CFORM.id
        group_name3 = 'Empty group'
        response = self.client.post(
            reverse('creme_config__add_custom_form_group', args=(cform_id,)),
            data={
                'name': group_name3,
                # 'cells': ...,
            },
        )
        self.assertNoFormError(response)

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)

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

        cform_id = FAKEACTIVITY_CREATION_CFORM.id
        group_name = 'Custom Fields'
        url = reverse('creme_config__add_custom_form_group', args=(cform_id,))
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

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
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

        response = self.assertPOST200(
            reverse(
                'creme_config__add_custom_form_group', args=(FAKEACTIVITY_CREATION_CFORM.id,)
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

        response1 = self.assertGET200(reverse(
            'creme_config__add_custom_form_group', args=[FAKEACTIVITY_CREATION_CFORM.id],
        ))

        with self.assertNoException():
            ignored_cells1 = [*response1.context['form'].fields['cells'].ignored_cells]

        self.assertNotIn(prop_cell, ignored_cells1)
        self.assertNotIn(rel_cell, ignored_cells1)

        # ---
        response2 = self.assertGET200(reverse(
            'creme_config__add_custom_form_group', args=[FAKEACTIVITY_EDITION_CFORM.id],
        ))

        with self.assertNoException():
            ignored_cells2 = [*response2.context['form'].fields['cells'].ignored_cells]

        self.assertIn(prop_cell, ignored_cells2)
        self.assertIn(rel_cell, ignored_cells2)

    def test_extra_group01(self):
        "Adding extra group."
        self.login()

        # See fake_populate
        self.assertFalse(
            [
                group
                for group in FAKEORGANISATION_CREATION_CFORM.groups()
                if isinstance(group, FakeAddressGroup)
            ]
        )

        cform_id = FAKEORGANISATION_CREATION_CFORM.id
        url = reverse('creme_config__add_custom_form_extra_group', args=[cform_id])
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

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
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
            reverse('creme_config__edit_custom_form_group', args=(cform_id, 1))
        )
        # Adding a group does not crash (extra group has no cell)
        self.assertGET200(
            reverse('creme_config__add_custom_form_group', args=(cform_id,))
        )

    def test_extra_group02(self):
        "Descriptor without extra group class."
        self.login()

        self.assertGET409(reverse(
            'creme_config__add_custom_form_extra_group',
            args=[FAKEACTIVITY_CREATION_CFORM.id],
        ))

    @parameterized.expand([
        (0, ['Where & when', 'Custom fields']),
        (1, ['General', 'Custom fields']),
    ])
    def test_group_deletion(self, deleted_group_id, remaining_group_names):
        self.login()
        cform_id = FAKEACTIVITY_CREATION_CFORM.id

        url = reverse('creme_config__delete_custom_form_group', args=(cform_id,))
        self.assertGET405(url)
        self.assertPOST200(url, data={'group_id': deleted_group_id})

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)

        dict_groups = cfci.groups_as_dicts()
        self.assertEqual(len(remaining_group_names), len(dict_groups))
        self.assertListEqual(
            remaining_group_names,
            [dict_group['name'] for dict_group in dict_groups],
        )

    def test_group_deletion_error(self):
        "Invalid ID."
        self.login()

        url = reverse(
            'creme_config__delete_custom_form_group', args=[FAKEACTIVITY_CREATION_CFORM.id],
        )
        self.assertPOST404(url, data={'group_id': 'notanint'})
        self.assertContains(
            self.client.post(url, data={'group_id': 3}),
            escape('The group ID "3" is invalid.'),
            status_code=409,
        )

    def test_delete_cell(self):
        self.login()
        desc = FAKEACTIVITY_CREATION_CFORM
        cform_id = desc.id

        cell_key = 'regular_field-place'

        # See fake_populate in core
        group1 = desc.groups()[1]
        self.assertIn(cell_key, [cell.key for cell in group1.cells])
        self.assertEqual(LAYOUT_DUAL_SECOND, group1.layout)

        url = reverse('creme_config__delete_custom_form_cell', args=(cform_id,))
        self.assertGET405(url)

        data = {'cell_key': cell_key}
        self.assertPOST200(url, data=data)

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
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

    @parameterized.expand([
        (0, LAYOUT_DUAL_FIRST),
        (1, LAYOUT_DUAL_SECOND),
    ])
    def test_group_set_layout(self, group_id, layout):
        self.login()
        cform_id = FAKEACTIVITY_CREATION_CFORM.id

        url = reverse('creme_config__setlayout_custom_form_group', args=(cform_id, group_id))
        self.assertGET405(url)
        self.assertPOST200(url, data={'layout': layout})

        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        self.assertEqual(layout, cfci.groups_as_dicts()[group_id]['layout'])

    def test_group_set_layout_error(self):
        "Invalid group, invalid layout."
        self.login()
        cform_id = FAKEACTIVITY_CREATION_CFORM.id

        self.assertPOST409(
            reverse('creme_config__setlayout_custom_form_group', args=(cform_id, 3)),
            data={'layout': LAYOUT_DUAL_SECOND},
        )
        self.assertPOST409(
            reverse('creme_config__setlayout_custom_form_group', args=(cform_id, 1)),
            data={'layout': 'INVALID'},
        )

    def test_group_reorder(self):
        self.login()

        group_id = 0
        target = 1

        cform_id = FAKEACTIVITY_CREATION_CFORM.id
        cfci = self.get_object_or_fail(CustomFormConfigItem, cform_id=cform_id)
        old_groups = cfci.groups_as_dicts()

        url = reverse('creme_config__reorder_custom_form_group', args=(cform_id, group_id))
        self.assertGET405(url)
        self.assertPOST200(url, data={'target': target})

        cfci = self.refresh(cfci)
        self.assertEqual(old_groups[group_id], cfci.groups_as_dicts()[target])

        # Errors
        self.assertPOST409(
            # Bad group ID
            reverse('creme_config__reorder_custom_form_group', args=(cform_id, 123)),
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

        CustomFormConfigItem.objects.create_if_needed(
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
        CustomFormConfigItem.objects.create_if_needed(
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
        CustomFormConfigItem.objects.create_if_needed(
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

        desc_data = brick.get_ctype_descriptors(user=user)
        self.assertIsInstance(desc_data, list)
        self.assertEqual(2, len(desc_data))

        def get_descriptors(model):
            ct = ContentType.objects.get_for_model(model)
            for ct_wrapper in desc_data:
                if ct_wrapper.ctype == ct:
                    return ct_wrapper.descriptors

            self.fail(f'No descriptor found for {ct}')

        activity_descriptors = get_descriptors(FakeActivity)
        self.assertEqual(2, len(activity_descriptors))

        act_desc1 = activity_descriptors[0]
        self.assertEqual(desc1.id,           act_desc1.id)
        self.assertEqual(desc1.verbose_name, act_desc1.verbose_name)
        self.assertListEqual(
            ['General', 'Where'],
            [g.name for g in act_desc1.groups],
        )
        self.assertListEqual([], act_desc1.errors)

        act_desc2 = activity_descriptors[1]
        self.assertEqual(desc2.id,           act_desc2.id)
        self.assertEqual(desc2.verbose_name, act_desc2.verbose_name)
        self.assertListEqual(['Misc'], [g.name for g in act_desc2.groups])
        self.assertListEqual([], act_desc2.errors)

        orga_descriptors = get_descriptors(FakeOrganisation)
        self.assertEqual(1, len(orga_descriptors))

        orga_desc = orga_descriptors[0]
        self.assertEqual(desc3.id,           orga_desc.id)
        self.assertEqual(desc3.verbose_name, orga_desc.verbose_name)
        self.assertListEqual(['General'], [g.name for g in orga_desc.groups])
        self.assertListEqual([], orga_desc.errors)

    def test_brick_error01(self):
        "Missing regular field."
        desc = CustomFormDescriptor(
            id='test-fakeactivity_creation',
            model=FakeActivity,
            verbose_name='Creation form for FakeActivity',
            excluded_fields=['place'],
        )
        CustomFormConfigItem.objects.create_if_needed(
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

        act_desc1 = brick.get_ctype_descriptors(user=user)[0].descriptors[0]
        self.assertEqual(desc.id, act_desc1.id)
        fmt = _('Missing required field: {}').format
        self.assertListEqual(
            [fmt(_('Owner user')), fmt(_('Activity type'))],  # Not 'place'
            act_desc1.errors,
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
        CustomFormConfigItem.objects.create_if_needed(
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

        act_desc1 = brick.get_ctype_descriptors(user=user)[0].descriptors[0]
        self.assertEqual(desc.id, act_desc1.id)
        self.assertListEqual(
            [_('Missing required custom field: {}').format(customfield.name)],
            act_desc1.errors,
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
        CustomFormConfigItem.objects.create_if_needed(
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

        act_desc1 = brick.get_ctype_descriptors(user=user)[0].descriptors[0]
        self.assertEqual(desc.id, act_desc1.id)
        self.assertListEqual(
            [
                _('Missing required special field: {}').format('Start'),
            ],
            act_desc1.errors,
        )

    # TODO: test credentials for views
