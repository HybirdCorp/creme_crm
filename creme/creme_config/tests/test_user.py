from json import dumps as json_dump
from unittest import skipIf

from django.conf import settings
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone as django_tz
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from parameterized import parameterized

from creme.creme_core import get_world_settings_model
from creme.creme_core.constants import ROOT_PASSWORD, UUID_CHANNEL_ADMIN
from creme.creme_core.core.setting_key import (
    SettingKey,
    SettingKeyRegistry,
    UserSettingKey,
    user_setting_key_registry,
)
from creme.creme_core.models import BrickState, CremeEntity
from creme.creme_core.models import CremeUser as User
from creme.creme_core.models import (
    Mutex,
    Notification,
    NotificationChannel,
    RelationType,
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
from ..auth import user_config_perm
from ..bricks import (
    BrickMypageLocationsBrick,
    NotificationChannelConfigItemsBrick,
    TeamsBrick,
    UsersBrick,
    UserSettingValuesBrick,
)
from ..notification import PasswordChangeContent, RoleSwitchContent


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

    def login_with_user_perm(self):
        return self.login_as_standard(special_permissions=[user_config_perm])

    # def login_as_config_admin(self):
    #     apps = ('creme_config',)
    #     return self.login_as_standard(allowed_apps=apps, admin_4_apps=apps)
    def login_without_user_perm(self):
        return self.login_as_standard(allowed_apps=('creme_config',))

    @skipIfNotCremeUser
    # @parameterized.expand([False, True])
    # def test_portal(self, superuser):
    def test_portal(self):
        # user = (
        #     self.login_as_super() if superuser else
        #     self.login_as_standard(admin_4_apps=['creme_config'])
        # )
        user = self.login_with_user_perm()
        User.objects.create(username='A-Team', is_team=True)
        User.objects.create(
            username='StaffMan', is_staff=True, first_name='Staff', last_name='Man',
        )

        other_user = self.create_user(index=1, is_active=False)

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

    def test_portal__forbidden(self):
        self.login_without_user_perm()
        self.assertGET403(reverse('creme_config__users'))

    def test_portal__hide_inactive(self):
        user = self.login_as_root_and_get()

        other_user = self.create_user()
        other_user.is_active = False
        other_user.save()

        brick_id = UsersBrick.id

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

    def test_portal__display_tz(self):
        user = self.login_as_super()

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

    def test_portal__staff(self):
        user = self.login_as_super(is_staff=True)
        other_user = self.create_user(1)

        response = self.assertGET200(reverse('creme_config__users'))
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=UsersBrick,
        )

        usernames = {
            n.text
            for n in brick_node.findall('.//td[@class="user-username"]')
        }
        self.assertIn(user.username, usernames)
        self.assertIn(other_user.username, usernames)

    @parameterized.expand([
        ('username', 'user-username'),
        ('last_name', 'user-lastname'),
        ('first_name', 'user-firstname'),
    ])
    def test_portal__search__single_word(self, field_name, css_class):
        user = self.login_as_super(index=0)
        other_user = self.create_user(index=1)

        # This user has different values for fields 'first_name', 'last_name' & 'username'
        root = self.get_root_user()

        field_value = getattr(root, field_name)
        response = self.assertGET200(
            reverse('creme_core__reload_bricks'),
            data={
                'brick_id': [UsersBrick.id],
                'extra_data': json_dump({UsersBrick.id: {'search': field_value[1:4]}}),
            },
        )
        bricks_info = response.json()
        self.assertIsList(bricks_info, length=1)

        brick_info = bricks_info[0]
        self.assertIsList(brick_info, length=2)
        self.assertEqual(UsersBrick.id, brick_info[0])

        brick_node = self.get_brick_node(
            self.get_html_tree(brick_info[1]),
            UsersBrick.id,
        )
        self.assertCountEqual(
            [field_value],
            [n.text for n in brick_node.findall(f'.//td[@class="{css_class}"]')],
        )

        build_url = self._build_edit_url
        self.assertBrickHasAction(
            brick_node, url=build_url(root.id), action_type='edit',
        )
        self.assertBrickHasNoAction(brick_node, url=build_url(user.id))
        self.assertBrickHasNoAction(brick_node, url=build_url(other_user.id))

    def test_portal__search__multiple_words(self):
        "No double quote => words are separated."
        user = self.login_as_super(index=0)
        other_user = self.create_user(index=1)
        root = self.get_root_user()

        response = self.assertGET200(
            reverse('creme_core__reload_bricks'),
            data={
                'brick_id': [UsersBrick.id],
                'extra_data': json_dump({
                    UsersBrick.id: {
                        'search': f'{user.username[1:4]} {other_user.last_name[1:4]}',
                    },
                }),
            },
        )
        bricks_info = response.json()
        self.assertIsList(bricks_info, length=1)

        brick_info = bricks_info[0]
        self.assertIsList(brick_info, length=2)

        brick_node = self.get_brick_node(
            self.get_html_tree(brick_info[1]), UsersBrick.id,
        )

        build_url = self._build_edit_url
        self.assertBrickHasAction(
            brick_node, url=build_url(user.id), action_type='edit',
        )
        self.assertBrickHasAction(
            brick_node, url=build_url(other_user.id), action_type='edit',
        )
        self.assertBrickHasNoAction(brick_node, url=build_url(root.id))

    def test_portal__search__multiple_words__double_quote(self):
        "Double quote => words are grouped."
        user = self.login_as_super(index=0)

        user.last_name = 'De La Sainte Grenade'
        user.save()

        other_user = self.create_user(index=1, last_name='Grenade')

        response = self.assertGET200(
            reverse('creme_core__reload_bricks'),
            data={
                'brick_id': [UsersBrick.id],
                'extra_data': json_dump({
                    UsersBrick.id: {
                        'search': '"Sainte Grena"',
                    },
                }),
            },
        )
        bricks_info = response.json()
        self.assertIsList(bricks_info, length=1)

        brick_info = bricks_info[0]
        self.assertIsList(brick_info, length=2)

        brick_node = self.get_brick_node(
            self.get_html_tree(brick_info[1]), UsersBrick.id,
        )

        build_url = self._build_edit_url
        self.assertBrickHasAction(
            brick_node, url=build_url(user.id), action_type='edit',
        )
        self.assertBrickHasNoAction(brick_node, url=build_url(other_user.id))

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_create_user__super_user(self):
        # user = self.login_as_root_and_get()
        user = self.login_with_user_perm()

        rtype1 = self.get_object_or_fail(RelationType, id=REL_SUB_EMPLOYED_BY)
        rtype2 = self.get_object_or_fail(RelationType, id=REL_SUB_MANAGES)
        rtype3 = RelationType.objects.builder(
            id='test-subject_employee_month', predicate='is the employee of the month for',
            models=[Contact],
        ).symmetric(
            id='test-object_employee_month', predicate='has the employee of the month',
            models=[Organisation],
        ).get_or_create()[0]
        rtype4 = RelationType.objects.builder(
            id='test-subject_generic', predicate='generic as ***',
        ).symmetric(id='test-object_generic', predicate='other side').get_or_create()[0]
        internal_rtype = RelationType.objects.builder(
            id='test-subject_employee_year', predicate='is the employee of the year for',
            models=[Contact],
            is_internal=True,
        ).symmetric(
            id='test-object_employee_year', predicate='has the employee of the year',
            models=[Organisation],
        ).get_or_create()[0]
        disabled_rtype = RelationType.objects.builder(
            id='test-subject_employee_week', predicate='is the employee of the week for',
            models=[Contact],
            enabled=False,
        ).symmetric(
            id='test-object_employee_week', predicate='has the employee of week year',
            models=[Organisation],
        ).get_or_create()[0]

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
                # 'role':         '',
                'roles':         [],
                'organisation': orga.id,
                'relation':     rtype1.id,
            },
        )
        self.assertNoFormError(response)

        user = self.get_alone_element(User.objects.filter(username=username))
        self.assertTrue(user.is_superuser)
        self.assertIsNone(user.role)
        self.assertFalse(user.roles.all())
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)
        self.assertEqual('',         user.displayed_name)
        self.assertTrue(user.check_password(password))
        self.assertDatetimesAlmostEqual(now(), user.modified)

        contact = self.get_object_or_fail(
            Contact,
            is_user=user, first_name=first_name, last_name=last_name, email=email,
        )
        self.assertHaveRelation(subject=contact, type=REL_SUB_EMPLOYED_BY, object=orga)

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_create_user__regular_user(self):
        "Not superuser; special chars in username; displayed_name."
        user = self.login_as_root_and_get()
        role = self.create_role(name='Mangaka', allowed_apps=['persons'])
        self.add_credentials(role, all=['VIEW'])

        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)

        username = 'dknut@eswat.ol'
        password = 'password'
        first_name = 'Deunan'
        last_name = 'Knut'
        displayed_name = 'D3un4n'
        response = self.client.post(
            self.ADD_URL,
            follow=True,
            data={
                'username': username,

                'password_1': password,
                'password_2': password,

                'first_name':     first_name,
                'last_name':      last_name,
                'email':          username,
                'displayed_name': displayed_name,

                # 'role': role.id,
                'roles': [role.id],

                'organisation': orga.id,
                'relation':     REL_SUB_MANAGES,
            },
        )
        self.assertNoFormError(response)

        user = self.get_object_or_fail(User, username=username)
        self.assertEqual(displayed_name, user.displayed_name)
        self.assertEqual(role, user.role)
        self.assertFalse(user.is_superuser)
        self.assertListEqual([role], [*user.roles.all()])

        self.assertTrue(user.has_perm_to_view(orga))

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(user, contact.is_user)
        self.assertHaveRelation(subject=contact, type=REL_SUB_MANAGES, object=orga)

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_create_user__several_roles(self):
        user = self.login_as_root_and_get()
        role1 = self.create_role(name='Mangaka')
        role2 = self.create_role(name='Animator')  # NB: alphabetically first
        role3 = self.create_role(name='Disabled', deactivated_on=now())

        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)

        # ---
        response1 = self.assertGET200(self.ADD_URL)
        with self.assertNoException():
            roles_choices = response1.context['form'].fields['roles'].choices

        self.assertInChoices(value=role1.id, label=str(role1), choices=roles_choices)
        self.assertInChoices(value=role2.id, label=str(role2), choices=roles_choices)
        self.assertNotInChoices(value=role3.id, choices=roles_choices)

        # ---
        username = 'dknut@eswat.ol'
        password = 'password'
        self.assertNoFormError(self.client.post(
            self.ADD_URL,
            follow=True,
            data={
                'username': username,

                'password_1': password,
                'password_2': password,

                'first_name':     'Deunan',
                'last_name':      'Knut',
                'email':          username,

                'roles': [role1.id, role2.id],

                'organisation': orga.id,
                'relation':     REL_SUB_MANAGES,
            },
        ))

        user = self.get_object_or_fail(User, username=username)
        self.assertFalse(user.is_superuser)
        self.assertCountEqual([role1, role2], user.roles.all())
        self.assertEqual(role2, user.role)

    @skipIfNotCremeUser
    def test_create_user__required_fields(self):
        "First name, last name, email, organisation, relation are required."
        self.login_as_root()

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

        form = self.get_form_or_fail(response)
        msg = _('This field is required.')
        self.assertFormError(form, field='first_name',   errors=msg)
        self.assertFormError(form, field='last_name',    errors=msg)
        self.assertFormError(form, field='email',        errors=msg)
        self.assertFormError(form, field='organisation', errors=msg)
        self.assertFormError(form, field='relation',     errors=msg)

    @skipIfNotCremeUser
    def test_create_user__forbidden(self):
        "No user special perm => error."
        # user = self.login_as_config_admin()
        user = self.login_without_user_perm()

        url = self.ADD_URL
        self.assertGET403(url)

        # ---
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
    def test_create_user__wrong_username(self):
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)
        # NB: crash in MariaDB on our CI with
        #    <django.db.utils.OperationalError:
        #    (1267, "Illegal mix of collations (latin1_swedish_ci,IMPLICIT) and
        #     (utf8mb4_general_ci,COERCIBLE) for operation 'like'")>
        #    DATABASES['default]['OPTIONS'] = {
        #        'charset': 'utf8mb4', 'collation': 'utf8mb4_general_ci',
        #    }
        #    does not work
        # TODO: document charset configuration?
        # username = 'é^ǜù'
        username = 'é^#!'
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
            self.get_form_or_fail(response),
            field='username',
            errors=_(
                'Enter a valid username. This value may contain only letters, numbers, '
                'and @/./+/-/_ characters.'
            ),
        )

    @skipIfNotCremeUser
    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[{
            'NAME': 'creme.creme_core.auth.password_validation.NumericPasswordValidator',
        }],
    )
    def test_create_user__password_errors(self):
        user = self.login_as_root_and_get()
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
        response1 = self.assertPOST200(url, follow=True, data=data)
        form1 = response1.context['form']
        msg = _('This field is required.')
        self.assertFormError(form1, field='password_1', errors=msg)
        self.assertFormError(form1, field='password_2', errors=msg)

        # ---
        response2 = self.assertPOST200(
            url, follow=True, data={**data, 'password_1': 'passwd'},
        )
        self.assertFormError(
            response2.context['form'],
            field='password_2', errors=msg,
        )

        # ---
        response3 = self.assertPOST200(
            url, follow=True, data={**data, 'password_2': 'passwd'},
        )
        self.assertFormError(
            response3.context['form'],
            field='password_1', errors=msg,
        )

        # ---
        response4 = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                'password_1': 'password',
                'password_2': 'passwd',
            },
        )
        self.assertFormError(
            response4.context['form'],
            field='password_2',
            errors=_("The two password fields didn’t match."),
        )

        # ---
        response5 = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                'password_1': '123',
                'password_2': '123',
            },
        )
        self.assertFormError(
            response5.context['form'],
            field='password_2',
            errors=_('This password is entirely numeric.'),
        )

    @skipIfNotCremeUser
    def test_create_user__unique_username(self):
        user = self.login_as_root_and_get()
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
            self.get_form_or_fail(response),
            field='username',
            errors=_('A user with that username already exists.'),
        )

    @skipIfNotCremeUser
    def test_create_user__unique_username__case(self):
        "Unique username (different case)."
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)

        password = 'password'
        response = self.assertPOST200(
            self.ADD_URL,
            data={
                'username':     user.username.upper(),
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
            self.get_form_or_fail(response),
            field='username',
            errors=_('A user with that username already exists.'),
        )

    @skipIfNotCremeUser
    def test_create_user__unique_email(self):
        "Unique email (among active users)."
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)

        other_user = self.create_user()
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
            response1.context['form'],
            field='email',
            errors=_('An active user with the same email address already exists.'),
        )

        # ---
        other_user.is_active = False
        other_user.save()
        self.assertNoFormError(self.client.post(self.ADD_URL, data))

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_create_user__relationship_error(self):
        "Internal relationships are forbidden."
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Olympus', is_managed=True)
        rtype = RelationType.objects.builder(
            id='creme_config-subject_test_badrtype', predicate='Bad RType',
            models=[Contact],
            is_internal=True,  # <==
        ).symmetric(
            id='creme_config-object_test_badrtype', predicate='Bad RType sym',
            models=[Organisation],
        ).get_or_create()[0]

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
            self.get_form_or_fail(response),
            field='relation',
            errors=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
        )

    @skipIfNotCremeUser
    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[{
            'NAME': 'creme.creme_core.auth.password_validation.UserAttributeSimilarityValidator',
        }],
    )
    def test_create_user__similarity_errors(self):
        user = self.login_as_root_and_get()
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
                self.get_form_or_fail(response),
                field='password_2',
                errors=_('The password is too similar to the %(verbose_name)s.') % {
                    'verbose_name': field_verbose_name,
                },
            )

        post('username', _('Username'))
        post('first_name', _('First name'))
        post('last_name', _('Last name'))
        post('email', _('Email address'))

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_edit_user__regular_user(self):
        # user = self.login_as_root_and_get()
        user = self.login_with_user_perm()

        role1 = self.create_role(name='Master', allowed_apps=['persons'])
        self.add_credentials(role1, all=['VIEW'])

        # other_user = User.objects.create(
        #     username='deunan', first_name='??', last_name='??', email='??', role=role1,
        # )
        other_user = User.objects.create_user(
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

        with self.assertNoException():
            form = response1.context['form']
        self.assertListEqual([role1], form.initial.get('roles'))

        # ----
        first_name = 'Deunan'
        last_name = 'Knut'
        email = 'd.knut@eswat.ol'
        role2 = self.create_role(name='Soldier')
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'first_name': first_name,
                'last_name':  last_name,
                'email':      email,
                # 'role':       role2.id,
                'roles':      [role2.id],
            },
        ))

        other_user = self.refresh(other_user)
        self.assertEqual(first_name, other_user.first_name)
        self.assertEqual(last_name,  other_user.last_name)
        self.assertEqual(email,      other_user.email)
        self.assertEqual('',         other_user.displayed_name)
        self.assertListEqual([role2], [*other_user.roles.all()])
        self.assertFalse(other_user.is_superuser)

        briareos = self.refresh(briareos)  # Refresh cache
        self.assertFalse(other_user.has_perm_to_view(briareos))

        # Contact is synced
        deunan = self.refresh(deunan)
        self.assertEqual(first_name,  deunan.first_name)
        self.assertEqual(last_name,   deunan.last_name)
        self.assertEqual(email,       deunan.email)

    @skipIfNotCremeUser
    def test_edit_user__regular_user__several_roles(self):
        self.login_as_root()

        role1 = self.get_regular_role()
        role2 = self.create_role(name='Mangaka')
        role3 = self.create_role(name='Animator')

        edited_user = User.objects.create_user(
            username='deunan', first_name='Deunan', last_name='Knut',
            email='d.knut@olympus.ol',
            role=role2, roles=[role1],
        )

        url = self._build_edit_url(edited_user.id)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            initial_roles = response1.context['form'].initial['roles']
        self.assertCountEqual([role1, role2], initial_roles)

        # ----
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={
                'first_name': edited_user.first_name,
                'last_name':  edited_user.last_name,
                'email':      edited_user.email,
                'roles':      [role2.id, role3.id],
            },
        ))

        edited_user = self.refresh(edited_user)
        self.assertFalse(edited_user.is_superuser)
        self.assertCountEqual([role2, role3], [*edited_user.roles.all()])
        self.assertEqual(role2, edited_user.role)  # Previous has been kept

    @skipIfNotCremeUser
    def test_edit_user__regular_user__several_roles__deactivated(self):
        self.login_as_root()

        role1 = self.get_regular_role()
        deactivated_on = now()
        role2 = self.create_role(name='Mangaka', deactivated_on=deactivated_on)
        role3 = self.create_role(name='Animator', deactivated_on=deactivated_on)
        role4 = self.create_role(name='Musician ', deactivated_on=deactivated_on)

        edited_user = User.objects.create_user(
            username='deunan', first_name='Deunan', last_name='Knut',
            email='d.knut@olympus.ol',
            role=role2, roles=[role1, role3],
        )

        url = self._build_edit_url(edited_user.id)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            form = response1.context['form']
            roles_choices = form.fields['roles'].choices
            initial_roles = form.initial['roles']

        self.assertCountEqual([role1, role2, role3], initial_roles)
        self.assertInChoices(value=role1.id, label=role1.name, choices=roles_choices)
        self.assertInChoices(
            value=role2.id, choices=roles_choices,
            label=_('{role} [deactivated]').format(role=role2.name),
        )
        self.assertInChoices(value=role3.id, label=str(role3), choices=roles_choices)
        self.assertNotInChoices(value=role4.id, choices=roles_choices)

        # ----
        data = {
            'first_name': edited_user.first_name,
            'last_name':  edited_user.last_name,
            'email':      edited_user.email,
        }
        response2 = self.assertPOST200(url, data={**data, 'roles': [role2.id]})
        self.assertFormError(
            response2.context['form'],
            field='roles', errors=_('Select at least one enabled role.'),
        )

        # ----
        self.assertNoFormError(self.client.post(
            url, follow=True, data={**data, 'roles': [role1.id, role2.id]},
        ))

        edited_user = self.refresh(edited_user)
        self.assertFalse(edited_user.is_superuser)
        self.assertCountEqual([role1, role2], [*edited_user.roles.all()])
        self.assertEqual(role1, edited_user.role)  # Set an active role

        admin_chan = self.get_object_or_fail(NotificationChannel, uuid=UUID_CHANNEL_ADMIN)
        notif = self.get_object_or_fail(
            Notification, user=edited_user, channel=admin_chan,
        )
        self.assertEqual(RoleSwitchContent.id, notif.content_id)
        self.assertDictEqual({}, notif.content_data)

    @skipIfNotCremeUser
    def test_edit_user__superuser(self):
        self.login_as_root()

        other_user = self.create_user()

        first_name = 'Briareos'
        last_name = 'Hecatonchires'
        email = 'briareos@eswat.ol'
        displayed = 'Briareos H11s'
        self.assertNoFormError(self.client.post(
            self._build_edit_url(other_user.id),
            follow=True,
            data={
                'first_name':     first_name,
                'last_name':      last_name,
                'email':          email,
                'displayed_name': displayed,
            },
        ))

        other_user = self.refresh(other_user)
        self.assertEqual(first_name, other_user.first_name)
        self.assertEqual(last_name,  other_user.last_name)
        self.assertEqual(email,      other_user.email)
        self.assertEqual(displayed,  other_user.displayed_name)
        self.assertTrue(other_user.is_superuser)
        self.assertIsNone(other_user.role)

    @skipIfNotCremeUser
    def test_edit_user__not_team(self):
        "Can not edit a team with the user edit view."
        self.login_as_root()

        user = self.create_user()
        team = self.create_team('Teamee', user)

        url = self._build_edit_url(team.id)
        self.assertGET404(url)
        self.assertPOST404(url)

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_edit_user__credentials(self):
        "No special user perm => error."
        # user = self.login_as_config_admin()
        user = self.login_without_user_perm()

        role1 = self.create_role(name='Lieutenant', allowed_apps=['persons'])
        self.add_credentials(role1, all=['VIEW'])

        other_user = User.objects.create(username='deunan', role=role1)

        briareos = Contact.objects.create(
            user=user, first_name='Briareos', last_name='Hecatonchires',
        )
        self.assertTrue(other_user.has_perm_to_view(briareos))

        url = self._build_edit_url(other_user.id)
        self.assertGET403(url)

        role2 = self.create_role(name='General')
        self.assertPOST403(
            url,
            data={
                'first_name': 'Deunan',
                'last_name':  'Knut',
                'email':      'd.knut@eswat.ol',
                # 'role':       role2.id,
                'roles':       [role2.id],
            },
        )

    @skipIfNotCremeUser
    def test_edit_user__empty_role(self):
        "Common user without role."
        self.login_as_root()

        other_user = self.create_user(role=self.get_regular_role())

        url = self._build_edit_url(other_user.id)
        self.assertGET200(url)

        # self.assertNoFormError(self.client.post(url, follow=True, data={'role': ''}))
        self.assertNoFormError(self.client.post(url, follow=True, data={
            'first_name': other_user.first_name,
            'last_name': other_user.last_name,
            'roles': [],  # <===
        }))

        other_user = self.refresh(other_user)
        self.assertIsNone(other_user.role)
        self.assertTrue(other_user.is_superuser)
        self.assertFalse(other_user.roles.all())

    @skipIfNotCremeUser
    def test_edit_user__staff(self):
        "Even a super-user cannot edit a staff user."
        self.login_as_root()

        user = self.create_user(is_staff=True)
        self.assertGET404(self._build_edit_url(user.id))

    @skipIfNotCremeUser
    def test_edit_user__staff_logged(self):
        "A staff-user can edit a staff user."
        self.login_as_super(is_staff=True)

        user = self.create_user(index=1, is_staff=True)
        self.assertGET200(self._build_edit_url(user.id))

    @skipIfNotCremeUser
    def test_edit_user__unique_email(self):
        "Unique email (among active users)."
        self.login_as_root()
        user = self.create_user(0)
        other_user = self.create_user(1)

        data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': other_user.email,  # <==
        }

        url = self._build_edit_url(user.id)
        response1 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response1.context['form'],
            field='email',
            errors=_('An active user with the same email address already exists.'),
        )

        # ---
        other_user.is_active = False
        other_user.save()
        self.assertNoFormError(self.client.post(url, data=data))

    @skipIfNotCremeUser
    def test_edit_user__unique_email__self_excluded(self):
        "Unique email (among active users) - self instance is excluded."
        self.login_as_root()

        other_user = self.create_user()
        self.assertNoFormError(self.client.post(
            self._build_edit_url(other_user.id),
            data={
                'first_name': other_user.first_name,
                'last_name': other_user.last_name,
                # 'role': '',
                'roles': [],
                'email': other_user.email,  # <==
            }
        ))

    @skipIfNotCremeUser
    def test_edit_user__super_to_regular(self):
        "Transform into regular user (bug-fix)."
        self.login_as_root()

        other_user = self.create_user()
        self.assertTrue(other_user.is_superuser)
        self.assertIsNone(other_user.role)

        role = self.create_role(name='Basic')
        self.assertNoFormError(self.client.post(
            self._build_edit_url(other_user.id),
            data={
                'first_name': other_user.first_name,
                'last_name': other_user.last_name,
                # 'role': role.id,
                'roles': [role.id],
                'email': other_user.email,
            },
        ))

        other_user = self.refresh(other_user)
        self.assertFalse(other_user.is_superuser)
        self.assertEqual(role, other_user.role)
        self.assertListEqual([role], [*other_user.roles.all()])

    @skipIfNotCremeUser
    def test_change_password(self):
        # self.login_as_root()
        self.login_with_user_perm()

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
            response2.context['form'],
            field='old_password',
            errors=_('Your old password was entered incorrectly. Please enter it again.'),
        )

        admin_chan = self.get_object_or_fail(NotificationChannel, uuid=UUID_CHANNEL_ADMIN)
        self.assertFalse(Notification.objects.filter(
            user=other_user, channel=admin_chan,
        ))

        # POST ---
        response3 = self.client.post(
            url,
            follow=True,
            data={
                # 'old_password': ROOT_PASSWORD,
                'old_password': self.USER_PASSWORD,
                'password_1': new_password,
                'password_2': new_password,
            },
        )
        self.assertNoFormError(response3)
        self.assertTrue(self.refresh(other_user).check_password(new_password))

        notif = self.get_object_or_fail(
            Notification, user=other_user, channel=admin_chan,
        )
        self.assertEqual(PasswordChangeContent.id, notif.content_id)
        self.assertDictEqual({}, notif.content_data)

        content = notif.content
        self.assertEqual(
            _('Password change'),
            content.get_subject(user=other_user),
        )
        body = _('Your password has been changed by an administrator.')
        self.assertEqual(body, content.get_body(user=other_user))
        self.assertEqual(body, content.get_html_body(user=other_user))

    @skipIfNotCremeUser
    def test_change_password__forbidden(self):
        "No special user perm => error."
        # self.login_as_config_admin()
        self.login_without_user_perm()

        other_user = User.objects.create(username='deunan')
        url = self._build_edit_url(other_user.id, password=True)
        self.assertGET403(url)

        password = 'password'
        self.assertPOST403(
            url, data={'password_1': password, 'password_2': password},
        )

    @skipIfNotCremeUser
    def test_change_password__mismatch(self):
        self.login_as_root()

        other_user = User.objects.create(username='deunan')
        url = self._build_edit_url(other_user.id, password=True)
        self.assertGET200(url)

        # ---
        password = 'password'
        response = self.client.post(
            url,
            follow=True,
            data={'password_1': password, 'password_2': password + '42'},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='password_2',
            errors=_("The two password fields didn’t match."),
        )

    @skipIfNotCremeUser
    @override_settings(AUTH_PASSWORD_VALIDATORS=[{
        'NAME': 'creme.creme_core.auth.password_validation.MinimumLengthValidator',
    }])
    def test_change_password__strength(self):
        self.login_as_root()

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
            self.get_form_or_fail(response),
            field='password_2',
            errors=ngettext(
                'This password is too short. It must contain at least %d character.',
                'This password is too short. It must contain at least %d characters.',
                8
            ) % (8,),
        )

    @skipIfNotCremeUser
    def test_change_own_password(self):
        user = self.login_as_root_and_get()

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
            response2.context['form'],
            field='old_password',
            errors=_('Your old password was entered incorrectly. Please enter it again.'),
        )

        # POST ---
        response3 = self.client.post(
            url,
            follow=True,
            data={
                'old_password': ROOT_PASSWORD,
                'password_1': new_password,
                'password_2': new_password,
            },
        )
        self.assertNoFormError(response3)
        self.assertTrue(self.refresh(user).check_password(new_password))

        self.assertFalse(
            Notification.objects.filter(user=user, channel__uuid=UUID_CHANNEL_ADMIN)
        )

    @skipIfNotCremeUser
    def test_user_activation(self):
        # self.login_as_root()
        self.login_with_user_perm()

        other_user = self.create_user(index=1)
        self.assertIs(other_user.is_active, True)
        self.assertIsNone(other_user.deactivated_on)

        # ---
        build_url = self._build_activation_url
        self.assertPOST200(build_url(other_user.id, activation=False))
        other_user = self.refresh(other_user)
        self.assertFalse(other_user.is_active)
        self.assertDatetimesAlmostEqual(other_user.deactivated_on, now())

        # ---
        self.assertPOST200(build_url(other_user.id, activation=True))
        other_user = self.refresh(other_user)
        self.assertTrue(other_user.is_active)
        self.assertIsNone(other_user.deactivated_on)

    @skipIfNotCremeUser
    def test_user_activation__forbidden(self):
        "No user special perm => error."
        # self.login_as_config_admin()
        self.login_without_user_perm()
        other_user = User.objects.create(username='deunan')
        self.assertPOST403(self._build_activation_url(other_user.id, activation=False))
        self.assertPOST403(self._build_activation_url(other_user.id, activation=True))

    @skipIfNotCremeUser
    def test_user_activation__errors(self):
        "Post only & Current user."
        user = self.login_as_super()
        url = self._build_activation_url(user.id, activation=False)
        self.assertGET405(url)
        self.assertPOST409(url)

    @skipIfNotCremeUser
    def test_user_activation__staff(self):
        "User is staff."
        self.login_as_root()
        other_user = User.objects.create(username='deunan', is_staff=True)
        response1 = self.client.post(self._build_activation_url(other_user.id, activation=True))
        self.assertContains(response1, _("You can't activate a staff user."), status_code=409)

        response2 = self.client.post(self._build_activation_url(other_user.id, activation=False))
        self.assertContains(response2, _("You can't deactivate a staff user."), status_code=409)

    @skipIfNotCremeUser
    def test_user_activation__unique_email(self):
        "Email must remain unique among active users."
        self.login_as_root()
        other_user = self.create_user(0)
        disabled_user = self.create_user(index=1, email=other_user.email, is_active=False)

        url = self._build_activation_url(disabled_user.id, activation=True)
        response1 = self.assertPOST409(url)
        self.assertHTMLEqual(
            '<ul class="errorlist"><li>{}</li></ul>'.format(
                _('An active user with the same email address already exists.')
            ),
            response1.text,
        )

        # ---
        other_user.is_active = False
        other_user.save()
        self.assertPOST200(url)

    @skipIfNotCremeUser
    @skipIfCustomContact
    def test_create_team(self):
        # self.login_as_root()
        self.login_with_user_perm()

        url = self.ADD_TEAM_URL
        context = self.assertGET200(url).context
        self.assertEqual(_('New team'),      context.get('title'))
        self.assertEqual(_('Save the team'), context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields

        self.assertIn('username', fields)
        self.assertNotIn('first_name',     fields)
        self.assertNotIn('last_name',      fields)
        self.assertNotIn('email',          fields)
        self.assertNotIn('displayed_name', fields)

        # ---
        user1 = self.create_user(index=1)
        user2 = self.create_user(index=2)

        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={'username': 'Team-A', 'teammates': [user1.id, user2.id]},
        ))

        team = self.get_alone_element(User.objects.filter(is_team=True))
        self.assertFalse(team.is_superuser)
        self.assertEqual('', team.first_name)
        self.assertEqual('', team.last_name)
        self.assertEqual('', team.email)

        teammates = team.teammates
        self.assertEqual(2, len(teammates))
        self.assertIn(user1.id, teammates)
        self.assertIn(user2.id, teammates)

        self.assertFalse(Contact.objects.filter(is_user=team))

        # Beware of email uniqueness not check (BUG)
        self.assertNoFormError(self.client.post(
            url,
            follow=True,
            data={'username': 'Team-B', 'teammates': [user2.id]},
        ))

    @skipIfNotCremeUser
    def test_create_team__forbidden(self):
        # self.login_as_config_admin()
        self.login_without_user_perm()

        url = self.ADD_TEAM_URL
        self.assertGET403(url)

        user = self.create_user(index=1)
        self.assertPOST403(
            url, data={'username':  'Team-A', 'teammates': [user.id]},
        )

    @skipIfNotCremeUser
    def test_edit_team(self):
        # self.login_as_root()
        self.login_with_user_perm()

        role = self.create_role(allowed_apps=['creme_core'])
        self.add_credentials(role, own=['VIEW'])

        user1 = self.create_user(1, role=role)
        user2 = self.create_user(2, role=role)
        user3 = self.create_user(3, role=role)

        self.assertGET404(reverse('creme_config__edit_team', args=(user1.id,)))

        team_name = 'Teamee'
        team = self.create_team(team_name, user1, user2)

        entity = CremeEntity.objects.create(user=team)
        self.assertTrue(user1.has_perm_to_view(entity))
        self.assertTrue(user2.has_perm_to_view(entity))
        self.assertFalse(user3.has_perm_to_view(entity))

        url = reverse('creme_config__edit_team', args=(team.id,))
        self.assertGET200(url)

        team_name += '_edited'
        response = self.client.post(
            url,
            follow=True,
            data={
                'username':  team_name,
                'teammates': [user2.id, user3.id],
            },
        )
        self.assertNoFormError(response)

        team = self.refresh(team)
        self.assertEqual(team_name, team.username)

        teammates = team.teammates
        self.assertEqual(2, len(teammates))
        self.assertIn(user2.id, teammates)
        self.assertIn(user3.id, teammates)
        self.assertNotIn(user1.id, teammates)

        # Credentials have been updated ?
        entity = CremeEntity.objects.get(pk=entity.id)
        self.assertFalse(self.refresh(user1).has_perm_to_view(entity))
        self.assertTrue(self.refresh(user2).has_perm_to_view(entity))
        self.assertTrue(self.refresh(user3).has_perm_to_view(entity))

    @skipIfNotCremeUser
    def test_edit_team__forbidden(self):
        # self.login_as_config_admin()
        self.login_without_user_perm()

        user1 = self.create_user(index=1)
        user2 = self.create_user(index=2)

        teamname = 'Teamee'
        team = self.create_team(teamname, user1, user2)

        url = reverse('creme_config__edit_team', args=(team.id,))
        self.assertGET403(url)
        self.assertPOST403(
            url, data={'username': teamname, 'teammates': [user2.id]},
        )

    @skipIfNotCremeUser
    def test_delete_team__transfer_to_user(self):
        # self.login_as_root()
        self.login_with_user_perm()

        user = self.create_user(index=1)
        team = self.create_team('Teamee')

        url = self._build_delete_url(team)
        self.assertGET200(url)
        self.assertPOST200(url, data={'to_user': user.id})
        self.assertDoesNotExist(team)

    @skipIfNotCremeUser
    def test_delete_team__transfer_to_team(self):
        self.login_as_root()

        user = self.create_user()
        team1 = self.create_team('Teamee', user)
        team2 = self.create_team('Teamee2', user)

        ce = CremeEntity.objects.create(user=team1)

        url = self._build_delete_url(team1)
        self.assertGET200(url)
        self.assertPOST200(url, data={'to_user': team2.id})
        self.assertDoesNotExist(team1)

        ce = self.assertStillExists(ce)
        self.assertEqual(team2, ce.user)

    @skipIfNotCremeUser
    def test_delete_team__transfer_to_self(self):
        user = self.login_as_root_and_get()

        team = self.create_team('Teamee')
        CremeEntity.objects.create(user=team)

        self.assertPOST200(self._build_delete_url(team), data={'to_user': user.id})
        self.assertDoesNotExist(team)

    @skipIfNotCremeUser
    def test_delete_team__forbidden(self):
        # self.login_as_config_admin()
        self.login_without_user_perm()

        user = self.create_user(index=1)
        team = self.create_team('Teamee')

        url = self._build_delete_url(team)
        self.assertGET403(url)
        self.assertPOST403(url, data={'to_user': user.id})

    @skipIfNotCremeUser
    def test_delete_user__superuser(self):
        "Delete view can delete a superuser if at least one remains."
        # user = self.login_as_super()
        user = self.login_with_user_perm()
        root = self.get_root_user()

        # self.assertEqual(2, User.objects.filter(is_superuser=True).count())
        self.assertEqual(1, User.objects.filter(is_superuser=True).count())
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
        # self.assertEqual(1, User.objects.filter(is_superuser=True).count())
        self.assertFalse(User.objects.filter(is_superuser=True))
        self.assertDoesNotExist(root)

    @skipIfNotCremeUser
    def test_delete_user__regular_user(self):
        "Delete view can delete any normal user."
        user = self.login_as_root_and_get()

        other_user = self.create_user(role=self.get_regular_role())
        self.assertFalse(other_user.is_superuser)

        ce = CremeEntity.objects.create(user=other_user)

        url = self._build_delete_url(other_user)
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, {'to_user': user.id}))
        self.assertDoesNotExist(other_user)

        ce = self.assertStillExists(ce)
        self.assertEqual(user, ce.user)

    @skipIfNotCremeUser
    def test_delete_user__last_superuser(self):
        "Delete view can not delete the last superuser."
        self.login_as_root()

        user = self.get_alone_element(User.objects.filter(is_superuser=True))

        url = self._build_delete_url(user)
        self.assertGET409(url)
        self.assertPOST409(url, {'to_user': user.id})

        self.assertStillExists(user)

    @skipIfNotCremeUser
    def test_delete_user__staff(self):
        "Delete view can not delete a staff user."
        user = self.login_as_root_and_get()
        hybird = User.objects.create(username='hybird', is_staff=True)

        url = self._build_delete_url(hybird)
        self.assertGET404(url)
        self.assertPOST404(url, {'to_user': user.id})

    @skipIfNotCremeUser
    def test_delete_user__during_transfer(self):
        "Delete view is protected by a lock."
        user = self.login_as_super()
        root = self.get_root_user()

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
    def test_delete_user__errors(self):
        "Validation errors."
        user = self.login_as_super()
        root = self.get_root_user()

        count = User.objects.count()
        self.assertGreater(count, 1)

        url = self._build_delete_url(root)
        self.assertGET200(url)

        response2 = self.assertPOST200(url)  # No data
        self.assertFormError(
            response2.context['form'],
            field='to_user', errors=_('This field is required.'),
        )
        self.assertEqual(count, User.objects.count())

        # Cannot move entities to deleted user
        response3 = self.assertPOST200(url, {'to_user': root.id})
        self.assertFormError(
            response3.context['form'],
            field='to_user',
            errors=_(
                'Select a valid choice. That choice is not one of the available choices.'
            ),
        )
        self.assertStillExists(user)

    @skipIfNotCremeUser
    def test_delete_user__credentials(self):
        "Only superusers are allowed."
        # user = self.login_as_config_admin()
        user = self.login_without_user_perm()

        url = self._build_delete_url(self.get_root_user())
        self.assertGET403(url)
        self.assertPOST403(url, data={'to_user': user.id})

    def test_brick_hide_inactive_user(self):
        user = self.login_as_root_and_get()

        def get_state():
            return BrickState.objects.get_for_brick_id(user=user, brick_id=UsersBrick.id)

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


class UserSettingsTestCase(BrickTestCaseMixin, CremeTestCase):
    def setUp(self):
        super().setUp()
        self._registered_skey = []

    def tearDown(self):
        super().tearDown()
        user_setting_key_registry.unregister(*self._registered_skey)

    def _register_key(self, *skeys):
        user_setting_key_registry.register(*skeys)
        self._registered_skey.extend(skeys)

    def test_user_settings01(self):
        self.login_as_root()
        response = self.assertGET200(reverse('creme_config__user_settings'))
        self.assertTemplateUsed(response, 'creme_config/user-settings.html')

        get = response.context.get
        self.assertEqual(
            reverse('creme_config__reload_user_settings_bricks'),
            get('bricks_reload_url'),
        )

        theme_form = get('theme_form')
        self.assertIsInstance(theme_form, str)
        self.assertStartsWith(theme_form, '<div>')
        self.assertIn('<label for="id_theme">', theme_form)

        tz_form = get('tz_form')
        self.assertIsInstance(tz_form, str)
        self.assertStartsWith(tz_form, '<div>')
        self.assertIn('<label for="id_time_zone">', tz_form)

        self.assertTrue(get_world_settings_model().objects.get().user_name_change_enabled)
        dname_form = get('displayed_name_form')
        self.assertIsInstance(dname_form, str)
        self.assertStartsWith(dname_form, '<div>')
        self.assertIn('<label for="id_displayed_name">', dname_form)

        doc = self.get_html_tree(response.content)
        self.get_brick_node(doc, brick=BrickMypageLocationsBrick)
        self.get_brick_node(doc, brick=NotificationChannelConfigItemsBrick)
        self.get_brick_node(doc, brick=UserSettingValuesBrick)

    def test_user_settings02(self):
        self.login_as_root()
        world_settings = get_world_settings_model().objects.get()
        world_settings.user_name_change_enabled = False
        world_settings.save()

        response = self.assertGET200(reverse('creme_config__user_settings'))
        self.assertIsNone(response.context.get('displayed_name_form'))

    @override_settings(THEMES=[
        ('icecream',  'Ice cream'),
        ('chantilly', 'Chantilly'),
    ])
    def test_change_theme(self):
        user = self.login_as_root_and_get()
        self.assertEqual(settings.THEMES[0][0], user.theme)

        url = reverse('creme_config__set_user_theme')

        def post(theme):
            self.assertPOST200(url, data={'theme': theme})

            self.assertEqual(theme, self.refresh(user).theme)

        post('chantilly')
        post('icecream')

    def test_change_timezone(self):
        user = self.login_as_root_and_get()
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
        user = self.login_as_root_and_get()
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
            response = self.assertGET200(content_url, headers={'accept-language': language})
            self.assertEqual(language, response['Content-Language'])

    def test_change_displayed_name(self):
        user = self.login_as_root_and_get()
        self.assertEqual('', user.displayed_name)

        world_settings = get_world_settings_model().objects.get()
        self.assertTrue(world_settings.user_name_change_enabled)

        post_url = reverse('creme_config__set_user_name')

        def post(dname):
            response = self.assertPOST200(
                post_url, data={'displayed_name': dname}, follow=True,
            )
            self.assertRedirects(response, reverse('creme_config__user_settings'))

            self.assertEqual(dname, self.refresh(user).displayed_name)

        post('foobar')
        post('')

        # ----
        world_settings.user_name_change_enabled = False
        world_settings.save()
        self.assertPOST403(post_url, data={'displayed_name': 'foobar'})

    def test_reload_user_settings_bricks(self):
        self.login_as_standard()

        response = self.assertGET200(
            reverse('creme_config__reload_user_settings_bricks'),
            data={'brick_id': [
                BrickMypageLocationsBrick.id,
                NotificationChannelConfigItemsBrick.id,
                'silly_id',
            ]},
        )
        self.assertEqual('application/json', response['Content-Type'])

        content = response.json()
        self.assertIsList(content, length=2)

        brick_info1 = content[0]
        self.assertIsList(brick_info1, length=2)
        self.assertEqual(BrickMypageLocationsBrick.id, brick_info1[0])
        self.get_brick_node(
            tree=self.get_html_tree(brick_info1[1]),
            brick=BrickMypageLocationsBrick,
        )

        brick_info2 = content[1]
        self.assertIsList(brick_info2, length=2)
        self.assertEqual(NotificationChannelConfigItemsBrick.id, brick_info2[0])
        self.get_brick_node(
            tree=self.get_html_tree(brick_info2[1]),
            brick=NotificationChannelConfigItemsBrick,
        )

    @staticmethod
    def _build_edit_user_svalue_url(setting_key):
        return reverse('creme_config__edit_user_setting', args=(setting_key.id,))

    def test_edit_user_setting_value01(self):
        user = self.login_as_root_and_get()
        sk = UserSettingKey(
            id='creme_config-test_edit_user_setting_value01',
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
        self.login_as_root()
        sk = UserSettingKey(
            id='creme_config-test_edit_user_setting_value02',
            description='Page displayed',
            app_label='creme_core',
            type=SettingKey.BOOL, hidden=True,
        )

        self._register_key(sk)
        self.assertGET409(self._build_edit_user_svalue_url(sk))

    def test_edit_user_setting_value03(self):
        "Not blank + STRING."
        self.login_as_root()
        sk = UserSettingKey(
            id='creme_config-test_edit_user_setting_value03',
            description='API key',
            app_label='creme_core',
            type=SettingKey.STRING,
        )
        self.assertFalse(sk.blank)
        self._register_key(sk)

        response = self.client.post(self._build_edit_user_svalue_url(sk), data={'value': ''})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='value', errors=_('This field is required.'),
        )

    def test_edit_user_setting_value04(self):
        "Blank + STRING."
        user = self.login_as_root_and_get()
        sk = UserSettingKey(
            id='creme_config-test_edit_user_setting_value04',
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
        user = self.login_as_root_and_get()
        sk = UserSettingKey(
            id='creme_config-test_edit_user_setting_value05',
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

    def test_UserSettingValuesBrick(self):
        user = self.login_as_root_and_get()
        brick = UserSettingValuesBrick()

        core_sk1 = UserSettingKey(
            id='creme_core-test_01',
            description='Page displayed',
            app_label='creme_core',
            type=SettingKey.BOOL, hidden=False,
        )
        core_sk2 = UserSettingKey(
            id='creme_core-test_02',
            description='Page title',
            app_label='creme_core',
            type=SettingKey.STRING, hidden=False,
        )

        doc_sk1 = UserSettingKey(
            id='documents-test_01',
            description='Size displayed',
            app_label='documents',
            type=SettingKey.BOOL, hidden=False,
        )
        doc_sk2 = UserSettingKey(
            id='documents-test_02',
            description='Metadata displayed',
            app_label='documents',
            type=SettingKey.BOOL, hidden=True,
        )

        reg_attname = 'user_setting_key_registry'
        self.assertHasAttr(brick, reg_attname)

        registry = SettingKeyRegistry(UserSettingKey).register(
            core_sk1, core_sk2, doc_sk1, doc_sk2
        )
        setattr(brick, reg_attname, registry)

        context = self.build_context(user=user)

        # with self.assertNumQueries(6):
        render = brick.detailview_display(context)

        brick_node = self.get_brick_node(
            self.get_html_tree(render), brick=UserSettingValuesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=3,
            title='{count} Setting value',
            plural_title='{count} Setting values',
        )

        # ---
        core_app_node = self.get_html_node_or_fail(
            brick_node,
            './/div[@class="'
            'brick-list-item '
            'setting-values-config-item '
            'setting-values-config-item-creme_core'
            '"]'
        )
        self.assertEqual(
            _('Core'),
            self.get_html_node_or_fail(
                core_app_node, './/div[@class="setting-values-config-app-name"]'
            ).text,
        )
        self.assertBrickHasAction(core_app_node, url=self._build_edit_user_svalue_url(core_sk1))
        self.assertBrickHasAction(core_app_node, url=self._build_edit_user_svalue_url(core_sk2))

        # ---
        doc_app_node = self.get_html_node_or_fail(
            brick_node,
            './/div[@class="'
            'brick-list-item '
            'setting-values-config-item '
            'setting-values-config-item-documents'
            '"]'
        )
        self.assertEqual(
            _('Documents'),
            self.get_html_node_or_fail(
                doc_app_node, './/div[@class="setting-values-config-app-name"]'
            ).text,
        )
        self.assertBrickHasAction(doc_app_node, url=self._build_edit_user_svalue_url(doc_sk1))
        self.assertBrickHasNoAction(doc_app_node, url=self._build_edit_user_svalue_url(doc_sk2))
