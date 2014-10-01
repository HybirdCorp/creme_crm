# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.utils.translation import ugettext as _
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import UserRole, SetCredentials
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.tests.base import CremeTestCase

    from creme.activities.models import Activity

    from creme.persons.models import Contact, Organisation #need CremeEntity

    from ..blocks import UserRolesBlock
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('UserRoleTestCase',)


class UserRoleTestCase(CremeTestCase):
    ADD_URL = '/creme_config/role/add/'
    DEL_CREDS_URL = '/creme_config/role/delete_credentials'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def _build_add_creds_url(self, role):
        return '/creme_config/role/add_credentials/%s' % role.id

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
        self.assertNotIn('creme_config', admin_choices) #<==

        get_ct = ContentType.objects.get_for_model
        name = 'CEO'
        creatable_ctypes = [get_ct(Contact).id, get_ct(Organisation).id]
        exportable_ctypes = [get_ct(Contact).id, get_ct(Activity).id]
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
        #self.assertGETRedirectsToLogin(url)
        self.assertGET403(url)
        #self.assertPOSTRedirectsToLogin(url, data={'name':              'CEO',
        self.assertPOST403(url, data={'name':              'CEO',
                                      'creatable_ctypes':  [],
                                      'exportable_ctypes': [],
                                      'allowed_apps':      [],
                                      'admin_4_apps':      [],
                                     }
                          )

    def test_add_credentials01(self):
        self.login()

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

        other_user = User.objects.create(username='chloe', role=role)
        contact    = Contact.objects.create(user=self.user, first_name='Yuki', last_name='Kajiura')
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

        contact = self.refresh(contact) #refresh cache
        other_user = self.refresh(other_user)
        self.assertTrue(other_user.has_perm_to_view(contact))

    def test_add_credentials02(self):
        self.login()

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

        set_type = SetCredentials.ESET_OWN
        ct_id = ContentType.objects.get_for_model(Contact).id
        response = self.client.post(self._build_add_creds_url(role),
                                    data={'can_view':   True,
                                          'can_change': True,
                                          'can_delete': False,
                                          'can_link':   False,
                                          'can_unlink': False,
                                          'set_type':   set_type,
                                          'ctype':      ct_id,
                                         }
                                   )
        self.assertNoFormError(response)

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(EntityCredentials.VIEW | EntityCredentials.CHANGE, creds.value)
        self.assertEqual(SetCredentials.ESET_OWN, creds.set_type)
        self.assertEqual(ct_id,                   creds.ctype_id)

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
        #self.assertPOSTRedirectsToLogin(self.DEL_CREDS_URL, data={'id': sc.id})
        self.assertPOST403(self.DEL_CREDS_URL, data={'id': sc.id})

    def test_edit01(self):
        self.login()

        role = UserRole.objects.create(name='CEO')
        SetCredentials.objects.create(role=role, value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL,
                                     )

        other_user = User.objects.create(username='chloe', role=role)
        contact    = Contact.objects.create(user=self.user, first_name='Yuki', last_name='Kajiura')
        self.assertFalse(other_user.has_perm_to_view(contact)) #role.allowed_apps does not contain 'persons'

        url = '/creme_config/role/edit/%s' % role.id
        self.assertGET200(url)

        name   = role.name + '_edited'
        get_ct = ContentType.objects.get_for_model
        creatable_ctypes = [get_ct(Contact).id, get_ct(Organisation).id]
        exportable_ctypes = [get_ct(Contact).id, get_ct(Activity).id]
        apps = ['persons', 'tickets']
        admin_apps = ['persons']
        response = self.client.post(url, follow=True,
                                    data={'name':                    name,
                                          'creatable_ctypes':        creatable_ctypes,
                                          'exportable_ctypes':       exportable_ctypes,
                                          'allowed_apps':            apps,
                                          'admin_4_apps':            admin_apps,
                                          #'set_credentials_check_0': True,
                                          #'set_credentials_value_0': SetCredentials.ESET_ALL,
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

        contact = self.refresh(contact) #refresh cache
        self.assertTrue(self.refresh(other_user).has_perm_to_view(contact)) #role.allowed_apps contains 'persons' now

    #def test_edit02(self):
        #self.login()

        #apps = ['persons']

        #role = UserRole(name='CEO')
        #role.allowed_apps = apps
        #role.save()

        #create_creds = SetCredentials.objects.create
        #create_creds(role=role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)
        #create_creds(role=role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_OWN)

        #other_user = User.objects.create(username='chloe', role=role)

        #create_contact = Contact.objects.create
        #yuki   = create_contact(user=self.user,  first_name='Yuki',    last_name='Kajiura')
        #altena = create_contact(user=other_user, first_name=u'Alténa', last_name='??')
        #self.assertTrue(other_user.has_perm_to_view(yuki))
        #self.assertTrue(other_user.has_perm_to_view(altena))

        #response = self.client.post('/creme_config/role/edit/%s' % role.id, follow=True,
                                    #data={'name':                    role.name,
                                          #'allowed_apps':            apps,
                                          #'admin_4_apps':            [],
                                          #'set_credentials_check_1': True,
                                          #'set_credentials_value_1': SetCredentials.ESET_OWN,
                                         #}
                                   #)
        #self.assertNoFormError(response)

        #role = self.refresh(role)
        #self.assertFalse(role.creatable_ctypes.exists())
        #self.assertFalse(role.exportable_ctypes.exists())

        ##beware to refresh caches
        #other_user = self.refresh(other_user)
        #self.assertFalse(other_user.has_perm_to_view(self.refresh(yuki))) #no more SetCredentials
        #self.assertTrue(other_user.has_perm_to_view(self.refresh(altena)))

    #def test_edit03(self):
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
        user = User.objects.create(username='chloe', role=role_2_del) #<= role is used

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
        User.objects.create(username='chloe', role=role) #<= role is used

        response = self.assertPOST200(self._build_del_role_url(role))
        self.assertFormError(response, 'form', 'to_role', [_('This field is required.')])
