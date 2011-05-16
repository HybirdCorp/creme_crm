# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from decimal import Decimal
from tempfile import NamedTemporaryFile

from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *
from creme_core.tests.base import CremeTestCase

from persons.models import *
from media_managers.models import Image, MediaCategory
from activities.models.activity import *


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

    def _setUpClone(self):
        self.rtype1, self.rtype2 = RelationType.create(('test-subject_foobar', 'is loving'),
                                                       ('test-object_foobar',  'is loved by'))

        self.ptype01 = CremePropertyType.create(str_pk='test-prop_foobar01', text='wears strange hats')
        self.ptype02 = CremePropertyType.create(str_pk='test-prop_foobar02', text='wears strange pants')

    def _test_same_relations_n_properties(self, entity1, entity2):
        self._test_same_properties(entity1, entity2)
        self._test_same_relations(entity1, entity2)

    def _test_same_relations(self, entity1, entity2):
        self.assertEqual(set(r.type_id for r in entity1.relations.all()),          set(r.type_id for r in entity2.relations.all()))
        self.assertEqual(set(r.object_entity.id for r in entity1.relations.all()), set(r.object_entity.id for r in entity2.relations.all()))

    def _test_same_properties(self, entity1, entity2):
        self.assertEqual(set(p.type_id for p in entity1.properties.all()), set(p.type_id for p in entity2.properties.all()))

    def test_clone01(self):
        self._setUpClone()

        created  = modified = datetime.now()
        entity1  = CremeEntity.objects.create(user=self.user)

        original_ce = CremeEntity.objects.create(created=created, modified=modified, is_deleted=False, is_actived=True, user=self.user)

        relation = Relation.objects.create(user=self.user, type=self.rtype1,
                                           subject_entity=original_ce, object_entity=entity1)

        property = CremeProperty.objects.create(type=self.ptype01, creme_entity=original_ce)

        clone_ce    = original_ce.clone()

        self.assertTrue(clone_ce.pk is not None)
        self.assertNotEqual(original_ce.pk, clone_ce.pk)

        self.assertNotEqual(original_ce.created,  clone_ce.created)
        self.assertNotEqual(original_ce.modified, clone_ce.modified)

        self.assertEqual(original_ce.is_deleted,  clone_ce.is_deleted)
        self.assertEqual(original_ce.is_actived,  clone_ce.is_actived)
        self.assertEqual(original_ce.entity_type, clone_ce.entity_type)
        self.assertEqual(original_ce.user,        clone_ce.user)
        self.assertEqual(original_ce.header_filter_search_field, clone_ce.header_filter_search_field)

        self._test_same_relations_n_properties(original_ce, clone_ce)

    def test_clone02(self):
        self._setUpClone()

        self.populate('creme_core', 'persons')
        civility = Civility.objects.all()[0]
        position = Position.objects.all()[0]
        sector   = Sector.objects.all()[0]
        language = Language.objects.all()[0]
        ct_contact = ContentType.objects.get_for_model(Contact)
        sasuke  = CremeEntity.objects.create(user=self.user)
        sakura  = CremeEntity.objects.create(user=self.user)

        tmpfile = NamedTemporaryFile()
        tmpfile.width = tmpfile.height = 0
        tmpfile._committed = True
        tmpfile.path = 'upload/file.jpg'
        image = Image.objects.create(user=self.user, image=tmpfile)

        naruto = Contact.objects.create(civility=civility, first_name=u'Naruto', last_name=u'Uzumaki',
                                        description=u"Ninja", skype=u"naruto.uzu", landline=u"+81 0 0 0 00 00",
                                        mobile=u"+81 0 0 0 00 01", fax=u"+81 0 0 0 00 02", position=position,
                                        sector=sector, email=u"naruto.uzumaki@konoha.jp",
                                        is_user=self.user, birthday=datetime.now(), image=image, user=self.user)

        naruto.language = [language]
        naruto.save()

        naruto.billing_address = Address.objects.create(name=u"Naruto's", address=u"Home", po_box=u"000",
                                                        city=u"Konoha", state=u"Konoha", zipcode=u"111",
                                                        country=u"The land of fire", department=u"Ninjas homes",
                                                        content_type=ct_contact, object_id=naruto.id)

        naruto.shipping_address = Address.objects.create(name=u"Naruto's", address=u"Home", po_box=u"000",
                                                        city=u"Konoha", state=u"Konoha", zipcode=u"111",
                                                        country=u"The land of fire", department=u"Ninjas homes",
                                                        content_type=ct_contact, object_id=naruto.id)

        for i in xrange(5):
            Address.objects.create(name=u"Naruto's", address=u"Home", po_box=u"000",
                                                        city=u"Konoha", state=u"Konoha", zipcode=u"111",
                                                        country=u"The land of fire", department=u"Ninjas homes",
                                                        content_type=ct_contact, object_id=naruto.id)

        property  = CremeProperty.objects.create(type=self.ptype01, creme_entity=naruto)
        property2 = CremeProperty.objects.create(type=self.ptype02, creme_entity=naruto)

        relation  = Relation.objects.create(user=self.user, type=self.rtype1,
                                           subject_entity=naruto, object_entity=sasuke)
        relation2 = Relation.objects.create(user=self.user, type=self.rtype2,
                                           subject_entity=naruto, object_entity=sakura)

        kage_bunshin = naruto.clone()

        self.assertNotEqual(kage_bunshin.pk, naruto.pk)

        self._test_same_relations_n_properties(naruto, kage_bunshin)

        attrs_to_check = ['civility', 'first_name', 'last_name', 'description', 'skype', 'landline', 'mobile',
                          'fax', 'position', 'sector', 'email', 'birthday', 'image']

        for attr in attrs_to_check:
            self.assertEqual(getattr(naruto, attr), getattr(kage_bunshin, attr))

        self.assertTrue(kage_bunshin.is_user is None)
        self.assertNotEqual(naruto.is_user, kage_bunshin.is_user)
        self.assertNotEqual(naruto.billing_address.object_id,  kage_bunshin.billing_address.object_id)
        self.assertNotEqual(naruto.shipping_address.object_id, kage_bunshin.shipping_address.object_id)

        self.assertEqual(Address.objects.filter(object_id=naruto.id).count(), Address.objects.filter(object_id=kage_bunshin.id).count())
        

    def test_clone03(self):
        orga_ct       = ContentType.objects.get_for_model(Organisation)
        cf_int        = CustomField.objects.create(name='int',        content_type=orga_ct, field_type=CustomField.INT)
        cf_float      = CustomField.objects.create(name='float',      content_type=orga_ct, field_type=CustomField.FLOAT)
        cf_bool       = CustomField.objects.create(name='bool',       content_type=orga_ct, field_type=CustomField.BOOL)
        cf_str        = CustomField.objects.create(name='str',        content_type=orga_ct, field_type=CustomField.STR)
        cf_date       = CustomField.objects.create(name='date',       content_type=orga_ct, field_type=CustomField.DATE)
        cf_enum       = CustomField.objects.create(name='enum',       content_type=orga_ct, field_type=CustomField.ENUM)
        cf_multi_enum = CustomField.objects.create(name='multi_enum', content_type=orga_ct, field_type=CustomField.MULTI_ENUM)

        enum1 = CustomFieldEnumValue.objects.create(custom_field= cf_enum, value=u"Enum1")

        m_enum1 = CustomFieldEnumValue.objects.create(custom_field= cf_multi_enum, value=u"MEnum1")
        m_enum2 = CustomFieldEnumValue.objects.create(custom_field= cf_multi_enum, value=u"MEnum2")

        orga = Organisation.objects.create(name=u"Konoha", user=self.user)

        CustomFieldInteger.objects.create(custom_field=cf_int, entity=orga, value=50)
#        CustomFieldValue.save_values_for_entities(cf_int, [orga], 50)
        CustomFieldFloat.objects.create(custom_field=cf_float, entity=orga, value=Decimal("10.5"))
        CustomFieldBoolean.objects.create(custom_field=cf_bool, entity=orga, value=True)
        CustomFieldString.objects.create(custom_field=cf_str, entity=orga, value="kunai")
        CustomFieldDateTime.objects.create(custom_field=cf_date, entity=orga, value=datetime.now())
        CustomFieldEnum.objects.create(custom_field=cf_enum, entity=orga, value=enum1)
        CustomFieldMultiEnum(custom_field=cf_multi_enum, entity=orga).set_value_n_save([m_enum1, m_enum2])


        clone = orga.clone()

        def get_cf_values(cf, entity):
            return cf.get_value_class().objects.get(custom_field=cf, entity=entity)

        self.assertEqual(get_cf_values(cf_int, orga).value, get_cf_values(cf_int, clone).value)
        self.assertEqual(get_cf_values(cf_float, orga).value, get_cf_values(cf_float, clone).value)
        self.assertEqual(get_cf_values(cf_bool, orga).value, get_cf_values(cf_bool, clone).value)
        self.assertEqual(get_cf_values(cf_str, orga).value, get_cf_values(cf_str, clone).value)
        self.assertEqual(get_cf_values(cf_date, orga).value, get_cf_values(cf_date, clone).value)

        self.assertEqual(get_cf_values(cf_enum, orga).value, get_cf_values(cf_enum, clone).value)
        
        self.assert_(get_cf_values(cf_multi_enum, orga).value.all())
        self.assertEqual(set(get_cf_values(cf_multi_enum, orga).value.values_list('pk', flat=True)),
                         set(get_cf_values(cf_multi_enum, clone).value.values_list('pk', flat=True)))


    def test_clone04(self):
        self._setUpClone()
        self.populate('creme_core', 'activities')

        ct_activity = ContentType.objects.get_for_model(Activity)

        act_type = ActivityType.objects.all()[0]

        activity1 = Activity.objects.create(user=self.user, type=act_type)

        activity2 = activity1.clone()

        self.assertNotEqual(activity1.pk, activity2.pk)

        attrs_to_check = ['user', 'title', 'start', 'end', 'description', 'minutes', 'type', 'is_all_day', 'status', 'busy']

        for attr in attrs_to_check:
            self.assertEqual(getattr(activity1, attr), getattr(activity2, attr))

    def test_clone05(self):
        self.populate('creme_core', 'activities')

        ct_activity = ContentType.objects.get_for_model(Activity)

        act_type = ActivityType.objects.all()[0]
        act_status = Status.objects.all()[0]#Import status as ActivityStatus ?
        rtype_participant = RelationType.objects.get(pk=REL_SUB_PART_2_ACTIVITY)

        activity1 = Meeting.objects.create(user=self.user, type=act_type, title=u"Meeting", start=datetime.now(),
                                           end=datetime.now(), description=u"Desc", minutes=u"123", is_all_day=False,
                                           status=act_status, busy=True, place=u"Here")

        contact1 = Contact.objects.create(user=self.user)
        contact2 = contact1.clone()

        relation   = Relation.objects.create(user=self.user, type=rtype_participant, subject_entity=contact1, object_entity=activity1)
        relation2  = Relation.objects.create(user=self.user, type=rtype_participant, subject_entity=contact2, object_entity=activity1)

        activity2 = activity1.clone().clone().clone().clone().clone().clone().clone()

        self.assertNotEqual(activity1.pk, activity2.pk)

        attrs_to_check = ['user', 'title', 'start', 'end', 'description', 'minutes', 'type', 'is_all_day', 'status', 'place']

        for attr in attrs_to_check:
            self.assertEqual(getattr(activity1, attr), getattr(activity2, attr))

        self.assertNotEqual(activity1.busy, activity2.busy)

        self._test_same_relations_n_properties(activity1, activity2)

    def test_clone06(self):
        self.populate('creme_core', 'media_managers')
        tmpfile = NamedTemporaryFile()
        tmpfile.width = tmpfile.height = 0
        tmpfile._committed = True
        tmpfile.path = 'upload/file.jpg'
        image = Image.objects.create(user=self.user, image=tmpfile, name=u'file', description=u"Desc")
        image.categories=MediaCategory.objects.all()
        image.save()

        image2 = image.clone()

        self.assertNotEqual(image.pk, image2.pk)

        attrs_to_check = ['user', 'name', 'image', 'description']

        for attr in attrs_to_check:
            self.assertEqual(getattr(image, attr), getattr(image2, attr))

        self.assertEqual(set(image.categories.values_list('pk', flat=True)), set(image2.categories.values_list('pk', flat=True)))


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
