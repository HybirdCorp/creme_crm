from functools import partial
from uuid import UUID

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import QuerySet
from django.db.models.deletion import ProtectedError
from django.test.utils import override_settings
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_config.auth import role_config_perm, user_config_perm
from creme.creme_config.models import FakeConfigEntity
from creme.creme_core import constants
from creme.creme_core.auth import STAFF_PERM, SUPERUSER_PERM, EntityCredentials
from creme.creme_core.auth.special import SpecialPermission
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    condition_handler,
    entity_filter_registries,
    operands,
    operators,
)
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CremeUser,
    CustomEntityType,
    EntityFilter,
    FakeActivity,
    FakeContact,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    FakeTodo,
    Relation,
    Sandbox,
    SetCredentials,
    UserRole,
)
from creme.creme_core.populate import UUID_USER_ROOT
from creme.creme_core.sandboxes import OnlySuperusersType
from creme.documents.models import Document, Folder
from creme.documents.tests.base import skipIfCustomDocument, skipIfCustomFolder

from ..base import CremeTestCase, skipIfNotInstalled


class BaseAuthTestCase(CremeTestCase):
    password = 'password'

    def _create_users(self):
        self.user       = self.create_user(index=0)
        self.other_user = self.create_user(index=1)

        return self.user, self.other_user

    def _create_users_n_contacts(self):
        user, other_user = self._create_users()

        create_contact = FakeContact.objects.create
        self.contact1 = create_contact(
            user=user, first_name='Musashi', last_name='Miyamoto',
        )
        self.contact2 = create_contact(
            user=other_user, first_name='Kojiro',  last_name='Sasaki',
        )

    @staticmethod
    def _create_role(name, allowed_apps=(), admin_4_apps=(), set_creds=(), users=()):
        role = UserRole.objects.create(
            name=name, allowed_apps=allowed_apps, admin_4_apps=admin_4_apps,
        )

        for sc in set_creds:
            sc.role = role
            sc.save()

        for user in users:
            user.is_superuser = False
            user.role = role
            user.save()

        return role


class UserRoleManagerTestCase(BaseAuthTestCase):
    def test_smart_create_role(self):
        name = 'Leader'
        allowed_apps = ['creme_core', 'documents']
        admin_4_apps = ['documents']
        creatable_models = [FakeOrganisation, FakeContact]
        listable_models = [FakeActivity]
        exportable_models = [FakeInvoice]
        role = UserRole.objects.smart_create(
            name=name,
            allowed_apps=allowed_apps,
            admin_4_apps=admin_4_apps,
            creatable_models=creatable_models,
            listable_models=listable_models,
            exportable_models=exportable_models,
        )
        self.assertIsInstance(role, UserRole)
        self.assertIsNotNone(role.pk)
        self.assertIsNotNone(role.id)
        self.assertEqual(name, role.name)
        self.assertCountEqual(allowed_apps, [*role.allowed_apps])
        self.assertCountEqual(admin_4_apps, [*role.admin_4_apps])
        self.assertCountEqual(
            creatable_models,
            [ct.model_class() for ct in role.creatable_ctypes.all()],
        )
        self.assertCountEqual(
            listable_models,
            [ct.model_class() for ct in role.listable_ctypes.all()],
        )
        self.assertCountEqual(
            exportable_models,
            [ct.model_class() for ct in role.exportable_ctypes.all()],
        )


class UserRoleTestCase(BaseAuthTestCase):
    def test_populate(self):
        role = UserRole.objects.order_by('id').first()
        self.assertIsNotNone(role)
        self.assertEqual(_('Regular user'), role.name)
        self.assertFalse(role.admin_4_apps)
        self.assertIsNone(role.deactivated_on)

        allowed_apps = role.allowed_apps
        self.assertIn('creme_core', allowed_apps)
        self.assertIn('creme_config', allowed_apps)

        set_creds = self.get_alone_element(role.credentials.all())
        self.assertTrue(set_creds.value & EntityCredentials.VIEW)
        self.assertTrue(set_creds.value & EntityCredentials.CHANGE)
        self.assertTrue(set_creds.value & EntityCredentials.DELETE)
        self.assertTrue(set_creds.value & EntityCredentials.LINK)
        self.assertTrue(set_creds.value & EntityCredentials.UNLINK)
        self.assertEqual(SetCredentials.ESET_ALL, set_creds.set_type)
        self.assertIsNone(set_creds.ctype)
        self.assertIsNone(set_creds.efilter)
        self.assertFalse(set_creds.forbidden)

        self.assertDictEqual({}, role.special_permissions)

    def test_str(self):
        name = 'Normal'
        role = UserRole(name=name)
        self.assertEqual(name, str(role))

        role.deactivated_on = now()
        self.assertEqual(_('{role} [deactivated]').format(role=name), str(role))

    def test_attributes(self):
        role = UserRole(name='Normal')
        self.assertEqual('', role.raw_allowed_apps)
        self.assertSetEqual(set(), role.allowed_apps)

        self.assertEqual('', role.raw_admin_4_apps)
        self.assertSetEqual(set(), role.admin_4_apps)

        role.allowed_apps = ['creme_core', 'documents']
        self.assertEqual({'creme_core', 'documents'}, role.allowed_apps)

        role.admin_4_apps = ['creme_core', 'persons']
        self.assertEqual({'creme_core', 'persons'}, role.admin_4_apps)

        role.special_permissions = [user_config_perm, role_config_perm]
        expected_perms = {
            user_config_perm.id: user_config_perm,
            role_config_perm.id: role_config_perm,
        }
        self.assertDictEqual(expected_perms, role.special_permissions)
        self.assertEqual(
            f'{user_config_perm.id}\n{role_config_perm.id}',
            role.raw_special_perms,
        )

        role.save()
        role = self.refresh(role)
        self.assertEqual({'creme_core', 'documents'}, role.allowed_apps)
        self.assertEqual({'creme_core', 'persons'}, role.admin_4_apps)
        self.assertDictEqual(expected_perms, role.special_permissions)

    def test_portable_key(self):
        role = self.create_role()
        with self.assertNoException():
            role_key = role.portable_key()
        self.assertIsInstance(role_key, str)
        self.assertUUIDEqual(role.uuid, role_key)

        with self.assertNoException():
            got_role = UserRole.objects.get_by_portable_key(role_key)
        self.assertEqual(role, got_role)

    def test_delete(self):
        role = self._create_role(
            'Coder', ['creme_core'],
            set_creds=[
                SetCredentials(value=EntityCredentials.CHANGE, set_type=SetCredentials.ESET_OWN),
                SetCredentials(value=EntityCredentials.VIEW,   set_type=SetCredentials.ESET_ALL),
            ],
        )
        self.assertEqual(2, SetCredentials.objects.filter(role=role).count())

        role.delete()
        self.assertFalse(UserRole.objects.filter(pk=role.id))
        self.assertFalse(SetCredentials.objects.filter(role=role.id))

    def test_delete__error(self):
        "Can not delete a role linked to a user."
        user = self.create_user()
        role = self._create_role(
            'Coder', ['creme_core'], users=[user],  # 'persons'
            set_creds=[
                SetCredentials(value=EntityCredentials.CHANGE, set_type=SetCredentials.ESET_OWN),
                SetCredentials(value=EntityCredentials.VIEW,   set_type=SetCredentials.ESET_ALL),
            ],
        )

        self.assertRaises(ProtectedError, role.delete)
        self.assertEqual(1, UserRole.objects.filter(pk=role.id).count())
        self.assertEqual(2, SetCredentials.objects.filter(role=role).count())


class SetCredentialsTestCase(BaseAuthTestCase):
    def test_str(self):
        self.assertEqual(
            _('For “{set}“ it is allowed to: {perms}').format(
                set=_('All entities'),
                perms=_('nothing allowed'),
            ),
            str(SetCredentials(
                # value=...,
                set_type=SetCredentials.ESET_ALL,
            ))
        )
        self.assertEqual(
            _('For “{set}“ it is allowed to: {perms}').format(
                set=_('All entities'),
                perms=_('view'),
            ),
            str(SetCredentials(
                value=EntityCredentials.VIEW,
                set_type=SetCredentials.ESET_ALL,
            )),
        )

        self.assertEqual(
            _('For “{set}“ it is forbidden to: {perms}').format(
                set=_("User's own entities"),
                perms=_('nothing forbidden'),
            ),
            str(SetCredentials(
                # value=...,
                set_type=SetCredentials.ESET_OWN,
                forbidden=True,
            )),
        )
        self.assertEqual(
            _('For “{set}“ it is forbidden to: {perms}').format(
                set=_("User's own entities"),
                perms='{}, {}'.format(_('change'), _('delete')),
            ),
            str(SetCredentials(
                value=EntityCredentials.CHANGE | EntityCredentials.DELETE,
                set_type=SetCredentials.ESET_OWN,
                forbidden=True,
            )),
        )

        self.assertEqual(
            _('For “{set}“ of type “{type}” it is allowed to: {perms}').format(
                set=_('All entities'),
                type='Test Contact',
                perms=_('link'),
            ),
            str(SetCredentials(
                value=EntityCredentials.LINK,
                set_type=SetCredentials.ESET_ALL,
                ctype=FakeContact,
            )),
        )
        self.assertEqual(
            _('For “{set}“ of type “{type}” it is forbidden to: {perms}').format(
                set=_("User's own entities"),
                type='Test Organisation',
                perms=_('unlink'),
            ),
            str(SetCredentials(
                value=EntityCredentials.UNLINK,
                set_type=SetCredentials.ESET_OWN,
                ctype=FakeOrganisation,
                forbidden=True,
            )),
        )


class CremeUserManagerTestCase(BaseAuthTestCase):
    def test_create_user(self):
        existing_user = self.create_user()
        role = self.get_regular_role()

        username = 'kanna'
        first_name = 'Kanna'
        last_name = 'Endo'
        data = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'password': self.password,
            'email': existing_user.email,  # <===
            'role': role,
        }

        with self.assertRaises(ValidationError) as cm:
            CremeUser.objects.create_user(**data)

        self.assertValidationError(
            cm.exception,
            messages={
                'email': _('An active user with the same email address already exists.'),
            },
        )

        # ---
        data['email'] = email = 'kanna@century.jp'
        with self.assertNoException():
            user = CremeUser.objects.create_user(**data)

        self.assertIsInstance(user, CremeUser)
        self.assertIsInstance(user.uuid, UUID)
        self.assertEqual(username,   user.username)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)
        self.assertTrue(user.check_password(self.password))
        self.assertFalse(user.is_superuser)
        self.assertEqual(role, user.role)
        self.assertListEqual([role], [*user.roles.all()])

    def test_create_user__roles(self):
        role1 = self.get_regular_role()
        role2 = self.create_role(name='CEO')
        role3 = self.create_role(name='Engineer')

        with self.assertNoException():
            user = CremeUser.objects.create_user(
                username='kanna',
                first_name='Kanna',
                last_name='Endo',
                password=self.password,
                email='kanna@20thcentury.jp',
                role=role1,
                roles=[role2, role3],
            )

        user = self.refresh(user)
        self.assertFalse(user.is_superuser)
        self.assertEqual(role1, user.role)
        self.assertCountEqual([role1, role2, role3], [*user.roles.all()])

    def test_create_user__only_roles(self):
        role1 = self.get_regular_role()
        role2 = self.create_role(name='CEO')

        with self.assertNoException():
            user = CremeUser.objects.create_user(
                username='kanna',
                first_name='Kanna',
                last_name='Endo',
                password=self.password,
                email='kanna@20thcentury.jp',
                roles=[role1, role2],
            )

        user = self.refresh(user)
        self.assertFalse(user.is_superuser)
        self.assertEqual(role1, user.role)
        self.assertCountEqual([role1, role2], [*user.roles.all()])

    def test_create_superuser(self):
        existing_user = self.create_user()

        username = 'kanna'
        first_name = 'Kanna'
        last_name = 'Endo'
        data = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'password': self.password,
            'email': existing_user.email,  # <===
        }

        with self.assertRaises(ValidationError) as cm:
            CremeUser.objects.create_superuser(**data)

        self.assertValidationError(
            cm.exception,
            messages={
                'email': _('An active user with the same email address already exists.'),
            },
        )

        # ---
        data['email'] = email = 'kanna@century.jp'
        with self.assertNoException():
            user = CremeUser.objects.create_superuser(**data)

        self.assertIsInstance(user, CremeUser)
        self.assertEqual(username,   user.username)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)
        self.assertTrue(user.check_password(self.password))
        self.assertTrue(user.is_superuser)
        self.assertIsNone(user.role)
        self.assertFalse(user.roles.all())

    # TODO: test get_admin()


class CremeUserTestCase(BaseAuthTestCase):
    def test_populate(self):
        user = self.get_root_user()
        self.assertUUIDEqual(UUID_USER_ROOT, user.uuid)

        sandbox = self.get_object_or_fail(Sandbox, uuid=constants.UUID_SANDBOX_SUPERUSERS)
        self.assertIsNone(sandbox.role)
        self.assertIsNone(sandbox.user)
        self.assertEqual(OnlySuperusersType.id, sandbox.type_id)
        self.assertIsInstance(sandbox.type, OnlySuperusersType)

    def test_str(self):
        user = CremeUser(
            username='kirika', first_name='Kirika', last_name='Yumura',
        )
        self.assertEqual('', user.displayed_name)
        self.assertEqual('Kirika Y.', str(user))

        user.displayed_name = dname = 'Kirika-chan'
        self.assertEqual(dname, str(user))

    def test_clean__email(self):
        user, other_user = self._create_users()
        user.email = other_user.email

        with self.assertRaises(ValidationError) as cm:
            user.clean()

        self.assertValidationError(
            cm.exception,
            messages={
                'email': _('An active user with the same email address already exists.'),
            },
        )

        # ---
        other_user.is_active = False
        other_user.save()

        with self.assertNoException():
            user.clean()

    def test_clean__role(self):
        user = CremeUser(
            username='Kenji', email='kenji@century.jp',
            first_name='Kenji', last_name='Gendou',
            # password='password',
            is_superuser=False,
            # role=role,  <===
        )

        with self.assertRaises(ValidationError) as cm:
            user.clean()

        self.assertValidationError(
            cm.exception, messages='A regular user must have a role.',
        )

    def test_clean__superuser(self):
        role = self.get_regular_role()

        user = CremeUser(
            username='Kenji', email='kenji@century.jp',
            first_name='Kenji', last_name='Gendou',
            # password='password',
            is_superuser=True,
            role=role,
        )

        with self.assertRaises(ValidationError) as cm:
            user.clean()

        self.assertValidationError(
            cm.exception, messages='A superuser cannot have a role.',
        )

    def test_clean__team__email(self):
        "Do not check email uniqueness with teams."
        team1 = CremeUser.objects.create(username='teamA', is_team=True)
        self.assertFalse(team1.email)

        with self.assertNoException():
            team1.clean()

        team1.save()

        # ---
        team2 = CremeUser.objects.create(username='teamB', is_team=True)
        self.assertFalse(team2.email)

        with self.assertNoException():
            team2.clean()

    def test_clean__team__role(self):
        "No role with teams."
        team = CremeUser(username='teamA', is_team=True, role=self.get_regular_role())

        with self.assertRaises(ValidationError) as cm:
            team.clean()

        self.assertValidationError(
            cm.exception, messages='A team cannot have a role.',
        )

    def test_clean__team__superuser(self):
        "Not superuser teams."
        team = CremeUser(username='teamA', is_team=True, is_superuser=True)

        with self.assertRaises(ValidationError) as cm:
            team.clean()

        self.assertValidationError(
            cm.exception, messages='A team cannot be marked as superuser.',
        )

    def test_clean__team__name(self):
        "No names."
        team1 = CremeUser(username='teamA', is_team=True, last_name='A')
        with self.assertRaises(ValidationError) as cm1:
            team1.clean()
        self.assertValidationError(
            cm1.exception, messages='A team cannot have a last name.',
        )

        # ---
        team2 = CremeUser(username='teamA', is_team=True, first_name='team')
        with self.assertRaises(ValidationError) as cm2:
            team2.clean()
        self.assertValidationError(
            cm2.exception, messages='A team cannot have a first name.',
        )

        # ---
        team3 = CremeUser(username='teamA', is_team=True, displayed_name='The famous A team')
        with self.assertRaises(ValidationError) as cm3:
            team3.clean()
        self.assertValidationError(
            cm3.exception, messages='A team cannot have a displayed name.',
        )

    def test_attributes(self):
        user = self.create_user()

        full_name = _('{first_name} {last_name}.').format(
            first_name=user.first_name,
            last_name=user.last_name[0],
        )
        self.assertEqual(full_name, user.get_full_name())
        self.assertEqual(full_name, str(user))

        self.assertEqual(user.username, user.get_short_name())

        self.assertEqual(settings.TIME_ZONE, user.time_zone)

        theme = settings.THEMES[0]
        self.assertEqual(theme[0], user.theme)
        self.assertEqual(theme, user.theme_info)

    def test_attributes__team(self):
        username1 = 'Teamee'
        team1 = CremeUser.objects.create(username=username1, is_team=True)

        self.assertEqual(_('{user} (team)').format(user=username1), str(team1))
        self.assertEqual(username1, team1.get_short_name())

        # TODO: error if team ??
        # self.assertEqual(settings.TIME_ZONE, user.time_zone)
        # theme = settings.THEMES[0]
        # self.assertEqual(theme[0], user.theme)
        # self.assertEqual(theme, user.theme_info)

        username2 = 'A-Team'
        team2 = CremeUser.objects.create(
            username=username2, is_team=True,
            first_name='NC', last_name=username2,
        )

        self.assertEqual(_('{user} (team)').format(user=username2), str(team2))

    @override_settings(
        THEMES=[
            ('this_theme_is_cool', 'Cool one'),
            ('yet_another_theme',  'I am cool too, bro'),
        ],
    )
    def test_theme_info(self):
        "The first valid theme is used if the registered theme is not valid."
        theme = settings.THEMES[0]
        user = self.build_user()
        self.assertNotEqual(theme[0], user.theme)
        self.assertEqual(theme, user.theme_info)

    def test_portable_key(self):
        user = self.create_user()
        with self.assertNoException():
            user_key = user.portable_key()
        self.assertIsInstance(user_key, str)
        self.assertUUIDEqual(user.uuid, user_key)

        with self.assertNoException():
            got_user = CremeUser.objects.get_by_portable_key(user_key)
        self.assertEqual(user, got_user)

    def test_normalize_roles(self):
        role1 = self.get_regular_role()
        user = CremeUser.objects.create(
            username='kanna',
            first_name='Kanna',
            last_name='Endo',
            email='kanna@20thcentury.jp',
            is_superuser=False,
            role=role1,
        )
        self.assertFalse(user.roles.all())

        role2 = self.create_role()
        user.roles.add(role2)

        with self.assertLogs(level='WARNING') as logs_manager:
            user.normalize_roles()
        self.assertCountEqual([role1, role2], user.roles.all())
        self.assertIn(
            f'The possible roles of the user "{user.username}" did not contain '
            f'its current job (user has been fixed).',
            logs_manager.output[0],
        )

        with self.assertNoLogs(level='WARNING'):
            user.normalize_roles()

    def test_normalize_roles__superuser(self):
        user = CremeUser.objects.create(
            username='kanna',
            first_name='Kanna',
            last_name='Endo',
            email='kanna@20thcentury.jp',
            is_superuser=True,
        )

        with self.assertNoLogs(level='WARNING'):
            user.normalize_roles()

    def test_create_not_team(self):
        user = self.create_user()
        fake_team = CremeUser.objects.create(username='Teamee')

        self.assertFalse(fake_team.is_team)

        with self.assertRaises(ValueError):
            fake_team.teammates = [user]

        with self.assertRaises(ValueError):
            fake_team.teammates  # NOQA

    def test_create_team(self):
        user, other = self._create_users()
        team = CremeUser.objects.create(username='Teamee', is_team=True)

        team.teammates = [user, other]
        teammates = team.teammates
        self.assertEqual(2, len(teammates))

        team = self.refresh(team)
        self.assertDictEqual({user.id: user, other.id: other}, team.teammates)

        with self.assertNumQueries(0):  # Teammates are cached
            team.teammates  # NOQA

        self.assertTrue(all(isinstance(u, CremeUser) for u in teammates.values()))

        ids_set = {user.id, other.id}
        self.assertSetEqual(ids_set, {*teammates})
        self.assertSetEqual(ids_set, {u.id for u in teammates.values()})

        user3 = CremeUser.objects.create_user(
            username='kanna', email='kanna@century.jp',
            first_name='Kanna', last_name='Gendou',
            password='uselesspw', is_superuser=True,
        )
        team.teammates = [user, other, user3]
        self.assertEqual(3, len(team.teammates))

        team.teammates = [other]
        self.assertEqual(1, len(team.teammates))
        self.assertDictEqual({other.id: other}, self.refresh(team).teammates)

        with self.assertRaises(ValueError):
            team.teams  # NOQA

        # ---
        team2 = CremeUser.objects.create(username='Team#2', is_team=True)
        with self.assertRaises(ValueError):
            team2.teammates = [team]


class PermissionsTestCase(BaseAuthTestCase):
    @staticmethod
    def _ids_list(iterable):
        return [e.id for e in iterable]

    def _build_contact_qs(self, *extra_contacts):
        return FakeContact.objects.filter(
            pk__in=[
                self.contact1.id,
                self.contact2.id,
                *(c.id for c in extra_contacts),
            ],
        )

    def test_super_user(self):
        self._create_users_n_contacts()
        user = self.user
        user.is_superuser = True  # <====

        has_perm = user.has_perm
        self.assertTrue(has_perm('creme_core'))

        self.assertEqual('*superuser*', SUPERUSER_PERM)
        self.assertTrue(has_perm(SUPERUSER_PERM))

        self.assertTrue(user.has_perms([SUPERUSER_PERM]))
        self.assertTrue(user.has_perms(SUPERUSER_PERM))

        with self.assertNoException():
            user.has_perm_or_die(SUPERUSER_PERM)

        contact1 = self.contact1
        self.assertTrue(has_perm('creme_core.view_entity',   contact1))
        self.assertTrue(has_perm('creme_core.change_entity', contact1))
        self.assertTrue(has_perm('creme_core.delete_entity', contact1))
        self.assertTrue(has_perm('creme_core.link_entity',   contact1))
        self.assertTrue(has_perm('creme_core.unlink_entity', contact1))

        contact2 = self.contact2
        self.assertTrue(has_perm('creme_core.view_entity',   contact2))
        self.assertTrue(has_perm('creme_core.change_entity', contact2))
        self.assertTrue(has_perm('creme_core.delete_entity', contact2))
        self.assertTrue(has_perm('creme_core.link_entity',   contact2))
        self.assertTrue(has_perm('creme_core.unlink_entity', contact2))

        self.assertTrue(has_perm('creme_core.link_fakecontact'))
        self.assertTrue(has_perm('creme_core.export_fakecontact'))

        # Helpers --------------------------------------------------------------
        self.assertTrue(user.has_perm_to_view(contact1))
        self.assertTrue(user.has_perm_to_change(contact1))
        self.assertTrue(user.has_perm_to_delete(contact1))
        self.assertTrue(user.has_perm_to_link(contact1))
        self.assertTrue(user.has_perm_to_unlink(contact1))

        self.assertTrue(user.has_perm_to_view(contact2))
        self.assertTrue(user.has_perm_to_change(contact2))

        self.assertTrue(user.has_perm_to_create(FakeContact))
        self.assertTrue(user.has_perm_to_export(FakeContact))

        # Helpers (exception version) ------------------------------------------
        self.assertNoException(user.has_perm_to_view_or_die,   contact1)
        self.assertNoException(user.has_perm_to_change_or_die, contact1)
        self.assertNoException(user.has_perm_to_delete_or_die, contact1)
        self.assertNoException(user.has_perm_to_link_or_die,   contact1)
        self.assertNoException(user.has_perm_to_unlink_or_die, contact1)

        # Filtering ------------------------------------------------------------
        with self.assertNumQueries(0):
            qs = EntityCredentials.filter(user, self._build_contact_qs())

        self.assertListEqual(
            [contact1.id, contact2.id], self._ids_list(qs),
        )

    def test_super_user__not(self):
        user = self.build_user()
        self._create_role('Salesman', ['creme_core'], users=[user])
        self.assertFalse(user.has_perm(SUPERUSER_PERM))

        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_or_die(SUPERUSER_PERM)
        self.assertEqual(_('A superuser is required.'), str(cm.exception))

    def test_staff(self):
        self.assertEqual('*staff*', STAFF_PERM)

        user = self.build_user()
        has_perm = user.has_perm
        self.assertFalse(has_perm(STAFF_PERM))

        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_or_die(STAFF_PERM)
        self.assertEqual(_('A staff user is required.'), str(cm.exception))

        # ---
        user.is_superuser = True
        self.assertFalse(has_perm(STAFF_PERM))

        user.is_staff = True
        self.assertTrue(has_perm(STAFF_PERM))

        with self.assertNoException():
            user.has_perm_or_die(STAFF_PERM)

    def test_special_permissions(self):
        user = self.build_user()
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.has_perm(user_config_perm.as_perm))
        self.assertTrue(user.has_special_perm(user_config_perm))
        with self.assertNoException():
            user.has_special_perm_or_die(user_config_perm)

        user.is_superuser = False
        user.role = self.create_role(name='Not user configurer')
        self.assertFalse(user.has_special_perm(user_config_perm))
        self.assertFalse(user.has_perm(user_config_perm.as_perm))

        # Regular user but no the wanted perm ---
        user.role = self.create_role(
            name='Role configurer', special_permissions=[role_config_perm],
        )
        self.assertFalse(user.has_special_perm(user_config_perm))

        with self.assertRaises(PermissionDenied) as cm:
            user.has_special_perm_or_die(user_config_perm)
        self.assertEqual(
            _('You have not this special permission: «{}»').format(
                user_config_perm.verbose_name,
            ),
            str(cm.exception),
        )

        self.assertFalse(user.has_perm(user_config_perm.as_perm))

        # Regular user with the wanted perm ---
        user.role = self.create_role(
            name='User configurer',
            special_permissions=[role_config_perm, user_config_perm],
        )
        self.assertTrue(user.has_special_perm(user_config_perm))
        with self.assertNoException():
            user.has_special_perm_or_die(user_config_perm)
        self.assertTrue(user.has_perm(user_config_perm.as_perm))

        # Error ---
        unregistered = SpecialPermission(
            id='my_app-unknown', verbose_name='?', description='??',
        )
        self.assertFalse(user.has_special_perm(unregistered))
        with self.assertRaises(PermissionDenied):
            user.has_special_perm_or_die(unregistered)
        with self.assertLogs(level='WARNING'):
            self.assertFalse(user.has_perm(unregistered.as_perm))

    def test_all__view(self):
        "VIEW + ESET_ALL."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        has_perm = user.has_perm
        # self.assertTrue(user.has_perm(''))  TODO?
        self.assertTrue(user.has_perms(''))
        self.assertTrue(user.has_perms([]))
        with self.assertNoException():
            user.has_perms_or_die('')
            user.has_perms_or_die([])

        contact1 = self.contact1
        self.assertTrue(has_perm('creme_core.view_entity',    contact1))
        self.assertFalse(has_perm('creme_core.change_entity', contact1))
        self.assertFalse(has_perm('creme_core.delete_entity', contact1))
        self.assertFalse(has_perm('creme_core.link_entity',   contact1))
        self.assertFalse(has_perm('creme_core.unlink_entity', contact1))

        self.assertFalse(has_perm('creme_core.link_fakecontact'))
        self.assertFalse(has_perm('creme_core.export_fakecontact'))

        contact2 = self.contact2
        self.assertTrue(has_perm('creme_core.view_entity',    contact2))
        self.assertFalse(has_perm('creme_core.change_entity', contact2))

        # Helpers --------------------------------------------------------------
        # Refresh caches
        user = self.refresh(user)
        contact1 = self.refresh(contact1)

        with self.assertNumQueries(2):  # 2 = get UserRole +  its SetCredentials
            can_view = user.has_perm_to_view(contact1)
        self.assertTrue(can_view)

        with self.assertNumQueries(0):  # UserRole & SetCredentials are cached
            can_change = user.has_perm_to_change(contact1)
        self.assertFalse(can_change)

        self.assertFalse(user.has_perm_to_delete(contact1))
        self.assertFalse(user.has_perm_to_link(contact1))
        self.assertFalse(user.has_perm_to_unlink(contact1))

        self.assertTrue(user.has_perm_to_view(contact2))
        self.assertFalse(user.has_perm_to_change(contact2))

        # Helpers (exception version) ------------------------------------------
        self.assertNoException(user.has_perm_to_view_or_die, contact1)
        self.assertRaises(PermissionDenied, user.has_perm_to_change_or_die, contact1)
        self.assertRaises(PermissionDenied, user.has_perm_to_delete_or_die, contact1)
        self.assertRaises(PermissionDenied, user.has_perm_to_link_or_die,   contact1)
        self.assertRaises(PermissionDenied, user.has_perm_to_unlink_or_die, contact1)

        # Filtering ------------------------------------------------------------
        creds_filter = EntityCredentials.filter
        qs1 = self._build_contact_qs()

        with self.assertNumQueries(1):
            _ = user.teams

        with self.assertNumQueries(0):
            creds_filter(user, qs1)

        self.assertIsNone(qs1._result_cache, 'Queryset has been retrieved (should be lazy)')

        all_ids = [contact1.id, contact2.id]
        self.assertListEqual(
            all_ids,
            self._ids_list(creds_filter(user, qs1, perm=EntityCredentials.VIEW))
        )

        self.assertListEqual(
            all_ids,
            self._ids_list(creds_filter(user, qs1, perm=EntityCredentials.VIEW))
        )
        self.assertFalse(creds_filter(user, qs1, perm=EntityCredentials.CHANGE))
        self.assertFalse(creds_filter(user, qs1, perm=EntityCredentials.DELETE))
        self.assertFalse(creds_filter(user, qs1, perm=EntityCredentials.LINK))
        self.assertFalse(creds_filter(user, qs1, perm=EntityCredentials.UNLINK))

    def test_all__view__noappcreds(self):
        "App is not allowed -> no creds."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder',
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        has_perm = user.has_perm
        contact1 = self.contact1
        self.assertFalse(has_perm('creme_core.view_entity',   contact1))
        self.assertFalse(has_perm('creme_core.change_entity', contact1))
        self.assertFalse(has_perm('creme_core.delete_entity', contact1))
        self.assertFalse(has_perm('creme_core.link_entity',   contact1))
        self.assertFalse(has_perm('creme_core.unlink_entity', contact1))

        self.assertFalse(has_perm('creme_core.view_entity',   self.contact2))

        # Helpers --------------------------------------------------------------
        self.assertFalse(user.has_perm_to_view(contact1))
        self.assertRaises(PermissionDenied, user.has_perm_to_view_or_die, contact1)

        # Filtering ------------------------------------------------------------
        self.assertFalse(EntityCredentials.filter(user, self._build_contact_qs()))

    def test_all__change(self):
        "CHANGE + ESET_ALL."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.CHANGE,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        has_perm = user.has_perm
        contact1 = self.contact1
        self.assertFalse(has_perm('creme_core.view_entity',   contact1))
        self.assertTrue(has_perm('creme_core.change_entity',  contact1))
        self.assertFalse(has_perm('creme_core.delete_entity', contact1))
        self.assertFalse(has_perm('creme_core.link_entity',   contact1))
        self.assertFalse(has_perm('creme_core.unlink_entity', contact1))

        contact2 = self.contact2
        self.assertFalse(has_perm('creme_core.view_entity',  contact2))
        self.assertTrue(has_perm('creme_core.change_entity', contact2))

        creds_filter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertFalse(creds_filter(perm=EntityCredentials.VIEW))
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(creds_filter(perm=EntityCredentials.CHANGE)),
        )
        self.assertFalse(creds_filter(perm=EntityCredentials.DELETE))
        self.assertFalse(creds_filter(perm=EntityCredentials.LINK))
        self.assertFalse(creds_filter(perm=EntityCredentials.UNLINK))

    def test_all__change__admincreds(self):
        "CHANGE + ESET_ALL (no app creds, but app admin creds)."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder',
            admin_4_apps=['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.CHANGE,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        contact1 = self.contact1
        self.assertFalse(user.has_perm_to_view(contact1))
        self.assertTrue(user.has_perm_to_change(contact1))

        contact2 = self.contact2
        self.assertFalse(user.has_perm_to_view(contact2))
        self.assertTrue(user.has_perm_to_change(contact2))

        creds_filter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertFalse(creds_filter(perm=EntityCredentials.VIEW))
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(creds_filter(perm=EntityCredentials.CHANGE)),
        )

    def test_all__delete(self):
        "DELETE + ESET_ALL."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.DELETE,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        has_perm = user.has_perm
        contact1 = self.contact1
        self.assertFalse(has_perm('creme_core.view_entity',   contact1))
        self.assertFalse(has_perm('creme_core.change_entity', contact1))
        self.assertTrue(has_perm('creme_core.delete_entity',  contact1))
        self.assertFalse(has_perm('creme_core.link_entity',   contact1))
        self.assertFalse(has_perm('creme_core.unlink_entity', contact1))

        contact2 = self.contact2
        self.assertFalse(has_perm('creme_core.view_entity',  contact2))
        self.assertTrue(has_perm('creme_core.delete_entity', contact2))

        creds_filter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertFalse(creds_filter(perm=EntityCredentials.VIEW))
        self.assertFalse(creds_filter(perm=EntityCredentials.CHANGE))
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(creds_filter(perm=EntityCredentials.DELETE)),
        )
        self.assertFalse(creds_filter(perm=EntityCredentials.LINK))
        self.assertFalse(creds_filter(perm=EntityCredentials.UNLINK))

    def test_all__link(self):
        "LINK + ESET_ALL."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.LINK,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        has_perm = user.has_perm
        contact1 = self.contact1
        self.assertFalse(has_perm('creme_core.view_entity',   contact1))
        self.assertFalse(has_perm('creme_core.change_entity', contact1))
        self.assertFalse(has_perm('creme_core.delete_entity', contact1))
        self.assertTrue(has_perm('creme_core.link_entity',    contact1))
        self.assertFalse(has_perm('creme_core.unlink_entity', contact1))

        self.assertTrue(has_perm('creme_core.link_fakecontact'))

        contact2 = self.contact2
        self.assertFalse(has_perm('creme_core.view_entity', contact2))
        self.assertTrue(has_perm('creme_core.link_entity',  contact2))

        creds_filter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertFalse(creds_filter(perm=EntityCredentials.VIEW))
        self.assertFalse(creds_filter(perm=EntityCredentials.CHANGE))
        self.assertFalse(creds_filter(perm=EntityCredentials.DELETE))
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(creds_filter(perm=EntityCredentials.LINK)),
        )
        self.assertFalse(creds_filter(perm=EntityCredentials.UNLINK))

    def test_all__unlink(self):
        "UNLINK + ESET_ALL."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.UNLINK,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        has_perm = user.has_perm
        contact1 = self.contact1
        self.assertFalse(has_perm('creme_core.view_entity',   contact1))
        self.assertFalse(has_perm('creme_core.change_entity', contact1))
        self.assertFalse(has_perm('creme_core.delete_entity', contact1))
        self.assertFalse(has_perm('creme_core.link_entity',   contact1))
        self.assertTrue(has_perm('creme_core.unlink_entity',  contact1))

        contact2 = self.contact2
        self.assertFalse(has_perm('creme_core.view_entity',  contact2))
        self.assertTrue(has_perm('creme_core.unlink_entity', contact2))

        creds_filter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertFalse(creds_filter(perm=EntityCredentials.VIEW))
        self.assertFalse(creds_filter(perm=EntityCredentials.CHANGE))
        self.assertFalse(creds_filter(perm=EntityCredentials.DELETE))
        self.assertFalse(creds_filter(perm=EntityCredentials.LINK))
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(creds_filter(perm=EntityCredentials.UNLINK)),
        )

    def test_own__view(self):
        "VIEW + ESET_OWN."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_OWN,
                ),
            ],
        )

        has_perm = user.has_perm
        contact1 = self.contact1
        self.assertTrue(has_perm('creme_core.view_entity',    contact1))
        self.assertFalse(has_perm('creme_core.change_entity', contact1))
        self.assertFalse(has_perm('creme_core.delete_entity', contact1))
        self.assertFalse(has_perm('creme_core.link_entity',   contact1))
        self.assertFalse(has_perm('creme_core.unlink_entity', contact1))

        contact2 = self.contact2
        self.assertFalse(has_perm('creme_core.view_entity',   contact2))
        self.assertFalse(has_perm('creme_core.change_entity', contact2))
        self.assertFalse(has_perm('creme_core.delete_entity', contact2))
        self.assertFalse(has_perm('creme_core.link_entity',   contact2))
        self.assertFalse(has_perm('creme_core.unlink_entity', contact2))

        creds_filter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        ids = [contact1.id]
        self.assertListEqual(ids, self._ids_list(creds_filter()))
        self.assertListEqual(ids, self._ids_list(creds_filter(perm=EntityCredentials.VIEW)))
        self.assertFalse(creds_filter(perm=EntityCredentials.CHANGE))
        self.assertFalse(creds_filter(perm=EntityCredentials.DELETE))
        self.assertFalse(creds_filter(perm=EntityCredentials.LINK))
        self.assertFalse(creds_filter(perm=EntityCredentials.UNLINK))

    def test_own__view_n_change(self):
        "ESET_OWN + VIEW/CHANGE."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.CHANGE | EntityCredentials.DELETE,
                    set_type=SetCredentials.ESET_OWN,
                ),
            ],
        )

        has_perm = user.has_perm
        contact1 = self.contact1
        self.assertFalse(has_perm('creme_core.view_entity',   contact1))
        self.assertTrue(has_perm('creme_core.change_entity',  contact1))
        self.assertTrue(has_perm('creme_core.delete_entity',  contact1))
        self.assertFalse(has_perm('creme_core.link_entity',   contact1))
        self.assertFalse(has_perm('creme_core.unlink_entity', contact1))

        contact2 = self.contact2
        self.assertFalse(has_perm('creme_core.view_entity',   contact2))
        self.assertFalse(has_perm('creme_core.change_entity', contact2))
        self.assertFalse(has_perm('creme_core.delete_entity', contact2))

        creds_filter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        ids = [contact1.id]
        self.assertFalse(creds_filter(perm=EntityCredentials.VIEW))
        self.assertListEqual(ids, self._ids_list(creds_filter(perm=EntityCredentials.CHANGE)))
        self.assertListEqual(ids, self._ids_list(creds_filter(perm=EntityCredentials.DELETE)))
        self.assertFalse(creds_filter(perm=EntityCredentials.LINK))
        self.assertFalse(creds_filter(perm=EntityCredentials.UNLINK))

    def test_own__delete(self):
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.DELETE,
                    set_type=SetCredentials.ESET_OWN,
                ),
            ],
        )

        contact1 = self.contact1

        self.assertFalse(user.has_perm_to_view(contact1))
        self.assertFalse(user.has_perm_to_change(contact1))
        self.assertTrue(user.has_perm_to_delete(contact1))
        self.assertFalse(user.has_perm_to_link(contact1))
        self.assertFalse(user.has_perm_to_unlink(contact1))

        self.assertFalse(user.has_perm_to_delete(self.contact2))

        creds_filter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertFalse(creds_filter(perm=EntityCredentials.VIEW))
        self.assertFalse(creds_filter(perm=EntityCredentials.CHANGE))
        self.assertListEqual(
            [contact1.id],
            self._ids_list(creds_filter(perm=EntityCredentials.DELETE)),
        )
        self.assertFalse(creds_filter(perm=EntityCredentials.LINK))
        self.assertFalse(creds_filter(perm=EntityCredentials.UNLINK))

    def test_own__link_n_unlink(self):
        "ESET_OWN + LINK/UNLINK."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder',
            allowed_apps=['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.LINK | EntityCredentials.UNLINK,
                    set_type=SetCredentials.ESET_OWN,
                ),
            ],
        )

        has_perm = user.has_perm
        contact1 = self.contact1
        self.assertFalse(has_perm('creme_core.view_entity',   contact1))
        self.assertFalse(has_perm('creme_core.change_entity', contact1))
        self.assertFalse(has_perm('creme_core.delete_entity', contact1))
        self.assertTrue(has_perm('creme_core.link_entity',    contact1))
        self.assertTrue(has_perm('creme_core.unlink_entity',  contact1))

        contact2 = self.contact2
        self.assertFalse(has_perm('creme_core.link_entity',   contact2))
        self.assertFalse(has_perm('creme_core.unlink_entity', contact2))

        creds_filter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        ids = [contact1.id]
        self.assertFalse(creds_filter(perm=EntityCredentials.VIEW))
        self.assertFalse(creds_filter(perm=EntityCredentials.CHANGE))
        self.assertFalse(creds_filter(perm=EntityCredentials.DELETE))
        self.assertListEqual(ids, self._ids_list(creds_filter(perm=EntityCredentials.LINK)))
        self.assertListEqual(ids, self._ids_list(creds_filter(perm=EntityCredentials.UNLINK)))

    def test_multiset__all_n_own(self):
        "ESET_ALL + ESET_OWN."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_ALL,
                ),
                SetCredentials(
                    value=EntityCredentials.CHANGE | EntityCredentials.DELETE,
                    set_type=SetCredentials.ESET_OWN,
                ),
            ],
        )

        has_perm = user.has_perm
        contact1 = self.contact1
        self.assertTrue(has_perm('creme_core.view_entity',    contact1))
        self.assertTrue(has_perm('creme_core.change_entity',  contact1))
        self.assertTrue(has_perm('creme_core.delete_entity',  contact1))
        self.assertFalse(has_perm('creme_core.link_entity',   contact1))
        self.assertFalse(has_perm('creme_core.unlink_entity', contact1))

        contact2 = self.contact2
        self.assertTrue(has_perm('creme_core.view_entity',    contact2))
        self.assertFalse(has_perm('creme_core.change_entity', contact2))
        self.assertFalse(has_perm('creme_core.delete_entity', contact2))

        creds_filter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(creds_filter(perm=EntityCredentials.VIEW)),
        )
        self.assertListEqual(
            [contact1.id],
            self._ids_list(creds_filter(perm=EntityCredentials.CHANGE)),
        )
        self.assertListEqual(
            [contact1.id],
            self._ids_list(creds_filter(perm=EntityCredentials.DELETE)),
        )
        self.assertFalse(creds_filter(perm=EntityCredentials.LINK))
        self.assertFalse(creds_filter(perm=EntityCredentials.UNLINK))

    def test_multiset__own_n_all(self):
        "ESET_OWN + ESET_ALL (so ESET_OWN before)."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW
        CHANGE = EntityCredentials.CHANGE
        DELETE = EntityCredentials.DELETE

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(value=VIEW | CHANGE | DELETE, set_type=SetCredentials.ESET_OWN),
                SetCredentials(value=VIEW,                   set_type=SetCredentials.ESET_ALL),
            ],
        )

        contact1 = self.contact1
        self.assertTrue(user.has_perm_to_view(contact1))
        self.assertTrue(user.has_perm_to_change(contact1))
        self.assertTrue(user.has_perm_to_delete(contact1))
        self.assertFalse(user.has_perm_to_link(contact1))
        self.assertFalse(user.has_perm_to_unlink(contact1))

        contact2 = self.contact2
        self.assertTrue(user.has_perm_to_view(contact2))
        self.assertFalse(user.has_perm_to_change(contact2))
        self.assertFalse(user.has_perm_to_delete(contact2))

        creds_filter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertListEqual([contact1.id, contact2.id], self._ids_list(creds_filter(perm=VIEW)))
        self.assertListEqual([contact1.id],              self._ids_list(creds_filter(perm=CHANGE)))
        self.assertListEqual([contact1.id],              self._ids_list(creds_filter(perm=DELETE)))
        self.assertFalse(creds_filter(perm=EntityCredentials.LINK))
        self.assertFalse(creds_filter(perm=EntityCredentials.UNLINK))

    def test_ct_credentials(self):
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_ALL,
                    ctype=FakeContact,
                ),
            ],
        )

        contact1 = self.contact1
        self.assertTrue(user.has_perm_to_view(contact1))  # <=====
        self.assertFalse(user.has_perm_to_change(contact1))
        self.assertFalse(user.has_perm_to_delete(contact1))
        self.assertFalse(user.has_perm_to_link(contact1))
        self.assertFalse(user.has_perm_to_unlink(contact1))

        contact2 = self.contact2
        self.assertTrue(user.has_perm_to_view(contact2))  # <=====
        self.assertFalse(user.has_perm_to_change(contact2))

        orga = FakeOrganisation.objects.create(user=user, name='Yoshioka')
        self.assertFalse(user.has_perm_to_view(orga))  # <=====
        self.assertFalse(user.has_perm_to_change(orga))
        self.assertFalse(user.has_perm_to_delete(orga))
        self.assertFalse(user.has_perm_to_link(orga))
        self.assertFalse(user.has_perm_to_unlink(orga))

        # Filtering ------------------------------------------------------------
        creds_filter = partial(EntityCredentials.filter, user)
        qs = self._build_contact_qs()
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(creds_filter(qs, perm=EntityCredentials.VIEW))
        )
        self.assertFalse(creds_filter(qs, perm=EntityCredentials.CHANGE))
        self.assertFalse(creds_filter(
            FakeOrganisation.objects.filter(pk=orga.id),
            perm=EntityCredentials.VIEW,
        ))

    def test_ct_credentials__error(self):
        "Cannot set CremeEntity."
        role = self._create_role('Coder', allowed_apps=['creme_core'])
        sc = SetCredentials(
            role=role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_ALL,
            ctype=CremeEntity,
        )
        with self.assertRaises(ValueError):
            sc.save()

    def test_forbidden__all(self):
        "ESET_ALL."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW
        ESET_ALL = SetCredentials.ESET_ALL

        creds1 = SetCredentials(value=VIEW, set_type=ESET_ALL)
        self.assertIs(creds1.forbidden, False)

        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                creds1,
                SetCredentials(
                    value=VIEW,
                    set_type=ESET_ALL,
                    ctype=FakeOrganisation,
                    forbidden=True,
                ),
            ],
        )

        contact1 = self.contact1
        self.assertTrue(user.has_perm_to_view(contact1))

        contact2 = self.contact2
        self.assertTrue(user.has_perm_to_view(contact2))

        orga = FakeOrganisation.objects.create(user=user, name='Yoshioka')
        self.assertFalse(user.has_perm_to_view(orga))

        invoice = FakeInvoice.objects.create(user=user, name='Swords & shields')
        self.assertTrue(user.has_perm_to_view(invoice))

        # Filtering ------------------------------------------------------------
        creds_filter = partial(EntityCredentials.filter, user)
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(creds_filter(self._build_contact_qs(), perm=VIEW))
        )
        self.assertFalse(creds_filter(
            FakeOrganisation.objects.filter(pk=orga.id),
            perm=VIEW,
        ))

        self.assertListEqual(
            [contact1.id, contact2.id, invoice.id],
            self._ids_list(EntityCredentials.filter_entities(
                user=user, perm=VIEW,
                queryset=CremeEntity.objects.filter(id__in=[
                    contact1.id, contact2.id, orga.id, invoice.id,
                ]).order_by('id'),
            ))
        )

    def test_forbidden__own_n_all_allowed(self):
        "ESET_OWN forbidden + ESET_ALL allowed."
        self._create_users_n_contacts()
        user = self.user
        other = self.other_user
        team = self.create_team('Teamee', user, other)

        VIEW = EntityCredentials.VIEW
        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_ALL,
                    ctype=FakeOrganisation,
                ),
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_OWN,
                    forbidden=True,
                ),
            ],
        )

        contact1 = self.contact1
        self.assertFalse(user.has_perm_to_view(contact1))

        contact2 = self.contact2
        self.assertFalse(user.has_perm_to_view(contact2))

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=other, name='Yoshioka')
        self.assertTrue(user.has_perm_to_view(orga1))

        orga2 = create_orga(user=user, name='Miyamoto')
        self.assertFalse(user.has_perm_to_view(orga2))

        orga3 = create_orga(user=team, name='Sasaki')
        self.assertFalse(user.has_perm_to_view(orga3))

        # Filtering ------------------------------------------------------------
        ec_filter = partial(EntityCredentials.filter, user)
        self.assertFalse(ec_filter(self._build_contact_qs(), perm=VIEW))
        self.assertListEqual(
            [orga1.id],
            self._ids_list(ec_filter(
                FakeOrganisation.objects.filter(pk__in=[orga1.id, orga2.id, orga3.id]),
                perm=VIEW,
            ))
        )
        self.assertListEqual(
            [orga1.id],
            self._ids_list(EntityCredentials.filter_entities(
                user=user, perm=VIEW,
                queryset=CremeEntity.objects.filter(id__in=[
                    contact1.id, contact2.id, orga1.id, orga2.id, orga3.id,
                ]).order_by('id'),
            ))
        )

    def test_forbidden__own_n_also_allowed(self):
        "ESET_OWN forbidden & allowed."
        self._create_users_n_contacts()
        user = self.user

        VIEW = EntityCredentials.VIEW
        ESET_OWN = SetCredentials.ESET_OWN

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(value=VIEW, set_type=ESET_OWN),
                SetCredentials(value=VIEW, set_type=ESET_OWN, forbidden=True),
            ],
        )

        contact1 = self.contact1
        self.assertFalse(user.has_perm_to_view(self.contact1))

        contact2 = self.contact2
        self.assertFalse(user.has_perm_to_view(self.contact2))

        self.assertFalse(EntityCredentials.filter(user, self._build_contact_qs(), perm=VIEW))
        self.assertFalse(
            EntityCredentials.filter_entities(
                user=user, perm=VIEW,
                queryset=CremeEntity.objects.filter(id__in=[contact1.id, contact2.id]),
            )
        )

    def test_forbidden__on_model__all_forbidden(self):
        "Permission on model (LINK on future instances) - ESET_ALL forbidden."
        user, other = self._create_users()
        LINK = EntityCredentials.LINK

        self._create_role(
            'Coder',
            allowed_apps=['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(value=LINK, set_type=SetCredentials.ESET_OWN),
                SetCredentials(
                    value=LINK,
                    set_type=SetCredentials.ESET_ALL,
                    ctype=FakeOrganisation,
                    forbidden=True
                ),
            ],
        )
        self.assertTrue(user.has_perm_to_link(FakeContact, owner=None))
        self.assertFalse(user.has_perm_to_link(FakeOrganisation, owner=None))

        self.assertTrue(user.has_perm_to_link(FakeContact, owner=user))
        self.assertFalse(user.has_perm_to_link(FakeOrganisation, owner=user))

        self.assertFalse(user.has_perm_to_link(FakeContact, owner=other))
        self.assertFalse(user.has_perm_to_link(FakeOrganisation, owner=other))

    def test_forbidden__on_model__own_forbidden(self):
        "Permission on model (LINK on future instances) - ESET_OWN forbidden."
        user, other = self._create_users()
        LINK = EntityCredentials.LINK

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(value=LINK, set_type=SetCredentials.ESET_ALL),
                SetCredentials(
                    value=LINK,
                    set_type=SetCredentials.ESET_OWN,
                    ctype=FakeOrganisation,
                    forbidden=True,
                ),
            ],
        )
        self.assertTrue(user.has_perm_to_link(FakeContact, owner=user))
        self.assertFalse(user.has_perm_to_link(FakeOrganisation, owner=user))

        self.assertTrue(user.has_perm_to_link(FakeContact, owner=None))
        self.assertTrue(user.has_perm_to_link(FakeOrganisation, owner=None))

        self.assertTrue(user.has_perm_to_link(FakeContact, owner=other))
        self.assertTrue(user.has_perm_to_link(FakeOrganisation, owner=other))

        team = self.create_team('Teamee', user, other)
        self.assertTrue(user.has_perm_to_link(FakeContact, owner=team))
        self.assertFalse(user.has_perm_to_link(FakeOrganisation, owner=team))

    def test_with_efilter__check(self):
        "Check ESET_FILTER."
        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )

        role = self.create_role()

        build_sc = partial(
            SetCredentials,
            role=role, value=EntityCredentials.VIEW, ctype=FakeContact,
        )

        sc1 = build_sc(set_type=SetCredentials.ESET_ALL, efilter=efilter)
        with self.assertRaises(ValueError):
            sc1.save()

        sc2 = build_sc(set_type=SetCredentials.ESET_OWN, efilter=efilter)
        with self.assertRaises(ValueError):
            sc2.save()

        sc3 = build_sc(set_type=SetCredentials.ESET_FILTER)
        with self.assertRaises(ValueError):
            sc3.save()

        sc4 = build_sc(
            set_type=SetCredentials.ESET_FILTER, efilter=efilter, ctype=FakeOrganisation,
        )
        with self.assertRaises(ValueError):
            sc4.save()

    def test_with_efilter__one_filter(self):
        "ESET_FILTER x 1."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2
        contact3 = FakeContact.objects.create(
            user=self.other_user,
            first_name=contact2.first_name,
            last_name=contact1.last_name,  # <== accepted
        )

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=[contact1.last_name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    ctype=FakeContact,
                    efilter=efilter,
                ),
            ],
        )

        orga = FakeOrganisation.objects.create(user=user, name=contact1.last_name)

        user = self.refresh(user)
        self.assertEqual(
            entity_filter_registries[EF_CREDENTIALS],
            user.role.credentials.first().efilter.registry,
        )

        # Filtering ------------------------------------------------------------
        ec_filter = partial(EntityCredentials.filter, user)
        self.assertCountEqual(
            [contact1, contact3],
            ec_filter(self._build_contact_qs(contact3), perm=VIEW),
        )
        self.assertFalse(ec_filter(
            FakeOrganisation.objects.filter(pk=orga.id),
            perm=VIEW,
        ))

        # Check simple entities ------------------------------------------------
        self.assertTrue(user.has_perm_to_view(contact1))
        self.assertFalse(user.has_perm_to_change(contact1))

        self.assertFalse(user.has_perm_to_view(contact2))
        self.assertTrue(user.has_perm_to_view(contact3))

        self.assertFalse(user.has_perm_to_view(orga))

        # Check base entity
        base_entity = CremeEntity.objects.get(id=contact1.id)
        self.assertTrue(user.has_perm_to_view(base_entity))
        self.assertFalse(user.has_perm_to_change(base_entity))

        # Filter base entity
        qs = CremeEntity.objects.filter(id__in=[contact1.id, contact2.id])

        with self.assertRaises(EntityCredentials.FilteringError):
            EntityCredentials.filter_entities(
                user=user, perm=VIEW, queryset=qs,
            )

        with self.assertRaises(EntityCredentials.FilteringError):
            EntityCredentials.filter_entities(
                user=user, perm=VIEW, queryset=qs,
                as_model=FakeContact,
            )

    def test_with_efilter__forbidden(self):
        "ESET_FILTER (forbidden)."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2
        contact3 = FakeContact.objects.create(
            user=user,
            first_name=contact2.first_name,
            last_name=contact1.last_name,  # <== rejected
        )

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=[contact1.last_name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    set_type=SetCredentials.ESET_FILTER,
                    value=VIEW,
                    ctype=FakeContact,
                    efilter=efilter,
                    forbidden=True,
                ),
            ],
        )

        # Filtering ------------------------------------------------------------
        self.assertFalse(
            EntityCredentials.filter(
                user=user, perm=VIEW,
                queryset=self._build_contact_qs(contact3),
            )
        )

        # Check simple entities ------------------------------------------------
        self.assertFalse(user.has_perm_to_view(contact1))
        self.assertFalse(user.has_perm_to_view(contact2))

    def test_with_efilter__forbidden_n_all(self):
        "ESET_FILTER (forbidden) + ESET_ALL."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2
        contact3 = FakeContact.objects.create(
            user=user,
            first_name=contact2.first_name,
            last_name=contact1.last_name,  # <== rejected
        )

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=[contact1.last_name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        build_cred = partial(SetCredentials, value=VIEW, ctype=FakeContact)
        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                build_cred(set_type=SetCredentials.ESET_FILTER, efilter=efilter, forbidden=True),
                build_cred(set_type=SetCredentials.ESET_ALL),
            ],
        )

        # Filtering ------------------------------------------------------------
        self.assertCountEqual(
            [contact2],
            EntityCredentials.filter(
                user=user, perm=VIEW,
                queryset=self._build_contact_qs(contact3),
            )
        )

        # Check simple entities ------------------------------------------------
        self.assertFalse(user.has_perm_to_view(contact1))
        self.assertTrue(user.has_perm_to_view(contact2))
        self.assertFalse(user.has_perm_to_view(contact3))

    def test_with_efilter__own_forbidden(self):
        "ESET_OWN (forbidden) + ESET_FILTER."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2
        contact3 = FakeContact.objects.create(
            user=self.other_user,  # <== not rejected
            first_name=contact2.first_name,
            last_name=contact1.last_name,  # <== accepted
        )

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=[contact1.last_name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        build_cred = partial(SetCredentials, value=VIEW, ctype=FakeContact)
        self._create_role(
            'Coder',
            allowed_apps=['creme_core'], users=[user],
            set_creds=[
                build_cred(set_type=SetCredentials.ESET_OWN, forbidden=True),
                build_cred(set_type=SetCredentials.ESET_FILTER, efilter=efilter),
            ],
        )

        # Filtering ------------------------------------------------------------
        self.assertCountEqual(
            [contact3],
            EntityCredentials.filter(
                user=user, perm=VIEW,
                queryset=self._build_contact_qs(contact3),
            )
        )

        # Check simple entities ------------------------------------------------
        self.assertFalse(user.has_perm_to_view(contact1))
        self.assertFalse(user.has_perm_to_view(contact2))
        self.assertTrue(user.has_perm_to_view(contact3))

    def test_with_efilter__all(self):
        "ESET_FILTER + ESET_ALL (created AFTER)."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=[contact1.last_name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        build_cred = partial(SetCredentials, value=VIEW, ctype=FakeContact)
        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                build_cred(set_type=SetCredentials.ESET_FILTER, efilter=efilter),
                build_cred(set_type=SetCredentials.ESET_ALL),
            ],
        )

        # Filtering ------------------------------------------------------------
        self.assertCountEqual(
            [contact1, self.contact2],
            EntityCredentials.filter(
                user=user,
                perm=VIEW,
                queryset=self._build_contact_qs(),
            )
        )

    def test_with_efilter__own(self):
        "ESET_FILTER + ESET_OWN."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2
        create_contact = FakeContact.objects.create
        contact3 = create_contact(
            user=user,  # <== accepted
            first_name=contact1.first_name,
            last_name=contact2.last_name,
        )
        contact4 = create_contact(
            user=self.other_user,
            first_name=contact2.first_name,
            last_name=contact1.last_name,  # <== accepted
        )

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=[contact1.last_name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        build_cred = partial(SetCredentials, value=VIEW, ctype=FakeContact)
        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                build_cred(set_type=SetCredentials.ESET_FILTER, efilter=efilter),
                build_cred(set_type=SetCredentials.ESET_OWN),
            ],
        )

        # Filtering ------------------------------------------------------------
        self.assertCountEqual(
            [contact1, contact3, contact4],
            EntityCredentials.filter(
                user=user, perm=VIEW,
                queryset=self._build_contact_qs(contact3, contact4),
            )
        )

    def test_with_efilter__2_efilters(self):
        "ESET_FILTER x 2."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2
        create_contact = partial(FakeContact.objects.create, user=user)
        contact3 = create_contact(
            first_name=contact2.first_name,
            last_name=contact1.last_name,  # <== accepted
        )
        contact4 = create_contact(
            first_name=contact1.first_name,  # <== accepted
            last_name=contact2.last_name,
        )
        contact5 = create_contact(
            first_name=contact2.first_name,
            last_name=contact2.last_name,
        )

        efilter1 = EntityFilter.objects.create(
            id='creme_core-test_auth1',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=[contact1.last_name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        efilter2 = EntityFilter.objects.create(
            id='creme_core-test_auth2',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='first_name', values=[contact1.first_name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder',
            allowed_apps=['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW, set_type=SetCredentials.ESET_FILTER,
                    ctype=FakeContact, efilter=efilter1,
                ),
                SetCredentials(
                    value=VIEW, set_type=SetCredentials.ESET_FILTER,
                    ctype=FakeContact, efilter=efilter2,
                ),
            ],
        )

        # Filtering ------------------------------------------------------------
        ec_filter = partial(EntityCredentials.filter, user)
        self.assertCountEqual(
            [contact1, contact3, contact4],
            ec_filter(self._build_contact_qs(contact3, contact4, contact5), perm=VIEW)
        )

    def test_with_efilter__forbidden_x2(self):
        "ESET_FILTER (forbidden) x 2."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2
        create_contact = partial(FakeContact.objects.create, user=user)
        contact3 = create_contact(
            first_name=contact2.first_name,
            last_name=contact1.last_name,  # <== rejected
        )
        contact4 = create_contact(
            first_name=contact1.first_name,  # <== rejected
            last_name=contact2.last_name,
        )
        contact5 = create_contact(
            first_name=contact2.first_name,
            last_name=contact2.last_name,
        )

        efilter1 = EntityFilter.objects.create(
            id='creme_core-test_auth1',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=[contact1.last_name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        efilter2 = EntityFilter.objects.create(
            id='creme_core-test_auth2',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='first_name', values=[contact1.first_name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    ctype=FakeContact,
                    efilter=efilter1,
                    forbidden=True,
                ),
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    ctype=FakeContact,
                    efilter=efilter2,
                    forbidden=True,
                ),
                SetCredentials(value=VIEW, set_type=SetCredentials.ESET_ALL),
            ],
        )

        # Filtering ------------------------------------------------------------
        ec_filter = partial(EntityCredentials.filter, user)
        self.assertCountEqual(
            [contact2, contact5],
            ec_filter(self._build_contact_qs(contact3, contact4, contact5), perm=VIEW)
        )

    def test_with_efilter__allowed_n_forbidden(self):
        "ESET_FILTER x 2: allowed + forbidden."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2
        create_contact = partial(FakeContact.objects.create, user=user)
        contact3 = create_contact(
            first_name=contact2.first_name,
            last_name=contact1.last_name,  # <== accepted
        )
        contact4 = create_contact(
            first_name=contact1.first_name,  # <== rejected
            last_name=contact2.last_name,
        )
        contact5 = create_contact(
            first_name=contact2.first_name,
            last_name=contact2.last_name,
        )

        efilter1 = EntityFilter.objects.create(
            id='creme_core-test_auth1',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='last_name', values=[contact1.last_name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        efilter2 = EntityFilter.objects.create(
            id='creme_core-test_auth2',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.IEQUALS,
                    field_name='first_name', values=[contact1.first_name],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    ctype=FakeContact,
                    efilter=efilter1,
                ),
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    ctype=FakeContact,
                    efilter=efilter2,
                    forbidden=True,
                ),
            ],
        )

        # Filtering ------------------------------------------------------------
        ec_filter = partial(EntityCredentials.filter, user)
        self.assertCountEqual(
            [contact3],
            ec_filter(self._build_contact_qs(contact3, contact4, contact5), perm=VIEW)
        )

    def test_with_efilter__condition_on_user__equals(self):
        "ESET_FILTER on CremeEntity + <user> argument."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2

        create_contact = FakeContact.objects.create
        contact3 = create_contact(
            user=user,
            first_name=contact2.first_name,
            last_name=contact1.last_name,
        )
        contact4 = create_contact(
            user=self.other_user,
            first_name=contact1.first_name,
            last_name=contact2.last_name,
        )

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=CremeEntity,
                    operator=operators.EQUALS,
                    field_name='user',
                    values=[operands.CurrentUserOperand.type_id],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    # ctype=CremeEntity,
                    efilter=efilter,
                ),
            ],
        )

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user,            name='Orga1')
        orga2 = create_orga(user=self.other_user, name='Orga2')

        # Filtering ------------------------------------------------------------
        ec_filter = partial(EntityCredentials.filter, user)
        self.assertCountEqual(
            [contact1, contact3],
            ec_filter(self._build_contact_qs(contact3, contact4), perm=VIEW)
        )
        self.assertCountEqual(
            [orga1],
            ec_filter(FakeOrganisation.objects.filter(pk__in=(orga1.id, orga2.id)), perm=VIEW),
        )

        # Filtering CremeEntities ----------------------------------------------
        with self.assertNoException():
            ids_list = self._ids_list(EntityCredentials.filter_entities(
                user=user, perm=VIEW,
                queryset=CremeEntity.objects.filter(id__in=[
                    contact1.id, contact2.id, contact3.id, contact4.id,
                    orga1.id, orga2.id,
                ]).order_by('id'),
            ))

        self.assertListEqual([contact1.id, contact3.id, orga1.id], ids_list)

    def test_with_efilter__condition_on_user__equals_not(self):
        "<user> argument + forbidden."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2

        create_contact = FakeContact.objects.create
        contact3 = create_contact(
            user=self.other_user,
            first_name=contact2.first_name,
            last_name=contact1.last_name,
        )
        contact4 = create_contact(
            user=user,
            first_name=contact1.first_name,
            last_name=contact2.last_name,
        )

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS_NOT,
                    field_name='user',
                    values=[operands.CurrentUserOperand.type_id],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        build_cred = partial(SetCredentials, value=VIEW, ctype=FakeContact)
        self._create_role(
            'Coder',
            allowed_apps=['creme_core'],
            users=[user],
            set_creds=[
                build_cred(
                    set_type=SetCredentials.ESET_FILTER,
                    efilter=efilter,
                    forbidden=True,
                ),
                build_cred(set_type=SetCredentials.ESET_ALL),
            ],
        )

        # Filtering ------------------------------------------------------------
        ec_filter = partial(EntityCredentials.filter, user)
        self.assertCountEqual(
            [contact1, contact4],
            ec_filter(self._build_contact_qs(contact3, contact4), perm=VIEW)
        )

        # Filtering CremeEntities ----------------------------------------------
        with self.assertNoException():
            ids_list = self._ids_list(EntityCredentials.filter_entities(
                user=user, perm=VIEW,
                queryset=CremeEntity.objects.filter(id__in=[
                    contact1.id, contact2.id, contact3.id, contact4.id,
                ]).order_by('id'),
            ))

        self.assertListEqual([contact1.id, contact4.id], ids_list)

    def test_creation_creds(self):
        user = self.create_user()
        role = self._create_role('Coder', users=[user])

        has_perm = user.has_perm
        has_perm_to_create = user.has_perm_to_create

        self.assertFalse(has_perm('creme_core.add_cremeproperty'))
        self.assertFalse(has_perm('creme_core.add_relation'))
        self.assertFalse(has_perm_to_create(CremeProperty))

        self.assertFalse(user.has_perms(['creme_core.add_cremeproperty']))
        self.assertFalse(user.has_perms('creme_core.add_cremeproperty'))

        msg = _('You are not allowed to create: {}').format(_('Property'))
        with self.assertRaises(PermissionDenied) as cm1:
            user.has_perm_or_die('creme_core.add_cremeproperty')
        self.assertEqual(msg, str(cm1.exception))

        with self.assertRaises(PermissionDenied) as cm2:
            user.has_perms_or_die('creme_core.add_cremeproperty')
        self.assertEqual(msg, str(cm2.exception))

        with self.assertRaises(PermissionDenied) as cm3:
            user.has_perms_or_die(['creme_core.add_cremeproperty'])
        self.assertEqual(msg, str(cm3.exception))

        # ---
        get_ct = ContentType.objects.get_for_model
        role.creatable_ctypes.set([get_ct(CremeProperty), get_ct(Relation)])

        user.role = self.refresh(role)  # Refresh cache
        self.assertTrue(has_perm('creme_core.add_cremeproperty'))
        self.assertTrue(has_perm('creme_core.add_relation'))
        self.assertFalse(has_perm('creme_core.add_cremepropertytype'))

        self.assertTrue(user.has_perms(['creme_core.add_cremeproperty']))
        self.assertTrue(user.has_perms('creme_core.add_cremeproperty'))
        self.assertFalse(user.has_perms([
            'creme_core.add_cremeproperty', 'creme_core.add_cremepropertytype'
        ]))

        with self.assertNoException():
            user.has_perms_or_die('creme_core.add_cremeproperty')
            user.has_perms_or_die(['creme_core.add_cremeproperty'])

        self.assertTrue(has_perm_to_create(CremeProperty))
        self.assertFalse(has_perm_to_create(CremePropertyType))

        entity = CremeEntity.objects.create(user=user)
        ptype = CremePropertyType.objects.create(text='text')
        prop  = CremeProperty.objects.create(type=ptype, creme_entity=entity)
        self.assertTrue(has_perm_to_create(prop))
        self.assertFalse(has_perm_to_create(ptype))

        with self.assertNoException():
            user.has_perm_to_create_or_die(prop)

        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_to_create_or_die(ptype)
        self.assertEqual(
            _('You are not allowed to create: {}').format(_('Type of property')),
            str(cm.exception),
        )

    def test_creation_creds__superuser(self):
        user = self.build_user(is_superuser=True)
        self.assertTrue(user.has_perm('creme_core.add_cremeproperty'))

    def test_creation_creds__custom_entities(self):
        user = self.create_user()
        role = self._create_role('Coder', users=[user])

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Lab'
        ce_type.plural_name = 'Labs'
        ce_type.save()

        msg = _('You are not allowed to create: {}').format(ce_type.name)
        with self.assertRaises(PermissionDenied) as model_cm:
            user.has_perm_to_create_or_die(ce_type.entity_model)
        self.assertEqual(msg, str(model_cm.exception))

        entity = ce_type.entity_model.objects.create(user=user, name='Whatever')
        with self.assertRaises(PermissionDenied) as instance_cm:
            user.has_perm_to_create_or_die(entity)
        self.assertEqual(msg, str(instance_cm.exception))

        with self.assertRaises(PermissionDenied) as ct_cm:
            user.has_perm_to_create_or_die(entity.entity_type)
        self.assertEqual(msg, str(ct_cm.exception))

        # ---
        role.creatable_ctypes.set([entity.entity_type])
        user.role = self.refresh(role)  # Refresh cache

        with self.assertNoException():
            user.has_perm_to_create_or_die(ce_type.entity_model)

    def test_creation_creds__disabled_custom_entity_type(self):
        user = self.get_root_user()

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        self.assertFalse(ce_type.enabled)

        model = ce_type.entity_model

        self.assertFalse(user.has_perm_to_create(model))

        with self.assertRaises(PermissionDenied) as enabled_cm:
            user.has_perm_to_create_or_die(model)
        self.assertEqual(
            _('You are not allowed to create: {}').format(_('Invalid custom type')),
            str(enabled_cm.exception)
        )

    def test_creation_creds__deleted_custom_entity_type(self):
        user = self.get_root_user()

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Lab'
        ce_type.plural_name = 'Labs'
        ce_type.deleted = True
        ce_type.save()

        model = ce_type.entity_model

        self.assertFalse(user.has_perm_to_create(model))

        with self.assertRaises(PermissionDenied) as enabled_cm:
            user.has_perm_to_create_or_die(model)
        self.assertEqual(
            _('You are not allowed to create: {}').format(
                _('{custom_model} [deleted]').format(custom_model=ce_type.name)
            ),
            str(enabled_cm.exception),
        )

    def test_list_creds__regular_user(self):
        user = self.create_user()
        role = self._create_role('Coder', ['creme_core'], users=[user])  # 'persons'

        get_ct = ContentType.objects.get_for_model
        contact_ct = get_ct(FakeContact)
        orga_ct = get_ct(FakeOrganisation)
        with self.assertNumQueries(1):
            self.assertFalse(role.can_list(contact_ct))
        with self.assertNumQueries(0):
            self.assertFalse(role.can_list(orga_ct))

        self.assertFalse(user.has_perm('persons.list_contact'))
        self.assertFalse(user.has_perm('persons.list_organisation'))
        self.assertFalse(user.has_perm_to_list(FakeContact))

        error_msg = _('You are not allowed to list: {}').format('Test Contact')
        with self.assertRaises(PermissionDenied) as cm1:
            user.has_perm_to_list_or_die(contact_ct)
        self.assertEqual(error_msg, str(cm1.exception))

        with self.assertRaises(PermissionDenied) as cm2:
            user.has_perm_or_die('creme_core.list_fakecontact')
        self.assertEqual(error_msg, str(cm2.exception))

        # ---
        role.listable_ctypes.add(contact_ct)

        user.role = role = self.refresh(role)  # Refresh cache
        self.assertTrue(role.can_list(contact_ct))
        self.assertFalse(role.can_list(orga_ct))

        self.assertTrue(user.has_perm('creme_core.list_fakecontact'))
        self.assertFalse(user.has_perm('creme_core.list_fakeorganisation'))
        self.assertTrue(user.has_perm_to_list(FakeContact))
        self.assertFalse(user.has_perm_to_list(FakeOrganisation))

        # Version with exception ---
        with self.assertNoException():
            user.has_perm_to_list_or_die(FakeContact)

        self.assertRaises(PermissionDenied, user.has_perm_to_list_or_die, FakeOrganisation)

    def test_list_creds__superuser(self):
        user = self.build_user(is_superuser=True)
        self.assertTrue(user.has_perm('persons.list_contact'))
        self.assertTrue(user.has_perm_to_list(FakeContact))

    def test_export_creds__regular_user(self):
        user = self.create_user()
        role = self._create_role('Coder', ['creme_core'], users=[user])  # 'persons'

        has_perm = user.has_perm
        has_perm_to_export = user.has_perm_to_export

        self.assertFalse(has_perm('persons.export_contact'))
        self.assertFalse(has_perm('persons.export_organisation'))
        self.assertFalse(has_perm_to_export(FakeContact))

        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_or_die('creme_core.export_fakecontact')
        self.assertEqual(
            _('You are not allowed to export: {}').format('Test Contact'),
            str(cm.exception),
        )

        # ---
        role.exportable_ctypes.add(ContentType.objects.get_for_model(FakeContact))

        user.role = self.refresh(role)  # Refresh cache
        self.assertTrue(has_perm('creme_core.export_fakecontact'))
        self.assertFalse(has_perm('creme_core.export_fakeorganisation'))
        self.assertTrue(has_perm_to_export(FakeContact))
        self.assertFalse(has_perm_to_export(FakeOrganisation))

        # Version with exception ---
        with self.assertNoException():
            user.has_perm_to_export_or_die(FakeContact)

        self.assertRaises(PermissionDenied, user.has_perm_to_export_or_die, FakeOrganisation)

    def test_export_creds__superuser(self):
        user = self.build_user(is_superuser=True)
        self.assertTrue(user.has_perm('persons.export_contact'))

    # TODO: test extending apps
    def test_app_creds(self):
        user = self.create_user()
        role = self._create_role('Salesman', users=[user])

        self.assertFalse(user.has_perm('creme_core'))
        self.assertFalse(user.has_perm('creme_config'))
        self.assertFalse(role.allowed_apps)

        self.assertFalse(user.has_perm_to_access('creme_core'))
        self.assertFalse(user.has_perm_to_access('creme_config'))

        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_to_access_or_die('creme_core')
        self.assertEqual(
            _('You are not allowed to access to the app: {}').format(_('Core')),
            str(cm.exception),
        )

        role.allowed_apps = ['creme_core', 'creme_config']
        role.save()

        user = self.refresh(user)
        role = user.role
        allowed_apps = role.allowed_apps
        self.assertEqual(2, len(allowed_apps))
        self.assertIn('creme_core',   allowed_apps)
        self.assertIn('creme_config', allowed_apps)

        self.assertEqual(allowed_apps, role.extended_allowed_apps)

        self.assertTrue(user.has_perm('creme_core'))
        self.assertTrue(user.has_perm('creme_config'))
        if apps.is_installed('creme.documents'):
            self.assertFalse(user.has_perm('documents'))

        with self.assertNoException():
            user.has_perm_to_access_or_die('creme_core')

        self.assertTrue(user.has_perm_to_access('creme_core'))
        self.assertTrue(user.has_perm_to_access('creme_config'))
        if apps.is_installed('creme.documents'):
            self.assertFalse(user.has_perm_to_access('documents'))

    # TODO: test extending apps
    def test_app_creds__admin(self):
        user = self.create_user()
        role = self._create_role('CEO', users=[user])

        self.assertTrue(apps.is_installed('creme.documents'))
        self.assertTrue(apps.is_installed('creme.persons'))

        self.assertFalse(user.has_perm_to_admin('creme_core'))
        self.assertFalse(user.has_perm_to_admin('documents'))
        self.assertFalse(user.has_perm('creme_core.can_admin'))
        self.assertFalse(user.has_perm('documents.can_admin'))
        self.assertFalse(role.admin_4_apps)

        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_to_admin_or_die('creme_core')

        fmt = _('You are not allowed to configure this app: {}').format
        self.assertEqual(fmt(_('Core')), str(cm.exception))

        role.admin_4_apps = ['creme_core', 'documents']
        role.save()

        user = self.refresh(user)
        role = user.role
        admin_4_apps = user.role.admin_4_apps
        self.assertEqual(2, len(admin_4_apps))
        self.assertIn('creme_core', admin_4_apps)
        self.assertIn('documents',  admin_4_apps)

        self.assertEqual(admin_4_apps, role.extended_admin_4_apps)

        self.assertTrue(user.has_perm_to_admin('creme_core'))
        self.assertTrue(user.has_perm_to_admin('documents'))
        self.assertFalse(user.has_perm_to_admin('persons'))
        self.assertTrue(user.has_perm('creme_core.can_admin'))
        self.assertTrue(user.has_perm('documents.can_admin'))
        self.assertFalse(user.has_perm('persons.can_admin'))

        with self.assertNoException():
            user.has_perm_to_admin_or_die('creme_core')
            user.has_perm_to_admin_or_die('documents')
            user.has_perm_or_die('documents.can_admin')

        invalid_app = 'persons'
        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_to_admin_or_die(invalid_app)

        self.assertEqual(
            fmt(apps.get_app_config('persons').verbose_name), str(cm.exception),
        )

        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_or_die(f'{invalid_app}.can_admin')

        self.assertEqual(
            fmt(apps.get_app_config('persons').verbose_name), str(cm.exception),
        )

        self.assertTrue(user.has_perm('creme_core'))
        self.assertTrue(user.has_perm('documents'))
        self.assertFalse(user.has_perm('persons'))

        with self.assertNoException():
            user.has_perm_or_die('documents')

        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_or_die('persons')
        self.assertEqual(
            _('You are not allowed to access to the app: {}').format(
                _('Accounts and Contacts')
            ),
            str(cm.exception),
        )

    def test_app_creds__superuser(self):
        user = self.build_user(is_superuser=True)

        self.assertTrue(user.has_perm_to_admin('creme_core'))
        self.assertTrue(user.has_perm_to_access('creme_core'))

        has_perm = user.has_perm
        self.assertTrue(has_perm('creme_core'))
        self.assertTrue(has_perm('creme_core.can_admin'))

    def test_edition_creds__custom_entities(self):
        user = self.get_root_user()

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Lab'
        ce_type.plural_name = 'Labs'
        ce_type.save()

        entity = ce_type.entity_model.objects.create(user=user, name='Whatever')
        self.assertTrue(user.has_perm_to_change(entity))

        with self.assertNoException():
            user.has_perm_to_change_or_die(entity)

    # NB: should not happen (a type can be disabled only if it ahs no related entity)
    # def test_edition_creds__disabled_custom_entity_type(self):
    #     user = self.get_root_user()
    #
    #     ce_type = self.get_object_or_fail(CustomEntityType, id=1)
    #     self.assertFalse(ce_type.enabled)
    #
    #     entity = ce_type.entity_model.objects.create(user=user, name='Whatever')
    #     self.assertFalse(user.has_perm_to_change(entity))
    #
    #     with self.assertRaises(PermissionDenied) as cm:
    #         user.has_perm_to_change_or_die(entity)
    #     self.assertEqual(
    #         _('You are not allowed to edit this entity: {}').format(entity.name),
    #         str(cm.exception),
    #     )

    def test_edition_creds__deleted_custom_entity_type(self):
        user = self.get_root_user()

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Lab'
        ce_type.plural_name = 'Labs'
        ce_type.deleted = True
        ce_type.save()

        entity = ce_type.entity_model.objects.create(user=user, name='Whatever')
        self.assertFalse(user.has_perm_to_change(entity))

        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_to_change_or_die(entity)
        self.assertEqual(
            _('You are not allowed to edit this entity: {}').format(entity.name),
            str(cm.exception),
        )

    def test_link_creds__custom_entities(self):
        user = self.get_root_user()

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Lab'
        ce_type.plural_name = 'Labs'
        ce_type.save()

        model = ce_type.entity_model
        self.assertTrue(user.has_perm_to_link(model))

        entity = model.objects.create(user=user, name='Whatever')
        self.assertTrue(user.has_perm_to_link(entity))

        with self.assertNoException():
            user.has_perm_to_link_or_die(entity)

    def test_link_creds__deleted_custom_entity_type(self):
        user = self.get_root_user()

        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        ce_type.enabled = True
        ce_type.name = 'Lab'
        ce_type.plural_name = 'Labs'
        ce_type.deleted = True
        ce_type.save()

        model = ce_type.entity_model
        self.assertFalse(user.has_perm_to_link(model))

        entity = model.objects.create(user=user, name='Whatever')
        self.assertFalse(user.has_perm_to_link(entity))

        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_to_link_or_die(entity)
        self.assertEqual(
            _('You are not allowed to link this entity: {}').format(entity.name),
            str(cm.exception),
        )

    def test_team_credentials(self):
        user, other = self._create_users()
        self._create_role(
            'Worker', ['creme_core'],
            users=[user, other],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_OWN,
                ),
            ],
        )

        team = self.create_team('Teamee', user)

        entity = self.refresh(
            FakeContact.objects.create(user=team, first_name='Ito', last_name='Ittosaï')
        )  # No cache
        user = self.refresh(user)  # Refresh cache

        with self.assertNumQueries(3):  # Role, SetCredentials & teams
            can_view = user.has_perm_to_view(entity)
        self.assertTrue(can_view)  # Belongs to the team

        with self.assertNumQueries(0):  # Role, SetCredentials & teams -> cached
            can_change = user.has_perm_to_change(entity)
        self.assertFalse(can_change)

        self.assertFalse(other.has_perm_to_view(entity))

        # 'teams' property------------------------------------------------------
        self.assertListEqual([team], user.teams)
        self.assertListEqual([],     other.teams)

        # Filtering ------------------------------------------------------------
        user = self.refresh(user)  # Refresh caches

        qs = FakeContact.objects.filter(pk=entity.id)
        creds_filter = EntityCredentials.filter

        with self.assertNumQueries(3):  # Role, SetCredentials & teams
            viewable = creds_filter(user, qs, perm=EntityCredentials.VIEW)
        self.assertListEqual([entity.id], self._ids_list(viewable))  # Belongs to the team

        with self.assertNumQueries(0):  # Role, SetCredentials & teams --> cache
            editable = creds_filter(user, qs, perm=EntityCredentials.CHANGE)
        self.assertFalse(editable)

        self.assertFalse(creds_filter(other, qs, perm=EntityCredentials.VIEW))

    def test_team_credentials__several_teams(self):
        "User in several teams."
        user, other = self._create_users()
        self._create_role(
            'Worker', ['creme_core'],
            users=[user, other],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_OWN,
                ),
            ],
        )

        create_team = self.create_team
        team1 = create_team('Teamee 1', user)
        team2 = create_team('Teamee 2', other, user)
        team3 = create_team('Teamee 3', other)

        create_user = FakeContact.objects.create
        entity1 = create_user(user=team1, first_name='Munisai', last_name='Shinmen')
        self.assertTrue(user.has_perm_to_view(entity1))  # Belongs to the team
        self.assertFalse(user.has_perm_to_change(entity1))
        self.assertFalse(other.has_perm_to_view(entity1))

        entity2 = create_user(user=team2, first_name='Kempo', last_name='Yoshioka')
        self.assertTrue(user.has_perm_to_view(entity2))  # Belongs to the team
        self.assertFalse(user.has_perm_to_change(entity2))
        self.assertTrue(other.has_perm_to_view(entity2))
        self.assertFalse(other.has_perm_to_change(entity2))

        # 'teams' property------------------------------------------------------
        self.assertCountEqual([team1, team2], user.teams)

        with self.assertNumQueries(0):  # Teams are cached
            user.teams  # NOQA

        # Filtering ------------------------------------------------------------
        entity3 = create_user(user=team3, first_name='Ryohei', last_name='Ueda')

        qs = FakeContact.objects.filter(pk__in=[entity1.id, entity2.id, entity3.id])
        creds_filter = EntityCredentials.filter
        self.assertListEqual(
            [entity1.id, entity2.id],
            self._ids_list(creds_filter(user, qs, perm=EntityCredentials.VIEW)),
        )  # Belongs to the teams
        self.assertFalse(creds_filter(user, qs, perm=EntityCredentials.CHANGE))

    def test_has_perm_to__not_real_entity(self):
        user = self.create_user()
        self._create_role(
            'Worker', ['creme_config'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_ALL,
                    ctype=FakeConfigEntity,
                ),
            ],
        )

        ec = FakeConfigEntity.objects.create(user=user, name='Conf #1')
        entity = CremeEntity.objects.get(id=ec.id)

        self.assertTrue(user.has_perm_to_view(ec))
        self.assertFalse(user.has_perm_to_change(ec))

        self.assertTrue(user.has_perm_to_view(entity))
        self.assertFalse(user.has_perm_to_change(entity))

    def test_has_perm_to__auxiliary_entity(self):
        "Not real entity + auxiliary entity + change/delete."
        user = self.create_user()
        ct = ContentType.objects.get_for_model(FakeInvoice)
        ESET_ALL = SetCredentials.ESET_ALL
        self._create_role(
            'Worker', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(value=EntityCredentials.VIEW,   set_type=ESET_ALL, ctype=ct),
                SetCredentials(value=EntityCredentials.CHANGE, set_type=ESET_ALL, ctype=ct),
            ],
        )

        invoice = FakeInvoice.objects.create(user=user, name='Swords & shields')
        line = FakeInvoiceLine.objects.create(user=user, linked_invoice=invoice, item='Sword')

        get_entity = CremeEntity.objects.get
        invoice_entity = get_entity(id=invoice.id)
        line_entity    = get_entity(id=line.id)

        # TODO (+ line asserts)
        # self.assertTrue(user.has_perm_to_view(invoice))
        # self.assertTrue(user.has_perm_to_view(invoice_entity))

        self.assertTrue(user.has_perm_to_change(invoice))

        with self.assertNumQueries(0):  # No need to retrieve the real entity, CT enough
            can_change_einvoice = user.has_perm_to_change(invoice_entity)
        self.assertTrue(can_change_einvoice)

        self.assertFalse(user.has_perm_to_delete(invoice))

        with self.assertNumQueries(0):
            can_delete_einvoice = user.has_perm_to_delete(invoice_entity)
        self.assertFalse(can_delete_einvoice)

        # TODO
        # self.assertTrue(user.has_perm_to_view(line))
        # self.assertTrue(user.has_perm_to_view(invoice_entity))

        with self.assertNumQueries(0):
            can_change_line = user.has_perm_to_change(line)
        self.assertTrue(can_change_line)

        with self.assertNumQueries(2):
            can_change_eline = user.has_perm_to_change(line_entity)
        self.assertTrue(can_change_eline)

        line_entity = self.refresh(line_entity)
        # with self.assertNumQueries(2):
        can_delete_eline = user.has_perm_to_delete(line_entity)
        self.assertTrue(can_delete_eline)

    def test_has_perm_to__auxiliary(self):
        "Simple Model + auxiliary entity + change/delete."
        user1 = self.create_user(0)
        user2 = self.create_user(1)
        ESET_OWN = SetCredentials.ESET_OWN
        self._create_role(
            'Worker', ['creme_core'], users=[user1, user2],
            set_creds=[
                SetCredentials(value=EntityCredentials.VIEW,   set_type=ESET_OWN),
                SetCredentials(value=EntityCredentials.CHANGE, set_type=ESET_OWN),
                # SetCredentials(value=EntityCredentials.DELETE, set_type=ESET_OWN),
            ],
        )

        entity = FakeContact.objects.create(user=user1, first_name='Munisai', last_name='Shinmen')
        todo = FakeTodo.objects.create(title='Todo#1', creme_entity=entity)

        self.assertTrue(user1.has_perm_to_view(entity))
        self.assertTrue(user1.has_perm_to_change(entity))
        self.assertFalse(user1.has_perm_to_delete(entity))
        self.assertFalse(user2.has_perm_to_view(entity))
        self.assertFalse(user2.has_perm_to_change(entity))
        self.assertFalse(user2.has_perm_to_delete(entity))

        self.assertTrue(user1.has_perm_to_view(todo))
        self.assertTrue(user1.has_perm_to_change(todo))
        self.assertTrue(user1.has_perm_to_delete(todo))
        self.assertFalse(user2.has_perm_to_view(todo))
        self.assertFalse(user2.has_perm_to_change(todo))
        self.assertFalse(user2.has_perm_to_delete(todo))

        # Not entity, not auxiliary
        with self.assertRaises(TypeError) as cm:
            user1.has_perm_to_view(user2)
        self.assertIn('get_related_entity', str(cm.exception))

    def test_has_perm_to_link__superuser(self):
        user = self.build_user(is_superuser=True)

        # self.assertTrue(user.has_perm_to_link()) TODO ??
        self.assertTrue(user.has_perm_to_link(FakeOrganisation))
        ct = ContentType.objects.get_for_model(FakeOrganisation)
        self.assertTrue(user.has_perm_to_link(ct))

        with self.assertNoException():
            user.has_perm_to_link_or_die(FakeOrganisation)

        with self.assertNoException():
            user.has_perm_to_link_or_die(ct)

    def test_has_perm_to_link__no_perm(self):
        "No LINK perm at all."
        user, other_user = self._create_users()
        self._create_role(
            'Worker',
            allowed_apps=['creme_core'],
            users=[user],
            set_creds=[SetCredentials(
                value=EntityCredentials.VIEW,
                set_type=SetCredentials.ESET_ALL,
            )],
        )

        has_perm_to_link = user.has_perm_to_link
        # self.assertFalse(user.has_perm_to_link()) TODO ??
        self.assertFalse(has_perm_to_link(FakeOrganisation))
        self.assertFalse(has_perm_to_link(FakeOrganisation, owner=None))
        self.assertFalse(has_perm_to_link(FakeOrganisation, owner=other_user))

        ct = ContentType.objects.get_for_model(FakeOrganisation)
        self.assertFalse(has_perm_to_link(ct))

        with self.assertRaises(PermissionDenied) as model_cm:
            user.has_perm_to_link_or_die(FakeOrganisation)
        msg = _('You are not allowed to link: {}').format('Test Organisation')
        self.assertEqual(msg, str(model_cm.exception))

        with self.assertRaises(PermissionDenied) as ct_cm:
            user.has_perm_to_link_or_die(ct)
        self.assertEqual(msg, str(ct_cm.exception))

    def test_has_perm_to_link__all(self):
        "Can LINK all."
        user, other_user = self._create_users()
        self._create_role(
            'Worker', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW | EntityCredentials.LINK,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        team = self.create_team('Teamee', user, self.other_user)

        has_perm_to_link = user.has_perm_to_link
        self.assertTrue(has_perm_to_link(FakeOrganisation))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=user))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=other_user))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=team))

    def test_has_perm_to_link__on_ctype(self):
        "With CT credentials -> has perm."
        user, other_user = self._create_users()
        ESET_ALL = SetCredentials.ESET_ALL
        self._create_role(
            'Worker', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(value=EntityCredentials.VIEW, set_type=ESET_ALL),
                SetCredentials(
                    value=EntityCredentials.LINK, set_type=ESET_ALL,
                    ctype=FakeOrganisation,
                ),
            ],
        )

        has_perm_to_link = user.has_perm_to_link
        self.assertTrue(has_perm_to_link(FakeOrganisation))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=None))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=user))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=other_user))

    def test_has_perm_to_link__on_forbidden_ctype(self):
        "With CT credentials -> has not perm."
        user, other_user = self._create_users()
        ESET_ALL = SetCredentials.ESET_ALL
        self._create_role(
            'Worker',
            allowed_apps=['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(value=EntityCredentials.VIEW, set_type=ESET_ALL),
                SetCredentials(
                    value=EntityCredentials.LINK, set_type=ESET_ALL,
                    ctype=FakeContact,  # <= not Organisation
                ),
            ],
        )

        has_perm_to_link = user.has_perm_to_link
        self.assertFalse(has_perm_to_link(FakeOrganisation))
        self.assertFalse(has_perm_to_link(FakeOrganisation, owner=user))
        self.assertTrue(has_perm_to_link(FakeContact))
        self.assertTrue(has_perm_to_link(FakeContact, owner=user))
        self.assertTrue(has_perm_to_link(FakeContact, owner=other_user))

    def test_has_perm_to_link__only_own(self):
        "Can link only own entities."
        user, other_user = self._create_users()
        self._create_role(
            'Worker',
            allowed_apps=['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL),
                SetCredentials(value=EntityCredentials.LINK, set_type=SetCredentials.ESET_OWN),
            ],
        )

        team1 = self.create_team('Team#1', user, other_user)
        team2 = self.create_team('Team#2', other_user)

        has_perm_to_link = user.has_perm_to_link
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=None))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=user))
        self.assertFalse(has_perm_to_link(FakeOrganisation, owner=other_user))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=team1))
        self.assertFalse(has_perm_to_link(FakeOrganisation, owner=team2))

        # Entity type which does not belong to creme_core
        if apps.is_installed('creme.persons'):
            from creme.persons import get_contact_model

            Contact = get_contact_model()
            self.assertFalse(has_perm_to_link(Contact, owner=None))  # <==
            self.assertFalse(has_perm_to_link(Contact, owner=user))
            self.assertFalse(has_perm_to_link(Contact, owner=other_user))

    def test_has_perm_to_link__on_model(self):
        "Ignore filters when checking credentials on model."
        user = self.create_user()

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=CremeEntity,
                    operator=operators.EQUALS,
                    field_name='user', values=[user.id],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Worker', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_ALL,
                ),
                SetCredentials(
                    value=EntityCredentials.LINK,
                    set_type=SetCredentials.ESET_FILTER,
                    efilter=efilter,
                ),
            ],
        )

        has_perm_to_link = user.has_perm_to_link
        self.assertFalse(has_perm_to_link(FakeOrganisation, owner=None))
        self.assertFalse(has_perm_to_link(FakeOrganisation, owner=user))

    def test_is_deleted(self):
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder',
            allowed_apps=['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=(
                        EntityCredentials.VIEW
                        | EntityCredentials.CHANGE
                        | EntityCredentials.LINK
                        | EntityCredentials.UNLINK
                    ),
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        contact = self.contact1
        self.assertTrue(user.has_perm_to_change(contact))
        self.assertTrue(user.has_perm_to_link(contact))
        self.assertTrue(user.has_perm_to_unlink(contact))

        contact.trash()

        self.assertFalse(user.has_perm_to_change(contact))
        self.assertFalse(user.has_perm_to_link(contact))
        self.assertTrue(user.has_perm_to_unlink(contact))

    def test_filter_entities__superuser(self):
        self._create_users_n_contacts()
        user = self.user
        user.is_superuser = True  # <====

        with self.assertRaises(ValueError):
            EntityCredentials.filter_entities(user, FakeContact.objects.all())

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Yoshioka')
        orga2 = create_orga(user=self.other_user, name='Miyamoto')

        qs = CremeEntity.objects.filter(
            pk__in=[self.contact1.id, self.contact2.id, orga1.id, orga2.id],
        )

        with self.assertNoException():
            qs2 = EntityCredentials.filter_entities(user, qs)

        self.assertCountEqual(
            [self.contact1, self.contact2, orga1, orga2],
            [e.get_real_entity() for e in qs2],
        )

        # ------
        with self.assertRaises(ValueError):
            EntityCredentials.filter(user, qs)

    def test_filter_entities__all(self):
        "ESET_ALL."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Yoshioka')
        orga2 = create_orga(user=self.other_user, name='Miyamoto')

        qs = CremeEntity.objects.filter(
            pk__in=[self.contact1.id, self.contact2.id, orga1.id, orga2.id]
        )
        qs2 = EntityCredentials.filter_entities(user, qs)

        self.assertIsInstance(qs2, QuerySet)
        self.assertIs(qs2.model, CremeEntity)

        self.assertCountEqual(
            [self.contact1, self.contact2, orga1, orga2],
            [e.get_real_entity() for e in qs2],
        )

    def test_filter_entities__own(self):
        "ESET_OWN + specific CT + team."
        self._create_users_n_contacts()
        user = self.user
        other = self.other_user
        team = self.create_team('Teamee', user, other)

        VIEW = EntityCredentials.VIEW
        CHANGE = EntityCredentials.CHANGE
        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(value=VIEW, set_type=SetCredentials.ESET_OWN),
                SetCredentials(
                    value=VIEW, set_type=SetCredentials.ESET_ALL,
                    ctype=FakeOrganisation,
                ),
                SetCredentials(value=CHANGE, set_type=SetCredentials.ESET_ALL),
            ],
        )

        contact3 = FakeContact.objects.create(
            user=team, first_name='Sekishusai', last_name='Yagyu',
        )

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Yoshioka')
        orga2 = create_orga(user=other, name='Miyamoto')

        contact1 = self.contact1
        contact2 = self.contact2
        qs = CremeEntity.objects.filter(
            pk__in=[contact1.id, contact2.id, contact3.id, orga1.id, orga2.id],
        )

        filter_entities = EntityCredentials.filter_entities
        self.assertSetEqual(
            {contact1, contact3, orga1, orga2},
            {e.get_real_entity() for e in filter_entities(user, qs, perm=VIEW)},
        )
        self.assertSetEqual(
            {contact1, contact2, contact3, orga1, orga2},
            {e.get_real_entity() for e in filter_entities(user, qs, perm=CHANGE)},
        )
        self.assertFalse(filter_entities(user, qs, perm=EntityCredentials.DELETE))

    def test_filter_entities__forbidden_app(self):
        "No app credentials => models of this app are excluded."
        self._create_users_n_contacts()
        user = self.user

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        create_econf = FakeConfigEntity.objects.create  # Need 'creme_config' credentials
        ec1 = create_econf(user=user, name='Conf1')
        ec2 = create_econf(user=self.other_user, name='Conf2')

        qs = CremeEntity.objects.filter(
            pk__in=[self.contact1.id, self.contact2.id, ec1.id, ec2.id],
        )
        qs2 = EntityCredentials.filter_entities(user, qs)
        self.assertCountEqual(
            [self.contact1, self.contact2], [e.get_real_entity() for e in qs2],
        )

    def test_filter_entities__as_model(self):
        "as_model."
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_OWN,
                    ctype=FakeContact,
                ),
            ],
        )

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Yoshioka')
        orga2 = create_orga(user=self.other_user, name='Miyamoto')

        # Beware: filter_entities() should not be used like this ;
        # 'qs' should not contain not Contact entities.
        qs = CremeEntity.objects.filter(
            pk__in=[self.contact1.id, self.contact2.id, orga1.id, orga2.id],
        )
        qs2 = EntityCredentials.filter_entities(user, qs, as_model=FakeContact)
        self.assertSetEqual(
            {self.contact1, orga1}, {e.get_real_entity() for e in qs2},
        )

    def test_filter_entities__efilter__entity_field(self):
        "One Filter with only one condition on a CremeEntity's field (allowed)."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=CremeEntity,
                    operator=operators.EQUALS,
                    field_name='user', values=[user.id],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    # ctype=CremeEntity,
                    efilter=efilter,
                ),
            ],
        )

        contact3 = FakeContact.objects.create(
            user=user, first_name='Sekishusai', last_name='Yagyu',
        )

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user,            name='Yoshioka')
        orga2 = create_orga(user=self.other_user, name='Miyamoto')

        contact1 = self.contact1
        contact2 = self.contact2
        qs = CremeEntity.objects.filter(
            pk__in=[contact1.id, contact2.id, contact3.id, orga1.id, orga2.id],
        )

        filter_entities = EntityCredentials.filter_entities
        self.assertSetEqual(
            {contact1, contact3, orga1},
            {e.get_real_entity() for e in filter_entities(user, qs, perm=VIEW)},
        )
        self.assertFalse(filter_entities(user, qs, perm=EntityCredentials.CHANGE))

    def test_filter_entities__efilter__forbidden(self):
        "Only a forbidden Filter."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=CremeEntity,
                    operator=operators.EQUALS,
                    field_name='user', values=[user.id],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    # ctype=CremeEntity,
                    efilter=efilter,
                    forbidden=True,
                ),
            ],
        )

        self.assertFalse(EntityCredentials.filter_entities(
            user=user,
            queryset=CremeEntity.objects.filter(pk__in=[self.contact1.id, self.contact2.id]),
            perm=VIEW,
        ))

    def test_filter_entities__efilter__entity_field_forbidden(self):
        "One Filter with only CremeEntity field (forbidden)."
        self._create_users_n_contacts()
        user = self.user
        other = self.other_user

        VIEW = EntityCredentials.VIEW
        CHANGE = EntityCredentials.CHANGE

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=CremeEntity,
                    operator=operators.EQUALS,
                    field_name='user', values=[other.id],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    # ctype=CremeEntity,
                    efilter=efilter,
                    forbidden=True,
                ),
                SetCredentials(
                    value=VIEW | CHANGE,
                    set_type=SetCredentials.ESET_ALL,
                    ctype=FakeContact,
                ),
            ],
        )

        contact3 = FakeContact.objects.create(
            user=user, first_name='Sekishusai', last_name='Yagyu',
        )

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user,            name='Yoshioka')
        orga2 = create_orga(user=self.other_user, name='Miyamoto')

        contact1 = self.contact1
        contact2 = self.contact2
        qs = CremeEntity.objects.filter(
            pk__in=[contact1.id, contact2.id, contact3.id, orga1.id, orga2.id],
        )

        filter_entities = EntityCredentials.filter_entities
        self.assertSetEqual(
            {contact1, contact3},
            {e.get_real_entity() for e in filter_entities(user, qs, perm=VIEW)},
        )
        self.assertSetEqual(
            {contact1, contact2, contact3},
            {
                e.get_real_entity()
                for e in filter_entities(user, qs, perm=EntityCredentials.CHANGE)
            },
        )

    def test_filter_entities__efilter__OR(self):
        "Several Filters: OR between conditions."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        create_efilter = partial(
            EntityFilter.objects.create,
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        )
        efilter1 = create_efilter(id='creme_core-test_auth1')
        efilter2 = create_efilter(id='creme_core-test_auth2')

        build_condition = condition_handler.RegularFieldConditionHandler.build_condition
        efilter1.set_conditions(
            [
                build_condition(
                    model=CremeEntity,
                    operator=operators.EQUALS,
                    field_name='user', values=[user.id],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )
        efilter2.set_conditions(
            [
                build_condition(
                    model=CremeEntity,
                    operator=operators.ISEMPTY,
                    field_name='description', values=[False],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    # ctype=CremeEntity,
                    efilter=efilter1,
                ),
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    # ctype=CremeEntity,
                    efilter=efilter2,
                ),
            ],
        )

        create_contact = FakeContact.objects.create
        contact3 = create_contact(
            user=self.other_user,
            first_name='Sekishusai', last_name='Yagyu',
            description='Great warrior',  # <== OK
        )
        contact4 = create_contact(
            user=user,  # <== OK
            first_name='Kempo', last_name='Yoshioka',
        )

        qs = CremeEntity.objects.filter(
            pk__in=[self.contact1.id, self.contact2.id, contact3.id, contact4.id],
        )
        self.assertSetEqual(
            {self.contact1, contact3, contact4},
            {
                e.get_real_entity()
                for e in EntityCredentials.filter_entities(user, qs, perm=VIEW)
            },
        )

    def test_filter_entities__efilter__OR_n_forbidden(self):
        "Several Filters: OR between conditions (forbidden)."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        create_efilter = partial(
            EntityFilter.objects.create,
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        )
        efilter1 = create_efilter(id='creme_core-test_auth1')
        efilter2 = create_efilter(id='creme_core-test_auth2')

        build_condition = condition_handler.RegularFieldConditionHandler.build_condition
        efilter1.set_conditions(
            [
                build_condition(
                    model=CremeEntity,
                    operator=operators.EQUALS,
                    field_name='user', values=[self.other_user.id],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )
        efilter2.set_conditions(
            [
                build_condition(
                    model=CremeEntity,
                    operator=operators.ISEMPTY,
                    field_name='description', values=[False],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_ALL,
                ),
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    # ctype=CremeEntity,
                    efilter=efilter1,
                    forbidden=True,
                ),
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    # ctype=CremeEntity,
                    efilter=efilter2,
                    forbidden=True,
                ),
            ],
        )

        contact3 = FakeContact.objects.create(
            user=user,
            first_name='Sekishusai', last_name='Yagyu',
            description='Great warrior',  # <== KO
        )

        qs = CremeEntity.objects.filter(
            pk__in=[self.contact1.id, self.contact2.id, contact3.id],
        )
        self.assertSetEqual(
            {self.contact1},
            {
                e.get_real_entity()
                for e in EntityCredentials.filter_entities(user, qs, perm=VIEW)
            }
        )

    def test_filter_entities__efilter__entity_field_n_ctype(self):
        "Filter on CremeEntity fields for a specific CT anyway."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2

        create_contact = FakeContact.objects.create
        contact3 = create_contact(
            user=user,
            first_name=contact2.first_name,
            last_name=contact1.last_name,
        )
        contact4 = create_contact(
            user=self.other_user,
            first_name=contact1.first_name,
            last_name=contact2.last_name,
        )

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user,            name='Orga1')
        orga2 = create_orga(user=self.other_user, name='Orga2')

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='user',
                    values=[operands.CurrentUserOperand.type_id],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    ctype=FakeContact,
                    efilter=efilter,
                ),
            ],
        )

        with self.assertNoException():
            ids_list = self._ids_list(EntityCredentials.filter_entities(
                user=user, perm=VIEW,
                queryset=CremeEntity.objects.filter(id__in=[
                    contact1.id, contact2.id, contact3.id, contact4.id,
                    orga1.id, orga2.id,
                ]).order_by('id'),
            ))

        self.assertListEqual([contact1.id, contact3.id], ids_list)  # No FakeOrganisation

    @skipIfNotInstalled('creme.documents')
    @skipIfCustomDocument
    @skipIfCustomFolder
    def test_filter_entities__efilter__forbidden_app(self):
        "Do not raise exception for filter of forbidden apps."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2

        doc = Document.objects.create(
            title='Pretty picture',
            user=user,
            linked_folder=Folder.objects.first(),
            file_size=0,
        )

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=Document,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Document,
                    operator=operators.ICONTAINS,
                    field_name='title', values=['Picture'],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(value=VIEW, set_type=SetCredentials.ESET_ALL),
                SetCredentials(
                    value=VIEW, set_type=SetCredentials.ESET_FILTER,
                    ctype=Document,
                    efilter=efilter,
                ),
            ],
        )

        with self.assertNoException():
            ids_list = self._ids_list(EntityCredentials.filter_entities(
                user=user, perm=VIEW,
                queryset=CremeEntity.objects.filter(id__in=[
                    contact1.id, contact2.id, doc.id,
                ]).order_by('id'),
            ))

        self.assertListEqual([contact1.id, contact2.id], ids_list)

    def test_filter_entities__efilter__as_model(self):
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW

        efilter_4_contact = EntityFilter.objects.create(
            id='creme_core-test_auth01',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='user', values=[user.id],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        efilter_4_orga = EntityFilter.objects.create(
            id='creme_core-test_auth02',
            entity_type=FakeOrganisation,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.ICONTAINS,
                    field_name='name', values=['Corp'],
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    ctype=FakeContact,
                    efilter=efilter_4_contact,
                ),
                SetCredentials(
                    value=VIEW,
                    set_type=SetCredentials.ESET_FILTER,
                    ctype=FakeOrganisation,
                    efilter=efilter_4_orga,
                ),
            ],
        )

        contact3 = FakeContact.objects.create(
            user=user, first_name='Sekishusai', last_name='Yagyu',
        )

        contact1 = self.contact1
        contact2 = self.contact2
        qs = CremeEntity.objects.filter(
            pk__in=[contact1.id, contact2.id, contact3.id],
        ).order_by('id')

        filter_entities = EntityCredentials.filter_entities

        with self.assertRaises(EntityCredentials.FilteringError):
            filter_entities(user, qs, perm=VIEW)

        with self.assertNoException():
            ids_list = self._ids_list(filter_entities(
                user=user, perm=VIEW, queryset=qs, as_model=FakeContact,
            ))

        self.assertListEqual([contact1.id, contact3.id], ids_list)

    def test_sandbox__owned_by_superuser(self):
        self._create_users_n_contacts()
        user = self.user
        self._create_role(
            'Coder',
            allowed_apps=['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        sandbox = Sandbox.objects.create()
        contact3 = FakeContact.objects.create(
            user=user, sandbox=sandbox,
            first_name='Ito', last_name='Ittosaï',
        )

        contact1 = self.contact1
        self.assertTrue(user.has_perm_to_view(contact1))
        self.assertFalse(user.has_perm_to_change(contact1))

        contact2 = self.contact2
        self.assertTrue(user.has_perm_to_view(contact2))
        self.assertFalse(user.has_perm_to_change(contact2))

        self.assertFalse(user.has_perm_to_view(contact3))
        self.assertFalse(user.has_perm_to_change(contact3))

        super_user = self.other_user
        super_user.is_superuser = True
        self.assertTrue(super_user.has_perm_to_view(contact3))

        # Filtering ------------------------------------------------------------
        ecfilter = EntityCredentials.filter
        contact_qs = self._build_contact_qs(contact3).order_by('id')

        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(ecfilter(user, contact_qs, perm=EntityCredentials.VIEW)),
        )
        self.assertListEqual(
            [contact1.id, contact2.id, contact3.id],
            self._ids_list(ecfilter(super_user, contact_qs, perm=EntityCredentials.VIEW)),
        )

        # Filtering (filter_entities()) ----------------------------------------
        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Yoshioka')
        orga2 = create_orga(user=user, name='Miyamoto', sandbox=sandbox)

        filter_entities = EntityCredentials.filter_entities
        entities_qs = CremeEntity.objects.filter(
            pk__in=[contact1.id, contact2.id, contact3.id, orga1.id, orga2.id],
        )
        self.assertCountEqual(
            [contact1, contact2, orga1],
            [e.get_real_entity() for e in filter_entities(user, entities_qs)],
        )
        self.assertCountEqual(
            [contact1, contact2, contact3, orga1, orga2],
            [e.get_real_entity() for e in filter_entities(super_user, entities_qs)],
        )

    def test_sandbox__owned_by_a_role(self):
        self._create_users_n_contacts()
        user = self.user
        other_user = self.other_user
        VIEW = EntityCredentials.VIEW
        ESET_ALL = SetCredentials.ESET_ALL

        role1 = self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[SetCredentials(value=VIEW, set_type=ESET_ALL)],
        )
        self._create_role(
            'DB admin', ['creme_core'], users=[other_user],
            set_creds=[SetCredentials(value=VIEW, set_type=ESET_ALL)],
        )

        sandbox = Sandbox.objects.create(role=role1)

        contact3 = FakeContact.objects.create(
            user=user, sandbox=sandbox,
            first_name='Ito', last_name='Ittosaï',
        )

        contact1 = self.contact1
        self.assertTrue(user.has_perm_to_view(contact1))
        self.assertTrue(other_user.has_perm_to_view(contact1))

        contact2 = self.contact2
        self.assertTrue(user.has_perm_to_view(contact2))
        self.assertTrue(other_user.has_perm_to_view(contact2))

        self.assertTrue(user.has_perm_to_view(contact3))
        self.assertFalse(other_user.has_perm_to_view(contact3))  # <== not the sandbox's role

        # Super user
        super_user = CremeUser.objects.create_superuser(
            username='super',
            first_name='Suppa', last_name='man',
            email='suppa@penguin.jp',
            password=self.password,
        )
        self.assertTrue(super_user.has_perm_to_view(contact3))  # superusers ignore the Sandbox

        # Filtering ------------------------------------------------------------
        ecfilter = EntityCredentials.filter
        contact_qs = self._build_contact_qs(contact3).order_by('id')

        self.assertListEqual(
            [contact1.id, contact2.id, contact3.id],
            self._ids_list(ecfilter(user, contact_qs, perm=EntityCredentials.VIEW)),
        )
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(ecfilter(other_user, contact_qs, perm=EntityCredentials.VIEW)),
        )

        # Filtering (filter_entities(user, qs)) --------------------------------
        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Yoshioka')
        orga2 = create_orga(user=user, name='Miyamoto', sandbox=sandbox)

        filter_entities = EntityCredentials.filter_entities
        entities_qs = CremeEntity.objects.filter(
            pk__in=[contact1.id, contact2.id, contact3.id, orga1.id, orga2.id],
        )
        self.assertSetEqual(
            {contact1, contact2, contact3, orga1, orga2},
            {e.get_real_entity() for e in filter_entities(user, entities_qs)},
        )
        self.assertSetEqual(
            {contact1, contact2, orga1},
            {e.get_real_entity() for e in filter_entities(other_user, entities_qs)},
        )

    def test_sandbox__owned_by_a_user(self):
        self._create_users_n_contacts()
        user = self.user
        other_user = self.other_user

        self._create_role(
            'Coder', allowed_apps=['creme_core'], users=[user, other_user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )
        sandbox = Sandbox.objects.create(user=user)

        contact3 = FakeContact.objects.create(
            user=user, sandbox=sandbox,
            first_name='Ito', last_name='Ittosaï',
        )

        contact1 = self.contact1
        self.assertTrue(user.has_perm_to_view(contact1))
        self.assertTrue(other_user.has_perm_to_view(contact1))

        contact2 = self.contact2
        self.assertTrue(user.has_perm_to_view(contact2))
        self.assertTrue(other_user.has_perm_to_view(contact2))

        self.assertTrue(user.has_perm_to_view(contact3))
        self.assertFalse(other_user.has_perm_to_view(contact3))  # <== not the sandbox's user

        # Filtering ------------------------------------------------------------
        ecfilter = EntityCredentials.filter
        contact_qs = self._build_contact_qs(contact3).order_by('id')

        self.assertListEqual(
            [contact1.id, contact2.id, contact3.id],
            self._ids_list(ecfilter(user, contact_qs, perm=EntityCredentials.VIEW)),
        )
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(ecfilter(other_user, contact_qs, perm=EntityCredentials.VIEW)),
        )

        # Filtering (filter_entities(user, qs)) --------------------------------
        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Yoshioka')
        orga2 = create_orga(user=user, name='Miyamoto', sandbox=sandbox)

        filter_entities = EntityCredentials.filter_entities
        entities_qs = CremeEntity.objects.filter(
            pk__in=[contact1.id, contact2.id, contact3.id, orga1.id, orga2.id],
        )
        self.assertSetEqual(
            {contact1, contact2, contact3, orga1, orga2},
            {e.get_real_entity() for e in filter_entities(user, entities_qs)},
        )
        self.assertSetEqual(
            {contact1, contact2, orga1},
            {e.get_real_entity() for e in filter_entities(other_user, entities_qs)},
        )

    def test_sandbox__owned_by_a_team(self):
        self._create_users_n_contacts()
        user = self.user
        other_user = self.other_user

        self._create_role(
            'Coder', ['creme_core'],
            users=[user, other_user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )
        team = self.create_team('Teamee', user)
        sandbox = Sandbox.objects.create(user=team)

        contact3 = FakeContact.objects.create(
            user=user, sandbox=sandbox,
            first_name='Ito', last_name='Ittosaï',
        )

        contact1 = self.contact1
        self.assertTrue(user.has_perm_to_view(contact1))
        self.assertTrue(other_user.has_perm_to_view(contact1))

        contact2 = self.contact2
        self.assertTrue(user.has_perm_to_view(contact2))
        # self.assertTrue(other_user.has_perm_to_view(contact2))

        self.assertTrue(user.has_perm_to_view(contact3))
        self.assertFalse(other_user.has_perm_to_view(contact3))  # <== not in the sandbox's team

        # Filtering ------------------------------------------------------------
        ecfilter = EntityCredentials.filter
        contact_qs = self._build_contact_qs(contact3).order_by('id')

        self.assertListEqual(
            [contact1.id, contact2.id, contact3.id],
            self._ids_list(ecfilter(user, contact_qs, perm=EntityCredentials.VIEW)),
        )
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(ecfilter(other_user, contact_qs, perm=EntityCredentials.VIEW)),
        )

        # Filtering (filter_entities(user, qs)) --------------------------------
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Yoshioka')
        orga2 = create_orga(name='Miyamoto', sandbox=sandbox)

        filter_entities = EntityCredentials.filter_entities
        entities_qs = CremeEntity.objects.filter(
            pk__in=[contact1.id, contact2.id, contact3.id, orga1.id, orga2.id],
        )
        self.assertSetEqual(
            {contact1, contact2, contact3, orga1, orga2},
            {e.get_real_entity() for e in filter_entities(user, entities_qs)}
        )
        self.assertSetEqual(
            {contact1, contact2, orga1},
            {e.get_real_entity() for e in filter_entities(other_user, entities_qs)}
        )

    def test_filtering_combo(self):
        "VIEW|CHANGE."
        self._create_users_n_contacts()
        user = self.user
        VIEW = EntityCredentials.VIEW
        CHANGE = EntityCredentials.CHANGE
        DELETE = EntityCredentials.DELETE

        ptype = CremePropertyType.objects.create(text='Kawaii')

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth_combo',
            name='Is strong',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        ).set_conditions(
            [
                condition_handler.PropertyConditionHandler.build_condition(
                    model=FakeContact,
                    ptype=ptype, has=True,
                    filter_type=EF_CREDENTIALS,
                ),
            ],
            check_cycles=False,  # There cannot be a cycle without sub-filter.
            check_privacy=False,  # No sense here.
        )

        self._create_role(
            'Coder', ['creme_core'],
            users=[user],
            set_creds=[
                SetCredentials(value=VIEW, set_type=SetCredentials.ESET_OWN),
                SetCredentials(
                    value=CHANGE,
                    set_type=SetCredentials.ESET_FILTER,
                    ctype=FakeContact,
                    efilter=efilter,
                ),
            ],
        )

        contact1 = self.contact1
        contact2 = self.contact2
        contact3 = FakeContact.objects.create(
            user=user, first_name='Ito', last_name='Ittosaï',
        )

        create_ptype = partial(CremeProperty.objects.create, type=ptype)
        create_ptype(creme_entity=contact2)
        create_ptype(creme_entity=contact3)

        creds_filter = EntityCredentials.filter
        qs1 = self._build_contact_qs(contact3)

        self.assertCountEqual(
            [contact1.id, contact3.id],
            self._ids_list(creds_filter(user, qs1, perm=VIEW))
        )
        self.assertCountEqual(
            [contact2.id, contact3.id],
            self._ids_list(creds_filter(user, qs1, perm=CHANGE))
        )
        self.assertListEqual(
            [contact3.id],
            self._ids_list(creds_filter(user, qs1, perm=VIEW | CHANGE))
        )
        self.assertFalse(
            self._ids_list(creds_filter(user, qs1, perm=VIEW | DELETE))
        )

        # EntityCredentials.filter_entities ---
        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user,            name='Miyamoto')
        orga2 = create_orga(user=self.other_user, name='Sasaki')
        orga3 = create_orga(user=user,            name='Ittosaï')

        create_ptype(creme_entity=orga2)
        create_ptype(creme_entity=orga3)

        qs2 = CremeEntity.objects.filter(id__in=[
            contact1.id, contact2.id, contact3.id,
            orga1.id,    orga2.id,    orga3.id,
        ])
        filter_entities = EntityCredentials.filter_entities
        self.assertCountEqual(
            [
                contact1.id, contact3.id,
                orga1.id,    orga3.id,
            ],
            self._ids_list(filter_entities(
                user=user, queryset=qs2, perm=VIEW,
                as_model=FakeContact,
            )),
        )
        self.assertCountEqual(
            [
                contact2.id, contact3.id,
                orga2.id,    orga3.id,
            ],
            self._ids_list(filter_entities(
                user=user, queryset=qs2, perm=CHANGE,
                as_model=FakeContact,
            )),
        )
        self.assertCountEqual(
            [contact3.id, orga3.id],
            self._ids_list(filter_entities(
                user=user, queryset=qs2, perm=VIEW | CHANGE,
                as_model=FakeContact,
            )),
        )
        self.assertFalse(
            self._ids_list(filter_entities(
                user=user, queryset=qs2, perm=VIEW | DELETE,
                as_model=FakeContact,
            )),
        )

        with self.assertRaises(ValueError):
            EntityCredentials.filter_entities(
                user=user, queryset=qs2, perm=VIEW | CHANGE,
            )

    def test_disabled_role(self):
        role = self.create_role(
            name='Coder',
            allowed_apps=['creme_core'],
            admin_4_apps=['creme_core'],
            creatable_models=[FakeContact],
            exportable_models=[FakeContact],
            listable_models=[FakeContact],
            deactivated_on=now(),
            special_permissions=[role_config_perm],
        )
        self.add_credentials(role, all='*')
        user = self.create_user(role=role)

        self.assertFalse(user.has_perm('creme_core'))
        self.assertFalse(user.has_perm('creme_core.can_admin'))

        self.assertFalse(user.has_perm_to_access('creme_core'))
        self.assertFalse(user.has_perm_to_admin('creme_core'))
        self.assertFalse(user.has_perm_to_create(FakeContact))
        self.assertFalse(user.has_perm_to_export(FakeContact))
        self.assertFalse(user.has_perm_to_list(FakeContact))
        self.assertFalse(user.has_special_perm(role_config_perm))

        contact = FakeContact.objects.create(
            user=user, first_name='Musashi', last_name='Miyamoto',
        )
        self.assertFalse(user.has_perm_to_view(contact))
        self.assertFalse(user.has_perm_to_link(FakeContact))
        self.assertFalse(user.has_perm_to_link(contact))
        self.assertFalse(user.has_perm_to_change(contact))
        self.assertFalse(user.has_perm_to_delete(contact))

        self.assertFalse(EntityCredentials.filter_entities(
            user=user, queryset=CremeEntity.objects.all(),
        ))
        self.assertFalse(EntityCredentials.filter(
            user=user, queryset=FakeContact.objects.all(),
        ))
