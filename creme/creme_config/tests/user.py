# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.conf import settings
    from django.contrib.sessions.models import Session
    from django.contrib.auth.models import User
    from django.utils.simplejson import loads as jsonloads
    from django.utils import timezone as django_tz
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import (CremeEntity, CremeProperty, Relation, EntityCredentials,
                                   UserRole, SetCredentials, Mutex)
    from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME
    from creme.creme_core.tests.base import CremeTestCase

    from creme.activities.models import Calendar

    from creme.persons.models import Contact, Organisation #need CremeEntity
    from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES

    from ..constants import USER_THEME_NAME, USER_TIMEZONE
    from ..models import SettingKey, SettingValue
    from ..utils import get_user_theme
    from ..blocks import UsersBlock, TeamsBlock, UserPreferedMenusBlock, BlockMypageLocationsBlock
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('UserTestCase', 'UserSettingsTestCase')


class UserTestCase(CremeTestCase):
    ADD_URL = '/creme_config/user/add/'
    ADD_TEAM_URL = '/creme_config/team/add/'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons')

    def _build_delete_url(self, user):
        return '/creme_config/user/delete/%s' % user.id

    def _build_edit_url(self, user_id, password=None):
        return '/creme_config/user/edit/%s%s' % ('password/' if password else '', user_id)

    def _build_activation_url(self, user_id, activation):
        return '/creme_config/user/%s/%s' % (activation, user_id)

    def login_not_as_superuser(self):
        apps = ('creme_config',)
        self.login(is_superuser=False, allowed_apps=apps, admin_4_apps=apps)

    def _aux_test_portal(self):
        response = self.assertGET200('/creme_config/user/portal/')
        self.assertContains(response, 'id="%s"' % UsersBlock.id_)
        self.assertContains(response, 'id="%s"' % TeamsBlock.id_)

    def test_portal01(self):
        self.login()
        self._aux_test_portal()

    def test_portal02(self):
        self.login_not_as_superuser()
        self._aux_test_portal()

    def test_create01(self):
        self.login()

        url = self.ADD_URL
        self.assertGET200(url)

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

        users = User.objects.filter(username=username)
        self.assertEqual(1, len(users))

        user = users[0]
        self.assertTrue(user.is_superuser)
        self.assertIsNone(user.role)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)
        self.assertTrue(user.check_password(password))

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

        SetCredentials.objects.create(role=role, value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        contact = Contact.objects.create(user=self.user, first_name='Deunan', last_name=u'Knut')

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        ce_count = CremeEntity.objects.count()

        username = 'deunan'
        password = 'password'
        response = self.client.post(self.ADD_URL, follow=True,
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

        users = User.objects.filter(username=username)
        self.assertEqual(1, len(users))

        user = users[0]
        self.assertEqual(role,     user.role)
        self.assertEqual(ce_count, CremeEntity.objects.count())

        self.assertTrue(user.has_perm_to_view(orga))

        contact = self.refresh(contact)
        self.assertEqual(user, contact.is_user)
        self.assertRelationCount(1, contact, REL_SUB_MANAGES, orga)

    def test_create03(self):
        "Relation is not recreate if it already exists"
        self.login()

        contact = Contact.objects.create(user=self.user, first_name='Deunan', last_name=u'Knut')

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        Relation.objects.create(user=self.user, subject_entity=contact, type_id=REL_SUB_MANAGES, object_entity=orga)

        username = 'deunan'
        password = 'password'
        response = self.client.post(self.ADD_URL, follow=True,
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

        user = self.get_object_or_fail(User, username=username)
        contact = self.refresh(contact)
        self.assertEqual(user, contact.is_user)
        self.assertRelationCount(1, contact, REL_SUB_MANAGES, orga) #not 2 !!

    def test_create04(self):
        self.login_not_as_superuser()

        url = self.ADD_URL
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

    def test_create05(self):
        "Linked contact can not be already linked to another user"
        self.login()

        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        contact = Contact.objects.create(user=self.user, first_name='Deunan', last_name=u'Knut', is_user=user)

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username = 'deunan'
        password = 'password'
        response = self.client.post(self.ADD_URL, follow=True,
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
        self.assertEqual(user, self.refresh(contact).is_user)

        new_user = self.get_object_or_fail(User, username=username)
        self.get_object_or_fail(Contact, is_user=new_user,
                                first_name=username, last_name=username
                               )

    def test_create06(self):
        "wrong username"
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username = 'é^ǜù'
        password = 'password'
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'username':     username,
                                          'password_1':   password,
                                          'password_2':   password,
                                          'is_superuser': True,
                                          'organisation': orga.id,
                                          'relation':     REL_SUB_MANAGES,
                                         }
                                   )

        self.assertFormError(response, 'form', 'username', _(u"The username must only contain alphanumeric (a-z, A-Z, 0-9), "
                                            "hyphen and underscores are allowed (but not as first character)."
                                           ))

    def test_create07(self):
        "wrong password"
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username = 'deunan'
        password = 'password'
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'username':     username,
                                          'password_1':   password,
                                          'password_2':   password + "5",
                                          'is_superuser': True,
                                          'organisation': orga.id,
                                          'relation':     REL_SUB_MANAGES,
                                         }
                                   )

        self.assertFormError(response, 'form', 'password_2', _(u"Passwords are different"))

    def test_create08(self):
        "common user without role"
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username = 'deunan'
        password = 'password'
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'username':     username,
                                          'password_1':   password,
                                          'password_2':   password + "5",
                                          'is_superuser': False,
                                          'organisation': orga.id,
                                          'relation':     REL_SUB_MANAGES,
                                         }
                                   )

        self.assertFormError(response, 'form', 'role', _(u"Choose a role or set superuser status to 'True'."))

    def test_edit01(self):
        self.login()

        role1 = UserRole(name='Master')
        role1.allowed_apps = ['persons']
        role1.save()
        SetCredentials.objects.create(role=role1, value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )
        other_user = User.objects.create(username='deunan', role=role1)

        briareos = Contact.objects.create(user=self.user, first_name='Briareos', last_name='Hecatonchires')
        self.assertTrue(other_user.has_perm_to_view(briareos))

        url = self._build_edit_url(other_user.id)
        self.assertGET200(url)

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

        other_user = self.refresh(other_user)
        self.assertEqual(first_name, other_user.first_name)
        self.assertEqual(last_name,  other_user.last_name)
        self.assertEqual(email,      other_user.email)
        self.assertEqual(role2,      other_user.role)

        briareos = self.refresh(briareos) #refresh cache
        self.assertFalse(other_user.has_perm_to_view(briareos))

    def test_edit02(self):
        "Can not edit a team with the user edit view"
        self.login()

        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        team  = self._create_team('Teamee', [user])

        url = self._build_edit_url(team.id)
        self.assertGET404(url)
        self.assertPOST404(url)

    def test_edit03(self):
        self.login_not_as_superuser()

        role1 = UserRole(name='Master')
        role1.allowed_apps = ['persons']
        role1.save()
        SetCredentials.objects.create(role=role1, value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )
        other_user = User.objects.create(username='deunan', role=role1)

        briareos = Contact.objects.create(user=self.user, first_name='Briareos', last_name='Hecatonchires')
        self.assertTrue(other_user.has_perm_to_view(briareos))

        url = self._build_edit_url(other_user.id)
        self.assertGETRedirectsToLogin(url)

        role2 = UserRole.objects.create(name='Slave')
        self.assertPOSTRedirectsToLogin(url,data={'first_name': 'Deunan',
                                                  'last_name':  'Knut',
                                                  'email':      'd.knut@eswat.ol',
                                                  'role':       role2.id,
                                                 }
                                       )

    def test_edit04(self):
        "Common user without role"
        self.login()

        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')

        url = self._build_edit_url(user.id)
        self.assertGET200(url)

        response = self.client.post(url, follow=True,
                                    data={'is_superuser': False}
                                   )
        self.assertFormError(response, 'form', 'role', _(u"Choose a role or set superuser status to 'True'."))

    def test_change_password01(self):
        self.login()

        other_user = User.objects.create(username='deunan')
        url = self._build_edit_url(other_user.id, password=True)
        self.assertGET200(url)

        password = 'password'
        response = self.client.post(url, follow=True,
                                    data={'password_1': password,
                                          'password_2': password,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertTrue(self.refresh(other_user).check_password(password))

    def test_change_password02(self):
        self.login_not_as_superuser()

        other_user = User.objects.create(username='deunan')
        url = self._build_edit_url(other_user.id, password=True)
        self.assertGETRedirectsToLogin(url)

        password = 'password'
        self.assertPOSTRedirectsToLogin(url, data={'password_1': password,
                                                   'password_2': password,
                                                  }
                                       )

    def test_change_password03(self):
        self.login()

        other_user = User.objects.create(username='deunan')
        url = self._build_edit_url(other_user.id, password=True)
        self.assertGET200(url)

        password = 'password'
        response = self.client.post(url, follow=True,
                                    data={'password_1': password,
                                          'password_2': password + '42',
                                         }
                                   )
        self.assertFormError(response, 'form', 'password_2', _(u"Passwords are different"))

    def test_user_activation01(self):
        "Not superuser"
        self.login_not_as_superuser()
        other_user = User.objects.create(username='deunan')
        url = partial(self._build_activation_url, other_user.id)
        self.assertGETRedirectsToLogin(url('deactivate'))
        self.assertGETRedirectsToLogin(url('activate'))

    def test_user_activation02(self):
        "Post only & Current user"
        self.login()
        url = self._build_activation_url(self.user.id, 'deactivate')
        self.assertGET404(url)
        self.assertPOST(409, url)

    def test_user_activation03(self):
        "user is staff"
        self.login()
        other_user = User.objects.create(username='deunan', is_staff=True)
        url = partial(self._build_activation_url, other_user.id)
        self.assertPOST(400, url('activate'))
        self.assertPOST(400, url('deactivate'))

    def test_user_activation04(self):
        "user is staff"
        self.login()
        other_user = User.objects.create(username='deunan', is_staff=True)
        url = partial(self._build_activation_url, other_user.id)
        self.assertPOST(400, url('activate'))
        self.assertPOST(400, url('deactivate'))

    def test_user_activation05(self):
        "user is staff"
        self.login()
        other_user = User.objects.create(username='deunan')
        url = partial(self._build_activation_url, other_user.id)

        self.assertPOST200(url('deactivate'))
        self.assertFalse(self.refresh(other_user).is_active)
        self.assertPOST200(url('activate'))
        self.assertTrue(self.refresh(other_user).is_active)

    def test_team_create01(self):
        self.login()

        url = self.ADD_TEAM_URL
        self.assertGET200(url)

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

        url = self.ADD_TEAM_URL
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
        SetCredentials.objects.create(role=role, value=EntityCredentials.VIEW,
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
        self.assertTrue(user01.has_perm_to_view(entity))
        self.assertTrue(user02.has_perm_to_view(entity))
        self.assertFalse(user03.has_perm_to_view(entity))

        url = '/creme_config/team/edit/%s' % team.id
        self.assertGET200(url)

        teamname += '_edited'
        response = self.client.post(url, follow=True,
                                    data={'username':  teamname,
                                          'teammates': [user02.id, user03.id],
                                        }
                                   )
        self.assertNoFormError(response)

        team = self.refresh(team)
        self.assertEqual(teamname, team.username)

        teammates = team.teammates
        self.assertEqual(2, len(teammates))
        self.assertIn(user02.id, teammates)
        self.assertIn(user03.id, teammates)
        self.assertNotIn(user01.id, teammates)

        #credentials have been updated ?
        entity = CremeEntity.objects.get(pk=entity.id)
        self.assertFalse(self.refresh(user01).has_perm_to_view(entity))
        self.assertTrue(self.refresh(user02).has_perm_to_view(entity))
        self.assertTrue(self.refresh(user03).has_perm_to_view(entity))

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

        url = self._build_delete_url(team)
        self.assertGET200(url)
        self.assertPOST200(url, data={'to_user': user.id})
        self.assertDoesNotExist(team)

    def test_team_delete02(self):
        self.login()

        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        team  = self._create_team('Teamee', [user])
        team2 = self._create_team('Teamee2', [user])

        ce = CremeEntity.objects.create(user=team)

        url = self._build_delete_url(team)
        self.assertGET200(url)
        self.assertPOST200(url, data={'to_user': team2.id})
        self.assertDoesNotExist(team)

        ce = self.get_object_or_fail(CremeEntity, pk=ce.id)
        self.assertEqual(team2, ce.user)

    def test_team_delete03(self):
        self.login()

        team = self._create_team('Teamee', [])
        CremeEntity.objects.create(user=team)

        self.assertPOST200(self._build_delete_url(team), data={'to_user': self.user.id})
        self.assertDoesNotExist(team)

    def test_team_delete04(self):
        self.login_not_as_superuser()

        user = User.objects.create_user('Maruo', 'maruo@century.jp', 'uselesspw')
        team = self._create_team('Teamee', [])

        url = self._build_delete_url(team)
        self.assertGETRedirectsToLogin(url)
        self.assertPOSTRedirectsToLogin(url, data={'to_user': user.id})

    def test_user_delete01(self):
        "Delete view can delete a superuser if at least one remains"
        self.login()
        user = self.user
        root = User.objects.get(username='root')

        self.assertEqual(2, User.objects.filter(is_superuser=True).count())
        self.assertEqual(1, User.objects.exclude(id=user.id).filter(is_superuser=True).count())

        url = self._build_delete_url(root)
        self.assertGET200(url)

        self.assertPOST200(url, {'to_user': user.id})
        self.assertEqual(1, User.objects.filter(is_superuser=True).count())
        self.assertEqual(0, User.objects.filter(username='root').count())

    def test_user_delete02(self):
        "Delete view can delete any normal user"
        self.login()

        user       = self.user;       self.assertTrue(user.is_superuser)
        other_user = self.other_user; self.assertFalse(other_user.is_superuser)
        ce = CremeEntity.objects.create(user=other_user)

        url = self._build_delete_url(other_user)
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, {'to_user': user.id}))
        self.assertFalse(User.objects.filter(id=other_user.id).exists())

        ce = self.get_object_or_fail(CremeEntity, pk=ce.id)
        self.assertEqual(user, ce.user)

    def test_user_cannot_delete_last_superuser(self):
        "Delete view can not delete the last superuser"
        self.client.login(username='root', password='root')

        self.assertEqual(1, User.objects.filter(is_superuser=True).count())
        user = self.get_object_or_fail(User, username='root', is_superuser=True)

        url = self._build_delete_url(user)
        self.assertGET(409, url)
        self.assertPOST(409, url, {'to_user': user.id})

        self.assertEqual(1, User.objects.filter(is_superuser=True).count())

    def test_user_cannot_delete_staff_user(self):
        "Delete view can not delete the staff user"
        self.login()
        hybird = User.objects.create(username='hybird', is_staff=True)
        
        url = self._build_delete_url(hybird)
        self.assertGET(400, url)
        self.assertPOST(400, url, {'to_user': hybird.id})

    def test_user_cannot_delete_during_transfert(self):
        "Delete view is protected by a lock"
        self.login()
        user = self.user
        root = User.objects.get(username='root')

        self.assertEqual(2, User.objects.filter(is_superuser=True).count())
        self.assertEqual(1, User.objects.exclude(id=user.id).filter(is_superuser=True).count())

        Mutex.get_n_lock('creme_config-forms-user-transfer_user')

        url = self._build_delete_url(root)
        self.assertGET200(url)
        self.assertPOST(400, url, {'to_user': user.id})

        self.assertEqual(2, User.objects.filter(is_superuser=True).count())

    #def test_user_delete_last_basic_user(self):
        #"Delete view can delete any normal user"
        #role = UserRole.objects.create(name='Basic')
        #role.allowed_apps = ('creme_core',)
        #role.admin_4_apps = ()
        #role.save()

        #self.role = role
        #basic_user = User.objects.create(username='Mireille', role=role)
        #basic_user.set_password('test')
        #basic_user.save()

        #self.client.login(username='root', password='root')

        #self.assertEqual(1, User.objects.filter(is_superuser=True).count())
        #self.assertEqual(1, User.objects.filter(is_superuser=False).count())

        #root = User.objects.get(is_superuser=True)

        #url = '/creme_config/user/delete/%s' % basic_user.id
        #self.assertEqual(200, self.client.get(url).status_code)

        #response = self.client.post(url, {'to_user': root.id})
        #self.assertEqual(200, response.status_code)

        #self.assertEqual(1, User.objects.filter(is_superuser=True).count())
        #self.assertEqual(0, User.objects.filter(is_superuser=False).count())

    def test_user_delete_errors(self):
        "Validation errors"
        self.login()
        root = User.objects.get(username='root')

        count = User.objects.count()
        self.assertGreater(count, 1)

        url = self._build_delete_url(root)
        self.assertGET200(url)

        response = self.assertPOST200(url) #no data
        self.assertFormError(response, 'form', 'to_user', [_(u'This field is required.')])
        self.assertEqual(count, User.objects.count())

        response = self.assertPOST200(url, {'to_user': root.id}) #cannot move entities to deleted user
        self.assertFormError(response, 'form', 'to_user',
                             [_(u'Select a valid choice. That choice is not one of the available choices.')]
                            )
        self.assertStillExists(self.user)

    #TODO: move to 'activities'
    def test_user_delete_calendar(self):
        self.login()

        user       = self.user
        other_user = self.other_user

        cal = Calendar.get_user_default_calendar(other_user)
        url = self._build_delete_url(other_user)

        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, {'to_user': user.id}))
        self.assertFalse(User.objects.filter(id=other_user.id).exists())

        cal = self.get_object_or_fail(Calendar, pk=cal.id)
        self.assertEqual(user, cal.user)

    def test_user_delete_is_user(self):
        "Manage Contact.is_user field : Contact is no more related to deleted user."
        self.login()

        user       = self.user
        other_user = self.other_user

        create_contact = Contact.objects.create
        create_contact(user=user,       is_user=user)
        create_contact(user=other_user, is_user=other_user)
        create_contact(user=user,       is_user=None)
        create_contact(user=other_user, is_user=None)

        self.assertNoFormError(self.client.post(self._build_delete_url(other_user),
                                                {'to_user': user.id}
                                               )
                              )
        self.assertDoesNotExist(other_user)

        self.assertFalse(Contact.objects.filter(user=other_user).exists())
        self.assertFalse(Contact.objects.filter(is_user=other_user).exists())

        self.assertEqual(1, Contact.objects.filter(is_user=user).count())

    def test_user_delete_settingkey(self):
        "Related SettingValues are deleted."
        self.login()

        setting_key = 'unit_test-test_userl_delete06'
        sk = SettingKey.create(pk=setting_key, description="",
                               app_label='creme_config', type=SettingKey.BOOL
                              )
        SettingValue.objects.create(key=sk, user=self.other_user, value=True)

        self.assertNoFormError(self.client.post(self._build_delete_url(self.other_user),
                                                {'to_user': self.user.id}
                                               )
                              )
        self.assertDoesNotExist(self.other_user)
        self.assertFalse(SettingValue.objects.filter(key=setting_key).exists())

    def test_user_delete_credentials(self):
        "Only super user are allowed"
        self.login_not_as_superuser()

        url = self._build_delete_url(self.other_user)
        self.assertGETRedirectsToLogin(url)
        self.assertPOSTRedirectsToLogin(url, data={'to_user': self.user.id})


class UserSettingsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.login()

    def test_user_settings(self):
        response = self.assertGET200('/creme_config/my_settings/')
        self.assertContains(response, 'id="%s"' % UserPreferedMenusBlock.id_)
        self.assertContains(response, 'id="%s"' % BlockMypageLocationsBlock.id_)

    def test_change_theme01(self):
        self.get_object_or_fail(SettingKey, pk=USER_THEME_NAME)
        self.assertFalse(SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME))

        def change_theme(theme):
            self.assertPOST200('/creme_config/my_settings/set_theme/', data={'theme': theme})

            svalues = SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME)
            self.assertEqual(1, len(svalues))
            self.assertEqual(theme, svalues[0].value)

        change_theme("chantilly")
        change_theme("icecream")

    def test_get_user_theme01(self):
        user = self.user

        class FakeRequest(object):
            def __init__(self):
                self.user = user
                self.session = {}

        self.get_object_or_fail(SettingKey, pk=USER_THEME_NAME)
        self.assertFalse(SettingValue.objects.filter(user=user, key=USER_THEME_NAME))

        self.assertEqual(settings.DEFAULT_THEME, get_user_theme(FakeRequest()))
        sv = self.get_object_or_fail(SettingValue, user=user, key=USER_THEME_NAME)

        sv.value = "unknown theme"
        sv.save()
        self.assertEqual(settings.DEFAULT_THEME, get_user_theme(FakeRequest()))

    def test_get_user_theme02(self):
        class FakeRequest(object):
            def __init__(self):
                sessions = Session.objects.all()
                assert 1 == len(sessions)
                self.session = sessions[0].get_decoded()

        def get_theme():
            try:
                theme = FakeRequest().session['usertheme']
            except Exception:
                theme = None

            return theme

        self.get_object_or_fail(SettingKey, pk=USER_THEME_NAME)
        self.assertFalse(SettingValue.objects.filter(user=self.user, key=USER_THEME_NAME))
        self.assertIsNone(get_theme())

        self.client.get('/')
        self.get_object_or_fail(SettingValue, user=self.user, key=USER_THEME_NAME)
        self.assertEqual(settings.DEFAULT_THEME, get_theme())

    def test_change_timezone01(self):
        self.get_object_or_fail(SettingKey, pk=USER_TIMEZONE)
        self.assertFalse(SettingValue.objects.filter(user=self.user, key=USER_TIMEZONE))

        #TODO: use 'nonlocal' in py3k
        inner = {'called':       False,
                 'activated_tz': None,
                }

        def fake_activate(tz):
            inner['called']       = True
            inner['activated_tz'] = tz

        django_tz.activate = fake_activate

        self.client.get('/')
        self.assertFalse(inner['called'])

        url = '/creme_config/my_settings/set_timezone/'

        def assertSelected(selected_tz):
            response = self.assertGET200(url)

            with self.assertNoException():
                form_str = jsonloads(response.content)['form']

            for line in form_str.split('\n'):
                if selected_tz in line:
                    option = line
                    break
            else:
                self.fail('Option not found')

            self.assertEqual(1, option.count('<option '))
            self.assertIn('selected', option)

        def change_tz(tz):
            self.assertPOST200(url, data={'time_zone': tz})

            svalues = SettingValue.objects.filter(user=self.user, key=USER_TIMEZONE)
            self.assertEqual(1, len(svalues))
            self.assertEqual(tz, svalues[0].value)

            self.client.get('/')
            self.assertTrue(inner['called'])
            self.assertEqual(tz, inner['activated_tz'])

            inner['called'] = False

        TIME_ZONE = settings.TIME_ZONE
        time_zones = [tz for tz in ('Asia/Tokyo', 'US/Eastern', 'Europe/Paris')
                        if tz != TIME_ZONE
                     ]

        assertSelected(TIME_ZONE)

        tz = time_zones[0]
        change_tz(tz)
        assertSelected(tz)

        change_tz(time_zones[1])
