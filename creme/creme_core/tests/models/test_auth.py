# -*- coding: utf-8 -*-

from functools import partial

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.db.models.deletion import ProtectedError
from django.test.utils import override_settings
from django.utils.translation import gettext as _

from creme.creme_config.models import FakeConfigEntity
from creme.creme_core import constants
from creme.creme_core.auth import STAFF_PERM, SUPERUSER_PERM, EntityCredentials
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
    EntityFilter,
    FakeContact,
    FakeInvoice,
    FakeInvoiceLine,
    FakeOrganisation,
    Relation,
    Sandbox,
    SetCredentials,
    UserRole,
)
from creme.creme_core.sandboxes import OnlySuperusersType
from creme.documents.models import Document, Folder
from creme.documents.tests.base import skipIfCustomDocument, skipIfCustomFolder

from ..base import CremeTestCase, skipIfNotInstalled


class CredentialsTestCase(CremeTestCase):
    password = 'password'

    def setUp(self):
        super().setUp()

        create_user = CremeUser.objects.create_user
        self.user = user = create_user(
            username='Kenji', email='kenji@century.jp',
            first_name='Kenji', last_name='Gendou',
            password=self.password,
        )
        self.other_user = other = create_user(
            username='Shogun',
            first_name='Choji', last_name='Ochiai',
            email='shogun@century.jp',
            password='uselesspw',
        )  # TODO: remove from here ??

        create_contact = FakeContact.objects.create
        self.contact1 = create_contact(user=user,  first_name='Musashi', last_name='Miyamoto')
        self.contact2 = create_contact(user=other, first_name='Kojiro',  last_name='Sasaki')

        self.client.login(username=user.username, password=self.password)

    @staticmethod
    def _ids_list(iterable):
        return [e.id for e in iterable]

    @staticmethod
    def _create_role(name, allowed_apps=(), admin_4_apps=(), set_creds=(), users=()):
        role = UserRole(name=name)
        role.allowed_apps = allowed_apps
        role.admin_4_apps = admin_4_apps
        role.save()

        for sc in set_creds:
            sc.role = role
            sc.save()

        for user in users:
            user.role = role
            user.save()

        return role

    def _build_contact_qs(self, *extra_contacts):
        return FakeContact.objects.filter(
            pk__in=[
                self.contact1.id,
                self.contact2.id,
                *(c.id for c in extra_contacts),
            ],
        )

    def test_populate(self):
        sandbox = self.get_object_or_fail(Sandbox, uuid=constants.UUID_SANDBOX_SUPERUSERS)
        self.assertIsNone(sandbox.role)
        self.assertIsNone(sandbox.user)
        self.assertEqual(OnlySuperusersType.id, sandbox.type_id)
        self.assertIsInstance(sandbox.type, OnlySuperusersType)

    def test_user_attributes01(self):
        user = self.user

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

    def test_user_attributes02(self):
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

    def test_role_attributes(self):
        role = UserRole(name='Normal')
        self.assertEqual('', role.raw_allowed_apps)
        self.assertSetEqual(set(), role.allowed_apps)

        self.assertEqual('', role.raw_admin_4_apps)
        self.assertSetEqual(set(), role.admin_4_apps)

        role.allowed_apps = ['creme_core', 'documents']
        self.assertEqual({'creme_core', 'documents'}, role.allowed_apps)

        role.admin_4_apps = ['creme_core', 'persons']
        self.assertEqual({'creme_core', 'persons'}, role.admin_4_apps)

        role.save()
        role = self.refresh(role)
        self.assertEqual({'creme_core', 'documents'}, role.allowed_apps)
        self.assertEqual({'creme_core', 'persons'}, role.admin_4_apps)

    @override_settings(
        THEMES=[
            ('this_theme_is_cool', 'Cool one'),
            ('yet_another_theme',  'I am cool too, bro'),
        ],
    )
    def test_theme_info(self):
        "The first valid theme is used if the registered theme is not valid."
        theme = settings.THEMES[0]
        user = self.user
        self.assertNotEqual(theme[0], user.theme)
        self.assertEqual(theme, user.theme_info)

    def test_super_user01(self):
        user = self.user
        user.is_superuser = True  # <====

        has_perm = user.has_perm
        self.assertTrue(has_perm('creme_core'))

        self.assertEqual('*superuser*', SUPERUSER_PERM)
        self.assertTrue(has_perm(SUPERUSER_PERM))

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

        # Helpers --------------------------------------------------------------
        self.assertTrue(user.has_perm_to_view(contact1))
        self.assertTrue(user.has_perm_to_change(contact1))
        self.assertTrue(user.has_perm_to_delete(contact1))
        self.assertTrue(user.has_perm_to_link(contact1))
        self.assertTrue(user.has_perm_to_unlink(contact1))

        self.assertTrue(user.has_perm_to_view(contact2))
        self.assertTrue(user.has_perm_to_change(contact2))

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

    def test_super_user02(self):
        user = self.user
        self._create_role('Salesman', ['creme_core'], users=[user])
        self.assertFalse(user.has_perm(SUPERUSER_PERM))

    def test_staff(self):
        self.assertEqual('*staff*', STAFF_PERM)

        user = self.user
        has_perm = user.has_perm
        self.assertFalse(has_perm(STAFF_PERM))

        user.is_superuser = True
        self.assertFalse(has_perm(STAFF_PERM))

        user.is_staff = True
        self.assertTrue(has_perm(STAFF_PERM))

    def test_role_esetall_view(self):
        "VIEW + ESET_ALL."
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
        contact1 = self.contact1
        self.assertTrue(has_perm('creme_core.view_entity',    contact1))
        self.assertFalse(has_perm('creme_core.change_entity', contact1))
        self.assertFalse(has_perm('creme_core.delete_entity', contact1))
        self.assertFalse(has_perm('creme_core.link_entity',   contact1))
        self.assertFalse(has_perm('creme_core.unlink_entity', contact1))

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
        efilter = EntityCredentials.filter
        qs1 = self._build_contact_qs()

        with self.assertNumQueries(1):
            _ = user.teams

        with self.assertNumQueries(0):
            efilter(user, qs1)

        self.assertIsNone(qs1._result_cache, 'Queryset has been retrieved (should be lazy)')

        all_ids = [contact1.id, contact2.id]
        self.assertEqual(all_ids, self._ids_list(efilter(user, qs1, perm=EntityCredentials.VIEW)))

        self.assertEqual(all_ids, self._ids_list(efilter(user, qs1, perm=EntityCredentials.VIEW)))
        self.assertFalse(efilter(user, qs1, perm=EntityCredentials.CHANGE))
        self.assertFalse(efilter(user, qs1, perm=EntityCredentials.DELETE))
        self.assertFalse(efilter(user, qs1, perm=EntityCredentials.LINK))
        self.assertFalse(efilter(user, qs1, perm=EntityCredentials.UNLINK))

    def test_role_esetall_view__noappcreds(self):
        "App is not allowed -> no creds."
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

    def test_role_esetall_change(self):
        "CHANGE + ESET_ALL."
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

        efilter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertFalse(efilter(perm=EntityCredentials.VIEW))
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(efilter(perm=EntityCredentials.CHANGE)),
        )
        self.assertFalse(efilter(perm=EntityCredentials.DELETE))
        self.assertFalse(efilter(perm=EntityCredentials.LINK))
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_role_esetall_change__admincreds(self):
        "CHANGE + ESET_ALL (no app creds, but app admin creds)."
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

        efilter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertFalse(efilter(perm=EntityCredentials.VIEW))
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(efilter(perm=EntityCredentials.CHANGE)),
        )

    def test_role_esetall_delete(self):
        "DELETE + ESET_ALL."
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

        efilter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertFalse(efilter(perm=EntityCredentials.VIEW))
        self.assertFalse(efilter(perm=EntityCredentials.CHANGE))
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(efilter(perm=EntityCredentials.DELETE)),
        )
        self.assertFalse(efilter(perm=EntityCredentials.LINK))
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_role_esetall_link(self):
        "LINK + ESET_ALL."
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

        contact2 = self.contact2
        self.assertFalse(has_perm('creme_core.view_entity', contact2))
        self.assertTrue(has_perm('creme_core.link_entity',  contact2))

        efilter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertFalse(efilter(perm=EntityCredentials.VIEW))
        self.assertFalse(efilter(perm=EntityCredentials.CHANGE))
        self.assertFalse(efilter(perm=EntityCredentials.DELETE))
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(efilter(perm=EntityCredentials.LINK)),
        )
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_role_esetall_unlink(self):
        "UNLINK + ESET_ALL."
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

        efilter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertFalse(efilter(perm=EntityCredentials.VIEW))
        self.assertFalse(efilter(perm=EntityCredentials.CHANGE))
        self.assertFalse(efilter(perm=EntityCredentials.DELETE))
        self.assertFalse(efilter(perm=EntityCredentials.LINK))
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(efilter(perm=EntityCredentials.UNLINK)),
        )

    def test_role_esetown_view(self):
        "VIEW + ESET_OWN."
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

        efilter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        ids = [contact1.id]
        self.assertEqual(ids, self._ids_list(efilter()))
        self.assertEqual(ids, self._ids_list(efilter(perm=EntityCredentials.VIEW)))
        self.assertFalse(efilter(perm=EntityCredentials.CHANGE))
        self.assertFalse(efilter(perm=EntityCredentials.DELETE))
        self.assertFalse(efilter(perm=EntityCredentials.LINK))
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_role_esetown_view_n_change(self):
        "ESET_OWN + VIEW/CHANGE."
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

        efilter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        ids = [contact1.id]
        self.assertFalse(efilter(perm=EntityCredentials.VIEW))
        self.assertEqual(ids, self._ids_list(efilter(perm=EntityCredentials.CHANGE)))
        self.assertEqual(ids, self._ids_list(efilter(perm=EntityCredentials.DELETE)))
        self.assertFalse(efilter(perm=EntityCredentials.LINK))
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_role_esetown_delete(self):
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

        efilter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertFalse(efilter(perm=EntityCredentials.VIEW))
        self.assertFalse(efilter(perm=EntityCredentials.CHANGE))
        self.assertListEqual(
            [contact1.id],
            self._ids_list(efilter(perm=EntityCredentials.DELETE)),
        )
        self.assertFalse(efilter(perm=EntityCredentials.LINK))
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_role_esetown_link_n_unlink(self):
        "ESET_OWN + LINK/UNLINK."
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
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

        efilter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        ids = [contact1.id]
        self.assertFalse(efilter(perm=EntityCredentials.VIEW))
        self.assertFalse(efilter(perm=EntityCredentials.CHANGE))
        self.assertFalse(efilter(perm=EntityCredentials.DELETE))
        self.assertListEqual(ids, self._ids_list(efilter(perm=EntityCredentials.LINK)))
        self.assertListEqual(ids, self._ids_list(efilter(perm=EntityCredentials.UNLINK)))

    def test_role_multiset01(self):
        "ESET_ALL + ESET_OWN."
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

        efilter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(efilter(perm=EntityCredentials.VIEW)),
        )
        self.assertListEqual(
            [contact1.id],
            self._ids_list(efilter(perm=EntityCredentials.CHANGE)),
        )
        self.assertListEqual(
            [contact1.id],
            self._ids_list(efilter(perm=EntityCredentials.DELETE)),
        )
        self.assertFalse(efilter(perm=EntityCredentials.LINK))
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_role_multiset02(self):
        "ESET_OWN + ESET_ALL (so ESET_OWN before)."
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

        efilter = partial(EntityCredentials.filter, user, self._build_contact_qs())
        self.assertListEqual([contact1.id, contact2.id], self._ids_list(efilter(perm=VIEW)))
        self.assertListEqual([contact1.id],              self._ids_list(efilter(perm=CHANGE)))
        self.assertListEqual([contact1.id],              self._ids_list(efilter(perm=DELETE)))
        self.assertFalse(efilter(perm=EntityCredentials.LINK))
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_ct_credentials01(self):
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
        efilter = partial(EntityCredentials.filter, user)
        qs = self._build_contact_qs()
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(efilter(qs, perm=EntityCredentials.VIEW))
        )
        self.assertFalse(efilter(qs, perm=EntityCredentials.CHANGE))
        self.assertFalse(efilter(
            FakeOrganisation.objects.filter(pk=orga.id),
            perm=EntityCredentials.VIEW,
        ))

    def test_ct_credentials02(self):
        "Cannot set CremeEntity."
        role = self._create_role('Coder', ['creme_core'])
        sc = SetCredentials(
            role=role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_ALL,
            ctype=CremeEntity,
        )
        with self.assertRaises(ValueError):
            sc.save()

    def test_role_forbidden01(self):
        "ESET_ALL."
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
        efilter = partial(EntityCredentials.filter, user)
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(efilter(self._build_contact_qs(), perm=VIEW))
        )
        self.assertFalse(efilter(
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

    def test_role_forbidden02(self):
        "ESET_OWN forbidden + ESET_ALL allowed."
        user = self.user
        other = self.other_user

        team = CremeUser.objects.create(username='Teamee', is_team=True)
        team.teammates = [user, other]

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

    def test_role_forbidden03(self):
        "ESET_OWN forbidden & allowed."
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

    def test_role_forbidden04(self):
        "Permission on model (LINK on future instances) - ESET_ALL forbidden."
        user = self.user
        LINK = EntityCredentials.LINK

        self._create_role(
            'Coder', ['creme_core'], users=[user],
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

        other = self.other_user
        self.assertFalse(user.has_perm_to_link(FakeContact, owner=other))
        self.assertFalse(user.has_perm_to_link(FakeOrganisation, owner=other))

    def test_role_forbidden05(self):
        "Permission on model (LINK on future instances) - ESET_OWN forbidden."
        user = self.user
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

        other = self.other_user
        self.assertTrue(user.has_perm_to_link(FakeContact, owner=other))
        self.assertTrue(user.has_perm_to_link(FakeOrganisation, owner=other))

        team = CremeUser.objects.create(username='Teamee', is_team=True)
        team.teammates = [user, other]
        self.assertTrue(user.has_perm_to_link(FakeContact, owner=team))
        self.assertFalse(user.has_perm_to_link(FakeOrganisation, owner=team))

    def test_credentials_with_filter01(self):
        "Check ESET_FILTER."
        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )

        role = UserRole.objects.create(name='Test')

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

    def test_credentials_with_filter02(self):
        "ESET_FILTER x 1."
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
        )
        efilter.set_conditions(
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

    def test_credentials_with_filter03(self):
        "ESET_FILTER (forbidden)."
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
        )
        efilter.set_conditions(
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

    def test_credentials_with_filter04(self):
        "ESET_FILTER (forbidden) + ESET_ALL."
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
        )
        efilter.set_conditions(
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

    def test_credentials_with_filter05(self):
        "ESET_OWN (forbidden) + ESET_FILTER."
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
        )
        efilter.set_conditions(
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

    def test_credentials_with_filter06(self):
        "ESET_FILTER + ESET_ALL (created AFTER)."
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )
        efilter.set_conditions(
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

    def test_credentials_with_filter07(self):
        "ESET_FILTER + ESET_OWN."
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
        )
        efilter.set_conditions(
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

    def test_credentials_with_filter08(self):
        "ESET_FILTER x 2."
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
        )
        efilter1.set_conditions(
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
        )
        efilter2.set_conditions(
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

    def test_credentials_with_filter09(self):
        "ESET_FILTER (forbidden) x 2."
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
        )
        efilter1.set_conditions(
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
        )
        efilter2.set_conditions(
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

    def test_credentials_with_filter10(self):
        "ESET_FILTER x 2: allowed + forbidden."
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
        )
        efilter1.set_conditions(
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
        )
        efilter2.set_conditions(
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

    def test_credentials_with_filter11(self):
        "ESET_FILTER on CremeEntity + <user> argument."
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
        )
        efilter.set_conditions(
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

    def test_credentials_with_filter12(self):
        "<user> argument + forbidden."
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
        )
        efilter.set_conditions(
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
            'Coder', ['creme_core'],
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

    def test_creation_creds01(self):
        user = self.user
        role = self._create_role('Coder', users=[user])

        has_perm = user.has_perm
        has_perm_to_create = user.has_perm_to_create

        self.assertFalse(has_perm('creme_core.add_cremeproperty'))
        self.assertFalse(has_perm('creme_core.add_relation'))
        self.assertFalse(has_perm_to_create(CremeProperty))  # Helper

        get_ct = ContentType.objects.get_for_model
        role.creatable_ctypes.set([get_ct(CremeProperty), get_ct(Relation)])

        user.role = self.refresh(role)  # Refresh cache
        self.assertTrue(has_perm('creme_core.add_cremeproperty'))
        self.assertTrue(has_perm('creme_core.add_relation'))
        self.assertFalse(has_perm('creme_core.add_cremepropertytype'))

        # Helpers
        self.assertTrue(has_perm_to_create(CremeProperty))
        self.assertFalse(has_perm_to_create(CremePropertyType))

        entity = CremeEntity.objects.create(user=user)
        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_foobar', text='text',
        )
        prop  = CremeProperty.objects.create(type=ptype, creme_entity=entity)
        self.assertTrue(has_perm_to_create(prop))
        self.assertFalse(has_perm_to_create(ptype))

        # Helpers (with exception)
        with self.assertNoException():
            user.has_perm_to_create_or_die(prop)

        self.assertRaises(PermissionDenied, user.has_perm_to_create_or_die, ptype)

    def test_creation_creds02(self):
        user = self.user
        user.is_superuser = True
        self.assertTrue(user.has_perm('creme_core.add_cremeproperty'))

    def test_export_creds01(self):
        user = self.user
        role = self._create_role('Coder', ['creme_core'], users=[user])  # 'persons'

        has_perm = user.has_perm
        has_perm_to_export = user.has_perm_to_export

        self.assertFalse(has_perm('persons.export_contact'))
        self.assertFalse(has_perm('persons.export_organisation'))
        self.assertFalse(has_perm_to_export(FakeContact))  # Helper

        role.exportable_ctypes.add(ContentType.objects.get_for_model(FakeContact))

        user.role = self.refresh(role)  # Refresh cache
        self.assertTrue(has_perm('creme_core.export_fakecontact'))
        self.assertFalse(has_perm('creme_core.export_fakeorganisation'))
        self.assertTrue(has_perm_to_export(FakeContact))
        self.assertFalse(has_perm_to_export(FakeOrganisation))

        # Helpers (with exception)
        with self.assertNoException():
            user.has_perm_to_export_or_die(FakeContact)

        self.assertRaises(PermissionDenied, user.has_perm_to_export_or_die, FakeOrganisation)

    def test_export_creds02(self):
        user = self.user
        user.is_superuser = True
        self.assertTrue(user.has_perm('persons.export_contact'))

    # TODO: test extending apps
    def test_app_creds01(self):
        user = self.user
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
    def test_app_creds02(self):
        "Admin_4_apps."
        user = self.user
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

        invalid_app = 'persons'
        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_to_admin_or_die(invalid_app)

        self.assertEqual(
            fmt(apps.get_app_config('persons').verbose_name), str(cm.exception),
        )

        self.assertTrue(user.has_perm('creme_core'))
        self.assertTrue(user.has_perm('documents'))
        self.assertFalse(user.has_perm('persons'))

    def test_app_creds03(self):
        "Super user."
        user = self.user
        user.is_superuser = True

        self.assertTrue(user.has_perm_to_admin('creme_core'))
        self.assertTrue(user.has_perm_to_access('creme_core'))

        has_perm = user.has_perm
        self.assertTrue(has_perm('creme_core'))
        self.assertTrue(has_perm('creme_core.can_admin'))

    def test_delete01(self):
        "Delete role."
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
        self.assertFalse(SetCredentials.objects.filter(role=role))

    def test_delete02(self):
        "Can not delete a role linked to a user."
        user = self.user
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

    def test_create_team01(self):
        team = CremeUser.objects.create(username='Teamee')

        self.assertFalse(team.is_team)

        with self.assertRaises(AssertionError):
            team.teammates = [self.user]

        with self.assertRaises(AssertionError):
            team.teammates  # NOQA

    def test_create_team02(self):
        team = CremeUser.objects.create(username='Teamee', is_team=True)

        user  = self.user
        other = self.other_user

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
            username='Kanna', email='kanna@century.jp',
            first_name='Kanna', last_name='Gendou',
            password='uselesspw',
        )
        team.teammates = [user, other, user3]
        self.assertEqual(3, len(team.teammates))

        team.teammates = [other]
        self.assertEqual(1, len(team.teammates))
        self.assertDictEqual({other.id: other}, self.refresh(team).teammates)

    def _create_team(self, name, teammates):
        team = CremeUser.objects.create(username=name, is_team=True, role=None)
        team.teammates = teammates
        return team

    def test_team_credentials01(self):
        user = self.user
        other = self.other_user
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

        team = self._create_team('Teamee', [user])

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
        efilter = EntityCredentials.filter

        with self.assertNumQueries(3):  # Role, SetCredentials & teams
            viewable = efilter(user, qs, perm=EntityCredentials.VIEW)
        self.assertListEqual([entity.id], self._ids_list(viewable))  # Belongs to the team

        with self.assertNumQueries(0):  # Role, SetCredentials & teams --> cache
            editable = efilter(user, qs, perm=EntityCredentials.CHANGE)
        self.assertFalse(editable)

        self.assertFalse(efilter(other, qs, perm=EntityCredentials.VIEW))

    def test_team_credentials02(self):
        "User in several teams."
        user = self.user
        other = self.other_user
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

        create_team = self._create_team
        team1 = create_team('Teamee 1', [user])
        team2 = create_team('Teamee 2', [other, user])
        team3 = create_team('Teamee 3', [other])

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
        teams = user.teams
        self.assertEqual(2, len(teams))
        self.assertSetEqual({team1, team2}, {*teams})

        with self.assertNumQueries(0):  # Teams are cached
            user.teams  # NOQA

        # Filtering ------------------------------------------------------------
        entity3 = create_user(user=team3, first_name='Ryohei', last_name='Ueda')

        qs = FakeContact.objects.filter(pk__in=[entity1.id, entity2.id, entity3.id])
        efilter = EntityCredentials.filter
        self.assertListEqual(
            [entity1.id, entity2.id],
            self._ids_list(efilter(user, qs, perm=EntityCredentials.VIEW))
        )  # Belongs to the teams
        self.assertFalse(efilter(user, qs, perm=EntityCredentials.CHANGE))

    def test_has_perm_to01(self):
        "Not real entity."
        user = self.user
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

    def test_has_perm_to02(self):
        "Not real entity + auxiliary entity + change/delete."
        user = self.user
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

    def test_has_perm_to_link01(self):
        "Super user."
        user = self.user
        user.is_superuser = True  # <====

        # self.assertTrue(user.has_perm_to_link()) TODO ??
        self.assertTrue(user.has_perm_to_link(FakeOrganisation))

        with self.assertNoException():
            user.has_perm_to_link_or_die(FakeOrganisation)

    def test_has_perm_to_link02(self):
        "No LINK perm at all."
        user = self.user
        self._create_role(
            'Worker', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL),
            ],
        )

        has_perm_to_link = user.has_perm_to_link
        # self.assertFalse(user.has_perm_to_link()) TODO ??
        self.assertFalse(has_perm_to_link(FakeOrganisation))
        self.assertFalse(has_perm_to_link(FakeOrganisation, owner=None))
        self.assertFalse(has_perm_to_link(FakeOrganisation, owner=self.other_user))

        self.assertRaises(PermissionDenied, user.has_perm_to_link_or_die, FakeOrganisation)

    def test_has_perm_to_link03(self):
        "Can LINK all."
        user = self.user
        self._create_role(
            'Worker', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(
                    value=EntityCredentials.VIEW | EntityCredentials.LINK,
                    set_type=SetCredentials.ESET_ALL,
                ),
            ],
        )

        team = self._create_team('Teamee', [user, self.other_user])

        has_perm_to_link = user.has_perm_to_link
        self.assertTrue(has_perm_to_link(FakeOrganisation))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=user))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=self.other_user))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=team))

    def test_has_perm_to_link04(self):
        "With CT credentials -> has perm."
        user = self.user
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
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=self.other_user))

    def test_has_perm_to_link05(self):
        "With CT credentials -> has not perm."
        user = self.user
        ESET_ALL = SetCredentials.ESET_ALL
        self._create_role(
            'Worker', ['creme_core'], users=[user],
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
        self.assertTrue(has_perm_to_link(FakeContact, owner=self.other_user))

    def test_has_perm_to_link06(self):
        "Can link only own entities."
        user = self.user
        self._create_role(
            'Worker', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL),
                SetCredentials(value=EntityCredentials.LINK, set_type=SetCredentials.ESET_OWN),
            ],
        )

        other_user = self.other_user
        team1 = self._create_team('Team#1', [user, other_user])
        team2 = self._create_team('Team#2', [other_user])

        has_perm_to_link = user.has_perm_to_link
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=None))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=user))
        self.assertFalse(has_perm_to_link(FakeOrganisation, owner=other_user))
        self.assertTrue(has_perm_to_link(FakeOrganisation, owner=team1))
        self.assertFalse(has_perm_to_link(FakeOrganisation, owner=team2))

    def test_has_perm_to_link07(self):
        "Ignore filters when checking credentials on model."
        user = self.user

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        )
        efilter.set_conditions(
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
        user = self.user
        self._create_role(
            'Coder', ['creme_core'],
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

    def test_filter_entities01(self):
        "Super user."
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

        # self.assertIs(qs, qs2)
        result = [e.get_real_entity() for e in qs2]
        self.assertEqual(4, len(result))
        self.assertSetEqual({self.contact1, self.contact2, orga1, orga2}, {*result})

        # ------
        with self.assertRaises(ValueError):
            EntityCredentials.filter(user, qs)

    def test_filter_entities02(self):
        "ESET_ALL."
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

        result = [e.get_real_entity() for e in qs2]
        self.assertEqual(4, len(result))
        self.assertSetEqual(
            {self.contact1, self.contact2, orga1, orga2}, {*result},
        )

    def test_filter_entities03(self):
        "ESET_OWN + specific CT + team."
        user = self.user
        other = self.other_user

        team = CremeUser.objects.create(username='Teamee', is_team=True)
        team.teammates = [user, other]

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
            {e.get_real_entity() for e in filter_entities(user, qs, perm=VIEW)}
        )
        self.assertSetEqual(
            {contact1, contact2, contact3, orga1, orga2},
            {e.get_real_entity() for e in filter_entities(user, qs, perm=CHANGE)}
        )
        self.assertFalse(filter_entities(user, qs, perm=EntityCredentials.DELETE))

    def test_filter_entities04(self):
        "No app credentials => models of this app are excluded."
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

        self.assertSetEqual(
            {self.contact1, self.contact2}, {e.get_real_entity() for e in qs2},
        )

    def test_filter_entities05(self):
        "as_model."
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

    def test_filter_entities_with_filter01(self):
        "One Filter with only CremeEntityField (allowed)."
        user = self.user
        VIEW = EntityCredentials.VIEW

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        )
        efilter.set_conditions(
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

    def test_filter_entities_with_filter02(self):
        "Only a forbidden Filter."
        user = self.user
        VIEW = EntityCredentials.VIEW

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        )
        efilter.set_conditions(
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

    def test_filter_entities_with_filter03(self):
        "One Filter with only CremeEntity field (forbidden)."
        user = self.user
        other = self.other_user

        VIEW = EntityCredentials.VIEW
        CHANGE = EntityCredentials.CHANGE

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=CremeEntity,
            filter_type=EF_CREDENTIALS,
        )
        efilter.set_conditions(
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

    def test_filter_entities_with_filter04(self):
        "Several Filters: OR between conditions."
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

    def test_filter_entities_with_filter05(self):
        "Several Filters: OR between conditions (forbidden)."
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

    def test_filter_entities_with_filter06(self):
        "Filter on CremeEntity fields for a specific CT anyway."
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
        )
        efilter.set_conditions(
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
    def test_filter_entities_with_filter07(self):
        "Do not raise exception for filter of forbidden apps."
        user = self.user
        VIEW = EntityCredentials.VIEW

        contact1 = self.contact1
        contact2 = self.contact2

        doc = Document.objects.create(
            title='Pretty picture',
            user=user,
            linked_folder=Folder.objects.first(),
        )

        efilter = EntityFilter.objects.create(
            id='creme_core-test_auth',
            entity_type=Document,
            filter_type=EF_CREDENTIALS,
        )
        efilter.set_conditions(
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

    def test_filter_entities_with_filter_as_model01(self):
        user = self.user
        VIEW = EntityCredentials.VIEW

        efilter_4_contact = EntityFilter.objects.create(
            id='creme_core-test_auth01',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )
        efilter_4_contact.set_conditions(
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
        )
        efilter_4_orga.set_conditions(
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

    def test_sandox01(self):
        "Owned by super-users."
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
        self.assertSetEqual(
            {contact1, contact2, orga1},
            {e.get_real_entity() for e in filter_entities(user, entities_qs)},
        )
        self.assertSetEqual(
            {contact1, contact2, contact3, orga1, orga2},
            {e.get_real_entity() for e in filter_entities(super_user, entities_qs)},
        )

    def test_sandox02(self):
        "Owned by a role."
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

    def test_sandox03(self):
        "Owned by a user."
        user = self.user
        other_user = self.other_user

        self._create_role(
            'Coder', ['creme_core'], users=[user, other_user],
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

    def test_sandox04(self):
        "Owned by a team."
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
        team = self._create_team('Teamee', [user])
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

    def test_credentials_str(self):
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
            ))
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
            ))
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
            ))
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
            ))
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
            ))
        )
