# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _
    from django.conf import settings
    from django.contrib.sessions.models import Session
    from django.contrib.auth.models import User

    from creme_core.models import CremeEntity, CremeProperty, EntityCredentials, UserRole, HistoryLine, SetCredentials
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
    print 'Error:', e


__all__ = ('UserTestCase', 'UserSettingsTestCase')


class UserTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config', 'persons') #'creme_core'
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/user/portal/').status_code)

    def test_create01(self):
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
        self.assert_(user.is_superuser)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)
        self.assertTrue(user.check_password(password))

        self.assertFalse(EntityCredentials.objects.filter(user=user).exists())

    def test_create02(self):
        role = UserRole(name='Mangaka')
        role.allowed_apps = ['persons']
        role.save()

        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username = 'deunan'
        password = 'password'
        response = self.client.post('/creme_config/user/add/', follow=True,
                                    data={'username':     username,
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

        self.assertTrue(orga.can_view(user))

    def test_edit01(self):
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

    def test_change_password(self):
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

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/user/portal/').status_code)

    def test_team_create(self):
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

    def _create_team(self, name, teammates):
        team = User.objects.create(username=name, is_team=True, role=None)
        team.teammates = teammates

        return team

    def test_team_edit(self):
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

        response = self.client.get('/creme_config/team/edit/%s' % user01.id)
        self.assertEqual(404, response.status_code)

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

    def test_team_delete01(self):
        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        team = self._create_team('Teamee', [])

        #user is not a team
        url = '/creme_config/team/delete/%s' % user.id
        self.assertEqual(400, self.client.get(url).status_code)
        self.assertEqual(400, self.client.post(url, data={'to_user': None}).status_code)

        url = '/creme_config/team/delete/%s' % team.id
        self.assertEqual(200, self.client.get(url).status_code)
        self.assertEqual(200, self.client.post(url, data={'to_user': user.id}).status_code)
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
        except CremeEntity.DoesNotExist as e:
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

        self.assertEqual(1, User.objects.count())

        response = self.client.get('/creme_config/user/delete/%s' % self.user.id)
        self.assertEqual(400, response.status_code)

        response = self.client.post('/creme_config/user/delete/%s' % self.user.id, {'to_user': self.user.id})

        self.assertEqual(400, response.status_code)#Delete is not permitted when there is only one user
        self.assertEqual(1, User.objects.count())

    def test_user_delete02(self):
        self.assertGreater(User.objects.count(), 1)

        response = self.client.get('/creme_config/user/delete/%s' % self.user.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/creme_config/user/delete/%s' % self.user.id, {'to_user': self.user.id})
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', None, [_(u"You can't delete and assign to the same user.")])
        self.assertTrue(User.objects.filter(pk=self.user.id).exists())

    def test_user_delete03(self):
        user       = self.user
        other_user = self.other_user

        ce = CremeEntity.objects.create(user=other_user)

        response = self.client.get('/creme_config/user/delete/%s' % other_user.id)
        self.assertEqual(200, response.status_code)

        response = self.client.post('/creme_config/user/delete/%s' % other_user.id, {'to_user': user.id})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertFalse(User.objects.filter(id=other_user.id).exists())

        try:
            ce = CremeEntity.objects.get(pk=ce.id)#Refresh
        except CremeEntity.DoesNotExist as e:
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

        self.assertFalse(User.objects.filter(id=other_user.id).exists())

        try:
            cal = Calendar.objects.get(pk=cal.id)
        except Calendar.DoesNotExist as e:
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

        self.assertFalse(User.objects.filter(id=other_user.id).exists())

        self.assertFalse(Contact.objects.filter(user=other_user).exists())
        self.assertFalse(Contact.objects.filter(is_user=other_user).exists())

        self.assertEqual(1, Contact.objects.filter(is_user=user).count())

    def test_user_delete06(self):
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


class UserSettingsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
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
