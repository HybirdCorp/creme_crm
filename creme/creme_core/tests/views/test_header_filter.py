# -*- coding: utf-8 -*-

try:
    from future_builtins import zip
    from functools import partial
    from json import loads as load_json

    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext as _

    from .base import ViewsTestCase
    from ..fake_constants import FAKE_REL_SUB_EMPLOYED_BY
    from ..fake_models import FakeContact as Contact, FakeOrganisation as Organisation
    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.models import (HeaderFilter, CremeEntity,
            FieldsConfig, RelationType, CustomField)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class HeaderFilterViewsTestCase(ViewsTestCase):
    DELETE_URL = '/creme_core/header_filter/delete'

    @classmethod
    def setUpClass(cls):
        ViewsTestCase.setUpClass()
        # cls.populate('creme_core')
        cls.contact_ct = ContentType.objects.get_for_model(Contact)

        cls._hf_backup = list(HeaderFilter.objects.all())
        HeaderFilter.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        ViewsTestCase.tearDownClass()
        HeaderFilter.objects.all().delete()
        HeaderFilter.objects.bulk_create(cls._hf_backup)

    def assertCellsEqual(self, cells1, cells2):
        self.assertEqual(len(cells1), len(cells2))

        for cell1, cell2 in zip(cells1, cells2):
            self.assertIs(cell1.__class__, cell2.__class__)
            self.assertEqual(cell1.value, cell2.value)

    def _build_add_url(self, ctype):
        return '/creme_core/header_filter/add/%s' % ctype.id

    def _build_edit_url(self, hf):
        return '/creme_core/header_filter/edit/%s' % hf.id

    def _build_get4ctype_url(self, ctype):
        return '/creme_core/header_filter/get_for_ctype/%s' % ctype.id

    def test_create01(self):
        self.login()

        # ct = ContentType.objects.get_for_model(CremeEntity)
        ct = ContentType.objects.get_for_model(Organisation)
        self.assertFalse(HeaderFilter.objects.filter(entity_type=ct))

        url = self._build_add_url(ct)
        self.assertGET200(url)

        name = 'DefaultHeaderFilter'
        response = self.client.post(url, data={'name':  name,
                                               'cells': 'regular_field-created',
                                              }
                                   )
        self.assertNoFormError(response, status=302)

        hfilters = HeaderFilter.objects.filter(entity_type=ct)
        self.assertEqual(1, len(hfilters))

        hfilter = hfilters[0]
        self.assertEqual(name, hfilter.name)
        self.assertIsNone(hfilter.user)
        self.assertFalse(hfilter.is_private)

        cells = hfilter.cells
        self.assertEqual(1, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual('created', cell.value)
        self.assertEqual('created__range', cell.filter_string)
        self.assertIs(cell.is_hidden, False)

        # self.assertRedirects(response, '/')
        self.assertRedirects(response, Organisation.get_lv_absolute_url())

    def test_create02(self):
        user = self.login()

        ct = self.contact_ct
        loves = RelationType.create(('test-subject_love', u'Is loving'),
                                    ('test-object_love',  u'Is loved by')
                                   )[0]
        customfield = CustomField.objects.create(name=u'Size (cm)',
                                                 field_type=CustomField.INT,
                                                 content_type=ct,
                                                )
        funcfield = Contact.function_fields.get('get_pretty_properties')

        url = self._build_add_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            cells_f = response.context['form'].fields['cells']

        build_4_field = partial(EntityCellRegularField.build, model=Contact)
        self.assertCellsEqual([build_4_field(name='first_name'),
                               build_4_field(name='last_name'),
                               EntityCellRelation(RelationType.objects.get(pk=FAKE_REL_SUB_EMPLOYED_BY)),
                              ],
                              cells_f.initial
                             )

        field_name = 'first_name'
        name = 'DefaultHeaderFilter'
        response = self.client.post(url, follow=True,
                                    data={'name': name,
                                          'user': user.id,
                                          'is_private': 'on',
                                          'cells': 'relation-%(rtype)s,'
                                                   'regular_field-%(rfield)s,'
                                                   'function_field-%(ffield)s,'
                                                   'custom_field-%(cfield)s' % {
                                                        'rfield': field_name,
                                                        'cfield': customfield.id,
                                                        'rtype':  loves.id,
                                                        'ffield': funcfield.name,
                                                    }
                                         }
                                   )
        self.assertNoFormError(response)

        hfilter = self.get_object_or_fail(HeaderFilter, name=name)
        self.assertEqual(user, hfilter.user)
        self.assertTrue(hfilter.is_private)

        cells = hfilter.cells
        self.assertEqual(4, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(loves.id, cell.value)

        cell = cells[1]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_name, cell.value)

        cell = cells[2]
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(funcfield.name, cell.value)

        cell = cells[3]
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(str(customfield.id), cell.value)

        self.assertRedirects(response, Contact.get_lv_absolute_url())

    def test_create03(self):
        "Check app credentials"
        self.login(is_superuser=False, allowed_apps=['documents'])

        uri = self._build_add_url(self.contact_ct)
        self.assertGET403(uri)

        self.role.allowed_apps = ['documents', 'creme_core']
        self.role.save()

        self.assertGET200(uri)

    def test_create04(self):
        "Cannot create a private filter for another user (but OK with one of our teams)"
        user = self.login()

        User = get_user_model()
        my_team = User.objects.create(username='TeamTitan', is_team=True)
        my_team.teammates = [user, self.other_user]

        a_team = User.objects.create(username='A-team', is_team=True)
        a_team.teammates = [self.other_user]

        name = 'DefaultHeaderFilter'

        def post(owner):
            return self.assertPOST200(self._build_add_url(self.contact_ct), follow=True,
                                      data={'name': name,
                                            'user': owner.id,
                                            'is_private': 'on',
                                            'cells': 'regular_field-first_name',
                                           },
                                     )

        response = post(self.other_user)
        msg = _('A private view of list must belong to you (or one of your teams).')
        self.assertFormError(response, 'form', 'user', msg)

        response = post(a_team)
        self.assertFormError(response, 'form', 'user', msg)

        response = post(my_team)
        self.assertNoFormError(response)
        self.get_object_or_fail(HeaderFilter, name=name)

    def test_create05(self):
        "A staff user can create a private filter for another user"
        self.login(is_staff=True)

        name = 'DefaultHeaderFilter'
        callback = Organisation.get_lv_absolute_url()
        response = self.client.post(self._build_add_url(self.contact_ct), follow=True,
                                    data={'name': name,
                                          'user': self.other_user.id,
                                          'is_private': 'on',
                                          'cells': 'regular_field-first_name',
                                          'cancel_url': callback,
                                         },
                                   )

        self.assertNoFormError(response)
        self.get_object_or_fail(HeaderFilter, name=name)

        self.assertRedirects(response, callback)

    def test_create06(self):
        "Not an Entity type"
        self.login()
        self.assertGET409(self._build_add_url(ContentType.objects.get_for_model(RelationType)))

    def test_create07(self):
        "FieldsConfig"
        self.login()

        valid_fname = 'last_name'
        hidden_fname = 'phone'
        FieldsConfig.create(Contact, descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})])

        response = self.assertGET200(self._build_add_url(self.contact_ct))

        with self.assertNoException():
            widget = response.context['form'].fields['cells'].widget
            choices_keys = {c[0] for c in widget.model_fields}

        rf_prefix = 'regular_field-'
        self.assertIn(rf_prefix + valid_fname,     choices_keys)
        self.assertNotIn(rf_prefix + hidden_fname, choices_keys)

    def test_edit01(self):
        self.login()

        field1 = 'first_name'
        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True,
                                 cells_desc=[EntityCellRegularField.build(model=Contact, name=field1)],
                                )

        url = self._build_edit_url(hf)
        response = self.assertGET200(url)

        with self.assertNoException():
            cells_f = response.context['form'].fields['cells']

        self.assertCellsEqual(hf.cells, cells_f.initial)

        name = 'Entity view v2'
        field2 = 'last_name'
        response = self.client.post(url, data={'name':  name,
                                               'cells': 'regular_field-%s,'
                                                        'regular_field-%s' % (
                                                                field1, field2,
                                                            ),
                                              },
                                   )
        self.assertNoFormError(response, status=302)

        hf = self.refresh(hf)
        self.assertEqual(name, hf.name)

        cells = hf.cells
        self.assertEqual(2,      len(cells))
        self.assertEqual(field1, cells[0].value)
        self.assertEqual(field2, cells[1].value)

        self.assertRedirects(response, Contact.get_lv_absolute_url())

    def test_edit02(self):
        "Not custom -> can be still edited"
        self.login()

        field1 = 'first_name'
        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=False,
                                 cells_desc=[EntityCellRegularField.build(model=Contact, name=field1)],
                                )
        self.assertGET200(self._build_edit_url(hf))

    def test_edit03(self):
        "Cannot edit HeaderFilter that belongs to another user"
        self.login(is_superuser=False)

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=self.other_user,
                                )
        self.assertGET403(self._build_edit_url(hf))

    def test_edit04(self):
        "User do not have the app credentials"
        user = self.login(is_superuser=False, allowed_apps=['documents'])

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=user,
                                )
        self.assertGET403(self._build_edit_url(hf))

    def test_edit05(self):
        "User belongs to the team -> OK"
        user = self.login(is_superuser=False)

        my_team = get_user_model().objects.create(username='TeamTitan', is_team=True)
        my_team.teammates = [user]

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=my_team,
                                )
        self.assertGET200(self._build_edit_url(hf))

    def test_edit06(self):
        "User does not belong to the team -> error"
        self.login(is_superuser=False)

        User = get_user_model()
        my_team = User.objects.create(username='TeamTitan', is_team=True)
        # my_team.teammates = [self.user] # <=====

        a_team = User.objects.create(username='A-team', is_team=True)
        a_team.teammates = [self.user]

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=my_team,
                                )
        self.assertGET403(self._build_edit_url(hf))

    def test_edit07(self):
        "Private filter -> cannot be edited by another user (even a super-user)"
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True,
                                 is_private=True, user=self.other_user,
                                )
        self.assertGET403(self._build_edit_url(hf))

    def test_edit08(self):
        "Staff users can edit all HeaderFilters + private filters must be assigned"
        self.login(is_staff=True)

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True,
                                 is_private=True, user=self.other_user,
                                )
        url = self._build_edit_url(hf)
        self.assertGET200(url)

        response = self.assertPOST200(url, follow=True,
                                      data={'name':       hf.name,
                                            'user':       '',
                                            'is_private': 'on',
                                            'cells':      'regular_field-last_name',
                                           }
                                     )
        self.assertFormError(response, 'form', 'user',
                             _('A private view of list must be assigned to a user/team.')
                            )

    def test_edit09(self):
        "Not custom filter cannot be private + callback url"
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=False,
                                )
        url = self._build_edit_url(hf)
        self.assertGET200(url)

        callback = Organisation.get_lv_absolute_url()
        response = self.client.post(url, data={'name':       hf.name,
                                               'user':       self.user.id,
                                               'is_private': 'on',  # Should not be used
                                               'cells':      'regular_field-last_name',
                                               'cancel_url': callback,
                                              }
                                   )
        self.assertNoFormError(response, status=302)
        self.assertFalse(self.refresh(hf).is_private)

        self.assertRedirects(response, callback)

    def test_edit10(self):
        "FieldsConfig"
        self.login()

        valid_fname = 'last_name'
        hidden_fname1 = 'phone'
        hidden_fname2 = 'birthday'
        build_cell = partial(EntityCellRegularField.build, model=Contact)
        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True,
                                 cells_desc=[build_cell(name=valid_fname),
                                             build_cell(name=hidden_fname1),
                                            ],
                                )
        FieldsConfig.create(Contact,
                            descriptions=[(hidden_fname1, {FieldsConfig.HIDDEN: True}),
                                          (hidden_fname2, {FieldsConfig.HIDDEN: True}),
                                         ]
                           )

        response = self.assertGET200(self._build_edit_url(hf))

        with self.assertNoException():
            widget = response.context['form'].fields['cells'].widget
            choices_keys = {c[0] for c in widget.model_fields}

        rf_prefix = 'regular_field-'
        self.assertIn(rf_prefix + valid_fname,   choices_keys)
        self.assertIn(rf_prefix + hidden_fname1, choices_keys)  # Was already in the HeaderFilter => still proposed
        self.assertNotIn(rf_prefix + hidden_fname2, choices_keys)

    def test_delete01(self):
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True,
                                 cells_desc=[EntityCellRegularField.build(model=Contact, name='first_name')],
                                )
        self.assertPOST200(self.DELETE_URL, follow=True, data={'id': hf.id})
        self.assertDoesNotExist(hf)

    def test_delete02(self):
        "Not custom -> undeletable"
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=False,
                                )
        self.client.post(self.DELETE_URL, data={'id': hf.id})
        self.assertStillExists(hf)

    def test_delete03(self):
        "Belongs to another user"
        self.login(is_superuser=False)

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=self.other_user,
                                )
        self.client.post(self.DELETE_URL, data={'id': hf.id})
        self.assertStillExists(hf)

    def test_delete04(self):
        "The user belongs to the owner team -> ok"
        user = self.login(is_superuser=False)

        my_team = get_user_model().objects.create(username='TeamTitan', is_team=True)
        my_team.teammates = [user]

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=my_team,
                                )
        self.assertPOST200(self.DELETE_URL, data={'id': hf.id}, follow=True)
        self.assertDoesNotExist(hf)

    def test_delete05(self):
        "Belongs to a team (not mine) -> KO"
        user = self.login(is_superuser=False)

        User = get_user_model()
        a_team = User.objects.create(username='TeamTitan', is_team=True)
        a_team.teammates = [self.other_user]

        my_team = User.objects.create(username='A-team', is_team=True)
        my_team.teammates = [user]

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=a_team,
                                )
        self.client.post(self.DELETE_URL, data={'id': hf.id}, follow=True)
        self.assertStillExists(hf)

    def test_delete06(self):
        "Logged as super user"
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=self.other_user,
                                )
        self.client.post(self.DELETE_URL, data={'id': hf.id})
        self.assertDoesNotExist(hf)

    def test_hfilters_for_ctype01(self):
        self.login()

        response = self.assertGET200(self._build_get4ctype_url(self.contact_ct))
        self.assertEqual([], load_json(response.content))

    def test_hfilters_for_ctype02(self):
        user = self.login()

        create_hf = HeaderFilter.create
        name01 = 'Contact view01'
        name02 = 'Contact view02'
        name03 = 'Contact view03'
        pk_fmt = 'tests-hf_contact%s'
        hf01 = create_hf(pk=pk_fmt % 1, name=name01,      model=Contact,      is_custom=False)
        hf02 = create_hf(pk=pk_fmt % 2, name=name02,      model=Contact,      is_custom=True)
        create_hf(pk='tests-hf_orga01', name='Orga view', model=Organisation, is_custom=True)
        hf03 = create_hf(pk=pk_fmt % 3, name=name03,      model=Contact,      is_custom=True, is_private=True, user=user)
        create_hf(pk=pk_fmt % 4,        name='Private',   model=Contact,      is_custom=True, is_private=True, user=self.other_user)

        response = self.assertGET200(self._build_get4ctype_url(self.contact_ct))
        self.assertEqual([[hf01.id, name01], [hf02.id, name02], [hf03.id, name03]],
                         load_json(response.content)
                        )

    def test_hfilters_for_ctype03(self):
        "No app credentials"
        self.login(is_superuser=False, allowed_apps=['documents'])
        self.assertGET403(self._build_get4ctype_url(self.contact_ct))
