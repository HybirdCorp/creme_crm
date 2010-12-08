# -*- coding: utf-8 -*-

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *
from creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme_core.management.commands.creme_populate import Command as PopulateCommand

from persons.models import Contact, Organisation #need CremeEntity
from persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES

#TODO: test views are allowed to admin only...


class UserRoleTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.create(username='Mireille')
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        self.password = 'test'
        self.user = None

        self.login()

    def assertNoFormError(self, response): #move in a CremeTestCase ???
        try:
            errors = response.context['form'].errors
        except Exception, e:
            pass
        else:
            self.fail(errors)

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

        redirect_chain = response.redirect_chain
        self.assertEqual(1, len(redirect_chain))
        self.assert_(redirect_chain[0][0].endswith('/creme_config/role/portal/'))

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
        self.failIf(contact.can_view(other_user))

        self.assertEqual(0, role.credentials.count())

        response = self.client.get('/creme_config/role/add_credentials/%s' % role.id)
        self.assertEqual(200,  response.status_code)

        response = self.client.post('/creme_config/role/add_credentials/%s' % role.id,
                                    data={
                                            'can_view':   True,
                                            'can_change': False,
                                            'can_delete': False,
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
        self.failIf(contact.can_view(other_user)) #role.allowed_apps does not contain 'persons'

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
        self.failIf(yuki.can_view(other_user)) #no more SetCredentials
        self.assert_(altena.can_view(other_user))

    def test_delete01(self):
        role = UserRole(name='CEO')
        role.allowed_apps = ['persons']
        role.save()
        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)

        other_user = User.objects.create(username='chloe', role=role)
        yuki = Contact.objects.create(user=self.user, first_name='Yuki', last_name='Kajiura')
        self.assert_(yuki.can_view(other_user))
        self.assertEqual(1, EntityCredentials.objects.count())

        response = self.client.post('/creme_config/role/delete', follow=True,
                                    data={'id': role.id}
                                   )
        self.assertEqual(200, response.status_code)
        self.failIf(UserRole.objects.count())

        self.failIf(EntityCredentials.get_default_creds().can_view())
        self.assertEqual(0, EntityCredentials.objects.count())
        self.assertEqual(0, SetCredentials.objects.count())
        self.assertEqual(1, User.objects.filter(pk=other_user.id).count())

        yuki = Contact.objects.get(pk=yuki.id) #refresh caches
        self.failIf(yuki.can_view(other_user)) #defaultCreds are applied

    def test_set_default_creds(self):
        defcreds = EntityCredentials.get_default_creds()
        self.failIf(defcreds.can_view())
        self.failIf(defcreds.can_change())
        self.failIf(defcreds.can_delete())

        response = self.client.get('/creme_config/role/set_default_creds/')
        self.assertEqual(200, response.status_code)

        response = self.client.post('/creme_config/role/set_default_creds/', follow=True,
                                    data={
                                            'can_view':   True,
                                            'can_change': True,
                                            'can_delete': True,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        defcreds = EntityCredentials.get_default_creds()
        self.assert_(defcreds.can_view())
        self.assert_(defcreds.can_change())
        self.assert_(defcreds.can_delete())

    def test_portal(self):
        response = self.client.get('/creme_config/role/portal/')
        self.assertEqual(200, response.status_code)


class UserTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.create(username='Mireille')
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        PopulateCommand().handle(application=['persons']) #'creme_core'
        self.password = 'test'
        self.user = None

        self.login()

    def assertNoFormError(self, response): #move in a CremeTestCase ???
        try:
            errors = response.context['form'].errors
        except Exception, e:
            pass
        else:
            self.fail(errors)

    def test_create01(self):
        response = self.client.get('/creme_config/user/add/')
        self.assertEqual(200, response.status_code)

        orga = Organisation.objects.create(user=self.user, name='Soldat')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username   = 'kirika'
        first_name = 'Kirika'
        last_name  = u'Yūmura'
        password   = 'password'
        email      = 'kirika@noir.jp'
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

        orga = Organisation.objects.create(user=self.user, name='Soldat')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username = 'kirika'
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
        self.assertEqual(2, CremeEntity.objects.count())
        self.assertEqual(2, EntityCredentials.objects.filter(user=user).count())

        self.assert_(orga.can_view(user))

    def test_edit01(self):
        role1 = UserRole(name='Master')
        role1.allowed_apps = ['persons']
        role1.save()
        SetCredentials.objects.create(role=role1, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)
        other_user = User.objects.create(username='kirika', role=role1)

        mireille = Contact.objects.create(user=self.user, first_name='Mireille', last_name='Bouquet')
        self.assert_(mireille.can_view(other_user))

        response = self.client.get('/creme_config/user/edit/%s' % other_user.id)
        self.assertEqual(200, response.status_code)

        first_name = 'Kirika'
        last_name  = u'Yūmura'
        email      = 'kirika@noir.jp'
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

        mireille = Contact.objects.get(pk=mireille.id) #refresh cache
        self.failIf(mireille.can_view(other_user))

    def test_change_password(self):
        other_user = User.objects.create(username='kirika')

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
        self.failIf(team.is_superuser)
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
        self.failIf(entity.can_view(user03))

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
        self.failIf(user01.id in teammates)

        #credentials have been updated ?
        entity = CremeEntity.objects.get(pk=entity.id)
        self.failIf(entity.can_view(user01))
        self.assert_(entity.can_view(user02))
        self.assert_(entity.can_view(user03))

    def test_team_delete01(self):
        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        team = self._create_team('Teamee', [])

        response = self.client.post('/creme_config/team/delete', data={'id': user.id})
        self.assertEqual(404, response.status_code)

        response = self.client.post('/creme_config/team/delete', data={'id': team.id})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0,   User.objects.filter(pk=team.id).count())

    def test_team_delete02(self):
        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        team = self._create_team('Teamee', [user])

        response = self.client.post('/creme_config/team/delete', data={'id': team.id})
        self.assertEqual(403, response.status_code)
        self.assertEqual(1, User.objects.filter(pk=team.id).count())

    def test_team_delete03(self):
        team = self._create_team('Teamee', [])
        CremeEntity.objects.create(user=team)

        response = self.client.post('/creme_config/team/delete', data={'id': team.id})
        self.assertEqual(403, response.status_code)
        self.assertEqual(1, User.objects.filter(pk=team.id).count())
