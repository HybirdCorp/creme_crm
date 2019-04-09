# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.apps import apps
    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.core.exceptions import PermissionDenied
    from django.db.models import QuerySet
    from django.db.models.deletion import ProtectedError
    from django.test.utils import override_settings
    from django.utils.translation import ugettext as _

    from ..base import CremeTestCase

    from creme.creme_core import constants
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import (CremeUser, Sandbox, CremeEntity, CremePropertyType,
            CremeProperty, Relation, UserRole, SetCredentials,
            FakeContact, FakeOrganisation, FakeInvoice, FakeInvoiceLine)
    from creme.creme_core.sandboxes import OnlySuperusersType

    from creme.creme_config.models import FakeConfigEntity
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class CredentialsTestCase(CremeTestCase):
    password = 'password'

    def setUp(self):
        create_user = CremeUser.objects.create_user
        self.user = user = create_user(username='Kenji', email='kenji@century.jp',
                                       first_name='Kenji', last_name='Gendou',
                                       password=self.password,
                                      )
        self.other_user = other = create_user(username='Shogun',
                                              first_name='Choji', last_name='Ochiai',
                                              email='shogun@century.jp',
                                              password='uselesspw',
                                             )  # TODO: remove from here ??

        create_contact = FakeContact.objects.create
        self.contact1 = create_contact(user=user,  first_name='Musashi', last_name='Miyamoto')
        self.contact2 = create_contact(user=other, first_name='Kojiro',  last_name='Sasaki')

        self.client.login(username=user.username, password=self.password)

    def _ids_list(self, iterable):
        return [e.id for e in iterable]

    def _create_role(self, name, allowed_apps=(), admin_4_apps=(), set_creds=(), users=()):
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
        ids = [self.contact1.id, self.contact2.id]
        ids.extend(c.id for c in extra_contacts)

        return FakeContact.objects.filter(pk__in=ids)

    def test_populate(self):
        sandbox = self.get_object_or_fail(Sandbox, uuid=constants.UUID_SANDBOX_SUPERUSERS)
        # self.assertIs(sandbox.superuser, True)
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
        team2 = CremeUser.objects.create(username=username2, is_team=True,
                                         first_name='NC', last_name=username2,
                                        )

        self.assertEqual(_('{user} (team)').format(user=username2), str(team2))

    def test_role_attributes(self):
        role = UserRole(name='Normal')
        self.assertEqual('', role.raw_allowed_apps)
        self.assertEqual(set(), role.allowed_apps)

        self.assertEqual('', role.raw_admin_4_apps)
        self.assertEqual(set(), role.admin_4_apps)

        role.allowed_apps = ['creme_core', 'documents']
        self.assertEqual({'creme_core', 'documents'}, role.allowed_apps)

        role.admin_4_apps = ['creme_core', 'persons']
        self.assertEqual({'creme_core', 'persons'}, role.admin_4_apps)

        role.save()
        role = self.refresh(role)
        self.assertEqual({'creme_core', 'documents'}, role.allowed_apps)
        self.assertEqual({'creme_core', 'persons'}, role.admin_4_apps)

    @override_settings(THEMES=[('this_theme_is_cool', 'Cool one'),
                               ('yet_another_theme',  'I am cool too, bro'),
                              ]
                      )
    def test_theme_info(self):
        "The first valid theme is used if the registered theme is not valid."
        theme = settings.THEMES[0]
        user = self.user
        self.assertNotEqual(theme[0], user.theme)
        self.assertEqual(theme, user.theme_info)

    def test_super_user(self):
        user = self.user
        user.is_superuser = True  # <====

        has_perm = user.has_perm
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

        self.assertEqual([contact1.id, contact2.id],
                         self._ids_list(qs)
                        )

    # TODO: this tests contribute_to_model too
    def test_role_esetall_view(self):
        "VIEW + ESET_ALL."
        user = self.user
        self._create_role('Coder', ['creme_core'], users=[user],
                          set_creds=[
                              SetCredentials(value=EntityCredentials.VIEW,
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
        self._create_role('Coder', users=[user],
                          set_creds=[
                              SetCredentials(value=EntityCredentials.VIEW,
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
        self._create_role('Coder', ['creme_core'], users=[user],
                          set_creds=[
                              SetCredentials(value=EntityCredentials.CHANGE,
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
        self.assertEqual([contact1.id, contact2.id],
                         self._ids_list(efilter(perm=EntityCredentials.CHANGE))
                        )
        self.assertFalse(efilter(perm=EntityCredentials.DELETE))
        self.assertFalse(efilter(perm=EntityCredentials.LINK))
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_role_esetall_change__admincreds(self):
        "CHANGE + ESET_ALL (no app creds, but app admin creds)."
        user = self.user
        self._create_role('Coder', admin_4_apps=['creme_core'], users=[user],
                          set_creds=[
                              SetCredentials(value=EntityCredentials.CHANGE,
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
        self.assertEqual([contact1.id, contact2.id],
                         self._ids_list(efilter(perm=EntityCredentials.CHANGE))
                        )

    def test_role_esetall_delete(self):
        "DELETE + ESET_ALL."
        user = self.user
        self._create_role('Coder', ['creme_core'], users=[user],
                          set_creds=[
                              SetCredentials(value=EntityCredentials.DELETE,
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
        self.assertEqual([contact1.id, contact2.id],
                         self._ids_list(efilter(perm=EntityCredentials.DELETE))
                        )
        self.assertFalse(efilter(perm=EntityCredentials.LINK))
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_role_esetall_link(self):
        "LINK + ESET_ALL."
        user = self.user
        self._create_role('Coder', ['creme_core'], users=[user],
                          set_creds=[
                              SetCredentials(value=EntityCredentials.LINK,
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
        self.assertEqual([contact1.id, contact2.id],
                         self._ids_list(efilter(perm=EntityCredentials.LINK))
                        )
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_role_esetall_unlink(self):
        "UNLINK + ESET_ALL."
        user = self.user
        self._create_role('Coder', ['creme_core'], users=[user],
                          set_creds=[
                              SetCredentials(value=EntityCredentials.UNLINK,
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
        self.assertEqual([contact1.id, contact2.id],
                         self._ids_list(efilter(perm=EntityCredentials.UNLINK))
                        )

    def test_role_esetown_view(self):
        "VIEW + ESET_OWN."
        user = self.user
        self._create_role('Coder', ['creme_core'], users=[user],  # 'persons'
                          set_creds=[
                              SetCredentials(value=EntityCredentials.VIEW,
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
            'Coder', ['creme_core'], users=[user],  # 'persons'
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
        self._create_role('Coder', ['creme_core'], users=[user],  # 'persons'
                          set_creds=[
                              SetCredentials(value=EntityCredentials.DELETE,
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
        self.assertEqual([contact1.id], self._ids_list(efilter(perm=EntityCredentials.DELETE)))
        self.assertFalse(efilter(perm=EntityCredentials.LINK))
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_role_esetown_link_n_unlink(self):
        "ESET_OWN + LINK/UNLINK."
        user = self.user
        self._create_role('Coder', ['creme_core'], users=[user],  # 'persons'
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
        self.assertEqual(ids, self._ids_list(efilter(perm=EntityCredentials.LINK)))
        self.assertEqual(ids, self._ids_list(efilter(perm=EntityCredentials.UNLINK)))

    def test_role_multiset01(self):
        "ESET_ALL + ESET_OWN."
        user = self.user
        self._create_role(
            'Coder', ['creme_core'], users=[user],  # 'persons'
            set_creds=[
                SetCredentials(value=EntityCredentials.VIEW,
                               set_type=SetCredentials.ESET_ALL,
                              ),
                SetCredentials(value=EntityCredentials.CHANGE | EntityCredentials.DELETE,
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
        self.assertEqual([contact1.id, contact2.id], self._ids_list(efilter(perm=EntityCredentials.VIEW)))
        self.assertEqual([contact1.id],              self._ids_list(efilter(perm=EntityCredentials.CHANGE)))
        self.assertEqual([contact1.id],              self._ids_list(efilter(perm=EntityCredentials.DELETE)))
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
        self.assertEqual([contact1.id, contact2.id], self._ids_list(efilter(perm=VIEW)))
        self.assertEqual([contact1.id],              self._ids_list(efilter(perm=CHANGE)))
        self.assertEqual([contact1.id],              self._ids_list(efilter(perm=DELETE)))
        self.assertFalse(efilter(perm=EntityCredentials.LINK))
        self.assertFalse(efilter(perm=EntityCredentials.UNLINK))

    def test_ct_credentials(self):
        user = self.user
        self._create_role('Coder', ['creme_core'], users=[user],
                          set_creds=[
                              SetCredentials(value=EntityCredentials.VIEW,
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
        self.assertEqual([contact1.id, contact2.id],
                         self._ids_list(efilter(qs, perm=EntityCredentials.VIEW))
                        )
        self.assertFalse(efilter(qs, perm=EntityCredentials.CHANGE))
        self.assertFalse(efilter(FakeOrganisation.objects.filter(pk=orga.id),
                                 perm=EntityCredentials.VIEW,
                                 )
                        )

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
        ptype = CremePropertyType.create(str_pk='test-prop_foobar', text='text')
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
        self.assertEqual(_('You are not allowed to access to the app: {}').format(_('Core')),
                         str(cm.exception)
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

        # self.assertEqual(fmt % (_('Invalid app "%s"') % invalid_app),
        self.assertEqual(fmt(apps.get_app_config('persons').verbose_name),
                         str(cm.exception)
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
            'Coder', ['creme_core'],  # 'persons'
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
            team.teammates

    def test_create_team02(self):
        team = CremeUser.objects.create(username='Teamee', is_team=True)

        user  = self.user
        other = self.other_user

        team.teammates = [user, other]
        teammates = team.teammates
        self.assertEqual(2, len(teammates))

        team = self.refresh(team)
        self.assertEqual({user.id: user, other.id: other}, team.teammates)

        with self.assertNumQueries(0):  # Teammates are cached
            team.teammates

        self.assertTrue(all(isinstance(u, CremeUser) for u in teammates.values()))

        ids_set = {user.id, other.id}
        self.assertEqual(ids_set, set(teammates))
        self.assertEqual(ids_set, {u.id for u in teammates.values()})

        user3 = CremeUser.objects.create_user(username='Kanna', email='kanna@century.jp',
                                              first_name='Kanna', last_name='Gendou',
                                              password='uselesspw',
                                             )
        team.teammates = [user, other, user3]
        self.assertEqual(3, len(team.teammates))

        team.teammates = [other]
        self.assertEqual(1, len(team.teammates))
        self.assertEqual({other.id: other}, self.refresh(team).teammates)

    def _create_team(self, name, teammates):
        team = CremeUser.objects.create(username=name, is_team=True, role=None)
        team.teammates = teammates
        return team

    def test_team_credentials01(self):
        user = self.user
        other = self.other_user
        self._create_role('Worker', ['creme_core'], users=[user, other],
                          set_creds=[
                              SetCredentials(value=EntityCredentials.VIEW,
                                             set_type=SetCredentials.ESET_OWN,
                                            ),
                          ],
                         )

        team = self._create_team('Teamee', [user])

        entity = self.refresh(FakeContact.objects.create(user=team, first_name='Ito', last_name='Ittosaï'))  # No cache
        user = self.refresh(user)  # Refresh cache

        with self.assertNumQueries(3):  # Role, SetCredentials & teams
            can_view = user.has_perm_to_view(entity)
        self.assertTrue(can_view)  # Belongs to the team

        with self.assertNumQueries(0):  # Role, SetCredentials & teams -> cached
            can_change = user.has_perm_to_change(entity)
        self.assertFalse(can_change)

        self.assertFalse(other.has_perm_to_view(entity))

        # 'teams' property------------------------------------------------------
        self.assertEqual([team], user.teams)
        self.assertEqual([],     other.teams)

        # Filtering ------------------------------------------------------------
        user = self.refresh(user)  # Refresh caches

        # qs = CremeEntity.objects.filter(pk=entity.id)
        qs = FakeContact.objects.filter(pk=entity.id)
        efilter = EntityCredentials.filter

        with self.assertNumQueries(3):  # Role, SetCredentials & teams
            viewable = efilter(user, qs, perm=EntityCredentials.VIEW)
        self.assertEqual([entity.id], self._ids_list(viewable))  # Belongs to the team

        with self.assertNumQueries(0):  # Role, SetCredentials & teams --> cache
            editable = efilter(user, qs, perm=EntityCredentials.CHANGE)
        self.assertFalse(editable)

        self.assertFalse(efilter(other, qs, perm=EntityCredentials.VIEW))

    def test_team_credentials02(self):
        "User in several teams."
        user = self.user
        other = self.other_user
        self._create_role('Worker', ['creme_core'], users=[user, other],
                          set_creds=[
                              SetCredentials(value=EntityCredentials.VIEW,
                                             set_type=SetCredentials.ESET_OWN,
                                            ),
                          ],
                         )

        create_team = self._create_team
        team1 = create_team('Teamee 1', [user])
        team2 = create_team('Teamee 2', [other, user])
        team3 = create_team('Teamee 3', [other])

        entity1 = FakeContact.objects.create(user=team1, first_name='Munisai', last_name='Shinmen')
        self.assertTrue(user.has_perm_to_view(entity1))  # Belongs to the team
        self.assertFalse(user.has_perm_to_change(entity1))
        self.assertFalse(other.has_perm_to_view(entity1))

        entity2 = FakeContact.objects.create(user=team2, first_name='Kempo', last_name='Yoshioka')
        self.assertTrue(user.has_perm_to_view(entity2))  # Belongs to the team
        self.assertFalse(user.has_perm_to_change(entity2))
        self.assertTrue(other.has_perm_to_view(entity2))
        self.assertFalse(other.has_perm_to_change(entity2))

        # 'teams' property------------------------------------------------------
        teams = user.teams
        self.assertEqual(2, len(teams))
        self.assertEqual({team1, team2}, set(teams))

        with self.assertNumQueries(0):  # Teams are cached
            user.teams

        # Filtering ------------------------------------------------------------
        entity3 = FakeContact.objects.create(user=team3, first_name='Ryohei', last_name='Ueda')

        qs = FakeContact.objects.filter(pk__in=[entity1.id, entity2.id, entity3.id])
        efilter = EntityCredentials.filter
        self.assertEqual([entity1.id, entity2.id],
                         self._ids_list(efilter(user, qs, perm=EntityCredentials.VIEW))
                        )  # Belongs to the teams
        self.assertFalse(efilter(user, qs, perm=EntityCredentials.CHANGE))

    def test_has_perm_to01(self):
        "Not real entity."
        user = self.user
        self._create_role(
            'Worker', ['creme_config'], users=[user],
            set_creds=[SetCredentials(value=EntityCredentials.VIEW,
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
        "Not real entity + auxiliary entity + change/delete"
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
        # self.assertFalse(user.has_perm_to_delete(invoice_entity))

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
                SetCredentials(value=EntityCredentials.VIEW | EntityCredentials.LINK,
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
                SetCredentials(value=EntityCredentials.LINK, set_type=ESET_ALL,
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
                SetCredentials(value=EntityCredentials.LINK, set_type=ESET_ALL,
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
        "Can link only own entities"
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

    def test_is_deleted(self):
        user = self.user
        self._create_role(
            'Coder', ['creme_core'], users=[user],  # 'persons'
            set_creds=[
                SetCredentials(value=EntityCredentials.VIEW | EntityCredentials.CHANGE |
                                     EntityCredentials.LINK | EntityCredentials.UNLINK,
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

        qs = CremeEntity.objects.filter(pk__in=[self.contact1.id, self.contact2.id, orga1.id, orga2.id])

        with self.assertNoException():
            qs2 = EntityCredentials.filter_entities(user, qs)

        # self.assertIs(qs, qs2)
        result = [e.get_real_entity() for e in qs2]
        self.assertEqual(4, len(result))
        self.assertEqual({self.contact1, self.contact2, orga1, orga2}, set(result))

        # ------
        with self.assertRaises(ValueError):
            EntityCredentials.filter(user, qs)

    def test_filter_entities02(self):
        "ESET_ALL."
        user = self.user
        self._create_role('Coder', ['creme_core'], users=[user],
                          set_creds=[
                              SetCredentials(value=EntityCredentials.VIEW,
                                             set_type=SetCredentials.ESET_ALL,
                                            ),
                          ],
                         )

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Yoshioka')
        orga2 = create_orga(user=self.other_user, name='Miyamoto')

        qs = CremeEntity.objects.filter(pk__in=[self.contact1.id, self.contact2.id, orga1.id, orga2.id])
        qs2 = EntityCredentials.filter_entities(user, qs)

        self.assertIsInstance(qs2, QuerySet)
        self.assertIs(qs2.model, CremeEntity)

        result = [e.get_real_entity() for e in qs2]
        self.assertEqual(4, len(result))
        self.assertEqual({self.contact1, self.contact2, orga1, orga2},
                         set(result)
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
                SetCredentials(value=VIEW, set_type=SetCredentials.ESET_ALL,
                               ctype=FakeOrganisation,
                              ),
                SetCredentials(value=CHANGE, set_type=SetCredentials.ESET_ALL),
            ],
        )

        contact3 = FakeContact.objects.create(user=team, first_name='Sekishusai', last_name='Yagyu')

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Yoshioka')
        orga2 = create_orga(user=other, name='Miyamoto')

        qs = CremeEntity.objects.filter(pk__in=[self.contact1.id, self.contact2.id, contact3.id,
                                                orga1.id, orga2.id,
                                               ],
                                       )

        filter_entities = EntityCredentials.filter_entities
        self.assertSetEqual(
            {self.contact1, contact3, orga1, orga2},
            {e.get_real_entity() for e in filter_entities(user, qs, perm=VIEW)}
        )
        self.assertSetEqual(
            {self.contact1, self.contact2, contact3, orga1, orga2},
            {e.get_real_entity() for e in filter_entities(user, qs, perm=CHANGE)}
        )
        self.assertFalse(filter_entities(user, qs, perm=EntityCredentials.DELETE))

    def test_filter_entities04(self):
        "No app credentials => models of this app are excluded."
        user = self.user

        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(value=EntityCredentials.VIEW,
                               set_type=SetCredentials.ESET_ALL,
                              ),
            ],
        )

        create_econf = FakeConfigEntity.objects.create  # Need 'creme_config' credentials
        ec1 = create_econf(user=user, name='Conf1')
        ec2 = create_econf(user=self.other_user, name='Conf2')

        qs = CremeEntity.objects.filter(pk__in=[self.contact1.id, self.contact2.id, ec1.id, ec2.id])
        qs2 = EntityCredentials.filter_entities(user, qs)

        self.assertEqual({self.contact1, self.contact2},
                         {e.get_real_entity() for e in qs2}
                        )

    def test_filter_entities05(self):
        "as_model."
        user = self.user
        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(value=EntityCredentials.VIEW,
                               set_type=SetCredentials.ESET_OWN,
                               ctype=FakeContact,
                              ),
            ],
        )

        create_orga = FakeOrganisation.objects.create
        orga1 = create_orga(user=user, name='Yoshioka')
        orga2 = create_orga(user=self.other_user, name='Miyamoto')

        # Beware: filter_entities() should not be used like this ; 'qs' should not contain not Contact entities.
        qs = CremeEntity.objects.filter(
            pk__in=[self.contact1.id, self.contact2.id, orga1.id, orga2.id],
        )
        qs2 = EntityCredentials.filter_entities(user, qs, as_model=FakeContact)
        self.assertSetEqual({self.contact1, orga1},
                            {e.get_real_entity() for e in qs2}
                           )

    def test_sandox01(self):
        "Owned by super-users."
        user = self.user
        self._create_role(
            'Coder', ['creme_core'], users=[user],
            set_creds=[
                SetCredentials(value=EntityCredentials.VIEW,
                               set_type=SetCredentials.ESET_ALL,
                              ),
            ],
        )

        # sandbox = Sandbox.objects.create(superuser=True)
        sandbox = Sandbox.objects.create()
        contact3 = FakeContact.objects.create(user=user, sandbox=sandbox,
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
            self._ids_list(ecfilter(user, contact_qs, perm=EntityCredentials.VIEW))
        )
        self.assertListEqual(
            [contact1.id, contact2.id, contact3.id],
            self._ids_list(ecfilter(super_user, contact_qs, perm=EntityCredentials.VIEW))
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
            {e.get_real_entity() for e in filter_entities(user, entities_qs)}
        )
        self.assertEqual(
            {contact1, contact2, contact3, orga1, orga2},
            {e.get_real_entity() for e in filter_entities(super_user, entities_qs)}
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

        contact3 = FakeContact.objects.create(user=user, sandbox=sandbox,
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
        super_user = CremeUser.objects.create_superuser(username='super',
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
            self._ids_list(ecfilter(user, contact_qs, perm=EntityCredentials.VIEW))
        )
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(ecfilter(other_user, contact_qs, perm=EntityCredentials.VIEW))
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
            {e.get_real_entity() for e in filter_entities(user, entities_qs)}
        )
        self.assertSetEqual(
            {contact1, contact2, orga1},
            {e.get_real_entity() for e in filter_entities(other_user, entities_qs)}
        )

    def test_sandox03(self):
        "Owned by a user."
        user = self.user
        other_user = self.other_user

        self._create_role(
            'Coder', ['creme_core'], users=[user, other_user],
            set_creds=[SetCredentials(value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL,
                                     ),
                      ],
        )
        sandbox = Sandbox.objects.create(user=user)

        contact3 = FakeContact.objects.create(user=user, sandbox=sandbox,
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
            self._ids_list(ecfilter(user, contact_qs, perm=EntityCredentials.VIEW))
        )
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(ecfilter(other_user, contact_qs, perm=EntityCredentials.VIEW))
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
            {e.get_real_entity() for e in filter_entities(user, entities_qs)}
        )
        self.assertSetEqual(
            {contact1, contact2, orga1},
            {e.get_real_entity() for e in filter_entities(other_user, entities_qs)}
        )

    def test_sandox04(self):
        "Owned by a team."
        user = self.user
        other_user = self.other_user

        self._create_role(
            'Coder', ['creme_core'], users=[user, other_user],
            set_creds=[SetCredentials(value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL,
                                     ),
                      ],
        )
        team = self._create_team('Teamee', [user])
        sandbox = Sandbox.objects.create(user=team)

        contact3 = FakeContact.objects.create(user=user, sandbox=sandbox,
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
            self._ids_list(ecfilter(user, contact_qs, perm=EntityCredentials.VIEW))
        )
        self.assertListEqual(
            [contact1.id, contact2.id],
            self._ids_list(ecfilter(other_user, contact_qs, perm=EntityCredentials.VIEW))
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
            {e.get_real_entity() for e in filter_entities(user, entities_qs)}
        )
        self.assertSetEqual(
            {contact1, contact2, orga1},
            {e.get_real_entity() for e in filter_entities(other_user, entities_qs)}
        )
