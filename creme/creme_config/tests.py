# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *
from creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme_core.tests.base import CremeTestCase

from persons.models import Contact, Organisation #need CremeEntity
from persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES

from creme_config.models import *

#TODO: test views are allowed to admin only...


class UserRoleTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core')
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
        self.failIf(contact.can_view(other_user))

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
        self.failIf(defcreds.can_link())
        self.failIf(defcreds.can_unlink())

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

    def test_portal(self):
        response = self.client.get('/creme_config/role/portal/')
        self.assertEqual(200, response.status_code)


class UserTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'persons') #'creme_core'
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/user/portal/').status_code)

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
        self.assertEqual(2 + 2, CremeEntity.objects.count())#2 from creme_core populate + 2 from now
        self.assertEqual(2 + 2, EntityCredentials.objects.filter(user=user).count())#2 from creme_core populate + 2 from now

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


class PropertyTypeTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core')
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/property_type/portal/').status_code)

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

        prop_type = prop_types[1]
        self.assertEqual(text, prop_type.text)
        self.assertEqual(0,    prop_type.subject_ctypes.count())

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

        prop_type = CremePropertyType.objects.all()[1]
        self.assertEqual(text, prop_type.text)

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
        self.populate('creme_core')
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/relation_type/portal/').status_code)

    def test_create01(self):
        url = '/creme_config/relation_type/add/'
        self.assertEqual(200, self.client.get(url).status_code)
        rel_type_core_populate_count = 4

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

        rel_type = rel_types[rel_type_core_populate_count]
        self.assertEqual(subject_pred, rel_type.predicate)
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

        response = self.client.post('/creme_config/relation_type/add/',
                                    data={
                                            'subject_predicate':  'employs',
                                            'object_predicate':   'is employed by',
                                            'subject_ctypes':     [ct_orga.id],
                                            'subject_properties': [pt_sub.id],
                                            'object_ctypes':      [ct_contact.id],
                                            'object_properties':  [pt_obj.id],
                                          }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        rel_type = RelationType.objects.all()[4]
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
        self.populate('creme_core')
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/blocks/portal/').status_code)

    def test_add_config(self):
        url = '/creme_config/blocks/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        ct = ContentType.objects.get_for_model(Contact)
        self.failIf(BlockConfigItem.objects.filter(content_type=ct).count())

        response = self.client.post(url, data={'ct_id': ct.id})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        bc_items = BlockConfigItem.objects.filter(content_type=ct)
        self.assertEqual(1, len(bc_items))

        bc_item = bc_items[0]
        self.assertEqual('', bc_item.block_id)
        self.assertEqual(1, bc_item.order)
        self.failIf(bc_item.on_portal)

        response = self.client.get(url)

        try:
            choices = response.context['form'].fields['ct_id'].choices
        except Exception, e:
            self.fail(str(e))

        self.assert_(ct.id not in (ct_id for ct_id, ctype in choices))

    def test_edit(self):
        ct = ContentType.objects.get_for_model(Contact)
        url = '/creme_config/blocks/edit/%s' % ct.id
        self.assertEqual(404, self.client.get(url).status_code)

        BlockConfigItem.objects.create(pk='bci01', content_type=ct, block_id='', order=1, on_portal=False)
        self.assertEqual(200, self.client.get(url).status_code)

        #TODO: complete

    def test_edit_default(self):
        url = '/creme_config/blocks/edit/0'
        self.assertEqual(404, self.client.get(url).status_code)

        BlockConfigItem.objects.create(pk='bci01', content_type=None, block_id='', order=1, on_portal=False)
        self.assertEqual(200, self.client.get(url).status_code)

        #TODO: complete

    def test_edit_portal(self):
        ct = ContentType.objects.get_for_model(Contact)
        url = '/creme_config/blocks/edit/%s/portal/' % ct.id
        self.assertEqual(404, self.client.get(url).status_code)

        BlockConfigItem.objects.create(pk='bci01', content_type=ct, block_id='', order=1, on_portal=False)
        self.assertEqual(200, self.client.get(url).status_code)

        #TODO: complete

    def test_edit_home(self):
        url = '/creme_config/blocks/edit/0/portal/'
        self.assertEqual(404, self.client.get(url).status_code)

        BlockConfigItem.objects.create(pk='bci01', content_type=None, block_id='', order=1, on_portal=False)
        self.assertEqual(200, self.client.get(url).status_code)

        #TODO: complete

    def test_delete(self):
        BlockConfigItem.objects.create(pk='bci01', content_type=None, block_id='', order=1, on_portal=False)
        url = '/creme_config/blocks/delete'
        self.assertEqual(404, self.client.post(url, data={'id': 0}).status_code)

        ct = ContentType.objects.get_for_model(Contact)
        bci = BlockConfigItem.objects.create(pk='bci02', content_type=ct, block_id='', order=1, on_portal=False)
        self.assertEqual(200, self.client.post(url, data={'id': ct.id}).status_code)

        self.failIf(BlockConfigItem.objects.filter(pk=bci.pk).count())

    def test_add_relationblock(self):
        rt, srt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                      ('test-objfoo', 'object_predicate'), is_custom=False
                                     )
        self.failIf(RelationBlockItem.objects.count())

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

        self.assertEqual(200, self.client.post('/creme_config/relation_block/delete', data={'id': rbi.id}).status_code)
        self.failIf(RelationBlockItem.objects.filter(pk=rbi.pk).count())

    #(r'^instance_block/delete$',  'blocks.delete_instance_block'), #TODO


class SettingsTestCase(CremeTestCase):
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
        self.failIf(sk.hidden)

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
        self.failIf(SettingValue.objects.get(pk=sv.pk).value)

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
        self.populate('creme_core')

    def test_user_settings(self):
        self.login()
        response = self.client.get('/creme_config/user/view/settings/')
        self.assertEqual(200, response.status_code)


class HistoryConfigTestCase(CremeTestCase):
    def test_portal(self):
        self.login()
        self.populate('creme_core')
        self.assertEqual(200, self.client.get('/creme_config/history/portal/').status_code)

    def test_add01(self):
        self.login()
        self.failIf(HistoryConfigItem.objects.count())

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
        self.failIf(HistoryConfigItem.objects.filter(pk=hci.id).count())


#TODO: complete test cases...
