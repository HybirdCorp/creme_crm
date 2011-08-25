# -*- coding: utf-8 -*-

from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *
from creme_core.tests.base import CremeTestCase

from persons.models import Contact, Organisation


__all__ = ('CredentialsTestCase',)


class CredentialsTestCase(CremeTestCase):
    def setUp(self):
        self.password = 'password'
        self.user = User.objects.create_user('Kenji', 'kenji@century.jp', self.password)
        self.other_user = User.objects.create_user('Shogun', 'shogun@century.jp', 'uselesspw')

        self.entity1 = CremeEntity.objects.create(user=self.user)
        self.entity2 = CremeEntity.objects.create(user=self.user)

        self.client.login(username=self.user.username, password=self.password)

    def test_default_perms(self):
        self.failIf(self.user.has_perm('creme_core.view_entity',   self.entity1))
        self.failIf(self.user.has_perm('creme_core.change_entity', self.entity1))
        self.failIf(self.user.has_perm('creme_core.delete_entity', self.entity1))
        self.failIf(self.user.has_perm('creme_core.link_entity',   self.entity1))
        self.failIf(self.user.has_perm('creme_core.unlink_entity', self.entity1))

        defcreds = EntityCredentials.get_default_creds()
        self.failIf(defcreds.can_view())
        self.failIf(defcreds.can_change())
        self.failIf(defcreds.can_delete())

        EntityCredentials.set_default_perms(view=True, change=True, delete=True, link=True, unlink=True)

        self.assert_(self.user.has_perm('creme_core.view_entity',   self.entity1))
        self.assert_(self.user.has_perm('creme_core.change_entity', self.entity1))
        self.assert_(self.user.has_perm('creme_core.delete_entity', self.entity1))
        self.assert_(self.user.has_perm('creme_core.link_entity',   self.entity1))
        self.assert_(self.user.has_perm('creme_core.unlink_entity', self.entity1))

        defcreds = EntityCredentials.get_default_creds()
        self.assert_(defcreds.can_view())
        self.assert_(defcreds.can_change())
        self.assert_(defcreds.can_delete())
        self.assert_(defcreds.can_link())
        self.assert_(defcreds.can_unlink())

    def test_entity_perms01(self):
        EntityCredentials.set_entity_perms(self.user, self.entity1, view=True, change=True, delete=True, link=True, unlink=True)

        self.assert_(self.user.has_perm('creme_core.view_entity',   self.entity1))
        self.assert_(self.user.has_perm('creme_core.change_entity', self.entity1))
        self.assert_(self.user.has_perm('creme_core.delete_entity', self.entity1))
        self.assert_(self.user.has_perm('creme_core.link_entity',   self.entity1))
        self.assert_(self.user.has_perm('creme_core.unlink_entity', self.entity1))

    def test_entity_perms02(self): #super-user
        self.user.is_superuser = True

        self.assert_(self.user.has_perm('creme_core.view_entity',   self.entity1))
        self.assert_(self.user.has_perm('creme_core.change_entity', self.entity1))
        self.assert_(self.user.has_perm('creme_core.delete_entity', self.entity1))
        self.assert_(self.user.has_perm('creme_core.link_entity',   self.entity1))
        self.assert_(self.user.has_perm('creme_core.unlink_entity', self.entity1))

    def build_qs(self):
        return CremeEntity.objects.filter(pk__in=(self.entity1.id, self.entity2.id))

    def ids_list(self, iterable):
        return [e.id for e in iterable]

    def test_filter01(self): #filter with default credentials OK
        EntityCredentials.set_default_perms(view=True) #change=True, delete=True

        ids = [self.entity1.id, self.entity2.id]
        qs = EntityCredentials.filter(self.user, self.build_qs()) #TODO: give wanted perms ???
        self.assertEqual(ids, self.ids_list(qs))

        qs = EntityCredentials.filter(self.other_user, self.build_qs())
        self.assertEqual(ids, self.ids_list(qs))

    def test_filter02(self): #filter with default credentials KO
        qs1 = self.build_qs()
        qs2 = EntityCredentials.filter(self.user, qs1)

        self.assert_(qs1._result_cache is None)
        self.failIf(qs2)
        self.failIf(EntityCredentials.filter(self.other_user, qs1))

    def test_filter03(self):  #filter with all credentials set
        EntityCredentials.set_entity_perms(self.user, self.entity1, view=False)
        EntityCredentials.set_entity_perms(self.user, self.entity2, view=True)

        qs1 = self.build_qs()
        qs2 = EntityCredentials.filter(self.user, qs1)

        self.assert_(qs1._result_cache is None, 'Queryset has been retrieved (should be lazy)')
        self.assertEqual([self.entity2.id], self.ids_list(qs2))

        self.failIf(EntityCredentials.filter(self.other_user, qs1))

    def test_filter04(self): #filter with some credentials set (and default OK)
        EntityCredentials.set_default_perms(view=True) #change=True, delete=True
        EntityCredentials.set_entity_perms(self.user, self.entity2, view=True)

        qs = EntityCredentials.filter(self.user, self.build_qs())
        self.assertEqual([self.entity1.id, self.entity2.id], self.ids_list(qs))

    def test_filter05(self): #filter with some credentials set (and default KO)
        EntityCredentials.set_entity_perms(self.user, self.entity2, view=True)

        qs = EntityCredentials.filter(self.user, self.build_qs())
        self.assertEqual([self.entity2.id], self.ids_list(qs))

    def test_filter06(self): #super-user
        self.user.is_superuser = True

        qs = EntityCredentials.filter(self.user, self.build_qs())
        self.assertEqual([self.entity1.id, self.entity2.id], self.ids_list(qs))

    def build_subject_n_relations(self):
        subject = CremeEntity.objects.create(user=self.user)
        rtype, srtype = RelationType.create(('test-subject_foobar', 'loves'), ('test-object_foobar',  'is loved by'))

        create_relation = lambda obj: Relation.objects.create(subject_entity=subject, object_entity=obj, type=rtype, user=self.user)
        r1 = create_relation(self.entity1)
        r2 = create_relation(self.entity2)

        return (subject, r1, r2)

    def test_filter_relations01(self): #filter with default credentials OK
        EntityCredentials.set_default_perms(view=True)

        subject, r1, r2 = self.build_subject_n_relations()
        ids = [r1.id, r2.id]
        qs = EntityCredentials.filter_relations(self.user, Relation.objects.filter(pk__in=ids))
        self.assertEqual(ids, self.ids_list(qs))

    def test_filter_relations02(self): #filter with default credentials KO
        subject, r1, r2 = self.build_subject_n_relations()
        ids = [r1.id, r2.id]
        qs1 = Relation.objects.filter(pk__in=ids)
        qs2 = EntityCredentials.filter_relations(self.user, qs1)

        self.assert_(qs1._result_cache is None)
        self.failIf(qs2)

    def test_filter_relations03(self):  #filter with all credentials set
        EntityCredentials.set_entity_perms(self.user, self.entity1, view=False)
        EntityCredentials.set_entity_perms(self.user, self.entity2, view=True)

        subject, r1, r2 = self.build_subject_n_relations()
        ids = [r1.id, r2.id]
        qs = EntityCredentials.filter_relations(self.user, Relation.objects.filter(pk__in=ids))
        self.assertEqual([r2.id], self.ids_list(qs))

    def test_filter_relations04(self): #super-user
        self.user.is_superuser = True

        subject, r1, r2 = self.build_subject_n_relations()
        ids = [r1.id, r2.id]
        qs = EntityCredentials.filter_relations(self.user, Relation.objects.filter(pk__in=ids))
        self.assertEqual(ids, self.ids_list(qs))

    def test_regularperms01(self): #regular perms not used
        ct = ContentType.objects.get_for_model(CremeProperty)

        try:
            perm = Permission.objects.get(codename='add_cremeproperty', content_type=ct)
        except Permission.DoesNotExist, e:
            self.fail(str(e))

        self.user.user_permissions.add(perm)
        self.failIf(self.user.has_perm('creme_core.add_cremeproperty'))

    def test_helpers01(self):
        self.assertRaises(PermissionDenied, self.entity1.can_view_or_die, self.user)
        self.failIf(self.entity1.can_view(self.user))

        EntityCredentials.set_default_perms(view=True)
        entity1 = CremeEntity.objects.get(pk=self.entity1.id) #refresh cache

        try:
            entity1.can_view_or_die(self.user)
        except PermissionDenied, e:
            self.fail(str(e))

        self.assert_(entity1.can_view(self.user))

    def test_helpers02(self):
        self.assertRaises(PermissionDenied, self.entity1.can_change_or_die, self.user)
        self.failIf(self.entity1.can_change(self.user))

        EntityCredentials.set_default_perms(change=True)
        entity1 = CremeEntity.objects.get(pk=self.entity1.id) #refresh cache

        try:
            entity1.can_change_or_die(self.user)
        except PermissionDenied, e:
            self.fail(str(e))

        self.assert_(entity1.can_change(self.user))

    def test_helpers03(self):
        self.assertRaises(PermissionDenied, self.entity1.can_delete_or_die, self.user)
        self.failIf(self.entity1.can_delete(self.user))

        EntityCredentials.set_default_perms(delete=True)
        entity1 = CremeEntity.objects.get(pk=self.entity1.id) #refresh cache

        try:
            entity1.can_delete_or_die(self.user)
        except PermissionDenied, e:
            self.fail(str(e))

        self.assert_(entity1.can_delete(self.user))

    def test_helpers04(self):
        self.assertRaises(PermissionDenied, self.entity1.can_link_or_die, self.user)
        self.failIf(self.entity1.can_link(self.user))

        EntityCredentials.set_default_perms(link=True)
        entity1 = CremeEntity.objects.get(pk=self.entity1.id) #refresh cache

        try:
            entity1.can_link_or_die(self.user)
        except PermissionDenied, e:
            self.fail(str(e))

        self.assert_(entity1.can_link(self.user))

    def test_helpers05(self):
        self.assertRaises(PermissionDenied, self.entity1.can_unlink_or_die, self.user)
        self.failIf(self.entity1.can_unlink(self.user))

        EntityCredentials.set_default_perms(unlink=True)
        entity1 = CremeEntity.objects.get(pk=self.entity1.id) #refresh cache

        try:
            entity1.can_unlink_or_die(self.user)
        except PermissionDenied, e:
            self.fail(str(e))

        self.assert_(entity1.can_unlink(self.user))

    def test_helpers_superuser(self):
        self.user.is_superuser = True

        self.entity1.can_view_or_die(self.user)
        self.entity1.can_change_or_die(self.user)
        self.entity1.can_delete_or_die(self.user)
        self.entity1.can_link_or_die(self.user)
        self.entity1.can_delete_or_die(self.user)

    def _create_role(self, name, allowed_apps=(), admin_4_apps=()):
        role = UserRole(name=name)
        role.allowed_apps = allowed_apps
        role.admin_4_apps = admin_4_apps
        role.save()

        return role

    #this tests contribute_to_model too
    def test_role_esetall01(self): # CRED_VIEW + ESET_ALL
        try:
            role = self._create_role('Coder', ['creme_core'])
            self.user.role = role
            self.user.save()
            SetCredentials.objects.create(role=role,
                                          value=SetCredentials.CRED_VIEW,
                                          set_type=SetCredentials.ESET_ALL) #helper ??
        except Exception, e:
            self.fail(str(e))

        entity3 = CremeEntity.objects.create(user=self.user) #created by user -> user can read, other_user has no creds
        self.assert_(self.user.has_perm('creme_core.view_entity', entity3))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity3))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity3))
        self.failIf(self.other_user.has_perm('creme_core.view_entity', entity3)) #default creds for him...

        entity4 = CremeEntity.objects.create(user=self.other_user) #created by user -> user can read in anyway
        self.assert_(self.user.has_perm('creme_core.view_entity',  entity4))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity4))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity4))
        self.failIf(self.other_user.has_perm('creme_core.view_entity',   entity4))
        self.failIf(self.other_user.has_perm('creme_core.change_entity', entity4))
        self.failIf(self.other_user.has_perm('creme_core.delete_entity', entity4))

    def test_role_esetall01__noappcreds(self): #app is not allowed -> no creds
        role = UserRole.objects.create(name='Coder')
        self.user.role = role
        self.user.save()
        SetCredentials.objects.create(role=role,
                                        value=SetCredentials.CRED_VIEW,
                                        set_type=SetCredentials.ESET_ALL) #helper ??

        entity3 = CremeEntity.objects.create(user=self.user) #created by user -> user can read, other_user has no creds
        self.failIf(self.user.has_perm('creme_core.view_entity', entity3))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity3))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity3))

        entity4 = CremeEntity.objects.create(user=self.other_user)
        self.failIf(self.user.has_perm('creme_core.view_entity',  entity4))

    def test_role_esetall02(self): # CRED_CHANGE + ESET_ALL
        try:
            role = self._create_role('Coder', ['creme_core'])
            self.user.role = role
            self.user.save()
            SetCredentials.objects.create(role=role,
                                          value=SetCredentials.CRED_CHANGE,
                                          set_type=SetCredentials.ESET_ALL)
        except Exception, e:
            self.fail(str(e))

        entity3 = CremeEntity.objects.create(user=self.user)
        self.failIf(self.user.has_perm('creme_core.view_entity',    entity3))
        self.assert_(self.user.has_perm('creme_core.change_entity', entity3))
        self.failIf(self.user.has_perm('creme_core.delete_entity',  entity3))

        entity4 = CremeEntity.objects.create(user=self.other_user)
        self.failIf(self.user.has_perm('creme_core.view_entity',    entity4))
        self.assert_(self.user.has_perm('creme_core.change_entity', entity4))
        self.failIf(self.user.has_perm('creme_core.delete_entity',  entity4))

    def test_role_esetall03(self): # CRED_DELETE + ESET_ALL
        role = self._create_role('Coder', ['creme_core'])
        self.user.role = role
        self.user.save()
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_DELETE,
                                      set_type=SetCredentials.ESET_ALL)

        entity3 = CremeEntity.objects.create(user=self.user)
        self.failIf(self.user.has_perm('creme_core.view_entity',    entity3))
        self.failIf(self.user.has_perm('creme_core.change_entity',  entity3))
        self.assert_(self.user.has_perm('creme_core.delete_entity', entity3))
        self.failIf(self.user.has_perm('creme_core.link_entity',    entity3))
        self.failIf(self.user.has_perm('creme_core.unlink_entity',  entity3))

        entity4 = CremeEntity.objects.create(user=self.other_user)
        self.failIf(self.user.has_perm('creme_core.view_entity',    entity4))
        self.failIf(self.user.has_perm('creme_core.change_entity',  entity4))
        self.assert_(self.user.has_perm('creme_core.delete_entity', entity4))
        self.failIf(self.user.has_perm('creme_core.link_entity',    entity4))
        self.failIf(self.user.has_perm('creme_core.unlink_entity',  entity4))

    def test_role_esetall04(self): # CRED_LINK + ESET_ALL
        role = self._create_role('Coder', ['creme_core'])
        self.user.role = role
        self.user.save()
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_LINK,
                                      set_type=SetCredentials.ESET_ALL)

        entity3 = CremeEntity.objects.create(user=self.user)
        self.failIf(self.user.has_perm('creme_core.view_entity',   entity3))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity3))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity3))
        self.assert_(self.user.has_perm('creme_core.link_entity',  entity3))
        self.failIf(self.user.has_perm('creme_core.unlink_entity', entity3))

        entity4 = CremeEntity.objects.create(user=self.other_user)
        self.failIf(self.user.has_perm('creme_core.view_entity',   entity4))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity4))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity4))
        self.assert_(self.user.has_perm('creme_core.link_entity',  entity4))
        self.failIf(self.user.has_perm('creme_core.unlink_entity', entity4))

    def test_role_esetown01(self): # CRED_VIEW + ESET_OWN
        role = self._create_role('Coder', ['creme_core'], ['creme_core'])
        self.user.role = role
        self.user.save()
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_OWN)

        entity3 = CremeEntity.objects.create(user=self.user)
        self.assert_(self.user.has_perm('creme_core.view_entity',  entity3))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity3))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity3))
        self.failIf(self.user.has_perm('creme_core.link_entity',   entity3))
        self.failIf(self.user.has_perm('creme_core.unlink_entity', entity3))

        entity4 = CremeEntity.objects.create(user=self.other_user)
        self.failIf(self.user.has_perm('creme_core.view_entity',   entity4))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity4))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity4))
        self.failIf(self.user.has_perm('creme_core.link_entity',   entity4))
        self.failIf(self.user.has_perm('creme_core.unlink_entity', entity4))

    def test_role_esetown02(self): # ESET_OWN + CRED_VIEW/CRED_CHANGE
        role = self._create_role('Coder', ['creme_core', 'foobar'])
        self.user.role = role
        self.user.save()
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE,
                                      set_type=SetCredentials.ESET_OWN)

        entity3 = CremeEntity.objects.create(user=self.user)
        self.failIf(self.user.has_perm('creme_core.view_entity',    entity3))
        self.assert_(self.user.has_perm('creme_core.change_entity', entity3))
        self.assert_(self.user.has_perm('creme_core.delete_entity', entity3))

        entity4 = CremeEntity.objects.create(user=self.other_user)
        self.failIf(self.user.has_perm('creme_core.view_entity',   entity4))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity4))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity4))

    def test_role_esetown03(self): # ESET_OWN + CRED_LINK/CRED_UNLINK
        role = self._create_role('Coder', ['creme_core'])
        self.user.role = role
        self.user.save()
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN)

        entity3 = CremeEntity.objects.create(user=self.user)
        self.failIf(self.user.has_perm('creme_core.view_entity',    entity3))
        self.assert_(self.user.has_perm('creme_core.link_entity',   entity3))
        self.assert_(self.user.has_perm('creme_core.unlink_entity', entity3))

        entity4 = CremeEntity.objects.create(user=self.other_user)
        self.failIf(self.user.has_perm('creme_core.view_entity',   entity4))
        self.failIf(self.user.has_perm('creme_core.link_entity',   entity4))
        self.failIf(self.user.has_perm('creme_core.unlink_entity', entity4))

    def test_role_multiset01(self): # ESET_OWN + ESET_ALL
        role = self._create_role('Coder', ['foobar', 'creme_core'])
        self.user.role = role
        self.user.save()
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE,
                                      set_type=SetCredentials.ESET_OWN)

        entity3 = CremeEntity.objects.create(user=self.user)
        self.assert_(self.user.has_perm('creme_core.view_entity',   entity3))
        self.assert_(self.user.has_perm('creme_core.change_entity', entity3))
        self.assert_(self.user.has_perm('creme_core.delete_entity', entity3))

        entity4 = CremeEntity.objects.create(user=self.other_user)
        self.assert_(self.user.has_perm('creme_core.view_entity',  entity4))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity4))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity4))

    def test_role_updating01(self):
        role = self._create_role('Coder', ['foobar', 'quux'], ['stuff', 'creme_core'])
        self.user.role = role
        self.user.save()
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)

        #the entities created before the role was set should have right credentials too
        self.user.update_credentials()
        self.assert_(self.user.has_perm('creme_core.view_entity',  self.entity1))
        self.failIf(self.user.has_perm('creme_core.change_entity', self.entity1))
        self.failIf(self.user.has_perm('creme_core.delete_entity', self.entity1))
        self.assert_(self.user.has_perm('creme_core.view_entity',  self.entity2))

        #we modify the user perms -> entities should still have the right credentials
        self.user.role = None
        self.user.save()
        self.user.update_credentials()
        self.failIf(self.user.has_perm('creme_core.view_entity', self.entity1))

    def test_role_updating02(self):
        role1 = self._create_role('View all', ['creme_core'])
        SetCredentials.objects.create(role=role1,
                                      value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)

        entity3 = CremeEntity.objects.create(user=self.other_user)

        self.user.role = role1
        self.user.save()
        self.user.update_credentials()
        self.assert_(self.user.has_perm('creme_core.view_entity',  self.entity1))
        self.failIf(self.user.has_perm('creme_core.change_entity', self.entity1))
        self.assert_(self.user.has_perm('creme_core.view_entity',  entity3))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity3))

        role2 = self._create_role('Isolated worker', ['creme_core'])
        SetCredentials.objects.create(role=role2,
                                      value=SetCredentials.CRED_VIEW|SetCredentials.CRED_CHANGE|SetCredentials.CRED_DELETE,
                                      set_type=SetCredentials.ESET_OWN)

        #we modify the user perms -> entities should still have the right credentials
        self.user.role = role2
        self.user.save()
        self.user.update_credentials()
        self.assert_(self.user.has_perm('creme_core.view_entity',   self.entity1))
        self.assert_(self.user.has_perm('creme_core.change_entity', self.entity1))
        self.failIf(self.user.has_perm('creme_core.view_entity',    entity3))
        self.failIf(self.user.has_perm('creme_core.change_entity',  entity3))

    def test_role_updating03(self): #detect a bug: all EntityCredentials were deleted when calling update_credentials()
        role1 = UserRole.objects.create(name='View all')
        SetCredentials.objects.create(role=role1,
                                      value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)

        self.user.role = role1
        self.user.update_credentials()
        self.assertEqual(2, EntityCredentials.objects.count())

        role2 = UserRole.objects.create(name='View all')
        SetCredentials.objects.create(role=role2,
                                      value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)

        self.other_user.role = role2
        self.other_user.update_credentials()
        self.assertEqual(4, EntityCredentials.objects.count())

    def test_creation_creds01(self):
        try:
            role = UserRole.objects.create(name='Coder')
            self.user.role = role
            self.user.save()
        except Exception, e:
            self.fail(str(e))

        self.failIf(self.user.has_perm('creme_core.add_cremeproperty'))
        self.failIf(self.user.has_perm('creme_core.add_relation'))
        self.failIf(self.user.has_perm_to_create(CremeProperty)) #helper

        get_ct = ContentType.objects.get_for_model
        role.creatable_ctypes = [get_ct(CremeProperty), get_ct(Relation)]

        self.user.role = UserRole.objects.get(pk=role.id) #refresh cache
        self.assert_(self.user.has_perm('creme_core.add_cremeproperty'))
        self.assert_(self.user.has_perm('creme_core.add_relation'))
        self.failIf(self.user.has_perm('creme_core.add_cremepropertytype'))

        #helpers
        self.assert_(self.user.has_perm_to_create(CremeProperty))
        self.failIf(self.user.has_perm_to_create(CremePropertyType))

        ptype = CremePropertyType.create(str_pk='test-prop_foobar', text='text')
        prop  = CremeProperty.objects.create(type=ptype, creme_entity=self.entity1)
        self.assert_(self.user.has_perm_to_create(prop))
        self.failIf(self.user.has_perm_to_create(ptype))

    def test_creation_creds02(self):
        self.user.is_superuser = True
        self.assert_(self.user.has_perm('creme_core.add_cremeproperty'))

    def test_export_creds01(self):
        role = self._create_role('Coder', ['creme_core', 'persons'])
        self.user.role = role
        self.user.save()

        self.failIf(self.user.has_perm('persons.export_contact'))
        self.failIf(self.user.has_perm('persons.export_organisation'))
        self.failIf(self.user.has_perm_to_export(Contact)) #helper

        role.exportable_ctypes.add(ContentType.objects.get_for_model(Contact))

        self.user.role = UserRole.objects.get(pk=role.id) #refresh cache
        self.assert_(self.user.has_perm('persons.export_contact'))
        self.failIf(self.user.has_perm('persons.export_organisation'))
        self.assert_(self.user.has_perm_to_export(Contact))
        self.failIf(self.user.has_perm_to_export(Organisation))

    def test_export_creds02(self):
        self.user.is_superuser = True
        self.assert_(self.user.has_perm('persons.export_contact'))

    def test_app_creds01(self):
        try:
            role = UserRole.objects.create(name='Salesman')
            self.user.role = role
            self.user.save()
        except Exception, e:
            self.fail(str(e))

        self.failIf(self.user.has_perm('creme_core'))
        self.failIf(self.user.has_perm('foobar'))
        self.failIf(role.allowed_apps)

        role.allowed_apps = ['creme_core', 'foobar']
        role.save()

        role = UserRole.objects.get(pk=role.id) #refresh object
        allowed_apps = role.allowed_apps
        self.assertEqual(2, len(allowed_apps))
        self.assert_('creme_core' in allowed_apps)
        self.assert_('foobar' in allowed_apps)

        self.user.role = role #refresh object
        self.assert_(self.user.has_perm('creme_core'))
        self.assert_(self.user.has_perm('foobar'))
        self.failIf(self.user.has_perm('quux'))

    def test_app_creds02(self):
        try:
            role = UserRole.objects.create(name='CEO')
            self.user.role = role
            self.user.save()
        except Exception, e:
            self.fail(str(e))

        self.failIf(self.user.has_perm('creme_core.can_admin'))
        self.failIf(self.user.has_perm('foobar.can_admin'))
        self.failIf(role.admin_4_apps)

        role.admin_4_apps = ['creme_core', 'foobar']
        role.save()

        role = UserRole.objects.get(pk=role.id) #refresh object
        admin_4_apps = role.admin_4_apps
        self.assertEqual(2, len(admin_4_apps))
        self.assert_('creme_core' in admin_4_apps)
        self.assert_('foobar' in admin_4_apps)

        self.user.role = role #refresh object
        self.assert_(self.user.has_perm('creme_core.can_admin'))
        self.assert_(self.user.has_perm('foobar.can_admin'))
        self.failIf(self.user.has_perm('quux.can_admin'))

        self.assert_(self.user.has_perm('creme_core'))
        self.assert_(self.user.has_perm('foobar'))
        self.failIf(self.user.has_perm('quux'))

    def test_app_creds03(self):
        self.user.is_superuser = True

        self.assert_(self.user.has_perm('creme_core'))
        self.assert_(self.user.has_perm('creme_core.can_admin'))

    def test_delete01(self): #delete role
        role = self._create_role('Coder', ['creme_core'])
        SetCredentials.objects.create(role=role,
                                        value=SetCredentials.CRED_VIEW,
                                        set_type=SetCredentials.ESET_ALL)

        self.user.role = role
        self.user.save()

        self.user.update_credentials()
        self.assert_(self.user.has_perm('creme_core.view_entity',  self.entity1))
        self.assertEqual(2, EntityCredentials.objects.count())

        #we delete the role -> entities should still have the right credentials
        role.delete()
        self.failIf(self.user.has_perm('creme_core.view_entity', self.entity1))
        self.assertEqual(0, EntityCredentials.objects.count())

    def test_delete02(self): #delete entity
        role = UserRole.objects.create(name='Coder')
        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)

        self.user.role = role
        self.user.save()

        self.user.update_credentials()
        self.assertEqual(2, EntityCredentials.objects.count())

        self.entity1.delete()
        self.assertEqual([self.entity2.id], [creds.entity_id for creds in EntityCredentials.objects.all()])

    def test_multisave01(self): #old lines were not cleaned if an Entiy was re-save
        role = UserRole.objects.create(name='Coder')
        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL)

        self.user.role = role
        self.user.save()
        self.other_user.role = role
        self.other_user.save()

        entity3 = CremeEntity.objects.create(user_id=self.user.id)
        self.assertEqual(2, EntityCredentials.objects.count())

        entity3.user = self.other_user
        entity3.save()
        self.assertEqual(2, EntityCredentials.objects.count())

    def test_create_team01(self):
        team = User.objects.create(username='Teamee')

        self.failIf(team.is_team)

        try:
            team.teammates = [self.user]
        except ValueError:
            pass
        else:
            self.fail()

        try:
            teammates = team.teammates
        except ValueError:
            pass
        else:
            self.fail()

    def test_create_team02(self):
        team = User.objects.create(username='Teamee', is_team=True)

        team.teammates = [self.user, self.other_user]
        teammates = team.teammates
        self.assertEqual(2, len(teammates))

        self.assert_(all(isinstance(u, User) for u in teammates.itervalues()))

        ids_set = set([self.user.id, self.other_user.id])
        self.assertEqual(ids_set, set(teammates.iterkeys()))
        self.assertEqual(ids_set, set(u.id for u in teammates.itervalues()))

        user3 = User.objects.create_user('Kanna', 'kanna@century.jp', 'uselesspw')
        team.teammates = [self.user, self.other_user, user3]
        self.assertEqual(3, len(team.teammates))

        team.teammates = [self.other_user]
        self.assertEqual(1, len(team.teammates))

    def _create_team(self, name, teammates):
        team = User.objects.create(username=name, is_team=True, role=None)
        team.teammates = teammates
        return team

    def test_team_credentials(self):
        role = self._create_role('Worker', ['creme_core'])
        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_OWN)

        self.user.role = role
        self.user.save()

        team = self._create_team('Teamee', [self.user])

        entity3 = CremeEntity.objects.create(user=team)
        self.assert_(not entity3.can_view(self.other_user))
        self.assert_(entity3.can_view(self.user)) #belongs to the team

        self.assertEqual(0, EntityCredentials.objects.filter(user=team).count())

    def test_team_credentials_updating01(self):
        role = self._create_role('Worker', ['creme_core'])
        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_OWN)

        self.user.role = role
        self.user.save()

        team    = self._create_team('Teamee', [])
        entity3 = CremeEntity.objects.create(user=team)

        self.assert_(not entity3.can_view(self.user))

        team.teammates = [self.user] #credentials should be updated automatically
        self.assert_(CremeEntity.objects.get(pk=entity3.id).can_view(self.user))

    def test_team_credentials_updating02(self):
        role = self._create_role('Worker', ['creme_core'])
        SetCredentials.objects.create(role=role, value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_OWN)

        self.user.role = role
        self.user.save()

        team    = self._create_team('Teamee', [self.user])
        entity3 = CremeEntity.objects.create(user=team)
        self.assert_(entity3.can_view(self.user))

        team.teammates = [] #ie: remove 'self.user'
        self.assertEqual({}, team.teammates)

        self.assert_(not CremeEntity.objects.get(pk=entity3.id).can_view(self.user))

    def test_ct_credentials(self):
        role = self._create_role('Coder', ['creme_core', 'persons'])
        self.user.role = role
        self.user.save()
        SetCredentials.objects.create(role=role,
                                      value=SetCredentials.CRED_VIEW,
                                      set_type=SetCredentials.ESET_ALL,
                                      ctype=ContentType.objects.get_for_model(Contact),
                                     )

        contact1 = Contact.objects.create(user=self.user, first_name='Musashi', last_name='Miyamoto')
        self.assert_(contact1.can_view(self.user))
        self.failIf(contact1.can_change(self.user))
        self.failIf(contact1.can_delete(self.user))

        contact2 = Contact.objects.create(user=self.other_user, first_name='Kojiro', last_name='Sasaki')
        self.assert_(contact2.can_view(self.user))
        self.failIf(contact2.can_change(self.user))
        self.failIf(contact2.can_delete(self.user))

        orga = Organisation.objects.create(user=self.user, name='Yoshioka')
        self.failIf(orga.can_view(self.user))
        self.failIf(orga.can_change(self.user))
        self.failIf(orga.can_delete(self.user))
