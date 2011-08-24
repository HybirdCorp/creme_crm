# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.sessions.models import Session

from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import simplejson

from creme_core.models import *
from creme_core import autodiscover
from creme_core import gui
from creme_core.blocks import history_block
from creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme_core.tests.base import CremeTestCase

from activities.models import Calendar

from persons.models import Contact, Organisation #need CremeEntity
from persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES

from creme_config.constants import USER_THEME_NAME
from creme_config.models import *
from creme_config.utils import get_user_theme

#TODO: test views are allowed to admin only...


class UserRoleTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/role/portal/').status_code)

    def test_create01(self):
        response = self.client.get('/creme_config/role/add/')
        self.assertEqual(200,  response.status_code)

        get_ct = ContentType.objects.get_for_model
        name   = 'CEO'
        ctypes = [get_ct(Contact).id, get_ct(Organisation).id]
        apps   = ['persons']
        response = self.client.post('/creme_config/role/add/', follow=True,
                                    data={
                                            'name':             name,
                                            'creatable_ctypes': ctypes,
                                            'allowed_apps':     apps,
                                            'admin_4_apps':     apps,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            role = UserRole.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(set(ctypes), set(ctype.id for ctype in role.creatable_ctypes.all()))
        self.assertEqual(set(apps),   role.allowed_apps)
        self.assertEqual(set(apps),   role.admin_4_apps)

    def test_add_credentials01(self):
        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()

        other_user = User.objects.create(username='chloe', role=role)
        contact    = Contact.objects.create(user=self.user, first_name='Yuki', last_name='Kajiura')
        self.assertFalse(contact.can_view(other_user))

        self.assertEqual(0, role.credentials.count())

        response = self.client.get('/creme_config/role/add_credentials/%s' % role.id)
        self.assertEqual(200,  response.status_code)

        response = self.client.post('/creme_config/role/add_credentials/%s' % role.id,
                                    data={
                                            'can_view':   True,
                                            'can_change': False,
                                            'can_delete': False,
                                            'can_link':   False,
                                            'can_unlink': False,
                                            'set_type':   SetCredentials.ESET_ALL,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(SetCredentials.CRED_VIEW, creds.value)
        self.assertEqual(SetCredentials.ESET_ALL,  creds.set_type)

        contact = Contact.objects.get(pk=contact.id) #refresh cache
        self.assert_(contact.can_view(other_user))

    def test_edit01(self):
        role = UserRole.objects.create(name='CEO')
        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)

        other_user = User.objects.create(username='chloe', role=role)
        contact    = Contact.objects.create(user=self.user, first_name='Yuki', last_name='Kajiura')
        self.assertFalse(contact.can_view(other_user)) #role.allowed_apps does not contain 'persons'

        response = self.client.get('/creme_config/role/edit/%s' % role.id)
        self.assertEqual(200,  response.status_code)

        name   = role.name + '_edited'
        get_ct = ContentType.objects.get_for_model
        ctypes = [get_ct(Contact).id, get_ct(Organisation).id]
        apps   = ['persons', 'tickets']
        admin_apps = ['persons']
        response = self.client.post('/creme_config/role/edit/%s' % role.id, follow=True,
                                    data={
                                            'name':             name,
                                            'creatable_ctypes': ctypes,
                                            'allowed_apps':     apps,
                                            'admin_4_apps':     admin_apps,
                                            'set_credentials_check_0': True,
                                            'set_credentials_value_0': SetCredentials.ESET_ALL,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        try:
            role = UserRole.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(set(ctypes), set(ctype.id for ctype in role.creatable_ctypes.all()))
        self.assertEqual(set(apps),       role.allowed_apps)
        self.assertEqual(set(admin_apps), role.admin_4_apps)

        setcreds = role.credentials.all()
        self.assertEqual(1, len(setcreds))

        creds = setcreds[0]
        self.assertEqual(SetCredentials.CRED_VIEW, creds.value)
        self.assertEqual(SetCredentials.ESET_ALL,  creds.set_type)

        contact = Contact.objects.get(pk=contact.id) #refresh cache
        self.assert_(contact.can_view(other_user)) #role.allowed_apps contains 'persons' now

    def test_edit02(self):
        apps = ['persons']

        role = UserRole(name='CEO')
        role.allowed_apps = apps
        role.save()

        create_creds = SetCredentials.objects.create
        create_creds(role=role, value=SetCredentials.CRED_VIEW, set_type=SetCredentials.ESET_ALL)
        create_creds(role=role, value=SetCredentials.CRED_VIEW, set_type=SetCredentials.ESET_OWN)

        other_user = User.objects.create(username='chloe', role=role)
        yuki   = Contact.objects.create(user=self.user, first_name='Yuki', last_name='Kajiura')
        altena = Contact.objects.create(user=other_user, first_name=u'Alténa', last_name='??')
        self.assert_(yuki.can_view(other_user))
        self.assert_(altena.can_view(other_user))

        get_ct = ContentType.objects.get_for_model
        ctypes = [get_ct(Contact).id, get_ct(Organisation).id]
        response = self.client.post('/creme_config/role/edit/%s' % role.id, follow=True,
                                    data={
                                            'name':                    role.name,
                                            'creatable_ctypes':        ctypes,
                                            'allowed_apps':            apps,
                                            'admin_4_apps':            [],
                                            'set_credentials_check_1': True,
                                            'set_credentials_value_1': SetCredentials.ESET_OWN,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            role = UserRole.objects.get(name=role.name)
        except Exception, e:
            self.fail(str(e))

        yuki = Contact.objects.get(pk=yuki.id) #refresh caches
        altena = Contact.objects.get(pk=altena.id)
        self.assertFalse(yuki.can_view(other_user)) #no more SetCredentials
        self.assert_(altena.can_view(other_user))

    def test_delete01(self):
        role = self.role
        role.allowed_apps = ['persons']
        role.save()
        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)

        other_user = self.other_user
        yuki = Contact.objects.create(user=self.user, first_name='Yuki', last_name='Kajiura')
        self.assert_(yuki.can_view(other_user))
        self.assertEqual(1, EntityCredentials.objects.count())

        response = self.client.post('/creme_config/role/delete', follow=True,
                                    data={'id': role.id}
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFalse(UserRole.objects.count())

        self.assertFalse(EntityCredentials.get_default_creds().can_view())
        self.assertEqual(0, EntityCredentials.objects.count())
        self.assertEqual(0, SetCredentials.objects.count())
        self.assertEqual(1, User.objects.filter(pk=other_user.id).count())

        yuki = Contact.objects.get(pk=yuki.id) #refresh caches
        self.assertFalse(yuki.can_view(other_user)) #defaultCreds are applied

    def test_set_default_creds(self):
        defcreds = EntityCredentials.get_default_creds()
        self.assertFalse(defcreds.can_view())
        self.assertFalse(defcreds.can_change())
        self.assertFalse(defcreds.can_delete())
        self.assertFalse(defcreds.can_link())
        self.assertFalse(defcreds.can_unlink())

        response = self.client.get('/creme_config/role/set_default_creds/')
        self.assertEqual(200, response.status_code)

        response = self.client.post('/creme_config/role/set_default_creds/', follow=True,
                                    data={
                                            'can_view':   True,
                                            'can_change': True,
                                            'can_delete': True,
                                            'can_link':   True,
                                            'can_unlink': True,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        defcreds = EntityCredentials.get_default_creds()
        self.assert_(defcreds.can_view())
        self.assert_(defcreds.can_change())
        self.assert_(defcreds.can_delete())
        self.assert_(defcreds.can_link())
        self.assert_(defcreds.can_unlink())


class UserTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config', 'persons') #'creme_core'
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/user/portal/').status_code)

    def test_create01(self):
        response = self.client.get('/creme_config/user/add/')
        self.assertEqual(200, response.status_code)

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username   = 'deunan'
        first_name = 'Deunan'
        last_name  = u'Knut'
        password   = 'password'
        email      = 'd.knut@eswat.ol'
        response = self.client.post('/creme_config/user/add/', follow=True,
                                    data={
                                        'username':     username,
                                        'password_1':   password,
                                        'password_2':   password,
                                        'first_name':   first_name,
                                        'last_name':    last_name,
                                        'email':        email,
                                        'is_superuser': True,
                                        'organisation': orga.id,
                                        'relation':     REL_SUB_EMPLOYED_BY,
                                        }
        )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        users = User.objects.filter(username=username)
        self.assertEqual(1, len(users))

        user = users[0]
        self.assert_(user.is_superuser)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)
        self.assert_(user.check_password(password))

        self.assertEqual(0, EntityCredentials.objects.filter(user=user).count())

    def test_create02(self):
        role = UserRole(name='Mangaka')
        role.allowed_apps = ['persons']
        role.save()

        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username = 'deunan'
        password = 'password'
        response = self.client.post('/creme_config/user/add/', follow=True,
                                    data={
                                        'username':     username,
                                        'password_1':   password,
                                        'password_2':   password,
                                        'role':         role.id,
                                        'organisation': orga.id,
                                        'relation':     REL_SUB_MANAGES,
                                        }
        )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        users = User.objects.filter(username=username)
        self.assertEqual(1, len(users))

        user = users[0]
        self.assertEqual(2 + 2, CremeEntity.objects.count())#2 from creme_core populate + 2 from now
        self.assertEqual(2 + 2, EntityCredentials.objects.filter(user=user).count())#2 from creme_core populate + 2 from now

        self.assert_(orga.can_view(user))

    def test_edit01(self):
        role1 = UserRole(name='Master')
        role1.allowed_apps = ['persons']
        role1.save()
        SetCredentials.objects.create(role=role1, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)
        other_user = User.objects.create(username='deunan', role=role1)

        briareos = Contact.objects.create(user=self.user, first_name='Briareos', last_name='Hecatonchires')
        self.assert_(briareos.can_view(other_user))

        response = self.client.get('/creme_config/user/edit/%s' % other_user.id)
        self.assertEqual(200, response.status_code)

        first_name = 'Deunan'
        last_name  = u'Knut'
        email      = 'd.knut@eswat.ol'
        role2 = UserRole.objects.create(name='Slave')
        response = self.client.post('/creme_config/user/edit/%s' % other_user.id, follow=True,
                                    data={
                                            'first_name':   first_name,
                                            'last_name':    last_name,
                                            'email':        email,
                                            'role':         role2.id,
                                         }
        )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        other_user = User.objects.get(pk=other_user.id)
        self.assertEqual(first_name, other_user.first_name)
        self.assertEqual(last_name,  other_user.last_name)
        self.assertEqual(email,      other_user.email)
        self.assertEqual(role2.id,   other_user.role_id)

        briareos = Contact.objects.get(pk=briareos.id) #refresh cache
        self.assertFalse(briareos.can_view(other_user))

    def test_change_password(self):
        other_user = User.objects.create(username='deunan')

        response = self.client.get('/creme_config/user/edit/password/%s' % other_user.id)
        self.assertEqual(200, response.status_code)

        password = 'password'
        response = self.client.post('/creme_config/user/edit/password/%s' % other_user.id,
                                    follow=True,
                                    data= {
                                        'password_1':   password,
                                        'password_2':   password,
                                        }
        )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        other_user = User.objects.get(pk=other_user.pk)
        self.assert_(other_user.check_password(password))

    def test_portal(self):
        response = self.client.get('/creme_config/user/portal/')
        self.assertEqual(200, response.status_code)

    def test_team_create(self):
        response = self.client.get('/creme_config/team/add/')
        self.assertEqual(200, response.status_code)

        create_user = User.objects.create_user
        user01 = create_user('Shogun', 'shogun@century.jp', 'uselesspw')
        user02 = create_user('Yoshitsune', 'yoshitsune@century.jp', 'uselesspw')

        username   = 'Team-A'
        response = self.client.post('/creme_config/team/add/', follow=True,
                                    data={
                                        'username':     username,
                                        'teammates':    [user01.id, user02.id],
                                        }
        )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        teams = User.objects.filter(is_team=True)
        self.assertEqual(1, len(teams))

        team = teams[0]
        self.assertFalse(team.is_superuser)
        self.assertEqual('',  team.first_name)
        self.assertEqual('',  team.last_name)
        self.assertEqual('',  team.email)

        teammates = team.teammates
        self.assertEqual(2, len(teammates))
        self.assert_(user01.id in teammates)
        self.assert_(user02.id in teammates)

    def _create_team(self, name, teammates):
        team = User.objects.create(username=name, is_team=True, role=None)

        team.teammates = teammates

        return team

    def test_team_edit(self):
        role = UserRole(name='Role')
        role.allowed_apps = ['creme_core']
        role.save()
        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_OWN)

        def create_user(name, email):
            user = User.objects.create_user(name, email, 'uselesspw')
            user.role = role
            user.save()

            return user

        user01 = create_user('Maruo',   'maruo@century.jp')
        user02 = create_user('Yokiji',  'yokiji@century.jp')
        user03 = create_user('Koizumi', 'koizumi@century.jp')

        response = self.client.get('/creme_config/team/edit/%s' % user01.id)
        self.assertEqual(404, response.status_code)

        teamname = 'Teamee'
        team = self._create_team(teamname, [user01, user02])

        entity = CremeEntity.objects.create(user=team)
        self.assert_(entity.can_view(user01))
        self.assert_(entity.can_view(user02))
        self.assertFalse(entity.can_view(user03))

        response = self.client.get('/creme_config/team/edit/%s' % team.id)
        self.assertEqual(200, response.status_code)

        teamname += '_edited'
        response = self.client.post('/creme_config/team/edit/%s' % team.id, follow=True,
                                    data={
                                        'username':     teamname,
                                        'teammates':    [user02.id, user03.id],
                                        }
        )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        team = User.objects.get(pk=team.id) #refresh
        self.assertEqual(teamname, team.username)

        teammates = team.teammates
        self.assertEqual(2, len(teammates))
        self.assert_(user02.id in teammates)
        self.assert_(user03.id in teammates)
        self.assertFalse(user01.id in teammates)

        #credentials have been updated ?
        entity = CremeEntity.objects.get(pk=entity.id)
        self.assertFalse(entity.can_view(user01))
        self.assert_(entity.can_view(user02))
        self.assert_(entity.can_view(user03))

    def test_team_delete01(self):
        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        team = self._create_team('Teamee', [])

        response = self.client.get('/creme_config/team/delete/%s' % user.id)#user is not a team
        self.assertEqual(400, response.status_code)

        response = self.client.post('/creme_config/team/delete/%s' % user.id, data={'to_user': None})#user is not a team
        self.assertEqual(400, response.status_code)

        response = self.client.get('/creme_config/team/delete/%s' % team.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/creme_config/team/delete/%s' % team.id, data={'to_user': user.id})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   User.objects.filter(pk=team.id).count())

    def test_team_delete02(self):
        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        team  = self._create_team('Teamee', [user])
        team2 = self._create_team('Teamee2', [user])

        ce = CremeEntity.objects.create(user=team)

        url = '/creme_config/team/delete/%s' % team.id

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(url, data={'to_user': team2.id})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, User.objects.filter(pk=team.id).count())

        try:
            ce = CremeEntity.objects.get(pk=ce.id)#Refresh
        except CremeEntity.DoesNotExist, e:
            self.fail(e)

        self.assertEqual(team2, ce.user)

    def test_team_delete03(self):
        team = self._create_team('Teamee', [])
        CremeEntity.objects.create(user=team)

        response = self.client.post('/creme_config/team/delete/%s' % team.id, data={'to_user': self.user.id})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, User.objects.filter(pk=team.id).count())

    def test_user_delete01(self):
        CremeEntity.objects.all().delete()#In creme_core populate some entities are created, so we avoid an IntegrityError
        HistoryLine.objects.all().delete()
        User.objects.all().exclude(pk=self.user.pk).delete()#Ensure there is only one user

        self.assertEqual(1, User.objects.all().count())

        response = self.client.get('/creme_config/user/delete/%s' % self.user.id)
        self.assertEqual(400, response.status_code)

        response = self.client.post('/creme_config/user/delete/%s' % self.user.id, {'to_user': self.user.id})

        self.assertEqual(400, response.status_code)#Delete is not permitted when there is only one user
        self.assertEqual(1, User.objects.all().count())

    def test_user_delete02(self):
        self.assert_(User.objects.all().count() > 1)

        response = self.client.get('/creme_config/user/delete/%s' % self.user.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/creme_config/user/delete/%s' % self.user.id, {'to_user': self.user.id})
        self.assertEqual(200, response.status_code)#Can't assign and delete the same user
        self.assert_(response.context['form'].errors)
        self.assert_(User.objects.filter(pk=self.user.id))

    def test_user_delete03(self):
        user       = self.user
        other_user = self.other_user

        ce = CremeEntity.objects.create(user=other_user)

        response = self.client.get('/creme_config/user/delete/%s' % other_user.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/creme_config/user/delete/%s' % other_user.id, {'to_user': user.id})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertFalse(User.objects.filter(id=other_user.id))

        try:
            ce = CremeEntity.objects.get(pk=ce.id)#Refresh
        except CremeEntity.DoesNotExist, e:
            self.fail(e)

        self.assertEqual(user, ce.user)

    def test_user_delete04(self):
        user       = self.user
        other_user = self.other_user

        cal = Calendar.get_user_default_calendar(other_user)
        url = '/creme_config/user/delete/%s' % other_user.id

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(url, {'to_user': user.id})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertFalse(User.objects.filter(id=other_user.id))

        try:
            cal = Calendar.objects.get(pk=cal.id)
        except Calendar.DoesNotExist, e:
            self.fail(e)

        self.assertEqual(user, cal.user)

    def test_user_delete05(self):
        user       = self.user
        other_user = self.other_user

        Contact.objects.create(user=user, is_user=user)
        Contact.objects.create(user=other_user, is_user=other_user)
        Contact.objects.create(user=user, is_user=None)
        Contact.objects.create(user=other_user, is_user=None)

        response = self.client.post('/creme_config/user/delete/%s' % other_user.id, {'to_user': user.id})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertFalse(User.objects.filter(id=other_user.id))

        self.assertFalse(Contact.objects.filter(user=other_user))
        self.assertFalse(Contact.objects.filter(is_user=other_user))

        self.assertEqual(1, Contact.objects.filter(is_user=user).count())

    def test_user_delete06(self):
        setting_key = 'unit_test-test_userl_delete06'
        sk = SettingKey.create(pk=setting_key,
                               description="",
                               app_label='creme_config', type=SettingKey.BOOL
                      )
        SettingValue.objects.create(key=sk, user=self.other_user, value=True)

        response = self.client.post('/creme_config/user/delete/%s' % self.other_user.id, {'to_user': self.user.id})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertFalse(User.objects.filter(id=self.other_user.id))
        self.assertFalse(SettingValue.objects.filter(key=setting_key))


class PropertyTypeTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/property_type/portal/').status_code)

    def _find_property_type(self, prop_types, text):
        for prop_type in prop_types:
            if prop_type.text == text:
                return prop_type

        self.fail('No property <%s>' % text)

    def test_create01(self):
        url = '/creme_config/property_type/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        self.assertEqual(1, CremePropertyType.objects.count())#The one from creme_core populate

        text = 'is beautiful'
        response = self.client.post(url, data={'text': text})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        prop_types = CremePropertyType.objects.all()
        self.assertEqual(2, len(prop_types))

        prop_type = self._find_property_type(prop_types, text)
        self.assertEqual(0, prop_type.subject_ctypes.count())

    def test_create02(self):
        get_ct = ContentType.objects.get_for_model
        ct_ids = [get_ct(Contact).id, get_ct(Organisation).id]
        text   = 'is beautiful'
        response = self.client.post('/creme_config/property_type/add/',
                                    data={
                                            'text':           text,
                                            'subject_ctypes': ct_ids,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        prop_type = self._find_property_type(CremePropertyType.objects.all(), text)
        ctypes = prop_type.subject_ctypes.all()
        self.assertEqual(2,           len(ctypes))
        self.assertEqual(set(ct_ids), set(ct.id for ct in ctypes))

    def test_edit01(self):
        get_ct = ContentType.objects.get_for_model
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [get_ct(Contact)], is_custom=False)

        self.assertEqual(404, self.client.get('/creme_config/property_type/edit/%s' % pt.id).status_code)

    def test_edit02(self):
        get_ct = ContentType.objects.get_for_model
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [get_ct(Contact)], is_custom=True)
        uri = '/creme_config/property_type/edit/%s' % pt.id
        self.assertEqual(200, self.client.get(uri).status_code)

        ct_orga = get_ct(Organisation)
        text   = 'is very beautiful'
        response = self.client.post(uri,
                                    data={
                                            'text':           text,
                                            'subject_ctypes': [ct_orga.id],
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        prop_type = CremePropertyType.objects.get(pk=pt.id)
        self.assertEqual(text,         prop_type.text)
        self.assertEqual([ct_orga.id], [ct.id for ct in prop_type.subject_ctypes.all()])

    def test_delete01(self):
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [], is_custom=False)
        self.assertEqual(404, self.client.post('/creme_config/property_type/delete', data={'id': pt.id}).status_code)

    def test_delete02(self):
        pt = CremePropertyType.create('test-foobar', 'is beautiful', [], is_custom=True)
        self.assertEqual(200, self.client.post('/creme_config/property_type/delete', data={'id': pt.id}).status_code)
        self.assertEqual(0,   CremePropertyType.objects.filter(pk=pt.id).count())


class RelationTypeTestCase(CremeTestCase):
    def setUp(self): #in CremeConfigTestCase ??
        self.populate('creme_core', 'creme_config')
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/relation_type/portal/').status_code)

    def _find_relation_type(self, relation_types, predicate):
        for relation_type in relation_types:
            if relation_type.predicate == predicate:
                return relation_type

        self.fail('No relation type <%s>' % predicate)

    def test_create01(self):
        url = '/creme_config/relation_type/add/'
        self.assertEqual(200, self.client.get(url).status_code)
        rel_type_core_populate_count = 2

        self.assertEqual(rel_type_core_populate_count, RelationType.objects.count())#4 from creme_core populate

        subject_pred = 'loves'
        object_pred  = 'is loved by'
        response = self.client.post(url, data={
                                                'subject_predicate': subject_pred,
                                                'object_predicate':  object_pred,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        rel_types = RelationType.objects.all()
        self.assertEqual(rel_type_core_populate_count + 2, len(rel_types))#4 from creme_core populate + 2freshly created

        rel_type = self._find_relation_type(rel_types, subject_pred)
        self.assert_(rel_type.is_custom)
        self.assertEqual(object_pred, rel_type.symmetric_type.predicate)
        self.assertEqual(0,           rel_type.subject_ctypes.count())
        self.assertEqual(0,           rel_type.object_ctypes.count())
        self.assertEqual(0,           rel_type.subject_properties.count())
        self.assertEqual(0,           rel_type.object_properties.count())

    def test_create02(self):
        pt_sub = CremePropertyType.create('test-pt_sub', 'has cash',  [Organisation])
        pt_obj = CremePropertyType.create('test-pt_sub', 'need cash', [Contact])

        get_ct     = ContentType.objects.get_for_model
        ct_orga    = get_ct(Organisation)
        ct_contact = get_ct(Contact)

        subject_pred = 'employs'
        response = self.client.post('/creme_config/relation_type/add/',
                                    data={
                                            'subject_predicate':  subject_pred,
                                            'object_predicate':   'is employed by',
                                            'subject_ctypes':     [ct_orga.id],
                                            'subject_properties': [pt_sub.id],
                                            'object_ctypes':      [ct_contact.id],
                                            'object_properties':  [pt_obj.id],
                                          }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        rel_type = self._find_relation_type(RelationType.objects.all(), subject_pred)
        self.assertEqual([ct_orga.id],    [ct.id for ct in rel_type.subject_ctypes.all()])
        self.assertEqual([ct_contact.id], [ct.id for ct in rel_type.object_ctypes.all()])
        self.assertEqual([pt_sub.id],     [pt.id for pt in rel_type.subject_properties.all()])
        self.assertEqual([pt_obj.id],     [pt.id for pt in rel_type.object_properties.all()])

    def test_edit01(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                      ('test-objfoo', 'object_predicate'), is_custom=False
                                     )
        self.assertEqual(404, self.client.get('/creme_config/relation_type/edit/%s' % rt.id).status_code)

    def test_edit02(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                      ('test-objfoo', 'object_predicate'),
                                      is_custom=True
                                     )
        url = '/creme_config/relation_type/edit/%s' % rt.id
        self.assertEqual(200, self.client.get(url).status_code)

        subject_pred = 'loves'
        object_pred  = 'is loved by'
        response = self.client.post(url,
                                    data={
                                            'subject_predicate': subject_pred,
                                            'object_predicate':  object_pred,
                                          }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        rel_type = RelationType.objects.get(pk=rt.id)
        self.assertEqual(subject_pred, rel_type.predicate)
        self.assertEqual(object_pred,  rel_type.symmetric_type.predicate)

    def test_delete01(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'), ('test-subfoo', 'object_predicate'), is_custom=False)
        self.assertEqual(404, self.client.post('/creme_config/relation_type/delete', data={'id': rt.id}).status_code)

    def test_delete02(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'), ('test-subfoo', 'object_predicate'), is_custom=True)
        self.assertEqual(200, self.client.post('/creme_config/relation_type/delete', data={'id': rt.id}).status_code)
        self.assertEqual(0,   RelationType.objects.filter(pk__in=[rt.id, srt.id]).count())


class BlocksConfigTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
        self.login()

        autodiscover()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/blocks/portal/').status_code)

    def test_add_detailview(self):
        url = '/creme_config/blocks/detailview/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        ct = ContentType.objects.get_for_model(Contact)
        self.assertEqual(0, BlockDetailviewLocation.objects.filter(content_type=ct).count())

        response = self.client.post(url, data={'ct_id': ct.id})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        b_locs = BlockDetailviewLocation.objects.filter(content_type=ct)
        self.assertEqual([('', 1)] * 4, [(bl.block_id, bl.order) for bl in b_locs])
        self.assertEqual(set([BlockDetailviewLocation.TOP, BlockDetailviewLocation.LEFT, BlockDetailviewLocation.RIGHT, BlockDetailviewLocation.BOTTOM]),
                         set(bl.zone for bl in b_locs)
                        )

        response = self.client.get(url)

        try:
            choices = response.context['form'].fields['ct_id'].choices
        except Exception, e:
            self.fail(str(e))

        self.assert_(ct.id not in (ct_id for ct_id, ctype in choices))

    def _find_field_index(self, formfield, name):
        for i, (fname, fvname) in enumerate(formfield.choices):
            if fname == name:
                return i

        self.fail('No "%s" field' % name)

    def _find_location(self, block_id, locations):
        for location in locations:
            if location.block_id == block_id:
                return location

        self.fail('No "%s" in locations' % block_id)

    def test_edit_detailview01(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.assertEqual(404, self.client.get('/creme_config/blocks/detailview/edit/%s' % ct.id).status_code)

    def test_edit_detailview02(self):
        model = Contact
        ct = ContentType.objects.get_for_model(model)

        self.client.post('/creme_config/blocks/detailview/add/', data={'ct_id': ct.id})
        self.assertEqual(4, BlockDetailviewLocation.objects.filter(content_type=ct).count())

        url = '/creme_config/blocks/detailview/edit/%s' % ct.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            fields = response.context['form'].fields
            top_field    = fields['top']
            left_field   = fields['left']
            right_field  = fields['right']
            bottom_field = fields['bottom']
        except KeyError, e:
            self.fail(str(e))

        blocks = list(gui.block.block_registry.get_compatible_blocks(model)) #TODO test get_compatible_blocks() in creme_core
        self.assert_(len(blocks) >= 5)

        block_top_id1   = blocks[0].id_
        block_top_id2   = blocks[1].id_
        block_left_id   = blocks[2].id_
        block_right_id  = blocks[3].id_
        block_bottom_id = blocks[4].id_

        block_top_index1 = self._find_field_index(top_field, block_top_id1)
        block_top_index2 = self._find_field_index(top_field, block_top_id2)
        block_left_index = self._find_field_index(left_field, block_left_id)
        block_right_index = self._find_field_index(right_field, block_right_id)
        block_bottom_index = self._find_field_index(bottom_field, block_bottom_id)

        response = self.client.post(url,
                                    data={
                                            'top_check_%s' % block_top_index1: 'on',
                                            'top_value_%s' % block_top_index1: block_top_id1,
                                            'top_order_%s' % block_top_index1: 1,

                                            'top_check_%s' % block_top_index2: 'on',
                                            'top_value_%s' % block_top_index2: block_top_id2,
                                            'top_order_%s' % block_top_index2: 2,

                                            'left_check_%s' % block_left_index: 'on',
                                            'left_value_%s' % block_left_index: block_left_id,
                                            'left_order_%s' % block_left_index: 1,

                                            'right_check_%s' % block_right_index: 'on',
                                            'right_value_%s' % block_right_index: block_right_id,
                                            'right_order_%s' % block_right_index: 1,

                                            'bottom_check_%s' % block_bottom_index: 'on',
                                            'bottom_value_%s' % block_bottom_index: block_bottom_id,
                                            'bottom_order_%s' % block_bottom_index: 1,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = BlockDetailviewLocation.objects.filter(content_type=ct)

        locations = [b_loc for b_loc in b_locs if  b_loc.zone == BlockDetailviewLocation.TOP]
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(block_top_id1, locations).order)
        self.assertEqual(2, self._find_location(block_top_id2, locations).order)

        locations = [b_loc for b_loc in b_locs if  b_loc.zone == BlockDetailviewLocation.LEFT]
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(block_left_id, locations).order)

        locations = [b_loc for b_loc in b_locs if  b_loc.zone == BlockDetailviewLocation.RIGHT]
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(block_right_id, locations).order)

        locations = [b_loc for b_loc in b_locs if  b_loc.zone == BlockDetailviewLocation.BOTTOM]
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(block_bottom_id, locations).order)

    def test_edit_detailview03(self): #when no block -> fake block
        model = Contact
        ct = ContentType.objects.get_for_model(model)

        blocks = list(gui.block.block_registry.get_compatible_blocks(model))
        self.assert_(len(blocks) >= 5, blocks)

        create_loc = BlockDetailviewLocation.objects.create
        create_loc(content_type=ct, block_id=blocks[0].id_, order=1, zone=BlockDetailviewLocation.TOP)
        create_loc(content_type=ct, block_id=blocks[1].id_, order=1, zone=BlockDetailviewLocation.LEFT)
        create_loc(content_type=ct, block_id=blocks[2].id_, order=1, zone=BlockDetailviewLocation.RIGHT)
        create_loc(content_type=ct, block_id=blocks[3].id_, order=1, zone=BlockDetailviewLocation.BOTTOM)

        url = '/creme_config/blocks/detailview/edit/%s' % ct.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            fields = response.context['form'].fields
            top_field    = fields['top']
            left_field   = fields['left']
            right_field  = fields['right']
            bottom_field = fields['bottom']
        except KeyError, e:
            self.fail(str(e))

        block_top_id1   = blocks[0].id_
        block_top_id2   = blocks[1].id_

        self.assertEqual([block_top_id1], top_field.initial)
        self.assertEqual([block_top_id2], left_field.initial)
        self.assertEqual([blocks[2].id_], right_field.initial)
        self.assertEqual([blocks[3].id_], bottom_field.initial)

        block_top_index1 = self._find_field_index(top_field, block_top_id1)
        block_top_index2 = self._find_field_index(top_field, block_top_id2)

        response = self.client.post(url,
                                    data={
                                            'top_check_%s' % block_top_index1: 'on',
                                            'top_value_%s' % block_top_index1: block_top_id1,
                                            'top_order_%s' % block_top_index1: 1,

                                            'top_check_%s' % block_top_index2: 'on',
                                            'top_value_%s' % block_top_index2: block_top_id2,
                                            'top_order_%s' % block_top_index2: 2,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        b_locs = BlockDetailviewLocation.objects.filter(content_type=ct)
        locations = [b_loc for b_loc in b_locs if  b_loc.zone == BlockDetailviewLocation.TOP]
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(block_top_id1, locations).order)
        self.assertEqual(2, self._find_location(block_top_id2, locations).order)

        self.assertEqual([('', 1)], [(bl.block_id, bl.order) for bl in b_locs if bl.zone == BlockDetailviewLocation.LEFT])
        self.assertEqual([('', 1)], [(bl.block_id, bl.order) for bl in b_locs if bl.zone == BlockDetailviewLocation.RIGHT])
        self.assertEqual([('', 1)], [(bl.block_id, bl.order) for bl in b_locs if bl.zone == BlockDetailviewLocation.BOTTOM])

    def test_edit_detailview04(self): #default conf
        BlockDetailviewLocation.objects.filter(content_type=None).delete()
        url = '/creme_config/blocks/detailview/edit/0'
        self.assertEqual(404, self.client.get(url).status_code)

        blocks = list(gui.block.block_registry.get_compatible_blocks(model=None))
        self.assert_(len(blocks) >= 5, blocks)

        create_loc = BlockDetailviewLocation.objects.create
        create_loc(block_id=blocks[0].id_, order=1, zone=BlockDetailviewLocation.TOP)
        create_loc(block_id=blocks[1].id_, order=1, zone=BlockDetailviewLocation.LEFT)
        create_loc(block_id=blocks[2].id_, order=1, zone=BlockDetailviewLocation.RIGHT)
        create_loc(block_id=blocks[3].id_, order=1, zone=BlockDetailviewLocation.BOTTOM)

        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        b_locs = BlockDetailviewLocation.objects.filter(content_type=None)
        self.assertEqual([('', 1)] * 4, [(bl.block_id, bl.order) for bl in b_locs])
        self.assertEqual(set([BlockDetailviewLocation.TOP, BlockDetailviewLocation.LEFT, BlockDetailviewLocation.RIGHT, BlockDetailviewLocation.BOTTOM]),
                         set(bl.zone for bl in b_locs)
                        )

    def test_edit_detailview05(self): #post one block several times -> validation error
        model = Contact
        ct = ContentType.objects.get_for_model(model)

        self.client.post('/creme_config/blocks/detailview/add/', data={'ct_id': ct.id})
        self.assertEqual(4, BlockDetailviewLocation.objects.filter(content_type=ct).count())

        url = '/creme_config/blocks/detailview/edit/%s' % ct.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            fields = response.context['form'].fields
            left_field  = fields['left']
            right_field = fields['right']
        except KeyError, e:
            self.fail(str(e))

        blocks = list(gui.block.block_registry.get_compatible_blocks(model))
        self.assert_(len(blocks))

        evil_block = blocks[0]

        block_left_id = block_right_id = evil_block.id_ # <= same block !!
        block_left_index  = self._find_field_index(left_field,  block_left_id)
        block_right_index = self._find_field_index(right_field, block_right_id)

        response = self.client.post(url,
                                    data={
                                            'right_check_%s' % block_right_index: 'on',
                                            'right_value_%s' % block_right_index: block_right_id,
                                            'right_order_%s' % block_right_index: 1,

                                            'left_check_%s' % block_left_index: 'on',
                                            'left_value_%s' % block_left_index: block_left_id,
                                            'left_order_%s' % block_left_index: 1,
                                         }
                                   )
        self.assertFormError(response, 'form', field=None,
                             errors=[_(u'The following block should be displayed only once: <%s>') % evil_block.verbose_name]
                            )

    def test_edit_detailview06(self): #instance block, relationtype block
        model = Contact
        ct = ContentType.objects.get_for_model(model)

        self.client.post('/creme_config/blocks/detailview/add/', data={'ct_id': ct.id})

        rtype = RelationType.objects.all()[0]
        rtype_block_id = gui.block.SpecificRelationsBlock.generate_id('test', 'foobar')
        RelationBlockItem.objects.create(block_id=rtype_block_id, relation_type=rtype)

        naru = Contact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')
        instance_block_id = InstanceBlockConfigItem.generate_id('test__blocks__FoobarBlock', 'test', 'foobar')
        InstanceBlockConfigItem.objects.create(block_id=instance_block_id, entity=naru, verbose='All stuffes')

        response = self.client.get('/creme_config/blocks/detailview/edit/%s' % ct.id)
        self.assertEqual(200, response.status_code)

        try:
            top_field = response.context['form'].fields['top']
        except KeyError, e:
            self.fail(str(e))

        choices = [block_id for block_id, block_name in top_field.choices]
        self.assert_(rtype_block_id in choices, choices)
        self.assert_(instance_block_id in choices, choices)

    def test_delete_detailview01(self): #can not delete default conf
        response = self.client.post('/creme_config/blocks/detailview/delete', data={'id': 0})
        self.assertEqual(404, response.status_code)

    def test_delete_detailview02(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.client.post('/creme_config/blocks/detailview/add/', data={'ct_id': ct.id})

        response = self.client.post('/creme_config/blocks/detailview/delete', data={'id': ct.id})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, BlockDetailviewLocation.objects.filter(content_type=ct).count())

    def test_add_portal(self):
        url = '/creme_config/blocks/portal/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        app_name = 'persons'
        self.assertEqual(0, BlockPortalLocation.objects.filter(app_name=app_name).count())

        response = self.client.post(url, data={'app_name': app_name})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        b_locs = list(BlockPortalLocation.objects.filter(app_name=app_name))
        self.assertEqual(1, len(b_locs))

        bpl = b_locs[-1]
        self.assertEqual(1,  bpl.order)
        self.assertEqual('', bpl.block_id)

        response = self.client.get(url)

        try:
            choices = response.context['form'].fields['app_name'].choices
        except Exception, e:
            self.fail(str(e))

        names = set(name for name, vname in choices)
        self.assert_(app_name not in names, names)
        self.assert_('creme_core' not in names, names)
        self.assert_('creme_config' not in names, names)

    def test_edit_portal01(self):
        self.assertEqual(404, self.client.get('/creme_config/blocks/portal/edit/persons').status_code)

    def test_edit_portal02(self):
        app_name = 'persons'

        self.client.post('/creme_config/blocks/portal/add/', data={'app_name': app_name})
        self.assertEqual(1, BlockPortalLocation.objects.filter(app_name=app_name).count())

        url = '/creme_config/blocks/portal/edit/%s' % app_name
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            blocks_field = response.context['form'].fields['blocks']
        except KeyError, e:
            self.fail(str(e))

        choices = blocks_field.choices
        self.assert_(len(choices) >= 2)

        block_id1 = choices[0][0]
        block_id2 = choices[1][0]

        index1 = self._find_field_index(blocks_field, block_id1)
        index2 = self._find_field_index(blocks_field, block_id2)

        response = self.client.post(url,
                                    data={
                                            'blocks_check_%s' % index1: 'on',
                                            'blocks_value_%s' % index1: block_id1,
                                            'blocks_order_%s' % index1: 1,

                                            'blocks_check_%s' % index2: 'on',
                                            'blocks_value_%s' % index2: block_id2,
                                            'blocks_order_%s' % index2: 2,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = list(BlockPortalLocation.objects.filter(app_name=app_name))
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(block_id1, b_locs).order)
        self.assertEqual(2, self._find_location(block_id2, b_locs).order)

    def _get_blocks_4_portal(self):
        blocks = list(block for block_id, block in  gui.block.block_registry if hasattr(block, 'portal_display'))
        self.assert_(len(blocks) >= 2, blocks)

        return blocks

    def test_edit_portal03(self): #set no block -> fake blocks
        app_name = 'persons'
        blocks = self._get_blocks_4_portal()

        create_loc = BlockPortalLocation.objects.create
        create_loc(app_name=app_name, block_id=blocks[0].id_, order=1)
        create_loc(app_name=app_name, block_id=blocks[1].id_, order=2)

        url = '/creme_config/blocks/portal/edit/%s' % app_name
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            blocks_field = response.context['form'].fields['blocks']
        except KeyError, e:
            self.fail(str(e))

        self.assertEqual([blocks[0].id_, blocks[1].id_], blocks_field.initial)

        response = self.client.post(url, data={})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        b_locs = list(BlockPortalLocation.objects.filter(app_name=app_name))
        self.assertEqual(1, len(b_locs))

        bpl = b_locs[0]
        self.assertEqual(1,  bpl.order)
        self.assertEqual('', bpl.block_id)

    def test_edit_portal04(self): #default conf
        BlockPortalLocation.objects.filter(app_name='').delete()
        url = '/creme_config/blocks/portal/edit/default'
        self.assertEqual(404, self.client.get(url).status_code)

        blocks = self._get_blocks_4_portal()
        create_loc = BlockPortalLocation.objects.create
        create_loc(app_name='', block_id=blocks[0].id_, order=1)
        create_loc(app_name='', block_id=blocks[1].id_, order=2)

        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        b_locs = list(BlockPortalLocation.objects.filter(app_name=''))
        self.assertEqual(1, len(b_locs))

        bpl = b_locs[0]
        self.assertEqual(1,  bpl.order)
        self.assertEqual('', bpl.block_id)

    def test_delete_portal(self):
        app_name = 'persons'
        self.client.post('/creme_config/blocks/portal/add/', data={'app_name': app_name})

        response = self.client.post('/creme_config/blocks/portal/delete', data={'id': app_name})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   BlockPortalLocation.objects.filter(app_name=app_name).count())

    def test_delete_home(self): #can not delete home conf
        #TODO: use a helper method ??
        app_name = 'creme_core'
        blocks = list(block for block_id, block in  gui.block.block_registry if hasattr(block, 'home_display'))
        self.assert_(len(blocks) >= 1, blocks)

        BlockPortalLocation.objects.create(app_name=app_name, block_id=blocks[0].id_, order=1)

        response = self.client.post('/creme_config/blocks/portal/delete', data={'id': app_name})
        self.assertEqual(404, response.status_code)

    def test_edit_default_mypage(self):
        url = '/creme_config/blocks/mypage/edit/default'
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            blocks_field = response.context['form'].fields['blocks']
        except KeyError, e:
            self.fail(str(e))

        choices = blocks_field.choices
        self.assert_(len(choices) >= 2)
        self.assertEqual(list(BlockMypageLocation.objects.filter(user=None).values_list('block_id', flat=True)),
                        blocks_field.initial
                        )

        block_id1 = choices[0][0]
        block_id2 = choices[1][0]

        index1 = self._find_field_index(blocks_field, block_id1)
        index2 = self._find_field_index(blocks_field, block_id2)

        response = self.client.post(url,
                                    data={
                                            'blocks_check_%s' % index1: 'on',
                                            'blocks_value_%s' % index1: block_id1,
                                            'blocks_order_%s' % index1: 1,

                                            'blocks_check_%s' % index2: 'on',
                                            'blocks_value_%s' % index2: block_id2,
                                            'blocks_order_%s' % index2: 2,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = list(BlockMypageLocation.objects.filter(user=None))
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(block_id1, b_locs).order)
        self.assertEqual(2, self._find_location(block_id2, b_locs).order)

    def test_edit_mypage(self):
        user = self.user
        url = '/creme_config/blocks/mypage/edit'
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            blocks_field = response.context['form'].fields['blocks']
        except KeyError, e:
            self.fail(str(e))

        choices = blocks_field.choices
        self.assert_(len(choices) >= 2)
        self.assertEqual(list(BlockMypageLocation.objects.filter(user=None).values_list('block_id', flat=True)),
                         blocks_field.initial
                        )

        block_id1 = choices[0][0]
        block_id2 = choices[1][0]

        index1 = self._find_field_index(blocks_field, block_id1)
        index2 = self._find_field_index(blocks_field, block_id2)

        response = self.client.post(url,
                                    data={
                                            'blocks_check_%s' % index1: 'on',
                                            'blocks_value_%s' % index1: block_id1,
                                            'blocks_order_%s' % index1: 1,

                                            'blocks_check_%s' % index2: 'on',
                                            'blocks_value_%s' % index2: block_id2,
                                            'blocks_order_%s' % index2: 2,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = list(BlockMypageLocation.objects.filter(user=user))
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(block_id1, b_locs).order)
        self.assertEqual(2, self._find_location(block_id2, b_locs).order)

    def test_delete_default_mypage01(self):
        loc = BlockMypageLocation.objects.create(user=None, block_id=history_block.id_, order=1)
        response = self.client.post('/creme_config/blocks/mypage/default/delete', data={'id': loc.id})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   BlockMypageLocation.objects.filter(pk=loc.pk).count())

    def test_delete_default_mypage02(self): #'user' must be 'None'
        loc = BlockMypageLocation.objects.create(user=self.user, block_id=history_block.id_, order=1)
        response = self.client.post('/creme_config/blocks/mypage/default/delete', data={'id': loc.id})
        self.assertEqual(404, response.status_code)
        self.assertEqual(1,   BlockMypageLocation.objects.filter(pk=loc.pk).count())

    def test_delete_mypage01(self):
        loc = BlockMypageLocation.objects.create(user=self.user, block_id=history_block.id_, order=1)
        response = self.client.post('/creme_config/blocks/mypage/delete', data={'id': loc.id})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   BlockMypageLocation.objects.filter(pk=loc.pk).count())

    def test_delete_mypage02(self): #BlockMypageLocation must belongs to the user
        loc = BlockMypageLocation.objects.create(user=self.other_user, block_id=history_block.id_, order=1)
        response = self.client.post('/creme_config/blocks/mypage/delete', data={'id': loc.id})
        self.assertEqual(404, response.status_code)
        self.assertEqual(1,   BlockMypageLocation.objects.filter(pk=loc.pk).count())

    def test_add_relationblock(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                      ('test-objfoo', 'object_predicate'), is_custom=False
                                     )
        self.assertFalse(RelationBlockItem.objects.count())

        url = '/creme_config/relation_block/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'relation_type': rt.id})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        rbi = RelationBlockItem.objects.all()
        self.assertEqual(1,     len(rbi))
        self.assertEqual(rt.id, rbi[0].relation_type.id)

    def test_delete_relationblock(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                      ('test-objfoo', 'object_predicate'), is_custom=False
                                     )
        rbi = RelationBlockItem.objects.create(block_id='foobarid', relation_type=rt)
        loc = BlockDetailviewLocation.create(block_id=rbi.block_id, order=5, zone=BlockDetailviewLocation.RIGHT, model=Contact)

        self.assertEqual(200, self.client.post('/creme_config/relation_block/delete', data={'id': rbi.id}).status_code)
        self.assertFalse(RelationBlockItem.objects.filter(pk=rbi.pk).count())
        self.assertFalse(BlockDetailviewLocation.objects.filter(pk=loc.pk).count())

    def test_delete_instanceblock(self): ##(r'^instance_block/delete$',  'blocks.delete_instance_block')
        naru = Contact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')
        instance_block_id = InstanceBlockConfigItem.generate_id('test__blocks__FoobarBlock', 'test', 'foobar')
        ibi = InstanceBlockConfigItem.objects.create(block_id=instance_block_id, entity=naru, verbose='All stuffes')
        loc = BlockDetailviewLocation.create(block_id=ibi.block_id, order=5, zone=BlockDetailviewLocation.RIGHT, model=Contact)

        self.assertEqual(200, self.client.post('/creme_config/instance_block/delete', data={'id': ibi.id}).status_code)
        self.assertFalse(InstanceBlockConfigItem.objects.filter(pk=ibi.pk).count())
        self.assertFalse(BlockDetailviewLocation.objects.filter(pk=loc.pk).count())


class SettingsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')

    def test_model01(self):
        sk = SettingKey.objects.create(pk='persons-title', description=u"Page title",
                                       app_label=None, type=SettingKey.STRING,
                                       hidden=False,
                                      )
        title = 'May the source be with you'
        sv = SettingValue.objects.create(key=sk, user=None, value=title)

        self.assertEqual(title, SettingValue.objects.get(pk=sv.pk).value)

    def test_model02(self):
        sk = SettingKey.objects.create(pk='persons-page_size', description=u"Page size",
                                       app_label='persons', type=SettingKey.INT
                                      )
        self.assertFalse(sk.hidden)

        size = 156
        sv = SettingValue.objects.create(key=sk, user=None, value=size)
        self.assertEqual(size, SettingValue.objects.get(pk=sv.pk).value)

    def test_model03(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo', description=u"Display logo ?",
                                       type=SettingKey.BOOL
                                      )
        sv = SettingValue.objects.create(key=sk, user=self.user, value=True)
        self.assert_(SettingValue.objects.get(pk=sv.pk).value is True)

        sv.value = False
        sv.save()
        self.assert_(SettingValue.objects.get(pk=sv.pk).value is False)

    def test_edit01(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-title', description=u"Page title",
                                       app_label='persons', type=SettingKey.STRING,
                                       hidden=False,
                                      )
        title = 'May the source be with you'
        sv = SettingValue.objects.create(key=sk, user=None, value=title)

        url = '/creme_config/setting/edit/%s' % sv.id
        self.assertEqual(200, self.client.get(url).status_code)

        title = title.upper()
        response = self.client.post(url, data={'value': title})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        sv = SettingValue.objects.get(pk=sv.pk) #refresh
        self.assertEqual(title, sv.value)

    def test_edit02(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-size', description=u"Page size",
                                       app_label='persons', type=SettingKey.INT,
                                       hidden=False,
                                      )
        size = 156
        sv = SettingValue.objects.create(key=sk, user=None, value=size)

        size += 15
        response = self.client.post('/creme_config/setting/edit/%s' % sv.id, data={'value': size})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(size, SettingValue.objects.get(pk=sv.pk).value)

    def test_edit03(self):
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo', description=u"Display logo ?",
                                       app_label='persons', type=SettingKey.BOOL,
                                       hidden=False,
                                      )
        sv = SettingValue.objects.create(key=sk, user=None, value=True)

        response = self.client.post('/creme_config/setting/edit/%s' % sv.id, data={}) #False -> empty POST
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertFalse(SettingValue.objects.get(pk=sv.pk).value)

    def test_edit04(self): #hidden => not editable
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo', description=u"Display logo ?",
                                       app_label='persons', type=SettingKey.BOOL,
                                       hidden=True,
                                      )
        sv = SettingValue.objects.create(key=sk, user=None, value=True)
        self.assertEqual(404, self.client.get('/creme_config/setting/edit/%s' % sv.id).status_code)

    def test_edit05(self): #hidden => not editable
        self.login()

        sk = SettingKey.objects.create(pk='persons-display_logo', description=u"Display logo ?",
                                       app_label='persons', type=SettingKey.BOOL,
                                       hidden=False,
                                      )
        sv = SettingValue.objects.create(key=sk, user=self.user, value=True)
        self.assertEqual(404, self.client.get('/creme_config/setting/edit/%s' % sv.id).status_code)


class UserSettingsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')

    def test_user_settings(self):
        self.login()
        response = self.client.get('/creme_config/user/view/settings/')
        self.assertEqual(200, response.status_code)

    def test_change_theme01(self):
        self.login()
#        settings.THEMES += [("chantilly2", "")]
        theme = "chantilly"
        self.assertEqual(1, SettingKey.objects.filter(pk=USER_THEME_NAME).count())
        self.assertEqual(0, SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME).count())
        response = self.client.post('/creme_config/user/edit/theme/',
                                    data={
                                        'themes': theme,
                                    })

        self.assertEqual(1,     SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME).count())
        self.assertEqual(theme, SettingValue.objects.get(user=self.user, key=USER_THEME_NAME).value)

#        theme = "chantilly2"
        theme = "icecream"
        response = self.client.post('/creme_config/user/edit/theme/',
                            data={
                                'themes': theme,
                            })
        self.assertEqual(1,     SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME).count())
        self.assertEqual(theme, SettingValue.objects.get(user=self.user, key=USER_THEME_NAME).value)

    def test_get_user_theme01(self):
        self.login()
        self.assertEqual(1, SettingKey.objects.filter(pk=USER_THEME_NAME).count())
        self.assertEqual(0, SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME).count())
        self.assertEqual(settings.DEFAULT_THEME, get_user_theme(self.user))
        self.assertEqual(1, SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME).count())
        sv = SettingValue.objects.get(user=self.user, key=USER_THEME_NAME)
        sv.value = "unknown theme"
        sv.save()
        self.assertEqual(settings.DEFAULT_THEME, get_user_theme(self.user))

    def test_get_user_theme02(self):
        self.login()
        class FakeRequest(object):
            def __init__(self):
                sessions = Session.objects.all()
                assert 1 == len(sessions)
                self.session = sessions[0].get_decoded()

        def get_theme():
            try:
                return FakeRequest().session['usertheme']
            except Exception, e:
                pass

        self.assertEqual(1, SettingKey.objects.filter(pk=USER_THEME_NAME).count())
        self.assertEqual(0, SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME).count())
        self.assertFalse(get_theme())
        response = self.client.get('/')
        self.assertEqual(1, SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME).count())
        self.assertEqual(settings.DEFAULT_THEME, get_theme())


class HistoryConfigTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')

    def test_portal(self):
        self.login()
        self.populate('creme_core')
        self.assertEqual(200, self.client.get('/creme_config/history/portal/').status_code)

    def test_add01(self):
        self.login()
        self.assertFalse(HistoryConfigItem.objects.count())

        rtype01, srtype01 = RelationType.create(('test-subject_foo', 'fooes'), ('test-object_foo', 'fooed'))
        rtype02, srtype02 = RelationType.create(('test-subject_bar', 'bars'),  ('test-object_bar', 'bared'))

        url = '/creme_config/history/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        rtype_ids = [rtype01.id, rtype02.id]
        response = self.client.post(url, data={'relation_types': rtype_ids})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        hc_items = HistoryConfigItem.objects.all()
        self.assertEqual(2, len(hc_items))
        self.assertEqual(set(rtype_ids), set(hc_item.relation_type.id for hc_item in hc_items))

    def test_add02(self): #no doublons
        self.login()

        rtype01, srtype01 = RelationType.create(('test-subject_foo', 'fooes'), ('test-object_foo', 'fooed'))
        rtype02, srtype02 = RelationType.create(('test-subject_bar', 'bars'),  ('test-object_bar', 'bared'))

        HistoryConfigItem.objects.create(relation_type=rtype01)

        rtype_ids = [rtype01.id, rtype02.id]
        response = self.client.post('/creme_config/history/add/', data={'relation_types': rtype_ids})
        self.assertFormError(response, 'form', field='relation_types',
                             errors=_(u'Select a valid choice. %s is not one of the available choices.') % rtype01.id
                            )

    def test_delete(self):
        self.login()

        rtype, srtype = RelationType.create(('test-subject_foo', 'fooes'), ('test-object_foo', 'fooed'))
        hci = HistoryConfigItem.objects.create(relation_type=rtype)

        response = self.client.post('/creme_config/history/delete', data={'id': hci.id})
        self.assertEqual(200, response.status_code)
        self.assertFalse(HistoryConfigItem.objects.filter(pk=hci.id).count())


#TODO: complete test cases...
