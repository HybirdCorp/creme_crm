# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _
    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import UserRole, SetCredentials
    from creme_core.auth.entity_credentials import EntityCredentials
    from creme_core.tests.base import CremeTestCase

    from activities.models import Meeting

    from persons.models import Contact, Organisation #need CremeEntity

    from creme_config import blocks
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('UserRoleTestCase',)


class UserRoleTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def login_not_as_superuser(self):
        apps = ('creme_config',)
        self.login(is_superuser=False, allowed_apps=apps, admin_4_apps=apps)

    def _aux_test_portal(self):
        response = self.assertGET200('/creme_config/role/portal/')
        self.assertContains(response, 'id="%s"' % blocks.UserRolesBlock.id_)

    def test_portal01(self):
        self.login()
        self._aux_test_portal()

    def test_portal02(self):
        self.login_not_as_superuser()
        self._aux_test_portal()

    def test_create01(self):
        self.login()

        url = '/creme_config/role/add/'
        self.assertGET200(url)

        get_ct = ContentType.objects.get_for_model
        name = 'CEO'
        creatable_ctypes = [get_ct(Contact).id, get_ct(Organisation).id]
        exportable_ctypes = [get_ct(Contact).id, get_ct(Meeting).id]
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
        self.assertEqual(set(creatable_ctypes),  set(ctype.id for ctype in role.creatable_ctypes.all()))
        self.assertEqual(set(exportable_ctypes), set(ctype.id for ctype in role.exportable_ctypes.all()))

        app_set = set(apps)
        self.assertEqual(app_set, role.allowed_apps)
        self.assertEqual(app_set, role.admin_4_apps)

    def test_create02(self):
        self.login_not_as_superuser()

        url = '/creme_config/role/add/'
        self.assertGETRedirectsToLogin(url)
        self.assertPOSTRedirectsToLogin(url, data={'name':              'CEO',
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
        self.assertFalse(contact.can_view(other_user))

        self.assertEqual(0, role.credentials.count())

        url = '/creme_config/role/add_credentials/%s' % role.id
        self.assertGET200(url)

        set_type = SetCredentials.ESET_ALL
        response = self.client.post(url, data={'can_view':   True,
                                               'can_change': False,
                                               'can_delete': False,
                                               'can_link':   False,
                                               'can_unlink': False,
                                               'set_type':   set_type,
                                               'ctype':      0,
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
        self.assertTrue(contact.can_view(other_user))

    def test_add_credentials02(self):
        self.login()

        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

        set_type = SetCredentials.ESET_OWN
        ct_id = ContentType.objects.get_for_model(Contact).id
        response = self.client.post('/creme_config/role/add_credentials/%s' % role.id,
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

        url = '/creme_config/role/add_credentials/%s' % role.id
        self.assertGETRedirectsToLogin(url)
        self.assertPOSTRedirectsToLogin(url, data={'can_view':   True,
                                                   'can_change': False,
                                                   'can_delete': False,
                                                   'can_link':   False,
                                                   'can_unlink': False,
                                                   'set_type':   SetCredentials.ESET_ALL,
                                                   'ctype':      0,
                                                   }
                                       )

    def test_edit01(self):
        self.login()

        role = UserRole.objects.create(name='CEO')
        SetCredentials.objects.create(role=role, value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL,
                                     )

        other_user = User.objects.create(username='chloe', role=role)
        contact    = Contact.objects.create(user=self.user, first_name='Yuki', last_name='Kajiura')
        self.assertFalse(contact.can_view(other_user)) #role.allowed_apps does not contain 'persons'

        url = '/creme_config/role/edit/%s' % role.id
        self.assertGET200(url)

        name   = role.name + '_edited'
        get_ct = ContentType.objects.get_for_model
        creatable_ctypes = [get_ct(Contact).id, get_ct(Organisation).id]
        exportable_ctypes = [get_ct(Contact).id, get_ct(Meeting).id]
        apps   = ['persons', 'tickets']
        admin_apps = ['persons']
        response = self.client.post(url, follow=True,
                                    data={'name':                    name,
                                          'creatable_ctypes':        creatable_ctypes,
                                          'exportable_ctypes':       exportable_ctypes,
                                          'allowed_apps':            apps,
                                          'admin_4_apps':            admin_apps,
                                          'set_credentials_check_0': True,
                                          'set_credentials_value_0': SetCredentials.ESET_ALL,
                                         }
                                   )
        self.assertNoFormError(response)

        role = self.refresh(role)
        self.assertEqual(set(creatable_ctypes),  set(ctype.id for ctype in role.creatable_ctypes.all()))
        self.assertEqual(set(exportable_ctypes), set(ctype.id for ctype in role.exportable_ctypes.all()))
        self.assertEqual(set(apps),       role.allowed_apps)
        self.assertEqual(set(admin_apps), role.admin_4_apps)

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(EntityCredentials.VIEW,  creds.value)
        self.assertEqual(SetCredentials.ESET_ALL, creds.set_type)

        contact = self.refresh(contact) #refresh cache
        self.assertTrue(contact.can_view(self.refresh(other_user))) #role.allowed_apps contains 'persons' now

    def test_edit02(self):
        self.login()

        apps = ['persons']

        role = UserRole(name='CEO')
        role.allowed_apps = apps
        role.save()

        create_creds = SetCredentials.objects.create
        create_creds(role=role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)
        create_creds(role=role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_OWN)

        other_user = User.objects.create(username='chloe', role=role)

        create_contact = Contact.objects.create
        yuki   = create_contact(user=self.user,  first_name='Yuki',    last_name='Kajiura')
        altena = create_contact(user=other_user, first_name=u'Alténa', last_name='??')
        self.assertTrue(yuki.can_view(other_user))
        self.assertTrue(altena.can_view(other_user))

        response = self.client.post('/creme_config/role/edit/%s' % role.id, follow=True,
                                    data={'name':                    role.name,
                                          'allowed_apps':            apps,
                                          'admin_4_apps':            [],
                                          'set_credentials_check_1': True,
                                          'set_credentials_value_1': SetCredentials.ESET_OWN,
                                         }
                                   )
        self.assertNoFormError(response)

        role = self.refresh(role)
        self.assertFalse(role.creatable_ctypes.exists())
        self.assertFalse(role.exportable_ctypes.exists())

        #beware to refresh caches
        other_user = self.refresh(other_user)
        self.assertFalse(self.refresh(yuki).can_view(other_user)) #no more SetCredentials
        self.assertTrue(self.refresh(altena).can_view(other_user))

    def test_edit03(self):
        self.login_not_as_superuser()

        role = UserRole.objects.create(name='CEO')
        url = '/creme_config/role/edit/%s' % role.id
        self.assertGETRedirectsToLogin(url)
        self.assertPOSTRedirectsToLogin(url, data={'name':              role.name,
                                                   'creatable_ctypes':  [],
                                                   'exportable_ctypes': [],
                                                   'allowed_apps':      [],
                                                   'admin_4_apps':      [],
                                                  }
                                       )


    def test_delete01(self):
        "Not superuser -> error"
        self.login_not_as_superuser()

        url = '/creme_config/role/delete/%s' % self.role.id
        self.assertGETRedirectsToLogin(url)
        self.assertPOSTRedirectsToLogin(url, data={})

    def test_delete02(self):
        "Role is not used"
        self.login()

        role = UserRole.objects.create(name='CEO')
        url = '/creme_config/role/delete/%s' % role.id
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            info = fields['info']

        self.assertFalse(info.required)
        self.assertNotIn('to_role', fields)

        self.assertNoFormError(self.client.post(url))

        rid = role.id
        self.assertFalse(UserRole.objects.filter(pk=rid))
        self.assertFalse(SetCredentials.objects.filter(role=rid))

    def test_delete03(self):
        "To replace by another role"
        self.login()

        replacing_role = self.role
        role_2_del = UserRole.objects.create(name='CEO')
        other_role = UserRole.objects.create(name='Coder')
        user = User.objects.create(username='chloe', role=role_2_del) #<= role is used

        url = '/creme_config/role/delete/%s' % role_2_del.id
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
        self.assertFalse(UserRole.objects.filter(pk=role_2_del.id))
        self.assertFalse(SetCredentials.objects.filter(role=role_2_del.id))
        self.assertEqual(replacing_role, self.refresh(user).role)

    def test_delete04(self):
        "Role is used -> replacing role is required"
        self.login()

        role = UserRole.objects.create(name='CEO')
        User.objects.create(username='chloe', role=role) #<= role is used

        response = self.assertPOST200('/creme_config/role/delete/%s' % role.id)
        self.assertFormError(response, 'form', 'to_role', [_('This field is required.')])
