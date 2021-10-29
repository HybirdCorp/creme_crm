# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellRegularField,
)
from creme.creme_core.models import (
    CustomField,
    FieldsConfig,
    SearchConfigItem,
    UserRole,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_models import (
    FakeContact,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.content_type import entity_ctypes
from creme.creme_core.utils.unicode_collation import collator

from ..bricks import SearchConfigBrick


class SearchConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    PORTAL_URL = reverse('creme_config__search')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        SearchConfigItem.objects.all().delete()  # TODO: backup ?

        get_ct = ContentType.objects.get_for_model
        cls.ct_contact = get_ct(FakeContact)
        cls.ct_orga    = get_ct(FakeOrganisation)

    def setUp(self):
        super().setUp()
        self.login()

    @staticmethod
    def _build_add_url(ctype):
        return reverse('creme_config__create_search_config', args=(ctype.id,))

    @staticmethod
    def _build_edit_url(sci):
        return reverse('creme_config__edit_search_config', args=(sci.id,))

    @staticmethod
    def _get_first_entity_ctype():
        ctypes = [*entity_ctypes()]
        ctypes.sort(key=lambda ct: collator.sort_key(str(ct)))

        return ctypes[0]

    def test_portal01(self):
        ctype = self._get_first_entity_ctype()
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ctype))

        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'creme_config/portals/search.html')
        self.assertTemplateUsed(response, 'creme_config/bricks/search-config.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            SearchConfigBrick.id_,
        )
        title_node = self.get_html_node_or_fail(
            brick_node, ".//div[@class='search-config-group-title']",
        )
        self.assertEqual([str(ctype)], [text.strip() for text in title_node.itertext()])

        # Missing default configurations are built
        sci = self.get_object_or_fail(SearchConfigItem, content_type=ctype)
        self.assertIsNone(sci.role)
        self.assertFalse(sci.superuser)
        self.assertTrue(sci.all_fields)

    def test_portal02(self):
        "Missing default configurations are built, even when configs for users exist."
        ctype = self._get_first_entity_ctype()
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ctype))

        SearchConfigItem.objects.create(content_type=ctype, superuser=True)

        self.assertGET200(self.PORTAL_URL)
        self.get_object_or_fail(
            SearchConfigItem,
            content_type=ctype, role=None, superuser=False,
        )

    def test_add01(self):
        role = self.role
        ct = self.ct_contact
        self.assertFalse(
            SearchConfigItem.objects.filter(content_type=ct, role=None, superuser=True)
        )

        url = self._build_add_url(ct)
        context = self.assertGET200(url).context
        self.assertEqual(
            _('New search configuration for «{model}»').format(model='Test Contact'),
            context.get('title'),
        )

        with self.assertNoException():
            # fields = context['form'].fields['fields']
            cells_f = context['form'].fields['cells']
            # choices = fields.choices

        # self.assertFalse(fields.initial)
        self.assertFalse(cells_f.initial)

        # fname = 'last_name'
        fname1 = 'last_name'
        # index = self.assertInChoices(value=fname, label=_('Last name'), choices=choices)

        fname2 = 'civility__title'
        # self.assertInChoices(value='first_name', label=_('First name'), choices=choices)
        # self.assertInChoices(
        #     value='civility__title',
        #     label=f"[{_('Civility')}] - {_('Title')}",
        #     choices=choices,
        # )
        # self.assertNotInChoices(value='birthday', choices=choices)

        fname3 = 'sector__title'
        fname4 = 'languages__name'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'role': role.id,

                # f'fields_check_{index}': 'on',
                # f'fields_value_{index}': fname,
                # f'fields_order_{index}': 1,
                'cells': f'regular_field-{fname1},'
                         f'regular_field-{fname2},'
                         f'regular_field-{fname3},'
                         f'regular_field-{fname4}'
            },
        ))

        sc_items = SearchConfigItem.objects.filter(content_type=ct)
        self.assertEqual(1, len(sc_items))

        sc_item = sc_items[0]
        self.assertEqual(role, sc_item.role)
        self.assertFalse(sc_item.superuser)
        self.assertFalse(sc_item.disabled)
        # self.assertEqual([fname], [sf.name for sf in sc_item.searchfields])
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, name)
                for name in (fname1, fname2, fname3, fname4)
            ],
            [*sc_item.cells],
        )

    def test_add02(self):
        "Other CT, super users."
        ct = self.ct_orga
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ct, superuser=True))

        self.assertNoFormError(self.client.post(
            self._build_add_url(ct), data={'role': ''}),
        )
        sc_item = self.get_object_or_fail(
            SearchConfigItem, content_type=ct, superuser=True, role=None,
        )
        self.assertTrue(sc_item.all_fields)

    def test_add03(self):
        "Unique configuration."
        role = self.role
        ct = self.ct_contact
        SearchConfigItem.objects.create(content_type=ct, role=role)

        role2 = UserRole.objects.create(name='CEO')

        response = self.assertGET200(self._build_add_url(ct))

        with self.assertNoException():
            role_f = response.context['form'].fields['role']
            choices = role_f.choices

        self.assertEqual(f"*{_('Superuser')}*", role_f.empty_label)

        self.assertInChoices(value=role2.id, label=str(role2), choices=choices)
        self.assertNotInChoices(value=role.id, choices=choices)

    def test_add04(self):
        "Unique configuration (super-user)."
        ct = self.ct_contact
        SearchConfigItem.objects.create_if_needed(
            FakeContact, role='superuser',
            fields=['first_name', 'last_name'],
        )

        response = self.assertGET200(self._build_add_url(ct))

        with self.assertNoException():
            role_f = response.context['form'].fields['role']

        self.assertIsNone(role_f.empty_label)

    def test_add_regular_fields_errors01(self):
        "Forbidden fields."
        url = self._build_add_url(self.ct_contact)

        def post(field_name, msg_fmt=None):
            response = self.assertPOST200(
                url, data={'cells': f'regular_field-{field_name}'}
            )
            if not msg_fmt:
                msg_fmt = _('This value is invalid: %(value)s')
            self.assertFormError(
                response, 'form', 'cells',
                # _('This value is invalid: %(value)s') % {'value': field_name},
                msg_fmt % {'value': field_name},
            )

        post('birthday')
        post('is_a_nerd')
        leaf_msg_fmt = _('This field has sub-field & cannot be selected: %(value)s')
        post('sector', msg_fmt=leaf_msg_fmt)  # FK
        post('languages', msg_fmt=leaf_msg_fmt)  # M2M
        post('image__user')
        post('image__user__username')

    def test_add_regular_fields_errors02(self):
        "Fields with 'choices' are not valid."
        field_name = 'discount_unit'
        model_field = FakeInvoiceLine._meta.get_field(field_name)
        self.assertTrue(model_field.choices)

        response = self.assertPOST200(
            self._build_add_url(ContentType.objects.get_for_model(FakeInvoiceLine)),
            data={'cells': f'regular_field-{field_name}'}
        )
        self.assertFormError(
            response, 'form', 'cells',
            _('This value is invalid: %(value)s') % {'value': field_name},
        )

    def test_add_regular_fields_errors03(self):
        "Exclude DatePeriodField."
        field_name = 'periodicity'
        response = self.assertPOST200(
            self._build_add_url(ContentType.objects.get_for_model(FakeInvoice)),
            data={'cells': f'regular_field-{field_name}'}
        )
        self.assertFormError(
            response, 'form', 'cells',
            _('This value is invalid: %(value)s') % {'value': field_name},
        )

    def test_add_custom_fields(self):
        ct = self.ct_orga
        create_cfield = partial(CustomField.objects.create, content_type=ct)
        cfield1 = create_cfield(name='ID number', field_type=CustomField.STR)
        cfield2 = create_cfield(name='2nd site',  field_type=CustomField.URL)
        cfield3 = create_cfield(name='Degree',    field_type=CustomField.ENUM)
        cfield4 = create_cfield(name='Hobbies',   field_type=CustomField.MULTI_ENUM)

        self.assertNoFormError(self.client.post(
            self._build_add_url(ct),
            data={
                'cells': f'custom_field-{cfield1.id},'
                         f'custom_field-{cfield2.id},'
                         f'custom_field-{cfield3.id},'
                         f'custom_field-{cfield4.id}'
            },
        ))

        sc_items = SearchConfigItem.objects.filter(content_type=ct)
        self.assertEqual(1, len(sc_items))
        self.assertListEqual(
            [
                EntityCellCustomField(cf)
                for cf in (cfield1, cfield2, cfield3, cfield4)
            ],
            [*sc_items[0].cells],
        )

    def test_add_custom_fields_errors(self):
        "Forbidden types."
        ct = self.ct_orga

        def post(cfield):
            response = self.assertPOST200(
                self._build_add_url(ct),
                data={'cells': f'custom_field-{cfield.id}'}
            )
            self.assertFormError(
                response, 'form', 'cells',
                _('This value is invalid: %(value)s') % {'value': cfield.id},
            )

        create_cfield = partial(CustomField.objects.create, content_type=ct)
        post(create_cfield(name='To be sold?',  field_type=CustomField.BOOL))
        post(create_cfield(name='Inauguration', field_type=CustomField.DATE))
        post(create_cfield(name='Next fiesta',  field_type=CustomField.DATETIME))

    # def _edit_config(self, url, sci, names_indexes, disabled=''):
    #     data = {'disabled': disabled}
    #     names = []
    #
    #     for order, (name, index) in enumerate(names_indexes, start=1):
    #         data[f'fields_check_{index}'] = 'on'
    #         data[f'fields_value_{index}'] = name
    #         data[f'fields_order_{index}'] = order
    #
    #         names.append(name)
    #
    #     response = self.client.post(url, data=data)
    #     self.assertNoFormError(response)
    #
    #     sci = self.refresh(sci)
    #     self.assertEqual(names, [sf.name for sf in sci.searchfields])
    #
    #     return sci
    def _edit_config(self, url, sci, *field_ids, disabled=''):
        cell_keys = [
            f'regular_field-{field_id}'
            for field_id in field_ids
        ]

        response = self.client.post(
            url, data={'disabled': disabled, 'cells': ','.join(cell_keys)},
        )
        self.assertNoFormError(response)

        sci = self.refresh(sci)
        self.assertListEqual(cell_keys, [c.key for c in sci.cells])

        return sci

    def test_edit01(self):
        sci = SearchConfigItem.objects.create_if_needed(FakeContact, fields=['last_name'])
        self.assertIsNone(sci.role)

        url = self._build_edit_url(sci)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit «{object}»').format(object=sci), context.get('title'))

        with self.assertNoException():
            # fields = context['form'].fields['fields']
            # choices = fields.choices
            cells_f = context['form'].fields['cells']

        # self.assertEqual(['last_name'], fields.initial)
        self.assertListEqual(
            [EntityCellRegularField.build(FakeContact, 'last_name')],
            cells_f.initial,
        )

        fname1 = 'last_name'
        # index1 = self.assertInChoices(value=fname1, label=_('Last name'), choices=choices)

        fname2 = 'first_name'
        # index2 = self.assertInChoices(value=fname2, label=_('First name'), choices=choices)
        #
        # self.assertInChoices(
        #     value='civility__title',
        #     label='[{}] - {}'.format(_('Civility'), _('Title')),
        #     choices=choices,
        # )
        # self.assertNotInChoices(value='birthday', choices=choices)

        # sci = self._edit_config(url, sci, ((fname1, index1), (fname2, index2)))
        sci = self._edit_config(url, sci, fname1, fname2)
        self.assertFalse(sci.disabled)

    def test_edit02(self):
        "Other CT + role + exclude BooleanField."
        sci = SearchConfigItem.objects.create(content_type=self.ct_orga, role=self.role)
        url = self._build_edit_url(sci)
        # response = self.assertGET200(url)

        # with self.assertNoException():
        #     choices = response.context['form'].fields['fields'].choices

        fname1 = 'name'
        # index1 = self.assertInChoices(value=fname1, label=_('Name'), choices=choices)

        fname2 = 'description'
        # index2 = self.assertInChoices(value=fname2, label=_('Description'), choices=choices)

        # self.assertNotInChoices(value='subject_to_vat', choices=choices)

        # self._edit_config(url, sci, ((fname1, index1), (fname2, index2)))
        self._edit_config(url, sci, fname1, fname2)

    # def test_edit03(self):
    def test_edit_disabled(self):
        sci = SearchConfigItem.objects.create(content_type=self.ct_contact)
        url = self._build_edit_url(sci)
        # response = self.assertGET200(url)

        # with self.assertNoException():
        #     choices = response.context['form'].fields['fields'].choices

        # fname = 'last_name'
        # index = self.assertInChoices(value=fname, label=_('Last name'), choices=choices)
        # sci = self._edit_config(url, sci, [(fname, index)], disabled='on')
        sci = self._edit_config(url, sci, 'last_name', disabled='on')
        self.assertTrue(sci.disabled)

    # def test_edit04(self):
    #     "Fields with 'choices' are not valid."
    #     fname = 'discount_unit'
    #     mfield = FakeInvoiceLine._meta.get_field(fname)
    #     self.assertTrue(mfield.choices)
    #
    #     sci = SearchConfigItem.objects.create(content_type=FakeInvoiceLine)
    #     response = self.assertGET200(self._build_edit_url(sci))
    #
    #     with self.assertNoException():
    #         choices = response.context['form'].fields['fields'].choices
    #
    #     self.assertInChoices(value='item', label='Item', choices=choices)
    #     self.assertNotInChoices(value=fname, choices=choices)

    # def test_edit05(self):
    #     "Exclude DatePeriodField."
    #     sci =SearchConfigItem.objects.create(content_type=FakeInvoice)
    #
    #     response = self.assertGET200(self._build_edit_url(sci))
    #
    #     with self.assertNoException():
    #         choices = response.context['form'].fields['fields'].choices
    #
    #     self.assertInChoices(value='name', label=_('Name'), choices=choices)
    #     self.assertNotInChoices(value='periodicity', choices=choices)

    # def test_edit06(self):
    def test_edit_fields_config01(self):
        "With FieldsConfig."
        model = FakeContact
        hidden_fname1 = 'position'
        hidden_fname2 = 'description'  # NB: in CremeEntity
        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )
        sci = SearchConfigItem.objects.create_if_needed(model, fields=['first_name'])

        # response = self.assertGET200(self._build_edit_url(sci))
        #
        # with self.assertNoException():
        #     fields_f = response.context['form'].fields['fields']
        #     choices = fields_f.choices
        #
        # self.assertListEqual(['first_name'], fields_f.initial)
        #
        # self.assertInChoices(value='first_name', label=_('First name'), choices=choices)
        # self.assertInChoices(
        #     value='civility__title',
        #     label=f"[{_('Civility')}] - {_('Title')}",
        #     choices=choices,
        # )
        #
        # self.assertNotInChoices(value=hidden_fname1,     choices=choices)
        # self.assertNotInChoices(value='position__title', choices=choices)

        url = self._build_edit_url(sci)

        def post(hidden_name):
            response = self.assertPOST200(
                url,
                data={'cells': f'regular_field-{hidden_name}'}
            )
            self.assertFormError(
                response, 'form', 'cells',
                _('This value is invalid: %(value)s') % {'value': hidden_name},
            )

        post(hidden_fname1)
        post(hidden_fname2)

        # ---
        field_name = 'last_name'
        sci = self._edit_config(url, sci, field_name)
        self.assertListEqual(
            [f'regular_field-{field_name}'],
            [c.key for c in self.refresh(sci).cells],
        )

    # def test_edit07(self):
    def test_edit_fields_config02(self):
        "With FieldsConfig + selected hidden fields."
        model = FakeContact
        hidden_fname1 = 'description'
        hidden_fname2 = 'position'
        hidden_sub_fname2 = hidden_fname2 + '__title'
        sci = SearchConfigItem.objects.create_if_needed(
            model,
            fields=['first_name', hidden_fname1, hidden_sub_fname2],
        )

        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        # response = self.assertGET200(self._build_edit_url(sci))
        #
        # with self.assertNoException():
        #     fields_f = response.context['form'].fields['fields']
        #     choices = fields_f.choices
        #
        # self.assertListEqual(
        #     ['first_name', hidden_fname1, hidden_sub_fname2],
        #     fields_f.initial,
        # )
        #
        # self.assertInChoices(value='first_name',  label=_('First name'),  choices=choices)
        # self.assertInChoices(value=hidden_fname1, label=_('Description'), choices=choices)
        # self.assertInChoices(
        #     value=hidden_sub_fname2,
        #     label=f"[{_('Position')}] - {_('Title')}",
        #     choices=choices,
        # )
        field_name = 'last_name'
        sci = self._edit_config(
            self._build_edit_url(sci), sci, field_name, hidden_sub_fname2,
        )
        self.assertListEqual(
            [f'regular_field-{field_name}', f'regular_field-{hidden_sub_fname2}'],
            [c.key for c in self.refresh(sci).cells],
        )

    def test_delete01(self):
        sci = SearchConfigItem.objects.create_if_needed(
            FakeContact, role=self.role, fields=['first_name', 'last_name'],
        )
        self.assertPOST200(reverse('creme_config__delete_search_config'), data={'id': sci.id})
        self.assertDoesNotExist(sci)

    def test_delete02(self):
        "Super users."
        sci = SearchConfigItem.objects.create_if_needed(
            FakeContact, role='superuser', fields=['first_name', 'last_name'],
        )
        self.assertPOST200(reverse('creme_config__delete_search_config'), data={'id': sci.id})
        self.assertDoesNotExist(sci)

    def test_delete03(self):
        "Cannot delete the default configuration."
        sci = SearchConfigItem.objects.create_if_needed(FakeContact, ['first_name', 'last_name'])
        self.assertPOST409(reverse('creme_config__delete_search_config'), data={'id': sci.id})
        self.assertStillExists(sci)
