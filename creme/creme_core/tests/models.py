# -*- coding: utf-8 -*-

from datetime import datetime

from django.test import TestCase
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *


class ModelsTestCase(TestCase):
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


class RelationsTestCase(TestCase):
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


class CredentialsTestCase(TestCase):
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

        defcreds = EntityCredentials.get_default_creds()
        self.failIf(defcreds.can_view())
        self.failIf(defcreds.can_change())
        self.failIf(defcreds.can_delete())

        EntityCredentials.set_default_perms(view=True, change=True, delete=True)

        self.assert_(self.user.has_perm('creme_core.view_entity',   self.entity1))
        self.assert_(self.user.has_perm('creme_core.change_entity', self.entity1))
        self.assert_(self.user.has_perm('creme_core.delete_entity', self.entity1))

        defcreds = EntityCredentials.get_default_creds()
        self.assert_(defcreds.can_view())
        self.assert_(defcreds.can_change())
        self.assert_(defcreds.can_delete())

    def test_entity_perms01(self):
        EntityCredentials.set_entity_perms(self.user, self.entity1, view=True, change=True, delete=True)

        self.assert_(self.user.has_perm('creme_core.view_entity',   self.entity1))
        self.assert_(self.user.has_perm('creme_core.change_entity', self.entity1))
        self.assert_(self.user.has_perm('creme_core.delete_entity', self.entity1))

    def test_entity_perms02(self): #super-user
        self.user.is_superuser = True

        self.assert_(self.user.has_perm('creme_core.view_entity',   self.entity1))
        self.assert_(self.user.has_perm('creme_core.change_entity', self.entity1))
        self.assert_(self.user.has_perm('creme_core.delete_entity', self.entity1))

    def build_qs(self):
        return CremeEntity.objects.filter(pk__in=(self.entity1.id, self.entity2.id))

    def ids_list(self, iterable):
        return [e.id for e in iterable]

    def test_filter01(self): #filter with default credentials OK
        EntityCredentials.set_default_perms(view=True, change=True, delete=True)

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

        self.assert_(qs1._result_cache is None)
        self.assertEqual([self.entity2.id], self.ids_list(qs2))

        self.failIf(EntityCredentials.filter(self.other_user, qs1))

    def test_filter04(self): #filter with some credentials set (and default OK)
        EntityCredentials.set_default_perms(view=True, change=True, delete=True)
        EntityCredentials.set_entity_perms(self.user, self.entity2, view=True)

        qs = EntityCredentials.filter(self.user, self.build_qs())
        self.assertEqual([self.entity1.id, self.entity2.id], self.ids_list(qs))

    def test_filter05(self): #filter with some credentials set (and default KO)
        EntityCredentials.set_entity_perms(self.user, self.entity2, view=True)

        qs = EntityCredentials.filter(self.user, self.build_qs())
        self.assertEqual([self.entity2.id], self.ids_list(qs))

    def test_filter05(self): #super-user
        self.user.is_superuser = True

        qs = EntityCredentials.filter(self.user, self.build_qs())
        self.assertEqual([self.entity1.id, self.entity2.id], self.ids_list(qs))

    def test_regularperms01(self): #regular perms not used
        ct = content_type=ContentType.objects.get_for_model(CremeProperty)

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

    def test_helpers04(self): #super-user
        self.user.is_superuser = True

        self.entity1.can_view_or_die(self.user)
        self.entity1.can_change_or_die(self.user)
        self.entity1.can_delete_or_die(self.user)

    #this tests contribute_to_model too
    def test_role_esetall01(self): # CRED_VIEW + ESET_ALL
        try:
            role = UserRole.objects.create(name='Coder')
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

    def test_role_esetall02(self): # CRED_CHANGE + ESET_ALL
        try:
            role = UserRole.objects.create(name='Coder')
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
        try:
            role = UserRole.objects.create(name='Coder')
            self.user.role = role
            self.user.save()
            SetCredentials.objects.create(role=role,
                                          value=SetCredentials.CRED_DELETE,
                                          set_type=SetCredentials.ESET_ALL)
        except Exception, e:
            self.fail(str(e))

        entity3 = CremeEntity.objects.create(user=self.user)
        self.failIf(self.user.has_perm('creme_core.view_entity',    entity3))
        self.failIf(self.user.has_perm('creme_core.change_entity',  entity3))
        self.assert_(self.user.has_perm('creme_core.delete_entity', entity3))

        entity4 = CremeEntity.objects.create(user=self.other_user)
        self.failIf(self.user.has_perm('creme_core.view_entity',    entity4))
        self.failIf(self.user.has_perm('creme_core.change_entity',  entity4))
        self.assert_(self.user.has_perm('creme_core.delete_entity', entity4))

    def test_role_esetown01(self): # CRED_VIEW + ESET_OWN
        try:
            role = UserRole.objects.create(name='Coder')
            self.user.role = role
            self.user.save()
            SetCredentials.objects.create(role=role,
                                          value=SetCredentials.CRED_VIEW,
                                          set_type=SetCredentials.ESET_OWN)
        except Exception, e:
            self.fail(str(e))

        entity3 = CremeEntity.objects.create(user=self.user)
        self.assert_(self.user.has_perm('creme_core.view_entity',  entity3))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity3))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity3))

        entity4 = CremeEntity.objects.create(user=self.other_user)
        self.failIf(self.user.has_perm('creme_core.view_entity',   entity4))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity4))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity4))

    def test_role_esetown02(self): # ESET_OWN + CRED_VIEW/CRED_CHANGE
        try:
            role = UserRole.objects.create(name='Coder')
            self.user.role = role
            self.user.save()
            SetCredentials.objects.create(role=role,
                                          value=SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE,
                                          set_type=SetCredentials.ESET_OWN)
        except Exception, e:
            self.fail(str(e))

        entity3 = CremeEntity.objects.create(user=self.user)
        self.failIf(self.user.has_perm('creme_core.view_entity',    entity3))
        self.assert_(self.user.has_perm('creme_core.change_entity', entity3))
        self.assert_(self.user.has_perm('creme_core.delete_entity', entity3))

        entity4 = CremeEntity.objects.create(user=self.other_user)
        self.failIf(self.user.has_perm('creme_core.view_entity',   entity4))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity4))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity4))

    def test_role_multiset01(self): # ESET_OWN + ESET_ALL
        try:
            role = UserRole.objects.create(name='Coder')
            self.user.role = role
            self.user.save()
            SetCredentials.objects.create(role=role,
                                          value=SetCredentials.CRED_VIEW,
                                          set_type=SetCredentials.ESET_ALL)
            SetCredentials.objects.create(role=role,
                                          value=SetCredentials.CRED_CHANGE | SetCredentials.CRED_DELETE,
                                          set_type=SetCredentials.ESET_OWN)
        except Exception, e:
            self.fail(str(e))

        entity3 = CremeEntity.objects.create(user=self.user)
        self.assert_(self.user.has_perm('creme_core.view_entity',   entity3))
        self.assert_(self.user.has_perm('creme_core.change_entity', entity3))
        self.assert_(self.user.has_perm('creme_core.delete_entity', entity3))

        entity4 = CremeEntity.objects.create(user=self.other_user)
        self.assert_(self.user.has_perm('creme_core.view_entity',  entity4))
        self.failIf(self.user.has_perm('creme_core.change_entity', entity4))
        self.failIf(self.user.has_perm('creme_core.delete_entity', entity4))

    def test_role_updating01(self):
        try:
            role = UserRole.objects.create(name='Coder')
            self.user.role = role
            self.user.save()
            SetCredentials.objects.create(role=role,
                                          value=SetCredentials.CRED_VIEW,
                                          set_type=SetCredentials.ESET_ALL)
        except Exception, e:
            self.fail(str(e))


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
        role1 = UserRole.objects.create(name='View all')
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

        role2 = UserRole.objects.create(name='Isolated worker')
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
        role = UserRole.objects.create(name='Coder')
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
        SetCredentials.objects.create(role=role,
                                        value=SetCredentials.CRED_VIEW,
                                        set_type=SetCredentials.ESET_ALL)

        self.user.role = role
        self.user.save()

        self.user.update_credentials()
        self.assertEqual(2, EntityCredentials.objects.count())

        self.entity1.delete()
        self.assertEqual([self.entity2.id], [creds.entity_id for creds in EntityCredentials.objects.all()])

    def test_multisave01(self): #old lines were not cleaned if an Entiywas re-save
        role = UserRole.objects.create(name='Coder')
        SetCredentials.objects.create(role=role,
                                        value=SetCredentials.CRED_VIEW,
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

    #TODO: don't write cred if equals to default creds ??????
