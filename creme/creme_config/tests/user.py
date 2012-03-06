# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _
    from django.conf import settings
    from django.contrib.sessions.models import Session
    from django.contrib.auth.models import User

    from creme_core.models import (CremeEntity, CremeProperty, Relation, EntityCredentials,
                                   UserRole, HistoryLine, SetCredentials)
    from creme_core.constants import PROP_IS_MANAGED_BY_CREME
    from creme_core.tests.base import CremeTestCase

    from activities.models import Calendar

    from persons.models import Contact, Organisation #need CremeEntity
    from persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES

    from creme_config.constants import USER_THEME_NAME
    from creme_config.models import SettingKey, SettingValue
    from creme_config.utils import get_user_theme
    from creme_config import blocks
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('UserTestCase', 'UserSettingsTestCase')


class UserTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons')

    def login_not_as_superuser(self):
        apps = ('creme_config',)
        self.login(is_superuser=False, allowed_apps=apps, admin_4_apps=apps)

    def aux_test_portal(self):
        response = self.client.get('/creme_config/user/portal/')
        self.assertEqual(200, response.status_code)

        self.assertContains(response, 'id="%s"' % blocks.UsersBlock.id_)
        self.assertContains(response, 'id="%s"' % blocks.TeamsBlock.id_)

    def test_portal01(self):
        self.login()
        self.aux_test_portal()

    def test_portal02(self):
        self.login_not_as_superuser()
        self.aux_test_portal()

    def test_create01(self):
        self.login()

        url = '/creme_config/user/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username   = 'deunan'
        first_name = 'Deunan'
        last_name  = u'Knut'
        password   = 'password'
        email      = 'd.knut@eswat.ol'
        response = self.client.post(url, follow=True,
                                    data={'username':     username,
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
        self.assertTrue(user.is_superuser)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)
        self.assertTrue(user.check_password(password))

        self.assertFalse(EntityCredentials.objects.filter(user=user))

        contact = self.get_object_or_fail(Contact, is_user=user,
                                          first_name=first_name,
                                          last_name=last_name
                                         )
        self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, orga)

    def test_create02(self):
        self.login()

        role = UserRole(name='Mangaka')
        role.allowed_apps = ['persons']
        role.save()

        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        contact = Contact.objects.create(user=self.user, first_name='Deunan', last_name=u'Knut')

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        ce_count = CremeEntity.objects.count()

        username = 'deunan'
        password = 'password'
        response = self.client.post('/creme_config/user/add/', follow=True,
                                    data={'username':     username,
                                          'password_1':   password,
                                          'password_2':   password,
                                          'role':         role.id,
                                          'contact':      contact.id,
                                          'organisation': orga.id,
                                          'relation':     REL_SUB_MANAGES,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        users = User.objects.filter(username=username)
        self.assertEqual(1, len(users))

        user = users[0]
        self.assertEqual(ce_count, CremeEntity.objects.count())
        self.assertEqual(ce_count, EntityCredentials.objects.filter(user=user).count())

        self.assertTrue(orga.can_view(user))

        contact = self.refresh(contact)
        self.assertEqual(user, contact.is_user)
        self.assertRelationCount(1, contact, REL_SUB_MANAGES, orga)

    def test_create03(self): #relation is not recreate if it already exists
        self.login()

        contact = Contact.objects.create(user=self.user, first_name='Deunan', last_name=u'Knut')

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        Relation.objects.create(user=self.user, subject_entity=contact, type_id=REL_SUB_MANAGES, object_entity=orga)

        username = 'deunan'
        password = 'password'
        response = self.client.post('/creme_config/user/add/', follow=True,
                                    data={'username':     username,
                                          'password_1':   password,
                                          'password_2':   password,
                                          'is_superuser': True,
                                          'contact':      contact.id,
                                          'organisation': orga.id,
                                          'relation':     REL_SUB_MANAGES,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        user = self.get_object_or_fail(User, username=username)
        contact = self.refresh(contact)
        self.assertEqual(user, contact.is_user)
        self.assertRelationCount(1, contact, REL_SUB_MANAGES, orga) #not 2 !!

    def test_create04(self):
        self.login_not_as_superuser()

        url = '/creme_config/user/add/'
        self.assertGETRedirectsToLogin(url)

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        password = 'password'
        self.assertPOSTRedirectsToLogin(url, data={'username':     'deunan',
                                                   'password_1':   password,
                                                   'password_2':   password,
                                                   'first_name':   'Deunan',
                                                   'last_name':    'Knut',
                                                   'email':        'd.knut@eswat.ol',
                                                   'is_superuser': False,
                                                   'organisation': orga.id,
                                                   'relation':     REL_SUB_EMPLOYED_BY,
                                                  }
                                       )

    def test_create05(self): #linked contact can not be already linked to another user
        self.login()

        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        contact = Contact.objects.create(user=self.user, first_name='Deunan', last_name=u'Knut', is_user=user)

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        #Relation.objects.create(user=self.user, subject_entity=contact, type_id=REL_SUB_MANAGES, object_entity=orga)

        username = 'deunan'
        password = 'password'
        #response = self.client.get('/creme_config/user/add/')
        response = self.client.post('/creme_config/user/add/', follow=True,
                                    data={'username':     username,
                                          'password_1':   password,
                                          'password_2':   password,
                                          'is_superuser': True,
                                          'contact':      contact.id,
                                          'organisation': orga.id,
                                          'relation':     REL_SUB_MANAGES,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        self.assertEqual(user, self.refresh(contact).is_user)

        #self.assertFormError(response, 'form', 'contact',
                             #[_(u'This contact is already linked to the user "%s"') % user]
                            #)
        new_user = self.get_object_or_fail(User, username=username)
        contact = self.get_object_or_fail(Contact, is_user=new_user,
                                          first_name=username,
                                          last_name=username
                                         )

    def test_edit01(self):
        self.login()

        role1 = UserRole(name='Master')
        role1.allowed_apps = ['persons']
        role1.save()
        SetCredentials.objects.create(role=role1, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )
        other_user = User.objects.create(username='deunan', role=role1)

        briareos = Contact.objects.create(user=self.user, first_name='Briareos', last_name='Hecatonchires')
        self.assertTrue(briareos.can_view(other_user))

        url = '/creme_config/user/edit/%s' % other_user.id
        self.assertEqual(200, self.client.get(url).status_code)

        first_name = 'Deunan'
        last_name  = u'Knut'
        email      = 'd.knut@eswat.ol'
        role2 = UserRole.objects.create(name='Slave')
        response = self.client.post(url, follow=True,
                                    data={'first_name': first_name,
                                          'last_name':  last_name,
                                          'email':      email,
                                          'role':       role2.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        other_user = self.refresh(other_user)
        self.assertEqual(first_name, other_user.first_name)
        self.assertEqual(last_name,  other_user.last_name)
        self.assertEqual(email,      other_user.email)
        self.assertEqual(role2,      other_user.role)

        briareos = self.refresh(briareos) #refresh cache
        self.assertFalse(briareos.can_view(other_user))

    def test_edit02(self): #can not edit a team with the user edit view
        self.login()

        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        team  = self._create_team('Teamee', [user])

        url = '/creme_config/user/edit/%s' % team.id
        self.assertGET404(url)
        self.assertPOST404(url)

    def test_edit03(self):
        self.login_not_as_superuser()

        role1 = UserRole(name='Master')
        role1.allowed_apps = ['persons']
        role1.save()
        SetCredentials.objects.create(role=role1, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )
        other_user = User.objects.create(username='deunan', role=role1)

        briareos = Contact.objects.create(user=self.user, first_name='Briareos', last_name='Hecatonchires')
        self.assertTrue(briareos.can_view(other_user))

        url = '/creme_config/user/edit/%s' % other_user.id
        self.assertGETRedirectsToLogin(url)

        role2 = UserRole.objects.create(name='Slave')
        self.assertPOSTRedirectsToLogin(url,data={'first_name': 'Deunan',
                                                  'last_name':  'Knut',
                                                  'email':      'd.knut@eswat.ol',
                                                  'role':       role2.id,
                                                 }
                                       )

    def test_change_password01(self):
        self.login()

        other_user = User.objects.create(username='deunan')
        url = '/creme_config/user/edit/password/%s' % other_user.id
        self.assertEqual(200, self.client.get(url).status_code)

        password = 'password'
        response = self.client.post(url, follow=True,
                                    data={'password_1': password,
                                          'password_2': password,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertTrue(self.refresh(other_user).check_password(password))

    def test_change_password02(self):
        self.login_not_as_superuser()

        other_user = User.objects.create(username='deunan')
        url = '/creme_config/user/edit/password/%s' % other_user.id
        self.assertGETRedirectsToLogin(url)

        password = 'password'
        self.assertPOSTRedirectsToLogin(url, data={'password_1': password,
                                                   'password_2': password,
                                                  }
                                       )

    def test_team_create01(self):
        self.login()

        url = '/creme_config/team/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        create_user = User.objects.create_user
        user01 = create_user('Shogun', 'shogun@century.jp', 'uselesspw')
        user02 = create_user('Yoshitsune', 'yoshitsune@century.jp', 'uselesspw')

        username   = 'Team-A'
        response = self.client.post(url, follow=True,
                                    data={'username':  username,
                                          'teammates': [user01.id, user02.id],
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
        self.assertIn(user01.id, teammates)
        self.assertIn(user02.id, teammates)

    def test_team_create02(self):
        self.login_not_as_superuser()

        url = '/creme_config/team/add/'
        self.assertGETRedirectsToLogin(url)

        user01 = User.objects.create_user('Shogun', 'shogun@century.jp', 'uselesspw')
        self.assertPOSTRedirectsToLogin(url, data={'username':  'Team-A',
                                                   'teammates': [user01.id],
                                                  }
                                       )

    def _create_team(self, name, teammates):
        team = User.objects.create(username=name, is_team=True, role=None)
        team.teammates = teammates

        return team

    def test_team_edit01(self):
        self.login()

        role = UserRole(name='Role')
        role.allowed_apps = ['creme_core']
        role.save()
        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        def create_user(name, email):
            user = User.objects.create_user(name, email, 'uselesspw')
            user.role = role
            user.save()

            return user

        user01 = create_user('Maruo',   'maruo@century.jp')
        user02 = create_user('Yokiji',  'yokiji@century.jp')
        user03 = create_user('Koizumi', 'koizumi@century.jp')

        self.assertGET404('/creme_config/team/edit/%s' % user01.id)

        teamname = 'Teamee'
        team = self._create_team(teamname, [user01, user02])

        entity = CremeEntity.objects.create(user=team)
        self.assertTrue(entity.can_view(user01))
        self.assertTrue(entity.can_view(user02))
        self.assertFalse(entity.can_view(user03))

        url = '/creme_config/team/edit/%s' % team.id
        self.assertEqual(200, self.client.get(url).status_code)

        teamname += '_edited'
        response = self.client.post(url, follow=True,
                                    data={'username':  teamname,
                                          'teammates': [user02.id, user03.id],
                                        }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        team = self.refresh(team)
        self.assertEqual(teamname, team.username)

        teammates = team.teammates
        self.assertEqual(2, len(teammates))
        self.assertIn(user02.id, teammates)
        self.assertIn(user03.id, teammates)
        self.assertNotIn(user01.id, teammates)

        #credentials have been updated ?
        entity = CremeEntity.objects.get(pk=entity.id)
        self.assertFalse(entity.can_view(user01))
        self.assertTrue(entity.can_view(user02))
        self.assertTrue(entity.can_view(user03))

    def test_team_edit02(self):
        self.login_not_as_superuser()

        create_user = User.objects.create_user
        user01 = create_user('Maruo',  'maruo@century.jp',  'uselesspw1')
        user02 = create_user('Yokiji', 'yokiji@century.jp', 'uselesspw2')

        teamname = 'Teamee'
        team = self._create_team(teamname, [user01, user02])

        url = '/creme_config/team/edit/%s' % team.id
        self.assertGETRedirectsToLogin(url)
        self.assertPOSTRedirectsToLogin(url, data={'username':  teamname,
                                                  'teammates': [user02.id],
                                                 }
                                      )

    def test_team_delete01(self):
        self.login()

        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        team = self._create_team('Teamee', [])

        url = '/creme_config/user/delete/%s' % team.id
        self.assertEqual(200, self.client.get(url).status_code)
        self.assertEqual(200, self.client.post(url, data={'to_user': user.id}).status_code)
        self.assertFalse(User.objects.filter(pk=team.id))

    def test_team_delete02(self):
        self.login()

        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        team  = self._create_team('Teamee', [user])
        team2 = self._create_team('Teamee2', [user])

        ce = CremeEntity.objects.create(user=team)

        url = '/creme_config/user/delete/%s' % team.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(url, data={'to_user': team2.id})
        self.assertEqual(200, response.status_code)
        self.assertFalse(User.objects.filter(pk=team.id))

        ce = self.get_object_or_fail(CremeEntity, pk=ce.id)
        self.assertEqual(team2, ce.user)

    def test_team_delete03(self):
        self.login()

        team = self._create_team('Teamee', [])
        CremeEntity.objects.create(user=team)

        response = self.client.post('/creme_config/user/delete/%s' % team.id,
                                    data={'to_user': self.user.id}
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFalse(User.objects.filter(pk=team.id))

    def test_team_delete04(self):
        self.login_not_as_superuser()

        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        team = self._create_team('Teamee', [])

        url = '/creme_config/user/delete/%s' % team.id
        self.assertGETRedirectsToLogin(url)
        self.assertPOSTRedirectsToLogin(url, data={'to_user': user.id})

    def test_user_delete01(self): #Delete can not delete the last super user
        self.login()

        user = self.user

        #CremeEntity.objects.all().delete()#In creme_core populate some entities are created, so we avoid an IntegrityError
        #HistoryLine.objects.all().delete()
        self.assertTrue(user.is_superuser)
        User.objects.exclude(pk=user.pk).update(is_superuser=False)

        count = User.objects.count()
        self.assertGreater(count, 1)

        url = '/creme_config/user/delete/%s' % user.id
        self.assertEqual(400, self.client.get(url).status_code)

        response = self.client.post(url, {'to_user': self.user.id})
        self.assertEqual(400, response.status_code)
        self.assertEqual(count, User.objects.count())

    def test_user_delete02(self): #Validation error
        self.login()

        count = User.objects.count()
        self.assertGreater(count, 1)

        url = '/creme_config/user/delete/%s' % self.user.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url) #no data
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'to_user', [_(u'This field is required.')])
        self.assertEqual(count, User.objects.count())

        response = self.client.post(url, {'to_user': self.user.id})
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'to_user',
                             [_(u'Select a valid choice. That choice is not one of the available choices.')]
                            )
        self.assertTrue(User.objects.filter(pk=self.user.id).exists())

    def test_user_delete03(self):
        self.login()

        user       = self.user
        other_user = self.other_user
        ce = CremeEntity.objects.create(user=other_user)

        url = '/creme_config/user/delete/%s' % other_user.id
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, {'to_user': user.id})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertFalse(User.objects.filter(id=other_user.id).exists())

        ce = self.get_object_or_fail(CremeEntity, pk=ce.id)
        self.assertEqual(user, ce.user)

    #TODO: move to 'activities'
    def test_user_delete04(self):
        self.login()

        user       = self.user
        other_user = self.other_user

        cal = Calendar.get_user_default_calendar(other_user)
        url = '/creme_config/user/delete/%s' % other_user.id

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(url, {'to_user': user.id})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)
        self.assertFalse(User.objects.filter(id=other_user.id).exists())

        cal = self.get_object_or_fail(Calendar, pk=cal.id)
        self.assertEqual(user, cal.user)

    def test_user_delete05(self):
        self.login()

        user       = self.user
        other_user = self.other_user

        Contact.objects.create(user=user, is_user=user)
        Contact.objects.create(user=other_user, is_user=other_user)
        Contact.objects.create(user=user, is_user=None)
        Contact.objects.create(user=other_user, is_user=None)

        response = self.client.post('/creme_config/user/delete/%s' % other_user.id, {'to_user': user.id})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertFalse(User.objects.filter(id=other_user.id).exists())

        self.assertFalse(Contact.objects.filter(user=other_user).exists())
        self.assertFalse(Contact.objects.filter(is_user=other_user).exists())

        self.assertEqual(1, Contact.objects.filter(is_user=user).count())

    def test_user_delete06(self):
        self.login()

        setting_key = 'unit_test-test_userl_delete06'
        sk = SettingKey.create(pk=setting_key, description="",
                               app_label='creme_config', type=SettingKey.BOOL
                              )
        SettingValue.objects.create(key=sk, user=self.other_user, value=True)

        response = self.client.post('/creme_config/user/delete/%s' % self.other_user.id, {'to_user': self.user.id})
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        self.assertFalse(User.objects.filter(id=self.other_user.id).exists())
        self.assertFalse(SettingValue.objects.filter(key=setting_key).exists())

    def test_user_delete07(self):
        self.login_not_as_superuser()

        url = '/creme_config/user/delete/%s' % self.other_user.id
        self.assertGETRedirectsToLogin(url)
        self.assertPOSTRedirectsToLogin(url, data={'to_user': self.user.id})


class UserSettingsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.login()

    def test_user_settings(self):
        response = self.client.get('/creme_config/my_settings/')
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'id="%s"' % blocks.UserPreferedMenusBlock.id_)
        self.assertContains(response, 'id="%s"' % blocks.BlockMypageLocationsBlock.id_)

    def test_change_theme01(self):
        self.assertEqual(1, SettingKey.objects.filter(pk=USER_THEME_NAME).count())
        self.assertEqual(0, SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME).count())

        def change_theme(theme):
            response = self.client.post('/creme_config/my_settings/edit_theme/', data={'themes': theme})
            self.assertEqual(200, response.status_code)

            svalues = SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME)
            self.assertEqual(1, len(svalues))
            self.assertEqual(theme, svalues[0].value)

        change_theme("chantilly")
        change_theme("icecream")

    def test_get_user_theme01(self):
        self.assertEqual(1, SettingKey.objects.filter(pk=USER_THEME_NAME).count())
        self.assertEqual(0, SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME).count())

        self.assertEqual(settings.DEFAULT_THEME, get_user_theme(self.user))
        self.assertEqual(1, SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME).count())

        sv = SettingValue.objects.get(user=self.user, key=USER_THEME_NAME)
        sv.value = "unknown theme"
        sv.save()
        self.assertEqual(settings.DEFAULT_THEME, get_user_theme(self.user))

    def test_get_user_theme02(self):
        class FakeRequest(object):
            def __init__(self):
                sessions = Session.objects.all()
                assert 1 == len(sessions)
                self.session = sessions[0].get_decoded()

        def get_theme():
            try:
                theme = FakeRequest().session['usertheme']
            except Exception as e:
                theme = None

            return theme

        self.assertEqual(1, SettingKey.objects.filter(pk=USER_THEME_NAME).count())
        self.assertEqual(0, SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME).count())
        self.assertIsNone(get_theme())

        self.client.get('/')
        self.assertEqual(1, SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME).count())
        self.assertEqual(settings.DEFAULT_THEME, get_theme())
