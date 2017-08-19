# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import SearchConfigItem, UserRole, FieldsConfig
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import FakeContact, FakeOrganisation, FakeInvoice, FakeInvoiceLine
    from creme.creme_core.tests.views.base import BrickTestCaseMixin
    from creme.creme_core.utils import creme_entity_content_types
    from creme.creme_core.utils.unicode_collation import collator

    from ..bricks import SearchConfigBrick
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class SearchConfigTestCase(CremeTestCase, BrickTestCaseMixin):
    # PORTAL_URL = '/creme_config/search/portal/'
    PORTAL_URL = reverse('creme_config__search')

    @classmethod
    def setUpClass(cls):
        # CremeTestCase.setUpClass()
        super(SearchConfigTestCase, cls).setUpClass()

        SearchConfigItem.objects.all().delete()  # TODO: backup ?
        # cls.populate('creme_core')

        get_ct = ContentType.objects.get_for_model
        cls.ct_contact = get_ct(FakeContact)
        cls.ct_orga    = get_ct(FakeOrganisation)

    def setUp(self):
        self.login()

    def assertNoChoice(self, formfield, field_name):
        for i, (f_field_name, f_field_vname) in enumerate(formfield.choices):
            if f_field_name == field_name:
                self.fail(field_name + ' in choices')

    def _build_add_url(self, ctype):
        # return '/creme_config/search/add/%s' % ctype.id
        return reverse('creme_config__create_search_config', args=(ctype.id,))

    def _build_edit_url(self, sci):
        # return '/creme_config/search/edit/%s' % sci.id
        return reverse('creme_config__edit_search_config', args=(sci.id,))

    def _find_field_index(self, formfield, field_name):
        for i, (f_field_name, f_field_vname) in enumerate(formfield.choices):
            if f_field_name == field_name:
                return i

        self.fail('No "%s" in field' % field_name)

    def _assertNotInChoices(self, formfield, field_name):
        for f_field_name, f_field_vname in formfield.choices:
            if f_field_name == field_name:
                self.fail('"%s" found in choices' % field_name)

    def _get_first_entity_ctype(self):
        ctypes = list(creme_entity_content_types())
        ctypes.sort(key=lambda ct: collator.sort_key(unicode(ct)))

        return ctypes[0]

    def test_portal01(self):
        ctype = self._get_first_entity_ctype()
        self.assertFalse(SearchConfigItem.objects.filter(content_type=ctype))

        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'creme_config/search_portal.html')
        self.assertTemplateUsed(response, 'creme_config/bricks/search-config.html')
        # self.assertContains(response, ' id="%s"' % SearchConfigBlock.id_)
        # self.assertContains(response, unicode(ctype))

        brick_node = self.get_brick_node(self.get_html_tree(response.content), SearchConfigBrick.id_)
        title_node = brick_node.find(".//div[@class='search-config-group-title']")
        self.assertIsNotNone(title_node)
        # self.assertIn(unicode(ctype), title_node.text)
        self.assertEqual([unicode(ctype)], [text.strip() for text in title_node.itertext()])

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
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields['fields']

        self.assertFalse(fields.initial)

        fname = 'last_name'
        index = self._find_field_index(fields, fname)

        self._find_field_index(fields, 'first_name')
        self._find_field_index(fields, 'civility__title')
        self.assertNoChoice(fields, 'birthday')

        self.assertNoFormError(self.client.post(url,
                                                data={'role': role.id,

                                                      'fields_check_%s' % index: 'on',
                                                      'fields_value_%s' % index: fname,
                                                      'fields_order_%s' % index: 1,
                                                     },
                                               )
                              )

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
        "Unique configuration"
        role = self.role
        ct = self.ct_contact
        SearchConfigItem.objects.create(content_type=ct, role=role)

        role2 = UserRole.objects.create(name='CEO')

        response = self.assertGET200(self._build_add_url(ct))

        with self.assertNoException():
            role_f = response.context['form'].fields['role']
            choices = role_f.choices

        self.assertEqual(u'*%s*' % _(u'Superuser'), role_f.empty_label)

        role_ids = {c[0] for c in choices}
        self.assertIn(role2.id, role_ids)
        self.assertNotIn(role.id, role_ids)

    def test_add04(self):
        "Unique configuration (super-user)"
        ct = self.ct_contact
        SearchConfigItem.create_if_needed(FakeContact, role='superuser',
                                          fields=['first_name', 'last_name'],
                                         )

        response = self.assertGET200(self._build_add_url(ct))

        with self.assertNoException():
            role_f = response.context['form'].fields['role']

        self.assertIsNone(role_f.empty_label)

    # def test_add05(self):
    #     "Invalid first column"
    #     role = self.role
    #     ct = self.ct_contact
    #
    #     url = self._build_add_url(ct)
    #     response = self.assertGET200(url)
    #
    #     with self.assertNoException():
    #         fields = response.context['form'].fields['fields']
    #
    #     fname_1 = 'email'
    #     index_1 = self._find_field_index(fields, fname_1)
    #
    #     fname_2 = 'first_name'
    #     index_2 = self._find_field_index(fields, fname_2)
    #
    #     fname_3 = 'last_name'  # thsi field is always OK
    #     index_3 = self._find_field_index(fields, fname_3)
    #
    #     def post(fname, index, error_msg):
    #         response = self.assertPOST200(url,
    #                                       data={'role': role.id,
    #
    #                                             'fields_check_%s' % index: 'on',
    #                                             'fields_value_%s' % index: fname,
    #                                             'fields_order_%s' % index: 1,
    #
    #                                             'fields_check_%s' % index_3: 'on',
    #                                             'fields_value_%s' % index_3: fname_3,
    #                                             'fields_order_%s' % index_3: 2,
    #                                            },
    #                                      )
    #         self.assertFormError(response, 'form', 'fields', error_msg)
    #
    #     post(fname_1, index_1, _(u'This type of field can not be the first column.'))
    #     post(fname_2, index_2, _(u'The first column cannot be a possibly empty field.'))
    #
    #     # The first column can be empty is there is only one column
    #     self.assertNoFormError(self.client.post(url,
    #                                             data={'role': role.id,
    #
    #                                                   'fields_check_%s' % index_2: 'on',
    #                                                   'fields_value_%s' % index_2: fname_2,
    #                                                   'fields_order_%s' % index_2: 1,
    #                                                  },
    #                                            )
    #                           )
    #
    #     sc_items = SearchConfigItem.objects.filter(content_type=ct)
    #     self.assertEqual(1, len(sc_items))
    #     self.assertEqual([fname_2], [sf.name for sf in sc_items[0].searchfields])

    def _edit_config(self, url, sci, names_indexes, disabled=''):
        data = {'disabled': disabled}
        names = []

        for order, (name, index) in enumerate(names_indexes, start=1):
            data['fields_check_%s' % index] = 'on'
            data['fields_value_%s' % index] = name
            data['fields_order_%s' % index] = order

            names.append(name)

        response = self.client.post(url, data=data)
        self.assertNoFormError(response)

        sci = self.refresh(sci)
        self.assertEqual(names, [sf.name for sf in sci.searchfields])

        return sci

    def test_edit01(self):
        sci = SearchConfigItem.create_if_needed(FakeContact, fields=['last_name'])
        self.assertIsNone(sci.role)

        url = self._build_edit_url(sci)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields['fields']

        self.assertEqual(['last_name'], fields.initial)

        fname1 = 'last_name'
        index1 = self._find_field_index(fields, fname1)

        fname2 = 'first_name'
        index2 = self._find_field_index(fields, fname2)

        self._find_field_index(fields, 'civility__title')
        self.assertNoChoice(fields, 'birthday')

        sci = self._edit_config(url, sci, ((fname1, index1), (fname2, index2)))
        self.assertFalse(sci.disabled)

    def test_edit02(self):
        "Other CT + role + exclude BooleanField"
        sci = SearchConfigItem.objects.create(content_type=self.ct_orga, role=self.role)
        url = self._build_edit_url(sci)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields['fields']

        fname1 = 'name'
        index1 = self._find_field_index(fields, fname1)

        fname2 = 'description'
        index2 = self._find_field_index(fields, fname2)

        self.assertNoChoice(fields, 'subject_to_vat')

        self._edit_config(url, sci, ((fname1, index1), (fname2, index2)))

    def test_edit03(self):
        "Disabled"
        sci = SearchConfigItem.objects.create(content_type=self.ct_contact)
        url = self._build_edit_url(sci)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields['fields']

        fname1 = 'last_name'
        index1 = self._find_field_index(fields, fname1)
        sci = self._edit_config(url, sci, [(fname1, index1)], disabled='on')
        self.assertTrue(sci.disabled)

    def test_edit04(self):
        "Fields with 'choices' are not valid"
        fname = 'discount_unit'
        mfield = FakeInvoiceLine._meta.get_field(fname)
        self.assertTrue(mfield.choices)

        sci = SearchConfigItem.objects.create(content_type=ContentType.objects.get_for_model(FakeInvoiceLine))
        response = self.assertGET200(self._build_edit_url(sci))

        with self.assertNoException():
            fields = response.context['form'].fields['fields']

        self._find_field_index(fields, 'item')
        self.assertNoChoice(fields, fname)

    def test_edit05(self):
        "Exclude DateperiodField"
        sci = SearchConfigItem.objects.create(content_type=ContentType.objects.get_for_model(FakeInvoice))
        response = self.assertGET200(self._build_edit_url(sci))

        with self.assertNoException():
            fields = response.context['form'].fields['fields']

        self._find_field_index(fields, 'name')
        self.assertNoChoice(fields, 'periodicity')

    def test_edit06(self):
        "With FieldsConfig"
        model = FakeContact
        hidden_fname1 = 'description'
        hidden_fname2 = 'position'
        FieldsConfig.create(model,
                            descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True}),
                                          (hidden_fname2, {FieldsConfig.HIDDEN: True}),
                                         ]
                           )
        sci = SearchConfigItem.create_if_needed(model, fields=['first_name'])

        response = self.assertGET200(self._build_edit_url(sci))

        with self.assertNoException():
            fields_f = response.context['form'].fields['fields']

        self.assertEqual(['first_name'], fields_f.initial)

        self._find_field_index(fields_f, 'first_name')
        self._find_field_index(fields_f, 'civility__title')

        self._assertNotInChoices(fields_f, hidden_fname1)
        self._assertNotInChoices(fields_f, 'position__title')

    def test_edit07(self):
        "With FieldsConfig + selected hidden fields"
        model = FakeContact
        hidden_fname1 = 'description'
        hidden_fname2 = 'position'
        hidden_sub_fname2 = hidden_fname2 + '__title'
        sci = SearchConfigItem.create_if_needed(model,
                                                fields=['first_name',
                                                        hidden_fname1,
                                                        hidden_sub_fname2,
                                                       ]
                                               )

        FieldsConfig.create(model,
                            descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True}),
                                          (hidden_fname2, {FieldsConfig.HIDDEN: True}),
                                         ]
                           )

        response = self.assertGET200(self._build_edit_url(sci))

        with self.assertNoException():
            fields_f = response.context['form'].fields['fields']

        self.assertEqual(['first_name', hidden_fname1, hidden_sub_fname2],
                         fields_f.initial
                        )

        self._find_field_index(fields_f, 'first_name')
        self._find_field_index(fields_f, hidden_fname1)
        self._find_field_index(fields_f, hidden_sub_fname2)

    def test_delete01(self):
        sci = SearchConfigItem.create_if_needed(FakeContact, role=self.role,
                                                fields=['first_name', 'last_name'],
                                                )
        # self.assertPOST200('/creme_config/search/delete', data={'id': sci.id})
        self.assertPOST200(reverse('creme_config__delete_search_config'), data={'id': sci.id})
        self.assertDoesNotExist(sci)

    def test_delete02(self):
        "Super users"
        sci = SearchConfigItem.create_if_needed(FakeContact, role='superuser',
                                                fields=['first_name', 'last_name'],
                                                )
        # self.assertPOST200('/creme_config/search/delete', data={'id': sci.id})
        self.assertPOST200(reverse('creme_config__delete_search_config'), data={'id': sci.id})
        self.assertDoesNotExist(sci)

    def test_delete03(self):
        "Cannot delete the default configuration"
        sci = SearchConfigItem.create_if_needed(FakeContact, ['first_name', 'last_name'])
        # self.assertPOST409('/creme_config/search/delete', data={'id': sci.id})
        self.assertPOST409(reverse('creme_config__delete_search_config'), data={'id': sci.id})
        self.assertStillExists(sci)
