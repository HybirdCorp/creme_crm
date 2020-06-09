# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.translation import gettext as _

    from creme.creme_core.models import SearchConfigItem, UserRole, FieldsConfig
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import FakeContact, FakeOrganisation, FakeInvoice, FakeInvoiceLine
    from creme.creme_core.tests.views.base import BrickTestCaseMixin
    from creme.creme_core.utils.content_type import entity_ctypes
    from creme.creme_core.utils.unicode_collation import collator

    from ..bricks import SearchConfigBrick
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class SearchConfigTestCase(CremeTestCase, BrickTestCaseMixin):
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

    def _build_add_url(self, ctype):
        return reverse('creme_config__create_search_config', args=(ctype.id,))

    def _build_edit_url(self, sci):
        return reverse('creme_config__edit_search_config', args=(sci.id,))

    def _get_first_entity_ctype(self):
        ctypes = [*entity_ctypes()]
        ctypes.sort(key=lambda ct: collator.sort_key(str(ct)))

        return ctypes[0]

    def test_portal01(self):
        ctype = self._get_first_entity_ctype()
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ctype))

        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'creme_config/search_portal.html')
        self.assertTemplateUsed(response, 'creme_config/bricks/search-config.html')
        self.assertEqual(reverse('creme_core__reload_bricks'),
                         response.context.get('bricks_reload_url')
                        )

        brick_node = self.get_brick_node(self.get_html_tree(response.content), SearchConfigBrick.id_)
        title_node = brick_node.find(".//div[@class='search-config-group-title']")
        self.assertIsNotNone(title_node)
        self.assertEqual([str(ctype)], [text.strip() for text in title_node.itertext()])

        # Missing default configurations are built
        sci = self.get_object_or_fail(SearchConfigItem, content_type=ctype)
        self.assertIsNone(sci.role)
        self.assertFalse(sci.superuser)
        self.assertTrue(sci.all_fields)

    def test_portal02(self):
        "Missing default configurations are built, even when configs for users exist"
        ctype = self._get_first_entity_ctype()
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ctype))

        SearchConfigItem.objects.create(content_type=ctype, superuser=True)

        self.assertGET200(self.PORTAL_URL)
        self.get_object_or_fail(SearchConfigItem, content_type=ctype,
                                role=None, superuser=False,
                               )

    def test_add01(self):
        role = self.role
        ct = self.ct_contact
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ct, role=None, superuser=True))

        url = self._build_add_url(ct)
        context = self.assertGET200(url).context
        self.assertEqual(_('New search configuration for «{model}»').format(model='Test Contact'),
                         context.get('title')
                        )

        with self.assertNoException():
            fields = context['form'].fields['fields']
            choices = fields.choices

        self.assertFalse(fields.initial)

        fname = 'last_name'
        index = self.assertInChoices(value=fname, label=_('Last name'), choices=choices)

        self.assertInChoices(value='first_name', label=_('First name'), choices=choices)
        self.assertInChoices(
            value='civility__title',
            label='[{}] - {}'.format(_('Civility'), _('Title')),
            choices=choices,
        )
        self.assertNotInChoices(value='birthday', choices=choices)

        self.assertNoFormError(self.client.post(
            url,
            data={
                'role': role.id,

                f'fields_check_{index}': 'on',
                f'fields_value_{index}': fname,
                f'fields_order_{index}': 1,
            },
        ))

        sc_items = SearchConfigItem.objects.filter(content_type=ct)
        self.assertEqual(1, len(sc_items))

        sc_item = sc_items[0]
        self.assertEqual(role, sc_item.role)
        self.assertFalse(sc_item.superuser)
        self.assertFalse(sc_item.disabled)
        self.assertEqual([fname], [sf.name for sf in sc_item.searchfields])

    def test_add02(self):
        "Other CT, super users"
        ct = self.ct_orga
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ct, superuser=True))

        self.assertNoFormError(self.client.post(self._build_add_url(ct),
                                                data={'role': ''},
                                               )
                              )
        sc_item = self.get_object_or_fail(SearchConfigItem, content_type=ct,
                                          superuser=True, role=None,
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

        self.assertEqual('*{}*'.format(_('Superuser')), role_f.empty_label)

        self.assertInChoices(value=role2.id, label=str(role2), choices=choices)
        self.assertNotInChoices(value=role.id, choices=choices)

    def test_add04(self):
        "Unique configuration (super-user)"
        ct = self.ct_contact
        SearchConfigItem.objects.create_if_needed(
            FakeContact, role='superuser',
            fields=['first_name', 'last_name'],
        )

        response = self.assertGET200(self._build_add_url(ct))

        with self.assertNoException():
            role_f = response.context['form'].fields['role']

        self.assertIsNone(role_f.empty_label)

    def _edit_config(self, url, sci, names_indexes, disabled=''):
        data = {'disabled': disabled}
        names = []

        for order, (name, index) in enumerate(names_indexes, start=1):
            data[f'fields_check_{index}'] = 'on'
            data[f'fields_value_{index}'] = name
            data[f'fields_order_{index}'] = order

            names.append(name)

        response = self.client.post(url, data=data)
        self.assertNoFormError(response)

        sci = self.refresh(sci)
        self.assertEqual(names, [sf.name for sf in sci.searchfields])

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
            fields = context['form'].fields['fields']
            choices = fields.choices

        self.assertEqual(['last_name'], fields.initial)

        fname1 = 'last_name'
        index1 = self.assertInChoices(value=fname1, label=_('Last name'), choices=choices)

        fname2 = 'first_name'
        index2 = self.assertInChoices(value=fname2, label=_('First name'), choices=choices)

        self.assertInChoices(
            value='civility__title',
            label='[{}] - {}'.format(_('Civility'), _('Title')),
            choices=choices,
        )
        self.assertNotInChoices(value='birthday', choices=choices)

        sci = self._edit_config(url, sci, ((fname1, index1), (fname2, index2)))
        self.assertFalse(sci.disabled)

    def test_edit02(self):
        "Other CT + role + exclude BooleanField."
        sci = SearchConfigItem.objects.create(content_type=self.ct_orga, role=self.role)
        url = self._build_edit_url(sci)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['fields'].choices

        fname1 = 'name'
        index1 = self.assertInChoices(value=fname1, label=_('Name'), choices=choices)

        fname2 = 'description'
        index2 = self.assertInChoices(value=fname2, label=_('Description'), choices=choices)

        self.assertNotInChoices(value='subject_to_vat', choices=choices)

        self._edit_config(url, sci, ((fname1, index1), (fname2, index2)))

    def test_edit03(self):
        "Disabled."
        sci = SearchConfigItem.objects.create(content_type=self.ct_contact)
        url = self._build_edit_url(sci)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['fields'].choices

        fname = 'last_name'
        index = self.assertInChoices(value=fname, label=_('Last name'), choices=choices)
        sci = self._edit_config(url, sci, [(fname, index)], disabled='on')
        self.assertTrue(sci.disabled)

    def test_edit04(self):
        "Fields with 'choices' are not valid."
        fname = 'discount_unit'
        mfield = FakeInvoiceLine._meta.get_field(fname)
        self.assertTrue(mfield.choices)

        sci = SearchConfigItem.objects.create(content_type=FakeInvoiceLine)
        response = self.assertGET200(self._build_edit_url(sci))

        with self.assertNoException():
            choices = response.context['form'].fields['fields'].choices

        self.assertInChoices(value='item', label='Item', choices=choices)
        self.assertNotInChoices(value=fname, choices=choices)

    def test_edit05(self):
        "Exclude DatePeriodField."
        sci = SearchConfigItem.objects.create(content_type=ContentType.objects.get_for_model(FakeInvoice))
        response = self.assertGET200(self._build_edit_url(sci))

        with self.assertNoException():
            choices = response.context['form'].fields['fields'].choices

        self.assertInChoices(value='name', label=_('Name'), choices=choices)
        self.assertNotInChoices(value='periodicity', choices=choices)

    def test_edit06(self):
        "With FieldsConfig."
        model = FakeContact
        hidden_fname1 = 'description'
        hidden_fname2 = 'position'
        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ]
        )
        sci = SearchConfigItem.objects.create_if_needed(model, fields=['first_name'])

        response = self.assertGET200(self._build_edit_url(sci))

        with self.assertNoException():
            fields_f = response.context['form'].fields['fields']
            choices = fields_f.choices

        self.assertListEqual(['first_name'], fields_f.initial)

        self.assertInChoices(value='first_name', label=_('First name'), choices=choices)
        self.assertInChoices(
            value='civility__title',
            label='[{}] - {}'.format(_('Civility'), _('Title')),
            choices=choices,
        )

        self.assertNotInChoices(value=hidden_fname1,     choices=choices)
        self.assertNotInChoices(value='position__title', choices=choices)

    def test_edit07(self):
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

        response = self.assertGET200(self._build_edit_url(sci))

        with self.assertNoException():
            fields_f = response.context['form'].fields['fields']
            choices = fields_f.choices

        self.assertEqual(['first_name', hidden_fname1, hidden_sub_fname2],
                         fields_f.initial
                        )

        self.assertInChoices(value='first_name',  label=_('First name'),  choices=choices)
        self.assertInChoices(value=hidden_fname1, label=_('Description'), choices=choices)
        self.assertInChoices(
            value=hidden_sub_fname2,
            label='[{}] - {}'.format(_('Position'), _('Title')),
            choices=choices,
        )

    def test_delete01(self):
        sci = SearchConfigItem.objects.create_if_needed(
            FakeContact, role=self.role, fields=['first_name', 'last_name'],
        )
        self.assertPOST200(reverse('creme_config__delete_search_config'), data={'id': sci.id})
        self.assertDoesNotExist(sci)

    def test_delete02(self):
        "Super users"
        sci = SearchConfigItem.objects.create_if_needed(
            FakeContact, role='superuser', fields=['first_name', 'last_name'],
        )
        self.assertPOST200(reverse('creme_config__delete_search_config'), data={'id': sci.id})
        self.assertDoesNotExist(sci)

    def test_delete03(self):
        "Cannot delete the default configuration"
        sci = SearchConfigItem.objects.create_if_needed(FakeContact, ['first_name', 'last_name'])
        self.assertPOST409(reverse('creme_config__delete_search_config'), data={'id': sci.id})
        self.assertStillExists(sci)
