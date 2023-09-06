from functools import partial
from unittest import skipIf

from django.conf import settings
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone as django_tz
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from parameterized import parameterized

from creme.creme_core.core.setting_key import (
    SettingKey,
    UserSettingKey,
    user_setting_key_registry,
)
from creme.creme_core.models import BrickState, CremeEntity
from creme.creme_core.models import CremeUser as User
from creme.creme_core.models import (
    EntityCredentials,
    Mutex,
    RelationType,
    SetCredentials,
    UserRole,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from creme.persons.models import Contact, Organisation
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .. import constants
from ..bricks import BrickMypageLocationsBrick, TeamsBrick, UsersBrick


def skipIfNotCremeUser(test_func):
    return skipIf(
        settings.AUTH_USER_MODEL != 'creme_core.CremeUser',
        "Skip this test which uses CremeUser model"
    )(test_func)


@skipIfCustomOrganisation
@override_settings(AUTH_PASSWORD_VALIDATORS=[])
class UserTestCase(CremeTestCase, BrickTestCaseMixin):
    ADD_URL = reverse('creme_config__create_user')
    ADD_TEAM_URL = reverse('creme_config__create_team')

    @staticmethod
    def _build_delete_url(user):
        return reverse('creme_config__delete_user', args=(user.id,))

    @staticmethod
    def _build_edit_url(user_id, password=False):
        return reverse(
            'creme_config__change_user_password' if password else 'creme_config__edit_user',
            args=(user_id,),
        )

    @staticmethod
    def _build_activation_url(user_id, activation=True):
        return reverse(
            'creme_config__activate_user' if activation else 'creme_config__deactivate_user',
            args=(user_id,),
        )

    def login_not_as_superuser(self):
        apps = ('creme_config',)
        return self.login(is_superuser=False, allowed_apps=apps, admin_4_apps=apps)

    @skipIfNotCremeUser
    @parameterized.expand([
        (False,),
        (True,),
    ])
    def test_portal(self, superuser):
        user = self.login(is_superuser=superuser, admin_4_apps=['creme_config'])
        User.objects.create(username='A-Team', is_team=True)
        User.objects.create(
            username='StaffMan', is_staff=True, first_name='Staff', last_name='Man',
        )

        other_user = self.other_user
        other_user.is_active = False
        other_user.save()

        response = self.assertGET200(reverse('creme_config__users'))
        self.assertTemplateUsed(response, 'creme_config/portals/user.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        # ---
        doc = self.get_html_tree(response.content)
        users_brick_node = self.get_brick_node(doc, brick=UsersBrick)
        self.assertBrickTitleEqual(
            users_brick_node,
            count=3, title='{count} User', plural_title='{count} Users',
        )
        self.assertCountEqual(
            ['root', user.username, other_user.username],
            [
                n.text
                for n in users_brick_node.findall('.//td[@class="user-username"]')
            ],
        )
        self.assertIsNone(users_brick_node.find('.//th[@data-key="regular_field-time_zone"]'))

        # ---
        teams_brick_node = self.get_brick_node(doc, brick=TeamsBrick)
        self.assertBrickTitleEqual(
            teams_brick_node,
            count=1, title='{count} Team', plural_title='{count} Teams',
        )

    def test_portal_hide_inactive(self):
        user = self.login()

        other_user = self.other_user
        other_user.is_active = False
        other_user.save()

        brick_id = UsersBrick.id_

        state = BrickState(user=user, brick_id=brick_id)
        state.set_extra_data(constants.BRICK_STATE_HIDE_INACTIVE_USERS, True)
        state.save()

        response = self.assertGET200(reverse('creme_config__users'))
        brick_node = self.get_brick_node(self.get_html_tree(response.content), brick_id)

        usernames = {
            n.text
            for n in brick_node.findall('.//td[@class="user-username"]')
        }
        self.assertIn(user.username, usernames)
        self.assertNotIn(other_user.username, usernames)

    def test_portal_display_tz(self):
        user = self.login()

        time_zone = settings.TIME_ZONE
        user.time_zone = (
            'Europe/Paris'
            if time_zone != 'Europe/Paris' else
            'Asia/Tokyo'
        )
        user.save()

        response = self.assertGET200(reverse('creme_config__users'))
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=UsersBrick,
        )

        self.assertIsNotNone(brick_node.find('.//th[@data-key="regular_field-time_zone"]'))
        self.assertSetEqual(
            {time_zone, user.time_zone},
            {
                n.text
                for n in brick_node.findall('.//td[@class="user-timezone"]')
            },
        )

    def test_portal_staff(self):
        user = self.login(is_staff=True)

        response = self.assertGET200(reverse('creme_config__users'))
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=UsersBrick,
        )

        usernames = {
            n.text
            for n in brick_node.findall('.//td[@class="user-username"]')
        }
        self.assertIn(user.username, usernames)
        self.assertIn(self.other_user.username, usernames)

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_create_user01(self):
        user = self.login()

        rtype1 = self.get_object_or_fail(RelationType, id=REL_SUB_EMPLOYED_BY)
        rtype2 = self.get_object_or_fail(RelationType, id=REL_SUB_MANAGES)
        rtype3 = RelationType.objects.smart_update_or_create(
            ('test-subject_employee_month', 'is the employee of the month for', [Contact]),
            ('test-object_employee_month',  'has the employee of the month',    [Organisation]),
        )[0]
        rtype4 = RelationType.objects.smart_update_or_create(
            ('test-subject_generic', 'generic as ***'),
            ('test-object_generic',  'other side'),
        )[0]
        internal_rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_employee_year', 'is the employee of the year for', [Contact]),
            ('test-object_employee_year',   'has the employee of the year', [Organisation]),
            is_internal=True,
        )[0]
        disabled_rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_employee_week', 'is the employee of the week for', [Contact]),
            ('test-object_employee_week',   'has the employee of week year',  [Organisation]),
        )[0]
        disabled_rtype.enabled = False
        disabled_rtype.save()

        url = self.ADD_URL
        context = self.assertGET200(url).context
        self.assertEqual(User.creation_label, context.get('title'))
        self.assertEqual(User.save_label,     context.get('submit_label'))

        with self.assertNoException():
            relation_choices = context['form'].fields['relation'].choices

        self.assertInChoices(value=rtype1.id, label=str(rtype1), choices=relation_choices)
        self.assertInChoices(value=rtype2.id, label=str(rtype2), choices=relation_choices)
        self.assertInChoices(value=rtype3.id, label=str(rtype3), choices=relation_choices)
        self.assertNotInChoices(value=rtype4.id,         choices=relation_choices)
        self.assertNotInChoices(value=internal_rtype.id, choices=relation_choices)
        self.assertNotInChoices(value=disabled_rtype.id, choices=relation_choices)

        # ---
        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)

        username = 'deunan'
        first_name = 'Deunan'
        last_name = 'Knut'
        password = 'password'
        email = 'd.knut@eswat.ol'
        response = self.client.post(
            url, follow=True,
            data={
                'username':     username,
                'password_1':   password,
                'password_2':   password,
                'first_name':   first_name,
                'last_name':    last_name,
                'email':        email,
                'role':         '',
                'organisation': orga.id,
                'relation':     rtype1.id,
            },
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

        contact = self.get_object_or_fail(
            Contact,
            is_user=user, first_name=first_name, last_name=last_name, email=email,
        )
        self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, orga)

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_create_user02(self):
        "Not superuser ; special chars in username."
        self.login()

        role = UserRole(name='Mangaka')
        role.allowed_apps = ['persons']
        role.save()

        SetCredentials.objects.create(
            role=role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL,
        )

        orga = Organisation.objects.create(user=self.user, name='Olympus', is_managed=True)

        username = 'dknut@eswat.ol'
        password = 'password'
        first_name = 'Deunan'
        last_name = 'Knut'
        response = self.client.post(
            self.ADD_URL,
            follow=True,
            data={
                'username':     username,
                'password_1':   password,
                'password_2':   password,
                'first_name':   first_name,
                'last_name':    last_name,
                'email':        username,
                'role':         role.id,
                'organisation': orga.id,
                'relation':     REL_SUB_MANAGES,
            },
        )
        self.assertNoFormError(response)

        user = self.get_object_or_fail(User, username=username)
        self.assertEqual(role, user.role)
        self.assertFalse(user.is_superuser)

        self.assertTrue(user.has_perm_to_view(orga))

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(user, contact.is_user)
        self.assertRelationCount(1, contact, REL_SUB_MANAGES, orga)

    @skipIfNotCremeUser
    def test_create_user_required_fields(self):
        "First name, last name, email, organisation, relation are required."
        self.login()

        password = 'password'
        response = self.assertPOST200(
            self.ADD_URL,
            follow=True,
            data={
                'username':   'deunan',
                'password_1': password,
                'password_2': password,
            },
        )

        msg = _('This field is required.')
        self.assertFormError(response, 'form', 'first_name',   msg)
        self.assertFormError(response, 'form', 'last_name',    msg)
        self.assertFormError(response, 'form', 'email',        msg)
        self.assertFormError(response, 'form', 'organisation', msg)
        self.assertFormError(response, 'form', 'relation',     msg)

    @skipIfNotCremeUser
    def test_create_user_credentials(self):
        "Not super-user => forbidden."
        user = self.login_not_as_superuser()

        url = self.ADD_URL
        self.assertGET403(url)

        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)

        password = 'password'
        self.assertPOST403(
            url,
            data={
                'username':     'deunan',
                'password_1':   password,
                'password_2':   password,
                'first_name':   'Deunan',
                'last_name':    'Knut',
                'email':        'd.knut@eswat.ol',
                'organisation': orga.id,
                'relation':     REL_SUB_EMPLOYED_BY,
            },
        )

    @skipIfNotCremeUser
    def test_create_user_wrong_username(self):
        user = self.login()

        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)

        username = 'é^ǜù'
        password = 'password'
        response = self.client.post(
            self.ADD_URL,
            follow=True,
            data={
                'username':     username,
                'password_1':   password,
                'password_2':   password,
                'organisation': orga.id,
                'relation':     REL_SUB_MANAGES,
            },
        )
        self.assertFormError(
            response, 'form', 'username',
            _(
                'Enter a valid username. This value may contain only letters, numbers, '
                'and @/./+/-/_ characters.'
            )
        )

    @skipIfNotCremeUser
    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[{
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        }],
    )
    def test_create_user_password_errors(self):
        user = self.login()
        url = self.ADD_URL
        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)

        data = {
            'username':     'deunan',
            'first_name':   'Deunan',
            'last_name':    'Knut',
            'email':        'd.knut@eswat.ol',
            'organisation': orga.id,
            'relation':     REL_SUB_EMPLOYED_BY,
        }
        response = self.assertPOST200(url, follow=True, data=data)
        msg = _('This field is required.')
        self.assertFormError(response, 'form', 'password_1', msg)
        self.assertFormError(response, 'form', 'password_2', msg)

        response = self.assertPOST200(
            url, follow=True, data={**data, 'password_1': 'passwd'},
        )
        self.assertFormError(response, 'form', 'password_2', msg)

        response = self.assertPOST200(
            url, follow=True, data={**data, 'password_2': 'passwd'},
        )
        self.assertFormError(response, 'form', 'password_1', msg)

        response = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                'password_1': 'password',
                'password_2': 'passwd',
            },
        )
        self.assertFormError(
            response, 'form', 'password_2',
            # _("The two password fields didn't match."),
            _("The two password fields didn’t match."),
        )

        response = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                'password_1': '123',
                'password_2': '123',
            },
        )
        self.assertFormError(
            response, 'form', 'password_2', _('This password is entirely numeric.'),
        )

    @skipIfNotCremeUser
    def test_create_user_unique_username(self):
        "Unique username."
        user = self.login()
        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)

        password = 'password'
        response = self.assertPOST200(
            self.ADD_URL,
            data={
                'username':     user.username,
                'password_1':   password,
                'password_2':   password,
                'first_name':   user.first_name,
                'last_name':    user.last_name,
                'email':        'd.knut@eswat.ol',
                'organisation': orga.id,
                'relation':     REL_SUB_EMPLOYED_BY,
            },
        )
        self.assertFormError(
            response, 'form', 'username', _('A user with that username already exists.'),
        )

    @skipIfNotCremeUser
    def test_create_user_unique_email(self):
        "Unique email (among active users)."
        user = self.login()
        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)

        other_user = self.other_user
        password = 'password'
        data = {
            'username': 'deunan',
            'first_name': 'Deunan',
            'last_name': 'Knut',
            'email': other_user.email,  # <===
            'organisation': orga.id,
            'relation': REL_SUB_EMPLOYED_BY,
            'password_1': password,
            'password_2': password,
        }

        response1 = self.assertPOST200(self.ADD_URL, data)
        self.assertFormError(
            response1, 'form', 'email',
            _('An active user with the same email address already exists.'),
        )

        # ---
        other_user.is_active = False
        other_user.save()
        self.assertNoFormError(self.client.post(self.ADD_URL, data))

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_create_user_relationship_error(self):
        "Internal relationships are forbidden."
        user = self.login()
        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)
        rtype = RelationType.objects.smart_update_or_create(
            ('creme_config-subject_test_badrtype', 'Bad RType',     [Contact]),
            ('creme_config-object_test_badrtype',  'Bad RType sym', [Organisation]),
            is_internal=True,  # <==
        )[0]

        password = 'password'
        response = self.assertPOST200(
            self.ADD_URL,
            follow=True,
            data={
                'username':     'deunan',
                'password_1':   password,
                'password_2':   password,
                'first_name':   'Deunan',
                'last_name':    'Knut',
                'email':        'd.knut@eswat.ol',
                'organisation': orga.id,
                'relation':     rtype.id,
            },
        )
        self.assertFormError(
            response, 'form', 'relation',
            _('Select a valid choice. That choice is not one of the available choices.'),
        )

    @skipIfNotCremeUser
    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[{
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        }],
    )
    def test_create_user_similarity_errors(self):
        user = self.login()
        url = self.ADD_URL
        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)

        data = {
            'username':     'agent123',
            'first_name':   'Deunan',
            'last_name':    'Knut',
            'email':        'd.knut@eswat.ol',

            'organisation': orga.id,
            'relation':     REL_SUB_EMPLOYED_BY,
        }

        def post(field_name, field_verbose_name):
            password = data[field_name]
            response = self.assertPOST200(
                url,
                follow=True,
                data={
                    **data,
                    'password_1': password,
                    'password_2': password,
                },
            )
            self.assertFormError(
                response, 'form', 'password_2',
                _("The password is too similar to the %(verbose_name)s.") % {
                    'verbose_name': field_verbose_name,
                },
            )

        post('username', _('Username'))
        post('first_name', _('First name'))
        post('last_name', _('Last name'))
        post('email', _('Email address'))

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_edit_user(self):
        user = self.login()

        role1 = UserRole(name='Master')
        role1.allowed_apps = ['persons']
        role1.save()
        SetCredentials.objects.create(
            role=role1, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL
        )
        other_user = User.objects.create(
            username='deunan', first_name='??', last_name='??', email='??', role=role1,
        )
        deunan = other_user.linked_contact

        briareos = Contact.objects.create(
            user=user, first_name='Briareos', last_name='Hecatonchires',
        )
        self.assertTrue(other_user.has_perm_to_view(briareos))

        url = self._build_edit_url(other_user.id)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Edit «{object}»').format(object=other_user),
            response1.context.get('title'),
        )

        # ----
        first_name = 'Deunan'
        last_name = 'Knut'
        email = 'd.knut@eswat.ol'
        role2 = UserRole.objects.create(name='Slave')
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'first_name': first_name,
                'last_name':  last_name,
                'email':      email,
                'role':       role2.id,
            },
        ))

        other_user = self.refresh(other_user)
        self.assertEqual(first_name, other_user.first_name)
        self.assertEqual(last_name,  other_user.last_name)
        self.assertEqual(email,      other_user.email)
        self.assertEqual(role2,      other_user.role)
        self.assertFalse(other_user.is_superuser)

        briareos = self.refresh(briareos)  # Refresh cache
        self.assertFalse(other_user.has_perm_to_view(briareos))

        # Contact is synced
        deunan = self.refresh(deunan)
        self.assertEqual(first_name,  deunan.first_name)
        self.assertEqual(last_name,   deunan.last_name)
        self.assertEqual(email,       deunan.email)

    @skipIfNotCremeUser
    def test_edit_user_not_team(self):
        "Can not edit a team with the user edit view."
        self.login()

        user = User.objects.create_user(
            username='deunan', first_name='Deunan', last_name='Knut',
            email='d.knut@eswat.ol', password='uselesspw',
        )
        team = self._create_team('Teamee', [user])

        url = self._build_edit_url(team.id)
        self.assertGET404(url)
        self.assertPOST404(url)

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_edit_user_credentials(self):
        "Logged as regular user."
        user = self.login_not_as_superuser()

        role1 = UserRole(name='Master')
        role1.allowed_apps = ['persons']
        role1.save()
        SetCredentials.objects.create(
            role=role1, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL,
        )
        other_user = User.objects.create(username='deunan', role=role1)

        briareos = Contact.objects.create(
            user=user, first_name='Briareos', last_name='Hecatonchires',
        )
        self.assertTrue(other_user.has_perm_to_view(briareos))

        url = self._build_edit_url(other_user.id)
        self.assertGET403(url)

        role2 = UserRole.objects.create(name='Slave')
        self.assertPOST403(
            url,
            data={
                'first_name': 'Deunan',
                'last_name':  'Knut',
                'email':      'd.knut@eswat.ol',
                'role':       role2.id,
            },
        )

    @skipIfNotCremeUser
    def test_edit_user_empty_role(self):
        "Common user without role."
        self.login()

        other_user = self.other_user
        role = other_user.role
        self.assertIsNotNone(role)

        url = self._build_edit_url(other_user.id)
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, follow=True, data={'role': ''}))

        other_user = self.refresh(other_user)
        self.assertIsNone(other_user.role)
        self.assertTrue(other_user.is_superuser)

    @skipIfNotCremeUser
    def test_edit_staff_user01(self):
        "Even a super-user cannot edit a staff user."
        self.login()

        user = User.objects.create_user(
            username='deunan', first_name='Deunan', last_name='Knut',
            email='d.knut@eswat.ol', password='uselesspw',
            is_staff=True,
        )
        self.assertGET404(self._build_edit_url(user.id))

    @skipIfNotCremeUser
    def test_edit_staff_user02(self):
        "A staff-user can edit a staff user."
        self.login(is_staff=True)

        user = User.objects.create_user(
            username='deunan', first_name='Deunan', last_name='Knut',
            email='d.knut@eswat.ol', password='uselesspw',
            is_staff=True,
        )
        self.assertGET200(self._build_edit_url(user.id))

    @skipIfNotCremeUser
    def test_edit_user_unique_email01(self):
        "Unique email (amon active users)."
        self.login()
        user = User.objects.create_user(
            username='deunan', first_name='Deunan', last_name='Knut',
            email='d.knut@eswat.ol', password='uselesspw',
        )

        other_user = self.other_user

        data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': other_user.role_id,
            'email': other_user.email,  # <==
        }

        url = self._build_edit_url(user.id)
        response1 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response1, 'form', 'email',
            _('An active user with the same email address already exists.'),
        )

        # ---
        other_user.is_active = False
        other_user.save()
        self.assertNoFormError(self.client.post(url, data=data))

    @skipIfNotCremeUser
    def test_edit_user_unique_email02(self):
        "Unique email (amon active users) - self instance is excluded."
        self.login()

        other_user = self.other_user
        self.assertNoFormError(self.client.post(
            self._build_edit_url(other_user.id),
            data={
                'first_name': other_user.first_name,
                'last_name': other_user.last_name,
                'role': '',
                'email': other_user.email,  # <==
            }
        ))

    @skipIfNotCremeUser
    def test_change_password01(self):
        self.login()

        other_user = User.objects.create(username='deunan')
        url = self._build_edit_url(other_user.id, password=True)

        # GET ---
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')

        context1 = response1.context
        self.assertEqual(
            _('Change password for «{object}»').format(object=other_user),
            context1.get('title'),
        )

        with self.assertNoException():
            fields = context1['form'].fields
            old_password_f = fields['old_password']
            password1_f = fields['password_1']
            password2_f = fields['password_2']

        self.assertEqual(_('Your password'), old_password_f.label)
        self.assertEqual(
            _('New password for «{user}»').format(user=other_user),
            password1_f.label,
        )
        self.assertEqual(_('New password confirmation'), password2_f.label)

        # POST (error) ---
        new_password = 'password'
        response2 = self.assertPOST200(
            url,
            follow=True,
            data={
                'old_password': 'mismatch',
                'password_1': new_password,
                'password_2': new_password,
            },
        )
        self.assertFormError(
            response2, 'form', 'old_password',
            _('Your old password was entered incorrectly. Please enter it again.'),
        )

        # POST ---
        response3 = self.client.post(
            url,
            follow=True,
            data={
                'old_password': self.password,
                'password_1': new_password,
                'password_2': new_password,
            },
        )
        self.assertNoFormError(response3)
        self.assertTrue(self.refresh(other_user).check_password(new_password))

    @skipIfNotCremeUser
    def test_change_password02(self):
        "Not administrator."
        self.login_not_as_superuser()

        other_user = User.objects.create(username='deunan')
        url = self._build_edit_url(other_user.id, password=True)
        self.assertGET403(url)

        password = 'password'
        self.assertPOST403(
            url, data={'password_1': password, 'password_2': password},
        )

    @skipIfNotCremeUser
    def test_change_password03(self):
        self.login()

        other_user = User.objects.create(username='deunan')
        url = self._build_edit_url(other_user.id, password=True)
        self.assertGET200(url)

        password = 'password'
        response = self.client.post(
            url,
            follow=True,
            data={'password_1': password, 'password_2': password + '42'},
        )
        self.assertFormError(
            response, 'form', 'password_2', _("The two password fields didn’t match."),
        )

    @skipIfNotCremeUser
    @override_settings(AUTH_PASSWORD_VALIDATORS=[{
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    }])
    def test_change_password04(self):
        self.login()

        other_user = User.objects.create(username='deunan')
        url = self._build_edit_url(other_user.id, password=True)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            password1_f = response1.context['form'].fields['password_1']

        msg = ngettext(
            "The password must contain at least %(min_length)d character.",
            "The password must contain at least %(min_length)d characters.",
            8,
        ) % {"min_length": 8}
        self.assertHTMLEqual(f'<ul><li>{msg}</li></ul>', password1_f.help_text)

        # ---
        password = 'pass'
        response = self.assertPOST200(
            url, data={'password_1': password, 'password_2': password}
        )
        self.assertFormError(
            response, 'form', 'password_2',
            ngettext(
                'This password is too short. It must contain at least %(min_length)d character.',
                'This password is too short. It must contain at least %(min_length)d characters.',
                8
            ) % {'min_length': 8},
        )

    @skipIfNotCremeUser
    def test_change_own_password(self):
        user = self.login()

        url = self._build_edit_url(user.id, password=True)

        # GET ---
        response1 = self.assertGET200(url)

        context1 = response1.context
        self.assertEqual(_('Change your password'), context1.get('title'))

        with self.assertNoException():
            fields = context1['form'].fields
            old_password_f = fields['old_password']
            password1_f = fields['password_1']
            password2_f = fields['password_2']

        self.assertEqual(_('Your old password'), old_password_f.label)
        self.assertEqual(_('New password'), password1_f.label)
        self.assertEqual(_('New password confirmation'), password2_f.label)

        # POST (error) ---
        new_password = 'password'
        response2 = self.assertPOST200(
            url,
            follow=True,
            data={
                'old_password': 'mismatch',
                'password_1': new_password,
                'password_2': new_password,
            },
        )
        self.assertFormError(
            response2, 'form',
            field='old_password',
            errors=_('Your old password was entered incorrectly. Please enter it again.'),
        )

        # POST ---
        response3 = self.client.post(
            url,
            follow=True,
            data={
                'old_password': self.password,
                'password_1': new_password,
                'password_2': new_password,
            },
        )
        self.assertNoFormError(response3)
        self.assertTrue(self.refresh(user).check_password(new_password))

    @skipIfNotCremeUser
    def test_user_activation(self):
        self.login()
        other_user = User.objects.create(username='deunan')

        build_url = self._build_activation_url
        self.assertPOST200(build_url(other_user.id, activation=False))
        self.assertFalse(self.refresh(other_user).is_active)

        self.assertPOST200(build_url(other_user.id, activation=True))
        self.assertTrue(self.refresh(other_user).is_active)

    @skipIfNotCremeUser
    def test_user_activation_credentials(self):
        "Not superuser."
        self.login_not_as_superuser()
        other_user = User.objects.create(username='deunan')
        self.assertGET403(self._build_activation_url(other_user.id, activation=False))
        self.assertGET403(self._build_activation_url(other_user.id, activation=True))

    @skipIfNotCremeUser
    def test_user_activation_errors(self):
        "Post only & Current user."
        user = self.login()
        url = self._build_activation_url(user.id, activation=False)
        self.assertGET405(url)
        self.assertPOST409(url)

    @skipIfNotCremeUser
    def test_user_activation_staff(self):
        "User is staff."
        self.login()
        other_user = User.objects.create(username='deunan', is_staff=True)
        # self.assertPOST(400, self._build_activation_url(other_user.id, activation=True))
        # self.assertPOST(400, self._build_activation_url(other_user.id, activation=False))
        response1 = self.client.post(self._build_activation_url(other_user.id, activation=True))
        self.assertContains(response1, _("You can't activate a staff user."), status_code=409)

        response2 = self.client.post(self._build_activation_url(other_user.id, activation=False))
        self.assertContains(response2, _("You can't deactivate a staff user."), status_code=409)

    @skipIfNotCremeUser
    def test_user_activation_unique_email(self):
        "Email must remain unique among active users."
        self.login()
        other_user = self.other_user
        disabled_user = User.objects.create(
            username='deunan', email=other_user.email, is_active=False,
        )

        url = self._build_activation_url(disabled_user.id, activation=True)
        response1 = self.assertPOST409(url)
        self.assertHTMLEqual(
            '<ul class="errorlist"><li>{}</li></ul>'.format(
                _('An active user with the same email address already exists.')
            ),
            response1.content.decode(),
        )

        # ---
        other_user.is_active = False
        other_user.save()
        self.assertPOST200(url)

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_create_team01(self):
        self.login()

        url = self.ADD_TEAM_URL
        context = self.assertGET200(url).context
        self.assertEqual(_('New team'),      context.get('title'))
        self.assertEqual(_('Save the team'), context.get('submit_label'))

        create_user = partial(User.objects.create_user, password='uselesspw')
        user01 = create_user(
            username='Shogun',
            first_name='Choji', last_name='Ochiai', email='shogun@century.jp',
        )
        user02 = create_user(
            username='Yukiji',
            first_name='Yukiji', last_name='Setoguchi', email='yukiji@century.jp',
        )

        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={'username': 'Team-A', 'teammates': [user01.id, user02.id]},
        ))

        teams = User.objects.filter(is_team=True)
        self.assertEqual(1, len(teams))

        team = teams[0]
        self.assertFalse(team.is_superuser)
        self.assertEqual('', team.first_name)
        self.assertEqual('', team.last_name)
        self.assertEqual('', team.email)

        teammates = team.teammates
        self.assertEqual(2, len(teammates))
        self.assertIn(user01.id, teammates)
        self.assertIn(user02.id, teammates)

        self.assertFalse(Contact.objects.filter(is_user=team))

        # Beware of email uniqueness not check (BUG)
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={'username': 'Team-B', 'teammates': [user02.id]},
        ))

    @skipIfNotCremeUser
    def test_create_team02(self):
        self.login_not_as_superuser()

        url = self.ADD_TEAM_URL
        self.assertGET403(url)

        user01 = User.objects.create_user(
            username='Shogun', first_name='Choji', last_name='Ochiai',
            email='shogun@century.jp', password='uselesspw',
        )
        self.assertPOST403(
            url, data={'username':  'Team-A', 'teammates': [user01.id]},
        )

    def _create_team(self, name, teammates):
        team = User.objects.create(username=name, is_team=True, role=None)
        team.teammates = teammates

        return team

    @skipIfNotCremeUser
    def test_edit_team01(self):
        self.login()

        role = UserRole(name='Role')
        role.allowed_apps = ['creme_core']
        role.save()
        SetCredentials.objects.create(
            role=role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_OWN,
        )

        def create_user(name, email):
            user = User.objects.create_user(
                username=name, email=email, first_name=name, last_name='Endou',
                password='uselesspw',
            )
            user.role = role
            user.save()

            return user

        user01 = create_user('Maruo',   'maruo@century.jp')
        user02 = create_user('Yokiji',  'yokiji@century.jp')
        user03 = create_user('Koizumi', 'koizumi@century.jp')

        self.assertGET404(reverse('creme_config__edit_team', args=(user01.id,)))

        teamname = 'Teamee'
        team = self._create_team(teamname, [user01, user02])

        entity = CremeEntity.objects.create(user=team)
        self.assertTrue(user01.has_perm_to_view(entity))
        self.assertTrue(user02.has_perm_to_view(entity))
        self.assertFalse(user03.has_perm_to_view(entity))

        url = reverse('creme_config__edit_team', args=(team.id,))
        self.assertGET200(url)

        teamname += '_edited'
        response = self.client.post(
            url,
            follow=True,
            data={
                'username':  teamname,
                'teammates': [user02.id, user03.id],
            },
        )
        self.assertNoFormError(response)

        team = self.refresh(team)
        self.assertEqual(teamname, team.username)

        teammates = team.teammates
        self.assertEqual(2, len(teammates))
        self.assertIn(user02.id, teammates)
        self.assertIn(user03.id, teammates)
        self.assertNotIn(user01.id, teammates)

        # Credentials have been updated ?
        entity = CremeEntity.objects.get(pk=entity.id)
        self.assertFalse(self.refresh(user01).has_perm_to_view(entity))
        self.assertTrue(self.refresh(user02).has_perm_to_view(entity))
        self.assertTrue(self.refresh(user03).has_perm_to_view(entity))

    @skipIfNotCremeUser
    def test_edit_team02(self):
        self.login_not_as_superuser()

        create_user = partial(User.objects.create_user, password='uselesspw')
        user01 = create_user(
            username='Shogun', first_name='Choji', last_name='Ochiai',
            email='shogun@century.jp',
        )
        user02 = create_user(
            username='Yukiji', first_name='Yukiji', last_name='Setoguchi',
            email='yukiji@century.jp',
        )

        teamname = 'Teamee'
        team = self._create_team(teamname, [user01, user02])

        url = reverse('creme_config__edit_team', args=(team.id,))
        self.assertGET403(url)
        self.assertPOST403(
            url, data={'username': teamname, 'teammates': [user02.id]},
        )

    @skipIfNotCremeUser
    def test_delete_team01(self):
        self.login()

        user = User.objects.create_user(
            username='Shogun',
            first_name='Choji', last_name='Ochiai',
            email='shogun@century.jp', password='uselesspw',
        )
        team = self._create_team('Teamee', [])

        url = self._build_delete_url(team)
        self.assertGET200(url)
        self.assertPOST200(url, data={'to_user': user.id})
        self.assertDoesNotExist(team)

    @skipIfNotCremeUser
    def test_delete_team02(self):
        self.login()

        user = User.objects.create_user(
            username='Shogun',
            first_name='Choji', last_name='Ochiai',
            email='shogun@century.jp', password='uselesspw',
        )
        team1 = self._create_team('Teamee', [user])
        team2 = self._create_team('Teamee2', [user])

        ce = CremeEntity.objects.create(user=team1)

        url = self._build_delete_url(team1)
        self.assertGET200(url)
        self.assertPOST200(url, data={'to_user': team2.id})
        self.assertDoesNotExist(team1)

        ce = self.assertStillExists(ce)
        self.assertEqual(team2, ce.user)

    @skipIfNotCremeUser
    def test_delete_team03(self):
        self.login()

        team = self._create_team('Teamee', [])
        CremeEntity.objects.create(user=team)

        self.assertPOST200(self._build_delete_url(team), data={'to_user': self.user.id})
        self.assertDoesNotExist(team)

    @skipIfNotCremeUser
    def test_delete_team04(self):
        self.login_not_as_superuser()

        user = User.objects.create_user(
            username='Shogun',
            first_name='Choji', last_name='Ochiai', email='shogun@century.jp',
            # password='uselesspw',
        )
        team = self._create_team('Teamee', [])

        url = self._build_delete_url(team)
        self.assertGET403(url)
        self.assertPOST403(url, data={'to_user': user.id})

    @skipIfNotCremeUser
    def test_delete_superuser(self):
        "Delete view can delete a superuser if at least one remains."
        user = self.login()
        root = self.get_object_or_fail(User, username='root')

        self.assertEqual(2, User.objects.filter(is_superuser=True).count())
        self.assertEqual(1, User.objects.exclude(id=user.id).filter(is_superuser=True).count())

        url = self._build_delete_url(root)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/delete-popup.html')

        context = response.context
        self.assertEqual(
            _('Delete «{object}» and assign his entities to user').format(object=root),
            context.get('title'),
        )
        self.assertEqual(_('Delete the user'), context.get('submit_label'))

        # ---
        self.assertPOST200(url, {'to_user': user.id})
        self.assertEqual(1, User.objects.filter(is_superuser=True).count())
        self.assertDoesNotExist(root)

    @skipIfNotCremeUser
    def test_delete_regular_user(self):
        "Delete view can delete any normal user."
        user = self.login()
        self.assertTrue(user.is_superuser)

        other_user = self.other_user
        self.assertFalse(other_user.is_superuser)

        ce = CremeEntity.objects.create(user=other_user)

        url = self._build_delete_url(other_user)
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, {'to_user': user.id}))
        self.assertDoesNotExist(other_user)

        ce = self.assertStillExists(ce)
        self.assertEqual(user, ce.user)

    @skipIfNotCremeUser
    def test_delete_last_superuser(self):
        "Delete view can not delete the last superuser."
        self.client.login(username='root', password='root')

        superusers = User.objects.filter(is_superuser=True)
        self.assertEqual(1, len(superusers))

        user = superusers[0]

        url = self._build_delete_url(user)
        self.assertGET409(url)
        self.assertPOST409(url, {'to_user': user.id})

        self.assertStillExists(user)

    @skipIfNotCremeUser
    def test_delete_staff_user(self):
        "Delete view can not delete a staff user."
        user = self.login()
        hybird = User.objects.create(username='hybird', is_staff=True)

        url = self._build_delete_url(hybird)
        self.assertGET(404, url)
        self.assertPOST(404, url, {'to_user': user.id})

    @skipIfNotCremeUser
    def test_delete_user_during_transfer(self):
        "Delete view is protected by a lock."
        user = self.login()
        root = self.get_object_or_fail(User, username='root')

        superusers = [*User.objects.filter(is_superuser=True)]
        self.assertEqual(2, len(superusers))
        self.assertIn(user, superusers)

        Mutex.get_n_lock('creme_config-user_transfer')

        url = self._build_delete_url(root)
        self.assertGET200(url)
        self.assertPOST(400, url, {'to_user': user.id})

        if 'postgresql' not in settings.DATABASES['default']['ENGINE']:
            # NB: PostgreSQL cancels all remaining queries after the error...
            self.assertEqual(2, User.objects.filter(is_superuser=True).count())

    @skipIfNotCremeUser
    def test_delete_user_errors(self):
        "Validation errors."
        user = self.login()
        root = User.objects.get(username='root')

        count = User.objects.count()
        self.assertGreater(count, 1)

        url = self._build_delete_url(root)
        self.assertGET200(url)

        response = self.assertPOST200(url)  # No data
        self.assertFormError(response, 'form', 'to_user', _('This field is required.'))
        self.assertEqual(count, User.objects.count())

        # Cannot move entities to deleted user
        response = self.assertPOST200(url, {'to_user': root.id})
        self.assertFormError(
            response, 'form', 'to_user',
            _('Select a valid choice. That choice is not one of the available choices.'),
        )
        self.assertStillExists(user)

    @skipIfNotCremeUser
    def test_delete_user_credentials(self):
        "Only superusers are allowed."
        user = self.login_not_as_superuser()

        url = self._build_delete_url(self.other_user)
        self.assertGET403(url)
        self.assertPOST403(url, data={'to_user': user.id})

    def test_brick_hide_inactive_user(self):
        user = self.login()

        def get_state():
            return BrickState.objects.get_for_brick_id(user=user, brick_id=UsersBrick.id_)

        self.assertIsNone(get_state().pk)

        url = reverse('creme_config__users_brick_hide_inactive')
        self.assertGET405(url)

        # ---
        self.assertPOST200(url, data={'value': 'true'})
        state1 = get_state()
        self.assertIsNotNone(state1.pk)
        self.assertIs(
            state1.get_extra_data(constants.BRICK_STATE_HIDE_INACTIVE_USERS),
            True,
        )

        # ---
        self.assertPOST200(url, data={'value': '0'})
        self.assertIs(
            get_state().get_extra_data(constants.BRICK_STATE_HIDE_INACTIVE_USERS),
            False,
        )


class UserSettingsTestCase(CremeTestCase, BrickTestCaseMixin):
    def setUp(self):
        super().setUp()
        self.login()
        self._registered_skey = []

    def tearDown(self):
        super().tearDown()
        user_setting_key_registry.unregister(*self._registered_skey)

    def _register_key(self, *skeys):
        user_setting_key_registry.register(*skeys)
        self._registered_skey.extend(skeys)

    def test_user_settings(self):
        response = self.assertGET200(reverse('creme_config__user_settings'))
        self.assertTemplateUsed(response, 'creme_config/user_settings.html')

        get = response.context.get
        self.assertEqual(reverse('creme_core__reload_bricks'), get('bricks_reload_url'))

        theme_form = get('theme_form')
        self.assertIsInstance(theme_form, str)
        self.assertIn('<span><label for="id_theme">', theme_form)

        tz_form = get('tz_form')
        self.assertIsInstance(tz_form, str)
        self.assertIn('<span><label for="id_time_zone">', tz_form)

        self.assertIsList(get('apps_usersettings_bricks'))  # TODO: improve

        doc = self.get_html_tree(response.content)
        self.get_brick_node(doc, brick=BrickMypageLocationsBrick)

    @override_settings(THEMES=[
        ('icecream',  'Ice cream'),
        ('chantilly', 'Chantilly'),
    ])
    def test_change_theme(self):
        user = self.user
        self.assertEqual(settings.THEMES[0][0], user.theme)

        url = reverse('creme_config__set_user_theme')

        def post(theme):
            self.assertPOST200(url, data={'theme': theme})

            self.assertEqual(theme, self.refresh(user).theme)

        post('chantilly')
        post('icecream')

    def test_change_timezone(self):
        user = self.user
        self.assertEqual(settings.TIME_ZONE, user.time_zone)

        called = False
        activated_tz = None

        def fake_activate(tz):
            nonlocal called, activated_tz
            called = True
            activated_tz = tz

        original_activate = django_tz.activate
        django_tz.activate = fake_activate

        try:
            self.client.get('/')
            self.assertFalse(called)

            url = reverse('creme_config__set_user_timezone')

            def assertSelected(selected_tz):
                response = self.assertGET200(url)

                with self.assertNoException():
                    form_str = response.json()['form']

                for line in form_str.split('\n'):
                    if selected_tz in line:
                        option = line
                        break
                else:
                    self.fail('Option not found')

                self.assertEqual(1, option.count('<option '))
                self.assertIn('selected', option)

            def change_tz(tz):
                nonlocal called

                self.assertPOST200(url, data={'time_zone': tz})

                self.assertEqual(tz, self.refresh(user).time_zone)

                self.client.get('/')
                self.assertTrue(called)
                self.assertEqual(tz, activated_tz)

                called = False

            TIME_ZONE = settings.TIME_ZONE
            time_zones = [
                tz
                for tz in ('Asia/Tokyo', 'US/Eastern', 'Europe/Paris')
                if tz != TIME_ZONE
            ]

            assertSelected(TIME_ZONE)

            tz = time_zones[0]
            change_tz(tz)
            assertSelected(tz)

            change_tz(time_zones[1])
        finally:
            django_tz.activate = original_activate

    @override_settings(LANGUAGES=[
        ('en', 'English'),
        ('fr', 'Français'),
    ])
    def test_change_language(self):
        user = self.user
        self.assertEqual('', user.language)

        post_url = reverse('creme_config__set_user_language')
        content_url = reverse('creme_config__user_settings')

        def post(language, test_content=True):
            self.assertPOST200(post_url, data={'language': language})
            self.assertEqual(language, self.refresh(user).language)

            if test_content:
                response = self.assertGET200(content_url)
                self.assertEqual(language, response['Content-Language'])

        # Fixed language ---
        post('en')
        post('fr')

        # From browser ----
        post('', False)

        for language in ('en', 'fr'):
            response = self.assertGET200(content_url, HTTP_ACCEPT_LANGUAGE=language)
            self.assertEqual(language, response['Content-Language'])

    @staticmethod
    def _build_edit_user_svalue_url(setting_key):
        return reverse('creme_config__edit_user_setting', args=(setting_key.id,))

    def test_edit_user_setting_value01(self):
        user = self.user
        sk = UserSettingKey(
            'creme_config-test_edit_user_setting_value01',
            description='Page displayed',
            app_label='creme_core',
            type=SettingKey.BOOL, hidden=False,
        )
        self.assertIsNone(user.settings.get(sk))

        url = self._build_edit_user_svalue_url(sk)
        self.assertGET404(url)

        # ---
        self._register_key(sk)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit «{key}»').format(key=sk.description), context.get('title'))
        # self.assertEqual(_('Save the modifications'), context.get('submit_label'))  TODO

        # ---
        response = self.client.post(url, data={'value': 'on'})
        self.assertNoFormError(response)

        self.assertIs(True, self.refresh(user).settings.get(sk))

    def test_edit_user_setting_value02(self):
        "hidden=True => error."
        sk = UserSettingKey(
            'creme_config-test_edit_user_setting_value02',
            description='Page displayed',
            app_label='creme_core',
            type=SettingKey.BOOL, hidden=True,
        )

        self._register_key(sk)
        self.assertGET409(self._build_edit_user_svalue_url(sk))

    def test_edit_user_setting_value03(self):
        "Not blank + STRING."
        sk = UserSettingKey(
            'creme_config-test_edit_user_setting_value03',
            description='API key',
            app_label='creme_core',
            type=SettingKey.STRING,
        )
        self.assertFalse(sk.blank)
        self._register_key(sk)

        response = self.client.post(self._build_edit_user_svalue_url(sk), data={'value': ''})
        self.assertFormError(response, 'form', 'value', _('This field is required.'))

    def test_edit_user_setting_value04(self):
        "Blank + STRING."
        user = self.user
        sk = UserSettingKey(
            'creme_config-test_edit_user_setting_value04',
            description='API key',
            app_label='creme_core',
            type=SettingKey.STRING,
            blank=True,
        )
        self.assertIsNone(user.settings.get(sk))

        url = self._build_edit_user_svalue_url(sk)
        self.assertGET404(url)

        self._register_key(sk)
        self.assertIsNone(user.settings.get(sk))
        self.assertGET200(url)

        response = self.client.post(url, data={'value': ''})
        self.assertNoFormError(response)
        self.assertEqual('', self.refresh(user).settings.get(sk))

        self.assertGET200(url)

    def test_edit_user_setting_value05(self):
        "Blank + INT."
        user = self.user
        sk = UserSettingKey(
            'creme_config-test_edit_user_setting_value05',
            description='API key',
            app_label='creme_core',
            type=SettingKey.INT,
            blank=True,
        )
        self._register_key(sk)

        usettings = user.settings
        with usettings:
            usettings[sk] = 123

        url = self._build_edit_user_svalue_url(sk)
        response = self.assertGET200(url)

        with self.assertNoException():
            value_f = response.context['form'].fields['value']

        self.assertEqual(123, value_f.initial)

        # ---
        response = self.client.post(url)
        self.assertNoFormError(response)
        self.assertIsNone(self.refresh(user).settings.get(sk))
