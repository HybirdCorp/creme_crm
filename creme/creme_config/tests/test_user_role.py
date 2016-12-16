# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext as _

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import CremeUser as User
    from creme.creme_core.models import UserRole, SetCredentials
    from creme.creme_core.tests.base import CremeTestCase, skipIfNotInstalled
    from creme.creme_core.tests.fake_models import FakeContact, FakeOrganisation, FakeActivity

    from creme.documents.models import Document
    from creme.persons.models import Contact, Organisation, Address
    from creme.activities.models import Activity

    from ..blocks import UserRolesBlock
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class UserRoleTestCase(CremeTestCase):
    ADD_URL = '/creme_config/role/add/'
    WIZARD_URL = '/creme_config/role/wizard/'
    DEL_CREDS_URL = '/creme_config/role/delete_credentials'

    # @classmethod
    # def setUpClass(cls):
    #     CremeTestCase.setUpClass()
    #     cls.populate('creme_core')

    def _build_add_creds_url(self, role):
        return '/creme_config/role/add_credentials/%s' % role.id

    def _build_wizard_edit_url(self, role):
        return '/creme_config/role/wizard/%s' % role.id

    def _build_del_role_url(self, role):
        return '/creme_config/role/delete/%s' % role.id

    def login_not_as_superuser(self):
        apps = ('creme_config',)
        self.login(is_superuser=False, allowed_apps=apps, admin_4_apps=apps)

    def _aux_test_portal(self):
        response = self.assertGET200('/creme_config/role/portal/')
        self.assertContains(response, 'id="%s"' % UserRolesBlock.id_)

    def test_portal01(self):
        self.login()
        self._aux_test_portal()

    def test_portal02(self):
        self.login_not_as_superuser()
        self._aux_test_portal()

    def test_create01(self):
        self.login()

        url = self.ADD_URL
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            apps_choices  = set(c[0] for c in fields['allowed_apps'].choices)
            admin_choices = set(c[0] for c in fields['admin_4_apps'].choices)

        self.assertIn('creme_core',   apps_choices)
        self.assertIn('creme_config', apps_choices)
        self.assertIn('persons',      apps_choices)

        self.assertIn('creme_core', admin_choices)
        self.assertIn('persons',    admin_choices)
        self.assertNotIn('creme_config', admin_choices)  # <==

        get_ct = ContentType.objects.get_for_model
        name = 'CEO'
        creatable_ctypes = [get_ct(FakeContact).id, get_ct(FakeOrganisation).id]
        exportable_ctypes = [get_ct(FakeContact).id, get_ct(FakeActivity).id]
        apps = ['persons']
        response = self.client.post(url, follow=True,
                                    data={'name':              name,
                                          'creatable_ctypes':  creatable_ctypes,
                                          'exportable_ctypes': exportable_ctypes,
                                          'allowed_apps':      apps,
                                          'admin_4_apps':      apps,
                                         }
                                   )
        self.assertNoFormError(response)

        role = self.get_object_or_fail(UserRole, name=name)
        self.assertEqual(set(creatable_ctypes),  {ctype.id for ctype in role.creatable_ctypes.all()})
        self.assertEqual(set(exportable_ctypes), {ctype.id for ctype in role.exportable_ctypes.all()})

        app_set = set(apps)
        self.assertEqual(app_set, role.allowed_apps)
        self.assertEqual(app_set, role.admin_4_apps)

    def test_create02(self):
        self.login_not_as_superuser()

        url = self.ADD_URL
        self.assertGET403(url)
        self.assertPOST403(url, data={'name':              'CEO',
                                      'creatable_ctypes':  [],
                                      'exportable_ctypes': [],
                                      'allowed_apps':      [],
                                      'admin_4_apps':      [],
                                     }
                          )

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.documents')
    @skipIfNotInstalled('creme.activities')
    def test_creation_wizard01(self):
        self.login()
        url = self.WIZARD_URL
        name = 'Basic role'
        apps = ['persons', 'documents']
        adm_apps = ['persons']

        # Step 1
        response = self.assertGET200(url)

        with self.assertNoException():
            app_labels = {c[0] for c in response.context['form'].fields['allowed_apps'].choices}

        self.assertIn(apps[0], app_labels)
        self.assertIn(apps[1], app_labels)
        self.assertIn('activities', app_labels)

        response = self.client.post(url,
                                    {'user_role_creation_wizard-current_step': '0',
                                     '0-name': name,
                                     '0-allowed_apps': apps,
                                    }
                                   )
        self.assertNoFormError(response)

        # Step 2
        with self.assertNoException():
            adm_app_labels = {c[0] for c in response.context['form'].fields['admin_4_apps'].choices}

        self.assertIn(apps[0], adm_app_labels)
        self.assertIn(apps[1], adm_app_labels)
        self.assertNotIn('activities', adm_app_labels)

        response = self.client.post(url,
                                    {'user_role_creation_wizard-current_step': '1',
                                     '1-admin_4_apps': adm_apps,
                                    }
                                   )
        self.assertNoFormError(response)

        # Step 3
        with self.assertNoException():
            creatable_ctypes = set(response.context['form'].fields['creatable_ctypes'].ctypes)

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)
        ct_doc = get_ct(Document)

        self.assertIn(ct_contact, creatable_ctypes)
        self.assertIn(get_ct(Organisation), creatable_ctypes)
        self.assertNotIn(get_ct(Address), creatable_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, creatable_ctypes)
        self.assertNotIn(get_ct(Activity), creatable_ctypes)  # App not allowed

        response = self.client.post(url,
                                    {'user_role_creation_wizard-current_step': '2',
                                     '2-creatable_ctypes': [ct_contact.id, ct_doc.id],
                                    }
                                   )
        self.assertNoFormError(response)

        # Step 4
        with self.assertNoException():
            exp_ctypes = response.context['form'].fields['exportable_ctypes'].ctypes

        self.assertIn(ct_contact, exp_ctypes)
        self.assertIn(get_ct(Organisation), exp_ctypes)
        self.assertNotIn(get_ct(Address), exp_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, exp_ctypes)
        self.assertNotIn(get_ct(Activity), exp_ctypes)  # App not allowed

        response = self.client.post(url,
                                    {'user_role_creation_wizard-current_step': '3',
                                     '3-exportable_ctypes': [ct_contact.id],
                                    }
                                   )
        self.assertNoFormError(response)

        # Step 5
        with self.assertNoException():
            cred_ctypes = set(response.context['form'].fields['ctype'].ctypes)

        self.assertIn(ct_contact, cred_ctypes)
        self.assertIn(get_ct(Organisation), cred_ctypes)
        self.assertNotIn(get_ct(Address), cred_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, cred_ctypes)
        self.assertNotIn(get_ct(Activity), cred_ctypes)  # App not allowed

        set_type = SetCredentials.ESET_ALL
        response = self.client.post(url,
                                    {'user_role_creation_wizard-current_step': '4',
                                     '4-can_change': True,

                                     '4-set_type': set_type,
                                     '4-ctype':    ct_contact.id,
                                    }
                                   )
        self.assertNoFormError(response)

        role = self.get_object_or_fail(UserRole, name=name)
        self.assertEqual(set(apps),     role.allowed_apps)
        self.assertEqual(set(adm_apps), role.admin_4_apps)

        self.assertEqual({ct_contact, ct_doc},  set(role.creatable_ctypes.all()))
        self.assertEqual([ct_contact],          list(role.exportable_ctypes.all()))

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(EntityCredentials.VIEW | EntityCredentials.CHANGE, creds.value)
        self.assertEqual(set_type, creds.set_type)
        self.assertEqual(ct_contact, creds.ctype)

    def test_creation_wizard02(self):
        "Not super-user"
        self.login_not_as_superuser()
        self.assertGET403(self.WIZARD_URL)

    def test_add_credentials01(self):
        user = self.login()

        role = UserRole(name='CEO')
        role.allowed_apps = ['creme_core']
        role.save()

        other_user = User.objects.create(username='chloe', role=role)
        contact    = FakeContact.objects.create(user=user, first_name='Yuki', last_name='Kajiura')
        self.assertFalse(other_user.has_perm_to_view(contact))

        self.assertEqual(0, role.credentials.count())

        url = self._build_add_creds_url(role)
        self.assertGET200(url)

        set_type = SetCredentials.ESET_ALL
        response = self.client.post(url, data={'can_view':   True,
                                               'can_change': False,
                                               'can_delete': False,
                                               'can_link':   False,
                                               'can_unlink': False,
                                               'set_type':   set_type,
                                               'ctype':      '',
                                              }
                                   )
        self.assertNoFormError(response)

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(EntityCredentials.VIEW, creds.value)
        self.assertEqual(set_type, creds.set_type)
        self.assertIsNone(creds.ctype)

        contact = self.refresh(contact)  # Refresh cache
        other_user = self.refresh(other_user)
        self.assertTrue(other_user.has_perm_to_view(contact))

    @skipIfNotInstalled('creme.persons')
    def test_add_credentials02(self):
        "Specific CType + ESET_OWN"
        self.login()

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

        url = self._build_add_creds_url(role)
        response = self.assertGET200(url)

        with self.assertNoException():
            cred_ctypes = set(response.context['form'].fields['ctype'].ctypes)

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)

        self.assertIn(ct_contact, cred_ctypes)
        self.assertIn(get_ct(Organisation), cred_ctypes)
        self.assertNotIn(get_ct(Activity), cred_ctypes)  # App not allowed

        set_type = SetCredentials.ESET_OWN
        response = self.client.post(url,
                                    data={'can_view':   True,
                                          'can_change': True,
                                          'can_delete': False,
                                          'can_link':   False,
                                          'can_unlink': False,
                                          'set_type':   set_type,
                                          'ctype':      ct_contact.id,
                                         }
                                   )
        self.assertNoFormError(response)

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(EntityCredentials.VIEW | EntityCredentials.CHANGE, creds.value)
        self.assertEqual(SetCredentials.ESET_OWN, creds.set_type)
        self.assertEqual(ct_contact.id,           creds.ctype_id)

    def test_add_credentials03(self):
        self.login_not_as_superuser()

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

        url = self._build_add_creds_url(role)
        self.assertGET403(url)
        self.assertPOST403(url, data={'can_view':   True,
                                      'can_change': False,
                                      'can_delete': False,
                                      'can_link':   False,
                                      'can_unlink': False,
                                      'set_type':   SetCredentials.ESET_ALL,
                                      'ctype':      0,
                                     }
                          )

    @skipIfNotInstalled('creme.persons')
    def test_edit_credentials(self):
        self.login()

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

        creds = SetCredentials.objects.create(role=role,
                                              set_type=SetCredentials.ESET_ALL,
                                              value=EntityCredentials.VIEW,
                                             )

        url = '/creme_config/role/edit_credentials/%s' % creds.id
        response = self.assertGET200(url)

        with self.assertNoException():
            cred_ctypes = set(response.context['form'].fields['ctype'].ctypes)

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)

        self.assertIn(ct_contact, cred_ctypes)
        self.assertIn(get_ct(Organisation), cred_ctypes)
        self.assertNotIn(get_ct(Activity), cred_ctypes)  # App not allowed

        response = self.client.post(url,
                                    data={'can_view':   True,
                                          'can_change': True,
                                          'can_delete': True,
                                          'can_link':   False,
                                          'can_unlink': False,
                                          'set_type':   SetCredentials.ESET_OWN,
                                          'ctype':      ct_contact.id,
                                         }
                                   )
        self.assertNoFormError(response)

        creds = self.refresh(creds)
        self.assertEqual(EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE, creds.value)
        self.assertEqual(SetCredentials.ESET_OWN, creds.set_type)
        self.assertEqual(ct_contact .id,          creds.ctype_id)

    def test_delete_credentials01(self):
        self.login()

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

        create_creds = partial(SetCredentials.objects.create, role=role, 
                               set_type=SetCredentials.ESET_ALL
                              )
        sc1 = create_creds(value=EntityCredentials.VIEW)
        sc2 = create_creds(value=EntityCredentials.CHANGE)

        url = self.DEL_CREDS_URL
        self.assertGET404(url)
        self.assertPOST404(url)
        self.assertPOST200(url, data={'id': sc1.id})

        self.assertDoesNotExist(sc1)
        self.assertStillExists(sc2)

    def test_delete_credentials02(self):
        self.login_not_as_superuser()

        sc = SetCredentials.objects.create(role=self.role, 
                                           set_type=SetCredentials.ESET_ALL,
                                           value=EntityCredentials.VIEW,
                                          )
        self.assertPOST403(self.DEL_CREDS_URL, data={'id': sc.id})

    def test_edit01(self):
        user = self.login()

        role = UserRole.objects.create(name='CEO')
        SetCredentials.objects.create(role=role, value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL,
                                     )

        other_user = User.objects.create(username='chloe', role=role)
        contact    = FakeContact.objects.create(user=user, first_name='Yuki', last_name='Kajiura')
        self.assertFalse(other_user.has_perm_to_view(contact))  # role.allowed_apps does not contain 'persons'

        url = '/creme_config/role/edit/%s' % role.id
        self.assertGET200(url)

        name   = role.name + '_edited'
        get_ct = ContentType.objects.get_for_model
        creatable_ctypes = [get_ct(FakeContact).id, get_ct(FakeOrganisation).id]
        exportable_ctypes = [get_ct(FakeContact).id, get_ct(FakeActivity).id]
        apps = ['creme_core', 'documents']
        admin_apps = ['creme_core']
        response = self.client.post(url, follow=True,
                                    data={'name':                    name,
                                          'creatable_ctypes':        creatable_ctypes,
                                          'exportable_ctypes':       exportable_ctypes,
                                          'allowed_apps':            apps,
                                          'admin_4_apps':            admin_apps,
                                         }
                                   )
        self.assertNoFormError(response)

        role = self.refresh(role)
        self.assertEqual(set(creatable_ctypes),  {ctype.id for ctype in role.creatable_ctypes.all()})
        self.assertEqual(set(exportable_ctypes), {ctype.id for ctype in role.exportable_ctypes.all()})
        self.assertEqual(set(apps),       role.allowed_apps)
        self.assertEqual(set(admin_apps), role.admin_4_apps)

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(EntityCredentials.VIEW,  creds.value)
        self.assertEqual(SetCredentials.ESET_ALL, creds.set_type)

        contact = self.refresh(contact)  # Refresh cache
        self.assertTrue(self.refresh(other_user).has_perm_to_view(contact))  # role.allowed_apps contains 'creme_core' now

    def test_edit02(self):
        self.login_not_as_superuser()

        role = UserRole.objects.create(name='CEO')
        url = '/creme_config/role/edit/%s' % role.id
        self.assertGET403(url)
        self.assertPOST403(url, data={'name':              role.name,
                                      'creatable_ctypes':  [],
                                      'exportable_ctypes': [],
                                      'allowed_apps':      [],
                                      'admin_4_apps':      [],
                                     }
                          )

    @skipIfNotInstalled('creme.persons')
    @skipIfNotInstalled('creme.documents')
    @skipIfNotInstalled('creme.activities')
    def test_edition_wizard01(self):
        self.login()

        role = UserRole.objects.create(name='CEO', allowed_apps=['persons'])
        SetCredentials.objects.create(role=role, value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL,
                                     )

        name = role.name + ' edited'
        apps = ['persons', 'documents']
        adm_apps = ['persons']

        url = self._build_wizard_edit_url(role)

        # Step 1
        response = self.assertGET200(url)

        with self.assertNoException():
            app_labels = {c[0] for c in response.context['form'].fields['allowed_apps'].choices}

        self.assertIn(apps[0], app_labels)
        self.assertIn(apps[1], app_labels)
        self.assertIn('activities', app_labels)

        response = self.client.post(url,
                                    {'user_role_edition_wizard-current_step': '0',
                                     '0-name': name,
                                     '0-allowed_apps': apps,
                                    }
                                   )
        self.assertNoFormError(response)

        # Step 2
        with self.assertNoException():
            adm_app_labels = {c[0] for c in response.context['form'].fields['admin_4_apps'].choices}

        self.assertIn(apps[0], adm_app_labels)
        self.assertIn(apps[1], adm_app_labels)
        self.assertNotIn('activities', adm_app_labels)

        response = self.client.post(url,
                                    {'user_role_edition_wizard-current_step': '1',
                                     '1-admin_4_apps': adm_apps,
                                    }
                                   )
        self.assertNoFormError(response)

        # Step 3
        with self.assertNoException():
            creatable_ctypes = set(response.context['form'].fields['creatable_ctypes'].ctypes)

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)
        ct_doc = get_ct(Document)

        self.assertIn(ct_contact, creatable_ctypes)
        self.assertIn(get_ct(Organisation), creatable_ctypes)
        self.assertNotIn(get_ct(Address), creatable_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, creatable_ctypes)
        self.assertNotIn(get_ct(Activity), creatable_ctypes)  # App not allowed

        response = self.client.post(url,
                                    {'user_role_edition_wizard-current_step': '2',
                                     '2-creatable_ctypes': [ct_contact.id, ct_doc.id],
                                    }
                                   )
        self.assertNoFormError(response)

        # Step 4
        with self.assertNoException():
            exp_ctypes = response.context['form'].fields['exportable_ctypes'].ctypes

        self.assertIn(ct_contact, exp_ctypes)
        self.assertIn(get_ct(Organisation), exp_ctypes)
        self.assertNotIn(get_ct(Address), exp_ctypes)  # Not CremeEntity
        self.assertIn(ct_doc, exp_ctypes)
        self.assertNotIn(get_ct(Activity), exp_ctypes)  # App not allowed

        response = self.client.post(url,
                                    {'user_role_edition_wizard-current_step': '3',
                                     '3-exportable_ctypes': [ct_contact.id],
                                    }
                                   )
        self.assertNoFormError(response)

        role = self.refresh(role)
        self.assertEqual(name,          role.name)
        self.assertEqual(set(apps),     role.allowed_apps)
        self.assertEqual(set(adm_apps), role.admin_4_apps)

        self.assertEqual({ct_contact, ct_doc},  set(role.creatable_ctypes.all()))
        self.assertEqual([ct_contact],          list(role.exportable_ctypes.all()))
        self.assertEqual(1, role.credentials.count())

    def test_edition_wizard02(self):
        "Not super-user"
        self.login_not_as_superuser()

        role = UserRole.objects.create(name='CEO')
        self.assertGET403(self._build_wizard_edit_url(role))

    def test_delete01(self):
        "Not superuser -> error"
        self.login_not_as_superuser()

        url = self._build_del_role_url(self.role)
        self.assertGET403(url)
        self.assertPOST403(url)

    def test_delete02(self):
        "Role is not used"
        self.login()

        role = UserRole.objects.create(name='CEO')
        url = self._build_del_role_url(role)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            info = fields['info']

        self.assertFalse(info.required)
        self.assertNotIn('to_role', fields)

        self.assertNoFormError(self.client.post(url))
        self.assertDoesNotExist(role)
        self.assertFalse(SetCredentials.objects.filter(role=role.id))

    def test_delete03(self):
        "To replace by another role"
        self.login()

        replacing_role = self.role
        role_2_del = UserRole.objects.create(name='CEO')
        other_role = UserRole.objects.create(name='Coder')
        user = User.objects.create(username='chloe', role=role_2_del)  # <= role is used

        url = self._build_del_role_url(role_2_del)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            choices = list(fields['to_role'].choices)

        self.assertNotIn('info', fields)

        self.assertIn((replacing_role.id, unicode(replacing_role)), choices)
        self.assertIn((other_role.id,     unicode(other_role)),     choices)
        self.assertNotIn((role_2_del.id,  unicode(role_2_del)),     choices)

        response = self.client.post(url, data={'to_role': replacing_role.id})
        self.assertNoFormError(response)
        self.assertDoesNotExist(role_2_del)
        self.assertFalse(SetCredentials.objects.filter(role=role_2_del.id))
        self.assertEqual(replacing_role, self.refresh(user).role)

    def test_delete04(self):
        "Role is used -> replacing role is required"
        self.login()

        role = UserRole.objects.create(name='CEO')
        User.objects.create(username='chloe', role=role)  # <= role is used

        response = self.assertPOST200(self._build_del_role_url(role))
        self.assertFormError(response, 'form', 'to_role', _('This field is required.'))
