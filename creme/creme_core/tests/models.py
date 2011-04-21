# -*- coding: utf-8 -*-

from datetime import datetime, date

from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *
from creme_core.tests.base import CremeTestCase

from persons.models import Contact, Organisation


class ModelsTestCase(CremeTestCase):
    def setUp(self):
        self.user = User.objects.create(username='name')

    def test_entity01(self):
        try:
            entity = CremeEntity.objects.create(user=self.user)
        except Exception, e:
            self.fail(str(e))

        now = datetime.now()

        self.assert_((now - entity.created).seconds < 10)
        self.assert_((now - entity.modified).seconds < 10)

    def test_property01(self):
        text = 'TEXT'

        try:
            ptype  = CremePropertyType.create(str_pk='test-prop_foobar', text=text)
            entity = CremeEntity.objects.create(user=self.user)
            prop   = CremeProperty.objects.create(type=ptype, creme_entity=entity)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(text, ptype.text)


class RelationsTestCase(CremeTestCase):
    def setUp(self):
        self.user = User.objects.create(username='name')

    def test_relation01(self):
        subject_pred = 'is loving'
        object_pred  = 'is loved by'

        try:
            rtype1, rtype2 = RelationType.create(('test-subject_foobar', subject_pred),
                                                 ('test-object_foobar',  object_pred))
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(rtype1.symmetric_type.id, rtype2.id)
        self.assertEqual(rtype2.symmetric_type.id, rtype1.id)
        self.assertEqual(rtype1.predicate,         subject_pred)
        self.assertEqual(rtype2.predicate,         object_pred)

        try:
            entity1  = CremeEntity.objects.create(user=self.user)
            entity2  = CremeEntity.objects.create(user=self.user)
            relation = Relation.objects.create(user=self.user, type=rtype1,
                                               subject_entity=entity1, object_entity=entity2)
        except Exception, e:
            self.fail(str(e))

        sym = relation.symmetric_relation
        self.assertEqual(sym.type.id, rtype2.id)
        self.assertEqual(sym.subject_entity.id, entity2.id)
        self.assertEqual(sym.object_entity.id,  entity1.id)

    def test_relation02(self): #BEWARE: bad usage of Relations (see the next test for good usage)
        rtype1, rtype2 = RelationType.create(('test-subject_foobar', 'is loving'),
                                             ('test-object_foobar',  'is loved by'))

        create_entity = CremeEntity.objects.create
        relation = Relation.objects.create(user=self.user, type=rtype1,
                                           subject_entity=create_entity(user=self.user),
                                           object_entity=create_entity(user=self.user))

        #This will not update symmetric relation !!
        relation.subject_entity = create_entity(user=self.user)
        relation.object_entity  = create_entity(user=self.user)

        self.assertNotEqual(relation.subject_entity_id, relation.symmetric_relation.object_entity_id)
        self.assertNotEqual(relation.object_entity_id,  relation.symmetric_relation.subject_entity_id)

    def test_relation03(self):
        rtype1, rtype2 = RelationType.create(('test-subject_foobar', 'is loving'),
                                             ('test-object_foobar',  'is loved by'))

        create_entity = CremeEntity.objects.create
        relation = Relation.objects.create(user=self.user, type=rtype1,
                                           subject_entity=create_entity(user=self.user),
                                           object_entity=create_entity(user=self.user)
                                          )

        entity3 = create_entity(user=self.user)
        entity4 = create_entity(user=self.user)
        relation.update_links(subject_entity=entity3, object_entity=entity4, save=True)

        relation = Relation.objects.get(pk=relation.id) #refresh
        self.assertEqual(entity3.id, relation.subject_entity.id)
        self.assertEqual(entity4.id, relation.object_entity.id)

        sym = relation.symmetric_relation
        self.assertEqual(entity4.id, sym.subject_entity.id)
        self.assertEqual(entity3.id, sym.object_entity.id)


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

        team.teammates = [self.user] #credentials should be updated automaticcaly
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

    #TODO: don't write cred if equals to default creds ??????


class EntityFiltersTestCase(CremeTestCase):
    def setUp(self):
        self.login()

        create = Contact.objects.create
        user = self.user

        self.contacts = [
            create(user=user, first_name=u'Spike',  last_name=u'Spiegel'),   #0
            create(user=user, first_name=u'Jet',    last_name=u'Black'),     #1
            create(user=user, first_name=u'Faye',   last_name=u'Valentine',
                   description=u'Sexiest woman is the universe'),            #2
            create(user=user, first_name=u'Ed',     last_name=u'Wong'),      #3
            create(user=user, first_name=u'Rei',    last_name=u'Ayanami'),   #4
            create(user=user, first_name=u'Misato', last_name=u'Katsuragi',
                  birthday=date(year=1986, month=12, day=8)),                #5
            create(user=user, first_name=u'Asuka',  last_name=u'Langley',
                   birthday=date(year=2001, month=12, day=4)),               #6
            create(user=user, first_name=u'Shinji', last_name=u'Ikari',
                   birthday=date(year=2001, month=6, day=6)),                #7
            create(user=user, first_name=u'Yui',    last_name=u'Ikari'),     #8
            create(user=user, first_name=u'Gendô',  last_name=u'IKARI'),     #9
            create(user=user, first_name=u'Genji',  last_name=u'Ikaru'),     #10 NB: startswith 'Gen'
            create(user=user, first_name=u'Risato', last_name=u'Katsuragu'), #11 NB contains 'isat' like #5
        ]

    def assertExpectedFiltered(self, efilter, model, ids, case_insensitive=False):
        msg = '(NB: maybe you have case sensitive problems with your DB configuration).' if case_insensitive else ''
        filtered = list(efilter.filter(model.objects.all()))
        self.assertEqual(len(ids), len(filtered), str(filtered) + msg)
        self.assertEqual(set(ids), set(c.id for c in filtered))

    def test_filter_field_equals(self):
        self.assertEqual(len(self.contacts), Contact.objects.count())

        efilter = EntityFilter.create('test-filter01', 'Ikari', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.EQUALS,
                                                            name='last_name', value='Ikari'
                                                           )
                               ])
        self.assertEqual(1, efilter.conditions.count())

        efilter =  EntityFilter.objects.get(pk=efilter.id) #refresh
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id, self.contacts[8].id])

    def test_filter_field_iequals(self):
        efilter = EntityFilter.create('test-filter01', 'Ikari (insensitive)', Contact,
                                      user=self.user, is_custom=False
                                     )
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.IEQUALS,
                                                            name='last_name', value='Ikari'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[i].id for i in (7, 8, 9)], True)

    def test_filter_field_not_equals(self):
        efilter = EntityFilter.create('test-filter01', 'Not Ikari', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact, type=EntityFilterCondition.EQUALS_NOT,
                                                            name='last_name', value='Ikari'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (7, 8)])

    def test_filter_field_not_iequals(self):
        pk = 'test-filter01'
        name = 'Not Ikari (case insensitive)'
        efilter = EntityFilter.create(pk, name, Contact)
        ct = ContentType.objects.get_for_model(Contact)

        efilters = EntityFilter.objects.filter(pk='test-filter01', name=name)
        self.assertEqual(1,          len(efilters))
        self.assertEqual(ct.id,      efilters[0].entity_type.id)
        self.assertEqual(efilter.id, efilters[0].id)

        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.IEQUALS_NOT,
                                                            name='last_name', value='Ikari'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (7, 8, 9)])

    def test_filter_field_contains(self):
        efilter = EntityFilter.create('test-filter01', name='Contains "isat"', model=Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.CONTAINS,
                                                            name='first_name', value='isat'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id, self.contacts[11].id])

    def test_filter_field_icontains(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Not contains "Misa"', model=Contact, user=self.user)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.ICONTAINS,
                                                            name='first_name', value='misa'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id], True)

    def test_filter_field_contains_not(self):
        efilter = EntityFilter.create('test-filter01', 'Not Ikari', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.CONTAINS_NOT,
                                                            name='first_name', value='sato'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (5, 11)])

    def test_filter_field_icontains_not(self):
        efilter = EntityFilter.create('test-filter01', 'Not contains "sato" (ci)', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.ICONTAINS_NOT,
                                                            name='first_name', value='sato'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (5, 11)], True)

    def test_filter_field_gt01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='> Yua', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.GT,
                                                            name='first_name', value='Yua'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[8].id])

    def test_filter_field_gt02(self): #date
        efilter = EntityFilter.create('test-filter01', '> Yua', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.GT,
                                                            name='birthday', value='2000-1-1'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[6].id, self.contacts[7].id])

    def test_filter_field_gte(self):
        efilter = EntityFilter.create('test-filter01', '>= Spike', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.GTE,
                                                            name='first_name', value='Spike'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id, self.contacts[8].id])

    def test_filter_field_lt(self):
        efilter = EntityFilter.create('test-filter01', '< Faye', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.LT,
                                                            name='first_name', value='Faye'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[3].id, self.contacts[6].id])

    def test_filter_field_lte(self):
        efilter = EntityFilter.create('test-filter01', '<= Faye', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.LTE,
                                                            name='first_name', value='Faye'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[i].id for i in (2, 3, 6)])

    def test_filter_field_startswith(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts "Gen"', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.STARTSWITH,
                                                            name='first_name', value='Gen'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[9].id, self.contacts[10].id])

    def test_filter_field_istartswith(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts "Gen" (ci)', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.ISTARTSWITH,
                                                            name='first_name', value='gen'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[9].id, self.contacts[10].id])

    def test_filter_field_startswith_not(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts not "Asu"', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.STARTSWITH_NOT,
                                                            name='first_name', value='Asu'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 6])

    def test_filter_field_istartswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'starts not "asu"', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.ISTARTSWITH_NOT,
                                                            name='first_name', value='asu'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 6])

    def test_filter_field_endswith(self):
        efilter = EntityFilter.create('test-filter01', 'ends "sato"', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.ENDSWITH,
                                                            name='first_name', value='sato'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id, self.contacts[11].id])

    def test_filter_field_iendswith(self):
        efilter = EntityFilter.create('test-filter01', 'ends "SATO"', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.IENDSWITH,
                                                            name='first_name', value='SATO'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id, self.contacts[11].id])

    def test_filter_field_endswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'ends not "sato"', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.ENDSWITH_NOT,
                                                            name='first_name', value='sato'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (5, 11)])

    def test_filter_field_iendswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'ends not "SATO" (ci)', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.IENDSWITH_NOT,
                                                            name='first_name', value='SATO'
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (5, 11)])

    def test_filter_field_isnull(self):
        efilter = EntityFilter.create(pk='test-filter01', name='is null', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                           type=EntityFilterCondition.ISNULL,
                                           name='description', value=True
                                          )
                               ])
        self.assertEqual(1, efilter.conditions.count())

        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 2])

    def test_filter_field_isnull_not(self):
        efilter = EntityFilter.create('test-filter01', 'is not null', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.ISNULL_NOT,
                                                            name='description', value=True
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[2].id])

    def test_filter_field_range01(self):
        create = Organisation.objects.create
        user = self.user
        orga01 = create(user=user, name='Bebop & cie', capital=1000)
        orga02 = create(user=user, name='Nerv',        capital=10000)
        orga03 = create(user=user, name='Seele',       capital=100000)

        efilter = EntityFilter.create('test-filter01', name='is not null', model=Organisation)
        cond = EntityFilterCondition.build(model=Organisation,
                                           type=EntityFilterCondition.RANGE,
                                           name='capital', value=(5000, 500000)
                                          )
        efilter.set_conditions([cond])
        self.assertExpectedFiltered(efilter, Organisation, [orga02.id, orga03.id])

    def test_filter_field_range02(self): #date
        efilter = EntityFilter.create('test-filter01', name='is not null', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.RANGE,
                                                            name='birthday', value=('2001-1-1', '2001-12-1')
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id])

    def test_build_condition(self): #errors
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build,
                          model=Contact, type=EntityFilterCondition.CONTAINS, name='unknown_field', value='Misato',
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build,
                          model=Organisation, type=EntityFilterCondition.GT, name='capital', value='Not an integer'
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build,
                          model=Contact, type=EntityFilterCondition.ISNULL, name='description', value='Not a boolean', #ISNULL => boolean
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build,
                          model=Contact, type=EntityFilterCondition.ISNULL_NOT, name='description', value='Not a boolean', #ISNULL_NOT => boolean
                         )

    def test_condition_update(self):
        build_cond = EntityFilterCondition.build
        cond1 = build_cond(model=Contact,      type=EntityFilterCondition.EQUALS,  name='first_name', value='Jet')
        self.failIf(build_cond(model=Contact,  type=EntityFilterCondition.EQUALS,  name='first_name', value='Jet').update(cond1))
        self.assert_(build_cond(model=Contact, type=EntityFilterCondition.IEQUALS, name='first_name', value='Jet').update(cond1))
        self.assert_(build_cond(model=Contact, type=EntityFilterCondition.EQUALS,  name='last_name',  value='Jet').update(cond1))
        self.assert_(build_cond(model=Contact, type=EntityFilterCondition.EQUALS,  name='first_name', value='Ed').update(cond1))
        self.assert_(build_cond(model=Contact, type=EntityFilterCondition.IEQUALS, name='last_name', value='Jet').update(cond1))
        self.assert_(build_cond(model=Contact, type=EntityFilterCondition.IEQUALS, name='last_name', value='Ed').update(cond1))

    def test_set_conditions01(self):
        efilter = EntityFilter.create('test-filter01', 'Jet', Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.EQUALS,
                                                            name='first_name', value='Jet'
                                                           )
                               ])

        #NB: create an other condition that has he last id (so if we delete the
        #    first condition, and recreate another one, the id will be different)
        EntityFilter.create('test-filter02', 'Faye', Contact) \
                    .set_conditions([EntityFilterCondition.build(model=Contact, type=EntityFilterCondition.EQUALS, name='first_name', value='Faye')])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))
        old_id = conditions[0].id

        type = EntityFilterCondition.CONTAINS
        name = 'last_name'
        value = 'Black'
        efilter.set_conditions([EntityFilterCondition.build(model=Contact, type=type, name=name, value=value)])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(type,           condition.type)
        self.assertEqual(name,           condition.name)
        self.assertEqual('"%s"' % value, condition.value)
        self.assertEqual(old_id,         condition.id)

    def test_set_conditions02(self):
        efilter = EntityFilter.create('test-filter01', 'Jet', Contact)

        kwargs1 = {
                'model': Contact,
                'type':  EntityFilterCondition.EQUALS,
                'name':  'first_name',
                'value': 'Jet',
            }
        kwargs2 = dict(kwargs1)
        kwargs2['type'] = EntityFilterCondition.IEQUALS

        build_cond = EntityFilterCondition.build
        efilter.set_conditions([build_cond(**kwargs1), build_cond(**kwargs2)])

        #NB: see test_set_conditions01()
        EntityFilter.create('test-filter02', 'Faye', Contact) \
                    .set_conditions([EntityFilterCondition.build(model=Contact, type=EntityFilterCondition.EQUALS, name='first_name', value='Faye')])

        conditions = efilter.conditions.all()
        self.assertEqual(2, len(conditions))

        for kwargs, condition in zip([kwargs1, kwargs2], conditions):
            self.assertEqual(kwargs['type'],           condition.type)
            self.assertEqual(kwargs['name'],           condition.name)
            self.assertEqual('"%s"' % kwargs['value'], condition.value)

        old_id = conditions[0].id

        kwargs1['type'] = EntityFilterCondition.GT
        efilter.set_conditions([build_cond(**kwargs1)])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(kwargs1['type'],           condition.type)
        self.assertEqual(kwargs1['name'],           condition.name)
        self.assertEqual('"%s"' % kwargs1['value'], condition.value)
        self.assertEqual(old_id,                    condition.id)

    def test_multi_conditions_and01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        build_cond = EntityFilterCondition.build
        efilter.set_conditions([build_cond(model=Contact,
                                          type=EntityFilterCondition.EQUALS,
                                          name='last_name', value='Ikari'
                                         ),
                                build_cond(model=Contact,
                                          type=EntityFilterCondition.STARTSWITH,
                                          name='first_name', value='Shin'
                                         )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id])

    def test_multi_conditions_or01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, use_or=True)
        build_cond = EntityFilterCondition.build
        efilter.set_conditions([build_cond(model=Contact,
                                          type=EntityFilterCondition.EQUALS,
                                          name='last_name', value='Spiegel'
                                         ),
                                build_cond(model=Contact,
                                          type=EntityFilterCondition.STARTSWITH,
                                          name='first_name', value='Shin'
                                         )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id, self.contacts[7].id])

    def test_subfilter01(self):
        build_cond = EntityFilterCondition.build
        sub_efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, use_or=True)
        sub_efilter.set_conditions([build_cond(model=Contact, type=EntityFilterCondition.EQUALS,     name='last_name',  value='Spiegel'),
                                    build_cond(model=Contact, type=EntityFilterCondition.STARTSWITH, name='first_name', value='Shin')
                                   ])
        efilter = EntityFilter.create(pk='test-filter02', name='Filter02', model=Contact, use_or=False)
        conds = [build_cond(model=Contact, type=EntityFilterCondition.STARTSWITH, name='first_name', value='Spi'),
                 build_cond(model=Contact, type=EntityFilterCondition.SUBFILTER,  value=sub_efilter),
                ]
        try:
            efilter.check_cycle(conds)
        except Exception, e:
            self.fail(str(e))

        efilter.set_conditions(conds)
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id])

        #Test that a CycleError is not raised
        sub_sub_efilter = EntityFilter.create(pk='test-filter03', name='Filter03', model=Contact)
        sub_sub_efilter.set_conditions([build_cond(model=Contact, type=EntityFilterCondition.EQUALS,     name='last_name',  value='Black'),
                                        build_cond(model=Contact, type=EntityFilterCondition.STARTSWITH, name='first_name', value='Jet')
                                       ])

        conds = [build_cond(model=Contact, type=EntityFilterCondition.STARTSWITH, name='first_name', value='Spi'),
                 build_cond(model=Contact, type=EntityFilterCondition.SUBFILTER,  value=sub_sub_efilter),
                ]
        try:
            sub_efilter.check_cycle(conds)
        except Exception, e:
            self.fail(str(e))

    def test_subfilter02(self): #cycle error (lenght = 0)
        efilter = EntityFilter.create(pk='test-filter02', name='Filter01', model=Contact, use_or=False)
        build_cond = EntityFilterCondition.build
        conds = [build_cond(model=Contact,
                            type=EntityFilterCondition.STARTSWITH,
                            name='first_name', value='Spi'
                           ),
                 build_cond(model=Contact,
                            type=EntityFilterCondition.SUBFILTER,
                            value=efilter
                           ),
                ]
        self.assertRaises(EntityFilter.CycleError, efilter.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter.set_conditions, conds)

    def test_subfilter03(self): #cycle error (lenght = 1)
        build_cond = EntityFilterCondition.build

        efilter01 = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, use_or=True)
        efilter01.set_conditions([build_cond(model=Contact, type=EntityFilterCondition.EQUALS, name='last_name', value='Spiegel')])

        efilter02 = EntityFilter.create(pk='test-filter02', name='Filter02', model=Contact, use_or=False)
        self.assertEqual(set([efilter02.id]), efilter02.get_connected_filter_ids())

        efilter02.set_conditions([build_cond(model=Contact, type=EntityFilterCondition.STARTSWITH, value='Spi', name='first_name'),
                                  build_cond(model=Contact, type=EntityFilterCondition.SUBFILTER,  value=efilter01),
                                 ])

        conds = [build_cond(model=Contact, type=EntityFilterCondition.CONTAINS,   value='Faye', name='first_name'),
                 build_cond(model=Contact, type=EntityFilterCondition.SUBFILTER,  value=efilter02),
                ]
        self.assertEqual(set([efilter01.id, efilter02.id]), efilter01.get_connected_filter_ids())
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_subfilter04(self): #cycle error (lenght = 2)
        build_cond = EntityFilterCondition.build

        efilter01 = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, use_or=True)
        efilter01.set_conditions([build_cond(model=Contact, type=EntityFilterCondition.EQUALS, name='last_name', value='Spiegel')])

        efilter02 = EntityFilter.create(pk='test-filter02', name='Filter02', model=Contact, use_or=False)
        efilter02.set_conditions([build_cond(model=Contact, type=EntityFilterCondition.STARTSWITH, value='Spi', name='first_name'),
                                  build_cond(model=Contact, type=EntityFilterCondition.SUBFILTER,  value=efilter01),
                                 ])

        efilter03 = EntityFilter.create(pk='test-filter03', name='Filter03', model=Contact, use_or=False)
        efilter03.set_conditions([build_cond(model=Contact, type=EntityFilterCondition.ISTARTSWITH, value='Misa', name='first_name'),
                                  build_cond(model=Contact, type=EntityFilterCondition.SUBFILTER,  value=efilter02),
                                 ])

        conds = [build_cond(model=Contact, type=EntityFilterCondition.EQUALS, name='last_name', value='Spiegel'),
                 build_cond(model=Contact, type=EntityFilterCondition.SUBFILTER,  value=efilter03),
                ]
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_properties01(self):
        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text=u'Kawaii')
        cute_ones = (2, 4, 5, 6)

        for girl_id in cute_ones:
            CremeProperty.objects.create(type=ptype, creme_entity=self.contacts[girl_id])

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.PROPERTY,
                                                            name=ptype.id,
                                                            value=True #entities that has got a property with this type
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[i].id for i in cute_ones])

        efilter.set_conditions([EntityFilterCondition.build(model=Contact,
                                                            type=EntityFilterCondition.PROPERTY,
                                                            name=ptype.id,
                                                            value=False #entities that does not have a property with this type
                                                           )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in cute_ones])

    def _aux_test_relations(self):
        loves, loved = RelationType.create(('test-subject_love', u'Is loving'),
                                           ('test-object_love',  u'Is loved by')
                                          )

        bebop = Organisation.objects.create(user=self.user, name='Bebop')

        c = self.contacts
        create = Relation.objects.create
        create(subject_entity=c[2], type=loves, object_entity=c[0],  user=self.user)
        create(subject_entity=c[7], type=loves, object_entity=c[4],  user=self.user)
        create(subject_entity=c[9], type=loves, object_entity=c[4],  user=self.user)
        create(subject_entity=c[1], type=loves, object_entity=bebop, user=self.user)

        return loves

    def test_relations01(self): #no ct/entity
        loves = self._aux_test_relations()
        in_love = [self.contacts[2].id, self.contacts[7].id, self.contacts[9].id, self.contacts[1].id]

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(model=Contact, rtype=loves, has=True)])
        self.assertExpectedFiltered(efilter, Contact, in_love)

        efilter.set_conditions([EntityFilterCondition.build_4_relation(model=Contact, rtype=loves, has=False)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for c in self.contacts if c.id not in in_love])

    def test_relations02(self): #wanted ct
        loves = self._aux_test_relations()
        ct = ContentType.objects.get_for_model(Contact)
        in_love = [self.contacts[2].id, self.contacts[7].id, self.contacts[9].id] # not 'jet' ('bebop' not is a Contact)

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(model=Contact, rtype=loves, has=True, ct=ct)])
        self.assertExpectedFiltered(efilter, Contact, in_love)

        efilter.set_conditions([EntityFilterCondition.build_4_relation(model=Contact, rtype=loves, has=False, ct=ct)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for c in self.contacts if c.id not in in_love])

    def test_relations03(self): #wanted entity
        loves = self._aux_test_relations()
        in_love = [self.contacts[7].id, self.contacts[9].id]
        rei = self.contacts[4]

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(model=Contact, rtype=loves, has=True, entity=rei)])
        self.assertExpectedFiltered(efilter, Contact, in_love)

        efilter.set_conditions([EntityFilterCondition.build_4_relation(model=Contact, rtype=loves, has=False, entity=rei)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for c in self.contacts if c.id not in in_love])

        #TODO: multivalue
        #TODO: field in fk, M2M

        #TODO:
        #DATE_RANGE_FILTER_VOLATILE, name=_(u"Date range"),        pattern_key='%s__range', pattern_value='(%s,%s)', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        #FROM_FILTER_RESULTS, name=_(u"From results of a filter"), pattern_key='%s__in',    pattern_value='%s',      is_exclude=False, type_champ="CharField", value_field_type='textfield')
