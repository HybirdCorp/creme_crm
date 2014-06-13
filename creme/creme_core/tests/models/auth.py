# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.auth.models import User, Permission
    from django.contrib.contenttypes.models import ContentType
    from django.core.exceptions import PermissionDenied
    from django.db.models.deletion import ProtectedError
    from django.utils.translation import ugettext as _

    from ..base import CremeTestCase
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import(CremeEntity, CremePropertyType,
            CremeProperty, Relation, UserRole, SetCredentials)

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('CredentialsTestCase',)


class CredentialsTestCase(CremeTestCase):
    password = 'password'

    @classmethod
    def setUpClass(cls):
        cls.autodiscover()

    def setUp(self):
        create_user = User.objects.create_user
        self.user       = user  = create_user('Kenji', 'kenji@century.jp', self.password)
        self.other_user = other = create_user('Shogun', 'shogun@century.jp', 'uselesspw') #TODO: remove from here ??

        create_contact = Contact.objects.create 
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
            if len(sc) == 2:
                value, set_type = sc
                ctype = None
            else:
                value, set_type, model = sc
                ctype = ContentType.objects.get_for_model(model)

            SetCredentials.objects.create(role=role, value=value, set_type=set_type, ctype=ctype)

        for user in users:
            user.role = role
            user.save()

        return role

    def _build_contact_qs(self):
        return Contact.objects.filter(pk__in=(self.contact1.id, self.contact2.id))

    def test_regularperms01(self):
        "Regular perms not used"
        ct = ContentType.objects.get_for_model(CremeProperty)

        try:
            perm = Permission.objects.get(codename='add_cremeproperty', content_type=ct)
        except Permission.DoesNotExist as e:
            self.fail(str(e))

        self.user.user_permissions.add(perm)
        self.assertFalse(self.user.has_perm('creme_core.add_cremeproperty'))

    def test_super_user(self):
        user = self.user
        user.is_superuser = True #<====

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

        #helpers ---------------------------------------------------------------
        self.assertTrue(user.has_perm_to_view(contact1))
        self.assertTrue(user.has_perm_to_change(contact1))
        self.assertTrue(user.has_perm_to_delete(contact1))
        self.assertTrue(user.has_perm_to_link(contact1))
        self.assertTrue(user.has_perm_to_unlink(contact1))

        self.assertTrue(user.has_perm_to_view(contact2))
        self.assertTrue(user.has_perm_to_change(contact2))

        #helpers (exception version) -------------------------------------------
        self.assertNoException(user.has_perm_to_view_or_die,   contact1)
        self.assertNoException(user.has_perm_to_change_or_die, contact1)
        self.assertNoException(user.has_perm_to_delete_or_die, contact1)
        self.assertNoException(user.has_perm_to_link_or_die,   contact1)
        self.assertNoException(user.has_perm_to_unlink_or_die, contact1)

        #filtering --------------------------------------------------------------
        with self.assertNumQueries(0):
            qs = EntityCredentials.filter(user, self._build_contact_qs())

        self.assertEqual([contact1.id, contact2.id],
                         self._ids_list(qs)
                        )

    #TODO: this tests contribute_to_model too
    def test_role_esetall_view(self):
        "VIEW + ESET_ALL"
        user = self.user
        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.VIEW, SetCredentials.ESET_ALL)]
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

        #helpers ---------------------------------------------------------------
        #refresh caches
        user = self.refresh(user)
        contact1 = self.refresh(contact1)

        with self.assertNumQueries(2): #2 = get UserRole +  its SetCredentials
            can_view = user.has_perm_to_view(contact1)
        self.assertTrue(can_view)

        with self.assertNumQueries(0): #UserRole & SetCredentials are cached
            can_change = user.has_perm_to_change(contact1)
        self.assertFalse(can_change)

        self.assertFalse(user.has_perm_to_delete(contact1))
        self.assertFalse(user.has_perm_to_link(contact1))
        self.assertFalse(user.has_perm_to_unlink(contact1))

        self.assertTrue(user.has_perm_to_view(contact2))
        self.assertFalse(user.has_perm_to_change(contact2))

        #helpers (exception version) -------------------------------------------
        #self.assertNoException(contact1.can_view_or_die, user)
        #self.assertRaises(PermissionDenied, contact1.can_change_or_die, user)
        #self.assertRaises(PermissionDenied, contact1.can_delete_or_die, user)
        #self.assertRaises(PermissionDenied, contact1.can_link_or_die, user)
        #self.assertRaises(PermissionDenied, contact1.can_unlink_or_die, user)

        self.assertNoException(user.has_perm_to_view_or_die, contact1)
        self.assertRaises(PermissionDenied, user.has_perm_to_change_or_die, contact1)
        self.assertRaises(PermissionDenied, user.has_perm_to_delete_or_die, contact1)
        self.assertRaises(PermissionDenied, user.has_perm_to_link_or_die,   contact1)
        self.assertRaises(PermissionDenied, user.has_perm_to_unlink_or_die, contact1)

        #filtering --------------------------------------------------------------
        efilter = EntityCredentials.filter
        qs1 = self._build_contact_qs()

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
        "App is not allowed -> no creds"
        user = self.user
        self._create_role('Coder', users=[user],
                          set_creds=[(EntityCredentials.VIEW, SetCredentials.ESET_ALL)]
                         )

        has_perm = user.has_perm
        contact1 = self.contact1
        self.assertFalse(has_perm('creme_core.view_entity',   contact1))
        self.assertFalse(has_perm('creme_core.change_entity', contact1))
        self.assertFalse(has_perm('creme_core.delete_entity', contact1))
        self.assertFalse(has_perm('creme_core.link_entity',   contact1))
        self.assertFalse(has_perm('creme_core.unlink_entity', contact1))

        self.assertFalse(has_perm('creme_core.view_entity',   self.contact2))

        #helpers ---------------------------------------------------------------
        #self.assertFalse(contact1.can_view(user))
        self.assertFalse(user.has_perm_to_view(contact1))
        #self.assertRaises(PermissionDenied, contact1.can_view_or_die, user)
        self.assertRaises(PermissionDenied, user.has_perm_to_view_or_die, contact1)

        #filtering --------------------------------------------------------------
        self.assertFalse(EntityCredentials.filter(user, self._build_contact_qs()))

    def test_role_esetall_change(self):
        "CHANGE + ESET_ALL"
        user = self.user
        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.CHANGE, SetCredentials.ESET_ALL)]
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
        "CHANGE + ESET_ALL (no app creds, but app admin creds)"
        user = self.user
        self._create_role('Coder', admin_4_apps=['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.CHANGE, SetCredentials.ESET_ALL)]
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
        "DELETE + ESET_ALL"
        user = self.user
        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.DELETE, SetCredentials.ESET_ALL)]
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
        "LINK + ESET_ALL"
        user = self.user
        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.LINK, SetCredentials.ESET_ALL)]
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
        "UNLINK + ESET_ALL"
        user = self.user
        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.UNLINK, SetCredentials.ESET_ALL)]
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
        "VIEW + ESET_OWN"
        user = self.user
        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.VIEW, SetCredentials.ESET_OWN)]
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
        "ESET_OWN + VIEW/CHANGE"
        user = self.user
        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.CHANGE | EntityCredentials.DELETE,
                                      SetCredentials.ESET_OWN
                                     )
                                    ]
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
        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.DELETE, SetCredentials.ESET_OWN)]
                         )

        contact1 = self.contact1

        #self.assertFalse(contact1.can_view(user))
        #self.assertFalse(contact1.can_change(user))
        #self.assertTrue(contact1.can_delete(user))
        #self.assertFalse(contact1.can_link(user))
        #self.assertFalse(contact1.can_unlink(user))

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
        "ESET_OWN + LINK/UNLINK"
        user = self.user
        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.LINK | EntityCredentials.UNLINK,
                                      SetCredentials.ESET_OWN
                                     )
                                    ]
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
        "ESET_ALL + ESET_OWN"
        user = self.user
        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.VIEW,                              SetCredentials.ESET_ALL),
                                     (EntityCredentials.CHANGE | EntityCredentials.DELETE, SetCredentials.ESET_OWN),
                                    ]
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
        "ESET_OWN + ESET_ALL (so ESET_OWN before)"
        user = self.user
        VIEW = EntityCredentials.VIEW
        CHANGE = EntityCredentials.CHANGE
        DELETE = EntityCredentials.DELETE

        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(VIEW | CHANGE | DELETE, SetCredentials.ESET_OWN),
                                     (VIEW,                   SetCredentials.ESET_ALL),
                                    ]
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
        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.VIEW, SetCredentials.ESET_ALL, Contact)]
                         )

        contact1 = self.contact1
        self.assertTrue(user.has_perm_to_view(contact1)) # <=====
        self.assertFalse(user.has_perm_to_change(contact1))
        self.assertFalse(user.has_perm_to_delete(contact1))
        self.assertFalse(user.has_perm_to_link(contact1))
        self.assertFalse(user.has_perm_to_unlink(contact1))

        contact2 = self.contact2
        self.assertTrue(user.has_perm_to_view(contact2)) # <=====
        self.assertFalse(user.has_perm_to_change(contact2))

        orga = Organisation.objects.create(user=user, name='Yoshioka')
        self.assertFalse(user.has_perm_to_view(orga)) # <=====
        self.assertFalse(user.has_perm_to_change(orga))
        self.assertFalse(user.has_perm_to_delete(orga))
        self.assertFalse(user.has_perm_to_link(orga))
        self.assertFalse(user.has_perm_to_unlink(orga))

        #filtering -------------------------------------------------------------
        efilter = partial(EntityCredentials.filter, user)
        qs = self._build_contact_qs()
        self.assertEqual([contact1.id, contact2.id],
                         self._ids_list(efilter(qs, perm=EntityCredentials.VIEW))
                        )
        self.assertFalse(efilter(qs, perm=EntityCredentials.CHANGE))
        self.assertFalse(efilter(Organisation.objects.filter(pk=orga.id),
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
        self.assertFalse(has_perm_to_create(CremeProperty)) #helper

        get_ct = ContentType.objects.get_for_model
        role.creatable_ctypes = [get_ct(CremeProperty), get_ct(Relation)]

        user.role = self.refresh(role) #refresh cache
        self.assertTrue(has_perm('creme_core.add_cremeproperty'))
        self.assertTrue(has_perm('creme_core.add_relation'))
        self.assertFalse(has_perm('creme_core.add_cremepropertytype'))

        #helpers
        self.assertTrue(has_perm_to_create(CremeProperty))
        self.assertFalse(has_perm_to_create(CremePropertyType))

        entity = CremeEntity.objects.create(user=user)
        ptype = CremePropertyType.create(str_pk='test-prop_foobar', text='text')
        prop  = CremeProperty.objects.create(type=ptype, creme_entity=entity)
        self.assertTrue(has_perm_to_create(prop))
        self.assertFalse(has_perm_to_create(ptype))

        #helpers (with exception)
        with self.assertNoException():
            user.has_perm_to_create_or_die(prop)

        self.assertRaises(PermissionDenied, user.has_perm_to_create_or_die, ptype)

    def test_creation_creds02(self):
        user = self.user
        user.is_superuser = True
        self.assertTrue(user.has_perm('creme_core.add_cremeproperty'))

    def test_export_creds01(self):
        user = self.user
        role = self._create_role('Coder', ['creme_core', 'persons'], users=[user])

        has_perm = user.has_perm
        has_perm_to_export = user.has_perm_to_export

        self.assertFalse(has_perm('persons.export_contact'))
        self.assertFalse(has_perm('persons.export_organisation'))
        self.assertFalse(has_perm_to_export(Contact)) #helper

        role.exportable_ctypes.add(ContentType.objects.get_for_model(Contact))

        user.role = self.refresh(role) #refresh cache
        self.assertTrue(has_perm('persons.export_contact'))
        self.assertFalse(has_perm('persons.export_organisation'))
        self.assertTrue(has_perm_to_export(Contact))
        self.assertFalse(has_perm_to_export(Organisation))

        #helpers (with exception)
        with self.assertNoException():
            user.has_perm_to_export_or_die(Contact)

        self.assertRaises(PermissionDenied, user.has_perm_to_export_or_die, Organisation)

    def test_export_creds02(self):
        user = self.user
        user.is_superuser = True
        self.assertTrue(user.has_perm('persons.export_contact'))

    def test_app_creds01(self):
        user = self.user
        role = self._create_role('Salesman', users=[user])

        has_perm = user.has_perm
        self.assertFalse(has_perm('creme_core'))
        self.assertFalse(has_perm('foobar'))
        self.assertFalse(role.allowed_apps)

        role.allowed_apps = ['creme_core', 'foobar']
        role.save()

        role = self.refresh(role)
        allowed_apps = role.allowed_apps
        self.assertEqual(2, len(allowed_apps))
        self.assertIn('creme_core', allowed_apps)
        self.assertIn('foobar',     allowed_apps)

        #user.role = role #refresh object
        self.assertTrue(has_perm('creme_core'))
        self.assertTrue(has_perm('foobar'))
        self.assertFalse(has_perm('quux'))

    def test_app_creds02(self):
        "Admin_4_apps"
        user = self.user
        role = self._create_role('CEO', users=[user])

        has_perm_to_admin = user.has_perm_to_admin
        has_perm = user.has_perm
        self.assertFalse(has_perm_to_admin('creme_core'))
        self.assertFalse(has_perm_to_admin('foobar'))
        self.assertFalse(has_perm('creme_core.can_admin'))
        self.assertFalse(has_perm('foobar.can_admin'))
        self.assertFalse(role.admin_4_apps)

        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_to_admin_or_die('creme_core')

        fmt = _('You are not allowed to configure this app: %s')
        self.assertEqual(fmt % _('Core'), unicode(cm.exception))

        role.admin_4_apps = ['creme_core', 'foobar']
        role.save()

        role = self.refresh(role)
        admin_4_apps = role.admin_4_apps
        self.assertEqual(2, len(admin_4_apps))
        self.assertIn('creme_core', admin_4_apps)
        self.assertIn('foobar',     admin_4_apps)

        #user.role = role #refresh object
        self.assertTrue(has_perm_to_admin('creme_core'))
        self.assertTrue(has_perm_to_admin('foobar'))
        self.assertFalse(has_perm_to_admin('quux'))
        self.assertTrue(has_perm('creme_core.can_admin'))
        self.assertTrue(has_perm('foobar.can_admin'))
        self.assertFalse(has_perm('quux.can_admin'))

        with self.assertNoException():
             user.has_perm_to_admin_or_die('creme_core')
             user.has_perm_to_admin_or_die('foobar')

        invalid_app = 'quux'
        with self.assertRaises(PermissionDenied) as cm:
            user.has_perm_to_admin_or_die(invalid_app)

        self.assertEqual(fmt % (_('Invalid app "%s"') % invalid_app),
                         unicode(cm.exception)
                        )

        self.assertTrue(has_perm('creme_core'))
        self.assertTrue(has_perm('foobar'))
        self.assertFalse(has_perm('quux'))

    def test_app_creds03(self):
        "Super user"
        user = self.user
        user.is_superuser = True

        self.assertTrue(user.has_perm_to_admin('creme_core'))

        has_perm = user.has_perm
        self.assertTrue(has_perm('creme_core'))
        self.assertTrue(has_perm('creme_core.can_admin'))

    def test_delete01(self):
        "Delete role"
        role = self._create_role('Coder', ['creme_core', 'persons'],
                                 set_creds=[(EntityCredentials.CHANGE, SetCredentials.ESET_OWN),
                                            (EntityCredentials.VIEW,   SetCredentials.ESET_ALL)
                                           ]
                                )
        self.assertEqual(2, SetCredentials.objects.filter(role=role).count())

        role.delete()
        self.assertFalse(UserRole.objects.filter(pk=role.id))
        self.assertFalse(SetCredentials.objects.filter(role=role))

    def test_delete02(self):
        "Can not delete a role linked to a user"
        user = self.user
        role = self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                                 set_creds=[(EntityCredentials.CHANGE, SetCredentials.ESET_OWN),
                                            (EntityCredentials.VIEW,   SetCredentials.ESET_ALL)
                                           ]
                                )

        self.assertRaises(ProtectedError, role.delete)
        self.assertEqual(1, UserRole.objects.filter(pk=role.id).count())
        self.assertEqual(2, SetCredentials.objects.filter(role=role).count())

    def test_create_team01(self):
        team = User.objects.create(username='Teamee')

        self.assertFalse(team.is_team)

        with self.assertRaises(AssertionError):
            team.teammates = [self.user]

        with self.assertRaises(AssertionError):
            team.teammates

    def test_create_team02(self):
        team = User.objects.create(username='Teamee', is_team=True)

        user  = self.user
        other = self.other_user

        team.teammates = [user, other]
        teammates = team.teammates
        self.assertEqual(2, len(teammates))

        team = self.refresh(team)
        self.assertEqual({user.id: user, other.id: other}, team.teammates)

        with self.assertNumQueries(0): #teammates are cached
            team.teammates

        self.assertTrue(all(isinstance(u, User) for u in teammates.itervalues()))

        ids_set = {user.id, other.id}
        self.assertEqual(ids_set, set(teammates.iterkeys()))
        self.assertEqual(ids_set, {u.id for u in teammates.itervalues()})

        user3 = User.objects.create_user('Kanna', 'kanna@century.jp', 'uselesspw')
        team.teammates = [user, other, user3]
        self.assertEqual(3, len(team.teammates))

        team.teammates = [other]
        self.assertEqual(1, len(team.teammates))
        self.assertEqual({other.id: other}, self.refresh(team).teammates)

    def _create_team(self, name, teammates):
        team = User.objects.create(username=name, is_team=True, role=None)
        team.teammates = teammates
        return team

    def test_team_credentials01(self):
        user = self.user
        other = self.other_user
        self._create_role('Worker', ['creme_core'], users=[user, other],
                          set_creds=[(EntityCredentials.VIEW, SetCredentials.ESET_OWN)]
                         )

        team = self._create_team('Teamee', [user])

        entity = self.refresh(CremeEntity.objects.create(user=team)) #no cache
        user = self.refresh(user) #refresh cache

        with self.assertNumQueries(3): #role, SetCredentials & teams
            can_view = user.has_perm_to_view(entity)
        self.assertTrue(can_view) #belongs to the team

        with self.assertNumQueries(0): #role, SetCredentials & teams -> cached
            can_change = user.has_perm_to_change(entity)
        self.assertFalse(can_change)

        self.assertFalse(other.has_perm_to_view(entity))

        #'teams' property-------------------------------------------------------
        self.assertEqual([team], user.teams)
        self.assertEqual([],     other.teams)

        #filtering -------------------------------------------------------------
        user = self.refresh(user) #refresh caches

        qs = CremeEntity.objects.filter(pk=entity.id)
        efilter = EntityCredentials.filter

        with self.assertNumQueries(3): #role, SetCredentials & teams
            viewable = efilter(user, qs, perm=EntityCredentials.VIEW)
        self.assertEqual([entity.id], self._ids_list(viewable)) #belongs to the team

        with self.assertNumQueries(0): #role, SetCredentials & teams --> cache
            editable = efilter(user, qs, perm=EntityCredentials.CHANGE)
        self.assertFalse(editable)

        self.assertFalse(efilter(other, qs, perm=EntityCredentials.VIEW))

    def test_team_credentials02(self):
        "User in several teams"
        user = self.user
        other = self.other_user
        self._create_role('Worker', ['creme_core'], users=[user, other],
                          set_creds=[(EntityCredentials.VIEW, SetCredentials.ESET_OWN)]
                         )

        create_team = self._create_team
        team1 = create_team('Teamee 1', [user])
        team2 = create_team('Teamee 2', [other, user])
        team3 = create_team('Teamee 3', [other])

        entity1 = CremeEntity.objects.create(user=team1)
        self.assertTrue(user.has_perm_to_view(entity1)) #belongs to the team
        self.assertFalse(user.has_perm_to_change(entity1))
        self.assertFalse(other.has_perm_to_view(entity1))

        entity2 = CremeEntity.objects.create(user=team2)
        self.assertTrue(user.has_perm_to_view(entity2)) #belongs to the team
        self.assertFalse(user.has_perm_to_change(entity2))
        self.assertTrue(other.has_perm_to_view(entity2))
        self.assertFalse(other.has_perm_to_change(entity2))

        #'teams' property-------------------------------------------------------
        teams = user.teams
        self.assertEqual(2, len(teams))
        self.assertEqual({team1, team2}, set(teams))

        with self.assertNumQueries(0): #teams are cached
            user.teams

        #filtering -------------------------------------------------------------
        entity3 = CremeEntity.objects.create(user=team3)

        qs = CremeEntity.objects.filter(pk__in=[entity1.id, entity2.id, entity3.id])
        efilter = EntityCredentials.filter
        self.assertEqual([entity1.id, entity2.id],
                         self._ids_list(efilter(user, qs, perm=EntityCredentials.VIEW))
                        ) #belongs to the teams
        self.assertFalse(efilter(user, qs, perm=EntityCredentials.CHANGE))

    def test_has_perm_to_link01(self):
        "Super user"
        user = self.user
        user.is_superuser = True #<====

        #has_perm = user.has_perm_to_link
        #self.assertTrue(user.has_perm_to_link()) TODO ??
        self.assertTrue(user.has_perm_to_link(Organisation))

        with self.assertNoException():
            user.has_perm_to_link_or_die(Organisation)

    def test_has_perm_to_link02(self):
        "No LINK perm at all"
        user = self.user
        self._create_role('Worker', ['creme_core'], users=[user],
                          set_creds=[(EntityCredentials.VIEW, SetCredentials.ESET_ALL)]
                         )

        has_perm_to_link = user.has_perm_to_link
        #self.assertFalse(user.has_perm_to_link()) TODO ??
        self.assertFalse(has_perm_to_link(Organisation))
        self.assertFalse(has_perm_to_link(Organisation, owner=None))
        self.assertFalse(has_perm_to_link(Organisation, owner=self.other_user))

        self.assertRaises(PermissionDenied, user.has_perm_to_link_or_die, Organisation)

    def test_has_perm_to_link03(self):
        "Can LINK all"
        user = self.user
        self._create_role('Worker', ['creme_core'], users=[user],
                          set_creds=[(EntityCredentials.VIEW | EntityCredentials.LINK,
                                      SetCredentials.ESET_ALL
                                     )
                                    ]
                         )

        team = self._create_team('Teamee', [user, self.other_user])

        has_perm_to_link = user.has_perm_to_link
        self.assertTrue(has_perm_to_link(Organisation))
        self.assertTrue(has_perm_to_link(Organisation, owner=user))
        self.assertTrue(has_perm_to_link(Organisation, owner=self.other_user))
        self.assertTrue(has_perm_to_link(Organisation, owner=team))

    def test_has_perm_to_link04(self):
        "With CT credentials -> has perm"
        user = self.user
        self._create_role('Worker', ['creme_core'], users=[user],
                          set_creds=[(EntityCredentials.VIEW, SetCredentials.ESET_ALL),
                                     (EntityCredentials.LINK, SetCredentials.ESET_ALL, Organisation),
                                    ]
                         )

        has_perm_to_link = user.has_perm_to_link
        self.assertTrue(has_perm_to_link(Organisation))
        self.assertTrue(has_perm_to_link(Organisation, owner=None))
        self.assertTrue(has_perm_to_link(Organisation, owner=user))
        self.assertTrue(has_perm_to_link(Organisation, owner=self.other_user))

    def test_has_perm_to_link05(self):
        "With CT credentials -> has not perm"
        user = self.user
        self._create_role('Worker', ['creme_core'], users=[user],
                          set_creds=[(EntityCredentials.VIEW, SetCredentials.ESET_ALL),
                                     (EntityCredentials.LINK, SetCredentials.ESET_ALL, Contact), #<= not Organisation
                                    ]
                         )

        has_perm_to_link = user.has_perm_to_link
        self.assertFalse(has_perm_to_link(Organisation))
        self.assertFalse(has_perm_to_link(Organisation, owner=user))
        self.assertTrue(has_perm_to_link(Contact))
        self.assertTrue(has_perm_to_link(Contact, owner=user))
        self.assertTrue(has_perm_to_link(Contact, owner=self.other_user))

    def test_has_perm_to_link06(self):
        "Can link only own entities"
        user = self.user
        self._create_role('Worker', ['creme_core'], users=[user],
                          set_creds=[(EntityCredentials.VIEW, SetCredentials.ESET_ALL),
                                     (EntityCredentials.LINK, SetCredentials.ESET_OWN),
                                    ]
                         )

        other_user = self.other_user
        team1 = self._create_team('Team#1', [user, other_user])
        team2 = self._create_team('Team#2', [other_user])

        has_perm_to_link = user.has_perm_to_link
        self.assertTrue(has_perm_to_link(Organisation, owner=None))
        self.assertTrue(has_perm_to_link(Organisation, owner=user))
        self.assertFalse(has_perm_to_link(Organisation, owner=other_user))
        self.assertTrue(has_perm_to_link(Organisation, owner=team1))
        self.assertFalse(has_perm_to_link(Organisation, owner=team2))

    def test_is_deleted(self):
        user = self.user
        self._create_role('Coder', ['creme_core', 'persons'], users=[user],
                          set_creds=[(EntityCredentials.VIEW | EntityCredentials.CHANGE |
                                      EntityCredentials.LINK | EntityCredentials.UNLINK,
                                      SetCredentials.ESET_ALL
                                     )
                                    ]
                         )

        contact = self.contact1
        #self.assertTrue(contact.can_change(user))
        #self.assertTrue(contact.can_link(user))
        #self.assertTrue(contact.can_unlink(user))
        self.assertTrue(user.has_perm_to_change(contact))
        self.assertTrue(user.has_perm_to_link(contact))
        self.assertTrue(user.has_perm_to_unlink(contact))

        contact.trash()

        #with self.assertNoException(): #refresh cache
            #contact = self.refresh(contact)

        #self.assertFalse(contact.can_change(user))
        #self.assertFalse(contact.can_link(user))
        #self.assertTrue(contact.can_unlink(user))
        self.assertFalse(user.has_perm_to_change(contact))
        self.assertFalse(user.has_perm_to_link(contact))
        self.assertTrue(user.has_perm_to_unlink(contact))
