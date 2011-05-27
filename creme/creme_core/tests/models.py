# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, date
from decimal import Decimal
from tempfile import NamedTemporaryFile

from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType

from creme_core.models import *
from creme_core.models.header_filter import *
from creme_core.tests.base import CremeTestCase

from persons.models import Contact, Organisation, Civility, Position, Sector, Address

from media_managers.models import Image, MediaCategory

from activities.models.activity import Activity, ActivityType, Status, Meeting
from activities.constants import REL_SUB_PART_2_ACTIVITY


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
        self.assertEqual(set(r.type_id for r in entity1.relations.all()),
                         set(r.type_id for r in entity2.relations.all())
                        )
        self.assertEqual(set(r.object_entity.id for r in entity1.relations.all()),
                         set(r.object_entity.id for r in entity2.relations.all())
                        )

    def _test_same_properties(self, entity1, entity2):
        self.assertEqual(set(p.type_id for p in entity1.properties.all()),
                         set(p.type_id for p in entity2.properties.all())
                        )

    def test_clone01(self):
        self._setUpClone()

        created = modified = datetime.now()
        entity1 = CremeEntity.objects.create(user=self.user)
        original_ce = CremeEntity.objects.create(created=created, modified=modified, is_deleted=False, is_actived=True, user=self.user)

        Relation.objects.create(user=self.user, type=self.rtype1, subject_entity=original_ce, object_entity=entity1)
        CremeProperty.objects.create(type=self.ptype01, creme_entity=original_ce)

        clone_ce = original_ce.clone()
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
                                        description=u"Ninja", skype=u"naruto.uzu", phone=u"+81 0 0 0 00 00",
                                        mobile=u"+81 0 0 0 00 01", fax=u"+81 0 0 0 00 02", position=position,
                                        sector=sector, email=u"naruto.uzumaki@konoha.jp",
                                        is_user=self.user, birthday=datetime.now(), image=image, user=self.user
                                       )
        naruto.language = [language]

        naruto.billing_address = Address.objects.create(name=u"Naruto's", address=u"Home", po_box=u"000",
                                                        city=u"Konoha", state=u"Konoha", zipcode=u"111",
                                                        country=u"The land of fire", department=u"Ninjas homes",
                                                        content_type=ct_contact, object_id=naruto.id
                                                       )

        naruto.shipping_address = Address.objects.create(name=u"Naruto's", address=u"Home", po_box=u"000",
                                                         city=u"Konoha", state=u"Konoha", zipcode=u"111",
                                                         country=u"The land of fire", department=u"Ninjas homes",
                                                         content_type=ct_contact, object_id=naruto.id
                                                        )
        naruto.save()

        for i in xrange(5):
            Address.objects.create(name=u"Naruto's", address=u"Home", po_box=u"000",
                                   city=u"Konoha", state=u"Konoha", zipcode=u"111",
                                   country=u"The land of fire", department=u"Ninjas homes",
                                   content_type=ct_contact, object_id=naruto.id
                                  )

        CremeProperty.objects.create(type=self.ptype01, creme_entity=naruto)
        CremeProperty.objects.create(type=self.ptype02, creme_entity=naruto)

        Relation.objects.create(user=self.user, type=self.rtype1, subject_entity=naruto, object_entity=sasuke)
        Relation.objects.create(user=self.user, type=self.rtype2, subject_entity=naruto, object_entity=sakura)

        kage_bunshin = naruto.clone()
        self.assertNotEqual(kage_bunshin.pk, naruto.pk)
        self._test_same_relations_n_properties(naruto, kage_bunshin)

        for attr in ['civility', 'first_name', 'last_name', 'description', 'skype', 'phone',
                     'mobile', 'fax', 'position', 'sector', 'email', 'birthday', 'image']:
            self.assertEqual(getattr(naruto, attr), getattr(kage_bunshin, attr))

        self.assertTrue(kage_bunshin.is_user is None)
        self.assertNotEqual(naruto.is_user, kage_bunshin.is_user)
        self.assertNotEqual(naruto.billing_address.object_id,  kage_bunshin.billing_address.object_id)
        self.assertNotEqual(naruto.shipping_address.object_id, kage_bunshin.shipping_address.object_id)

        self.assertEqual(Address.objects.filter(object_id=naruto.id).count(),
                         Address.objects.filter(object_id=kage_bunshin.id).count()
                        )

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

        self.assertEqual(get_cf_values(cf_int,   orga).value, get_cf_values(cf_int,   clone).value)
        self.assertEqual(get_cf_values(cf_float, orga).value, get_cf_values(cf_float, clone).value)
        self.assertEqual(get_cf_values(cf_bool,  orga).value, get_cf_values(cf_bool,  clone).value)
        self.assertEqual(get_cf_values(cf_str,   orga).value, get_cf_values(cf_str,   clone).value)
        self.assertEqual(get_cf_values(cf_date,  orga).value, get_cf_values(cf_date,  clone).value)

        self.assertEqual(get_cf_values(cf_enum, orga).value, get_cf_values(cf_enum, clone).value)

        self.assert_(get_cf_values(cf_multi_enum, orga).value.all())
        self.assertEqual(set(get_cf_values(cf_multi_enum, orga).value.values_list('pk', flat=True)),
                         set(get_cf_values(cf_multi_enum, clone).value.values_list('pk', flat=True))
                        )

    def test_clone04(self):
        self._setUpClone()
        self.populate('creme_core', 'activities')

        ct_activity = ContentType.objects.get_for_model(Activity)
        act_type = ActivityType.objects.all()[0]
        activity1 = Activity.objects.create(user=self.user, type=act_type)
        activity2 = activity1.clone()
        self.assertNotEqual(activity1.pk, activity2.pk)

        for attr in ['user', 'title', 'start', 'end', 'description', 'minutes', 'type', 'is_all_day', 'status', 'busy']:
            self.assertEqual(getattr(activity1, attr), getattr(activity2, attr))

    def test_clone05(self):
        self.populate('creme_core', 'activities')

        ct_activity = ContentType.objects.get_for_model(Activity)

        act_type = ActivityType.objects.all()[0]
        act_status = Status.objects.all()[0]#Import status as ActivityStatus ?
        rtype_participant = RelationType.objects.get(pk=REL_SUB_PART_2_ACTIVITY)

        activity1 = Meeting.objects.create(user=self.user, type=act_type, title=u"Meeting",
                                           start=datetime.now(), end=datetime.now(),
                                           description=u"Desc", minutes=u"123", is_all_day=False,
                                           status=act_status, busy=True, place=u"Here"
                                          )
        contact1 = Contact.objects.create(user=self.user)
        contact2 = contact1.clone()

        Relation.objects.create(user=self.user, type=rtype_participant, subject_entity=contact1, object_entity=activity1)
        Relation.objects.create(user=self.user, type=rtype_participant, subject_entity=contact2, object_entity=activity1)

        activity2 = activity1.clone().clone().clone().clone().clone().clone().clone()
        self.assertNotEqual(activity1.pk, activity2.pk)

        for attr in ['user', 'title', 'start', 'end', 'description', 'minutes', 'type', 'is_all_day', 'status', 'place']:
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

        for attr in ['user', 'name', 'image', 'description']:
            self.assertEqual(getattr(image, attr), getattr(image2, attr))

        self.assertEqual(set(image.categories.values_list('pk', flat=True)),
                         set(image2.categories.values_list('pk', flat=True))
                        )


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

    def test_get_compatible_ones01(self):
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [Contact]),
                                               ('test-object_foobar',  'is managed by', [Organisation])
                                      )

        internal_rtype, internal_sym_rtype = RelationType.create(('test-subject_foobar_2', 'manages internal',       [Contact]),
                                                                 ('test-object_foobar_2',  'is managed by internal', [Organisation]),
                                                                 is_internal=True,
                                      )

        contact_ct_id = ContentType.objects.get_for_model(Contact).id

        compatibles_ids = RelationType.get_compatible_ones(contact_ct_id).values_list('id', flat=True)
        self.assertEqual(set([rtype.id]), set(compatibles_ids))

        compatibles_ids_w_internals = RelationType.get_compatible_ones(contact_ct_id, include_internals=True).values_list('id', flat=True)
        self.assertEqual(set([rtype.id, internal_rtype.id]), set(compatibles_ids_w_internals))

    def test_get_compatible_ones02(self):
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages',       [Contact]),
                                               ('test-object_foobar',  'is managed by', [Organisation]),
                                               is_internal=True,
                                      )

        internal_rtype, internal_sym_rtype = RelationType.create(('test-subject_foobar_2', 'manages internal',       [Contact]),
                                                                 ('test-object_foobar_2',  'is managed by internal', [Organisation]),
                                                                 is_internal=True,
                                      )

        contact_ct_id = ContentType.objects.get_for_model(Contact).id

        compatibles_ids = RelationType.get_compatible_ones(contact_ct_id).values_list('id', flat=True)
        self.assertEqual(0,  len(compatibles_ids))
        self.assertEqual(set(), set(compatibles_ids))

        compatibles_ids = RelationType.get_compatible_ones(contact_ct_id, include_internals=True).values_list('id', flat=True)
        self.assertEqual(2,  len(compatibles_ids))
        self.assertEqual(set([rtype.id, internal_rtype.id]), set(compatibles_ids))

    def test_get_compatible_ones03(self):
        rtype, sym_rtype = RelationType.create(('test-subject_foobar', 'manages'),
                                               ('test-object_foobar',  'is managed by'))

        internal_rtype, internal_sym_rtype = RelationType.create(('test-subject_foobar_2', 'manages internal'),
                                                                 ('test-object_foobar_2',  'is managed by internal'),
                                                                 is_internal=True)

        contact_ct_id = ContentType.objects.get_for_model(Contact).id

        compatibles_ids = RelationType.get_compatible_ones(contact_ct_id).values_list('id', flat=True)
        self.assertEqual(set([rtype.id, sym_rtype.id]), set(compatibles_ids))

        compatibles_ids = RelationType.get_compatible_ones(contact_ct_id, include_internals=True).values_list('id', flat=True)
        self.assertEqual(set([rtype.id, sym_rtype.id, internal_rtype.id, internal_sym_rtype.id]), set(compatibles_ids))


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


class HeaderFiltersTestCase(CremeTestCase):
    def test_relation01(self): #delete RelationType
        self.login()

        loves, loved = RelationType.create(('test-subject_love', u'Is loving'), ('test-object_love',  u'Is loved by'))
        hates, hated = RelationType.create(('test-subject_hate', u'Is hating'), ('test-object_hate',  u'Is hated by'))

        #TODO: create helper methods like in EntityFilter/EntityFilterCondition
        hf = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=Contact)
        hfi01 = HeaderFilterItem.objects.create(pk='test-hfi_01', order=1, name='last_name',  title=u'Last name',
                                                type=HFI_FIELD, header_filter=hf, filter_string="last_name__icontains"
                                               )
        hfi02 = HeaderFilterItem.objects.create(pk='test-hfi_02', order=2, name='is_loving', title=u'Loves',
                                                type=HFI_RELATION, header_filter=hf, has_a_filter=True, editable=False,
                                                filter_string="", relation_predicat_id=loves.id
                                               )
        hfi03 = HeaderFilterItem.objects.create(pk='test-hfi_03', order=2, name='is_loved_by', title=u'Loved',
                                                type=HFI_RELATION, header_filter=hf, has_a_filter=True, editable=False,
                                                filter_string="", relation_predicat_id=loved.id
                                               )
        hfi04 = HeaderFilterItem.objects.create(pk='test-hfi_04', order=3, name='is_hating', title=u'Hates',
                                                type=HFI_RELATION, header_filter=hf, has_a_filter=True, editable=False,
                                                filter_string="", relation_predicat_id=hates.id
                                               )
        self.assertEqual(4, hf.header_filter_items.count())

        loves_id = loves.id
        loves.delete()
        self.assertEqual(0, RelationType.objects.filter(pk=loves_id).count())
        self.assertEqual([hfi01.id, hfi04.id], [hfi.id for hfi in hf.header_filter_items.all()])

    def test_customfield01(self): #delete CustomField
        self.login()

        contact_ct = ContentType.objects.get_for_model(Contact)
        custom_field01 = CustomField.objects.create(name='Size (cm)', content_type=contact_ct, field_type=CustomField.INT)
        custom_field02 = CustomField.objects.create(name='IQ',        content_type=contact_ct, field_type=CustomField.INT)

        #TODO: create helper methods like in EntityFilter/EntityFilterCondition
        hf = HeaderFilter.create(pk='test-hf01', name=u'Contact view', model=Contact)
        hfi01 = HeaderFilterItem.objects.create(pk='test-hfi_01', order=1, name='last_name',  title=u'Last name',
                                                type=HFI_FIELD, header_filter=hf, filter_string="last_name__icontains"
                                               )
        hfi02 = HeaderFilterItem.objects.create(pk='test-hfi_02', order=2, name=custom_field01.id, title=custom_field01.name,
                                                type=HFI_CUSTOM, header_filter=hf,
                                                filter_string="%s__value__icontains" % custom_field01.get_value_class().get_related_name()
                                               )
        hfi03 = HeaderFilterItem.objects.create(pk='test-hfi_03', order=3, name=custom_field02.id, title=custom_field02.name,
                                                type=HFI_CUSTOM, header_filter=hf,
                                                filter_string="%s__value__icontains" % custom_field02.get_value_class().get_related_name()
                                               )
        self.assertEqual(3, hf.header_filter_items.count())

        custom_field01.delete()
        self.assertEqual([hfi01.id, hfi03.id], [hfi.id for hfi in hf.header_filter_items.all()])


class EntityFiltersTestCase(CremeTestCase):
    def setUp(self):
        self.login()

        create = Contact.objects.create
        user = self.user

        self.civ_miss   = miss   = Civility.objects.create(title='Miss')
        self.civ_mister = mister = Civility.objects.create(title='Mister')

        self.contacts = [
            create(user=user, first_name=u'Spike',  last_name=u'Spiegel',   civility=mister), #0
            create(user=user, first_name=u'Jet',    last_name=u'Black',     civility=mister), #1
            create(user=user, first_name=u'Faye',   last_name=u'Valentine', civility=miss,
                   description=u'Sexiest woman is the universe'),                             #2
            create(user=user, first_name=u'Ed',     last_name=u'Wong', description=u''),      #3
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

        self.contact_ct = ContentType.objects.get_for_model(Contact)

    def assertExpectedFiltered(self, efilter, model, ids, case_insensitive=False):
        msg = '(NB: maybe you have case sensitive problems with your DB configuration).' if case_insensitive else ''
        filtered = list(efilter.filter(model.objects.all()))
        self.assertEqual(len(ids), len(filtered), str(filtered) + msg)
        self.assertEqual(set(ids), set(c.id for c in filtered))

    def test_filter_field_equals01(self):
        self.assertEqual(len(self.contacts), Contact.objects.count())

        efilter = EntityFilter.create('test-filter01', 'Ikari', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='last_name', values=['Ikari']
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())

        efilter =  EntityFilter.objects.get(pk=efilter.id) #refresh
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id, self.contacts[8].id])

    def test_filter_field_equals02(self):
        efilter = EntityFilter.create('test-filter01', 'Spike & Faye', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='first_name',
                                                                    values=['Spike', 'Faye']
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())

        efilter =  EntityFilter.objects.get(pk=efilter.id) #refresh
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id, self.contacts[2].id])

    def test_filter_field_iequals(self):
        efilter = EntityFilter.create('test-filter01', 'Ikari (insensitive)', Contact,
                                      user=self.user, is_custom=False
                                     )
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='last_name', values=['Ikari']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[i].id for i in (7, 8, 9)], True)

    def test_filter_field_not_equals(self):
        efilter = EntityFilter.create('test-filter01', 'Not Ikari', Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS_NOT,
                                                                    name='last_name', values=['Ikari']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (7, 8)])

    def test_filter_field_not_iequals(self):
        pk = 'test-filter01'
        name = 'Not Ikari (case insensitive)'
        efilter = EntityFilter.create(pk, name, Contact)

        efilters = EntityFilter.objects.filter(pk='test-filter01', name=name)
        self.assertEqual(1,                  len(efilters))
        self.assertEqual(self.contact_ct.id, efilters[0].entity_type.id)
        self.assertEqual(efilter.id,         efilters[0].id)

        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS_NOT,
                                                                    name='last_name', values=['Ikari']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (7, 8, 9)])

    def test_filter_field_contains(self):
        efilter = EntityFilter.create('test-filter01', name='Contains "isat"', model=Contact, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.CONTAINS,
                                                                    name='first_name', values=['isat']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id, self.contacts[11].id])

    def test_filter_field_icontains(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Not contains "Misa"', model=Contact, user=self.user)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ICONTAINS,
                                                                    name='first_name', values=['misa']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id], True)

    def test_filter_field_contains_not(self):
        efilter = EntityFilter.create('test-filter01', 'Not Ikari', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.CONTAINS_NOT,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (5, 11)])

    def test_filter_field_icontains_not(self):
        efilter = EntityFilter.create('test-filter01', 'Not contains "sato" (ci)', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ICONTAINS_NOT,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (5, 11)], True)

    def test_filter_field_gt(self):
        efilter = EntityFilter.create(pk='test-filter01', name='> Yua', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.GT,
                                                                    name='first_name', values=['Yua']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[8].id])

    def test_filter_field_gte(self):
        efilter = EntityFilter.create('test-filter01', '>= Spike', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.GTE,
                                                                    name='first_name', values=['Spike']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id, self.contacts[8].id])

    def test_filter_field_lt(self):
        efilter = EntityFilter.create('test-filter01', '< Faye', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.LT,
                                                                    name='first_name', values=['Faye']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[3].id, self.contacts[6].id])

    def test_filter_field_lte(self):
        efilter = EntityFilter.create('test-filter01', '<= Faye', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.LTE,
                                                                    name='first_name', values=['Faye']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[i].id for i in (2, 3, 6)])

    def test_filter_field_startswith(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts "Gen"', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.STARTSWITH,
                                                                    name='first_name', values=['Gen']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[9].id, self.contacts[10].id])

    def test_filter_field_istartswith(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts "Gen" (ci)', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='first_name', values=['gen']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[9].id, self.contacts[10].id])

    def test_filter_field_startswith_not(self):
        efilter = EntityFilter.create(pk='test-filter01', name='starts not "Asu"', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.STARTSWITH_NOT,
                                                                    name='first_name', values=['Asu']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 6])

    def test_filter_field_istartswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'starts not "asu"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISTARTSWITH_NOT,
                                                                    name='first_name', values=['asu']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 6])

    def test_filter_field_endswith(self):
        efilter = EntityFilter.create('test-filter01', 'ends "sato"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ENDSWITH,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id, self.contacts[11].id])

    def test_filter_field_iendswith(self):
        efilter = EntityFilter.create('test-filter01', 'ends "SATO"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IENDSWITH,
                                                                    name='first_name', values=['SATO']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id, self.contacts[11].id])

    def test_filter_field_endswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'ends not "sato"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ENDSWITH_NOT,
                                                                    name='first_name', values=['sato']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (5, 11)])

    def test_filter_field_iendswith_not(self):
        efilter = EntityFilter.create('test-filter01', 'ends not "SATO" (ci)', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IENDSWITH_NOT,
                                                                    name='first_name', values=['SATO']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in (5, 11)])

    def test_filter_field_isnull01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='is null', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='description', values=[True]
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 2])

    def test_filter_field_isnull02(self):
        efilter = EntityFilter.create('test-filter01', 'is not null', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='description', values=[False]
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[2].id])

    def test_filter_field_isnull03(self): #not charfield
        create = Organisation.objects.create
        user = self.user
        orga01 = create(user=user, name='Bebop & cie', capital=None)
        orga02 = create(user=user, name='Nerv',        capital=10000)

        efilter = EntityFilter.create('test-filter01', 'is not null', Organisation)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                    operator=EntityFilterCondition.ISEMPTY,
                                                                    name='capital', values=[False]
                                                                   )
                               ])
        self.assertEqual(1, efilter.conditions.count())
        self.assertExpectedFiltered(efilter, Organisation, [orga02.id])

    def test_filter_field_range(self):
        create = Organisation.objects.create
        user = self.user
        orga01 = create(user=user, name='Bebop & cie', capital=1000)
        orga02 = create(user=user, name='Nerv',        capital=10000)
        orga03 = create(user=user, name='Seele',       capital=100000)

        efilter = EntityFilter.create('test-filter01', name='Between 5K & 500K', model=Organisation)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                    operator=EntityFilterCondition.RANGE,
                                                                    name='capital', values=(5000, 500000)
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Organisation, [orga02.id, orga03.id])

    def test_filter_fk01(self):
        efilter = EntityFilter.create('test-filter01', 'Misters', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='civility', values=[self.civ_mister.id] #TODO: "self.mister" ??
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id, self.contacts[1].id])

        efilter = EntityFilter.create('test-filter01', 'Not Misses', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.EQUALS_NOT,
                                                                    name='civility', values=[self.civ_miss.id]
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 2])

    def test_filter_fk02(self):
        efilter = EntityFilter.create('test-filter01', 'Mist..', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ISTARTSWITH,
                                                                    name='civility__title', values=['Mist']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id, self.contacts[1].id])

    def test_filter_m2m(self):
        l1 = Language.objects.create(name='Japanese', code='JP')
        l2 = Language.objects.create(name='German',   code='G')
        l3 = Language.objects.create(name='Engrish',  code='EN')

        jet = self.contacts[1];     jet.language   = [l1, l3]
        rei = self.contacts[4];     rei.language   = [l1]
        asuka = self.contacts[6];   asuka.language = [l1, l2, l3]

        self.assertEqual(3, Contact.objects.filter(language__code='JP').count())
        self.assertEqual(4, Contact.objects.filter(language__name__contains='an').count()) #BEWARE: doublon !!
        self.assertEqual(3, Contact.objects.filter(language__name__contains='an').distinct().count())

        efilter = EntityFilter.create('test-filter01', 'JP', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.IEQUALS,
                                                                    name='language__code', values=['JP']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [jet.id, rei.id, asuka.id])

        efilter = EntityFilter.create('test-filter02', 'lang contains "an"', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Contact,
                                                                    operator=EntityFilterCondition.ICONTAINS,
                                                                    name='language__name', values=['an']
                                                                   )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [jet.id, rei.id, asuka.id])

    def test_problematic_validation_fields(self):
        efilter = EntityFilter.create('test-filter01', 'Mist..', Contact)
        build = EntityFilterCondition.build_4_field

        try:
            #Problem a part of a email address is not a valid email address
            efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.ISTARTSWITH, name='email', values=['misato'])])
        except Exception, e:
            self.fail(str(e))

        try:
            efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.RANGE, name='email', values=['misato', 'yui'])])
        except Exception, e:
            self.fail(str(e))

        try:
            efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS, name='email', values=['misato@nerv.jp'])])
        except Exception, e:
            self.fail(str(e))

        self.assertRaises(EntityFilterCondition.ValueError, build,
                          model=Contact, operator=EntityFilterCondition.EQUALS, name='email', values=['misato'],
                         )

    def test_build_condition(self): #errors
        ValueError = EntityFilterCondition.ValueError
        build_4_field = EntityFilterCondition.build_4_field

        self.assertRaises(ValueError, build_4_field,
                          model=Contact, operator=EntityFilterCondition.CONTAINS, name='unknown_field', values=['Misato'],
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Organisation, operator=EntityFilterCondition.GT, name='capital', values=['Not an integer']
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Contact, operator=EntityFilterCondition.ISEMPTY, name='description', values=['Not a boolean'], #ISEMPTY => boolean
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Contact, operator=EntityFilterCondition.ISEMPTY, name='description', values=[True, True], #only one boolean is expected
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Contact, operator=EntityFilterCondition.STARTSWITH, name='civility__unknown', values=['Mist']
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Organisation, operator=EntityFilterCondition.RANGE, name='capital', values=[5000]
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Organisation, operator=EntityFilterCondition.RANGE, name='capital', values=[5000, 50000, 100000]
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Organisation, operator=EntityFilterCondition.RANGE, name='capital', values=['not an integer', 500000]
                         )
        self.assertRaises(ValueError, build_4_field,
                          model=Organisation, operator=EntityFilterCondition.RANGE, name='capital', values=[500000, 'not an integer']
                         )

    def test_condition_update(self):
        build = EntityFilterCondition.build_4_field
        cond1 = build(model=Contact,      operator=EntityFilterCondition.EQUALS,  name='first_name', values=['Jet'])
        self.failIf(build(model=Contact,  operator=EntityFilterCondition.EQUALS,  name='first_name', values=['Jet']).update(cond1))
        self.assert_(build(model=Contact, operator=EntityFilterCondition.IEQUALS, name='first_name', values=['Jet']).update(cond1))
        self.assert_(build(model=Contact, operator=EntityFilterCondition.EQUALS,  name='last_name',  values=['Jet']).update(cond1))
        self.assert_(build(model=Contact, operator=EntityFilterCondition.EQUALS,  name='first_name', values=['Ed']).update(cond1))
        self.assert_(build(model=Contact, operator=EntityFilterCondition.IEQUALS, name='last_name', values=['Jet']).update(cond1))
        self.assert_(build(model=Contact, operator=EntityFilterCondition.IEQUALS, name='last_name', values=['Ed']).update(cond1))

    def test_set_conditions01(self):
        build = EntityFilterCondition.build_4_field
        efilter = EntityFilter.create('test-filter01', 'Jet', Contact)
        efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS, name='first_name', values=['Jet'])])

        #NB: create an other condition that has he last id (so if we delete the
        #    first condition, and recreate another one, the id will be different)
        EntityFilter.create('test-filter02', 'Faye', Contact) \
                    .set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS, name='first_name', values=['Faye'])])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))
        old_id = conditions[0].id

        operator = EntityFilterCondition.CONTAINS
        name = 'last_name'
        value = 'Black'
        efilter.set_conditions([build(model=Contact, operator=operator, name=name, values=[value])])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,           condition.type)
        self.assertEqual(name,                                      condition.name)
        self.assertEqual({'operator': operator, 'values': [value]}, condition.decoded_value)
        self.assertEqual(old_id,                                    condition.id)

    def test_set_conditions02(self):
        efilter = EntityFilter.create('test-filter01', 'Jet', Contact)

        kwargs1 = {
                'model':     Contact,
                'operator':  EntityFilterCondition.EQUALS,
                'name':      'first_name',
                'values':    ['Jet'],
            }
        kwargs2 = dict(kwargs1)
        kwargs2['operator'] = EntityFilterCondition.IEQUALS

        build = EntityFilterCondition.build_4_field
        efilter.set_conditions([build(**kwargs1), build(**kwargs2)])

        #NB: see test_set_conditions01()
        EntityFilter.create('test-filter02', 'Faye', Contact) \
                    .set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS, name='first_name', values=['Faye'])])

        conditions = efilter.conditions.all()
        self.assertEqual(2, len(conditions))

        for kwargs, condition in zip([kwargs1, kwargs2], conditions):
            self.assertEqual(EntityFilterCondition.EFC_FIELD, condition.type)
            self.assertEqual(kwargs['name'],                  condition.name)
            self.assertEqual({'operator': kwargs['operator'], 'values': kwargs['values']}, condition.decoded_value)

        old_id = conditions[0].id

        kwargs1['operator'] = EntityFilterCondition.GT
        efilter.set_conditions([build(**kwargs1)])

        conditions = efilter.conditions.all()
        self.assertEqual(1, len(conditions))

        condition = conditions[0]
        self.assertEqual(EntityFilterCondition.EFC_FIELD,                                condition.type)
        self.assertEqual(kwargs1['name'],                                                condition.name)
        self.assertEqual({'operator': kwargs1['operator'], 'values': kwargs1['values']}, condition.decoded_value)
        self.assertEqual(old_id,                                                         condition.id)

    def test_multi_conditions_and01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        build = EntityFilterCondition.build_4_field
        efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS,
                                      name='last_name', values=['Ikari']
                                     ),
                                build(model=Contact, operator=EntityFilterCondition.STARTSWITH,
                                      name='first_name', values=['Shin']
                                     )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id])

    def test_multi_conditions_or01(self):
        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, use_or=True)
        build = EntityFilterCondition.build_4_field
        efilter.set_conditions([build(model=Contact, operator=EntityFilterCondition.EQUALS,
                                      name='last_name', values=['Spiegel']
                                     ),
                                build(model=Contact, operator=EntityFilterCondition.STARTSWITH,
                                      name='first_name', values=['Shin']
                                     )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id, self.contacts[7].id])

    def test_subfilter01(self):
        build_4_field = EntityFilterCondition.build_4_field
        build_sf      = EntityFilterCondition.build_4_subfilter
        sub_efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, use_or=True)
        sub_efilter.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,     name='last_name',  values=['Spiegel']),
                                    build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Shin'])
                                   ])
        efilter = EntityFilter.create(pk='test-filter02', name='Filter02', model=Contact, use_or=False)
        conds = [build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Spi']),
                 build_sf(sub_efilter),
                ]
        try:
            efilter.check_cycle(conds)
        except Exception, e:
            self.fail(str(e))

        efilter.set_conditions(conds)
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[0].id])

        #Test that a CycleError is not raised
        sub_sub_efilter = EntityFilter.create(pk='test-filter03', name='Filter03', model=Contact)
        sub_sub_efilter.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,     name='last_name',  values=['Black']),
                                        build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Jet'])
                                       ])

        conds = [build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Spi']),
                 build_sf(sub_sub_efilter),
                ]
        try:
            sub_efilter.check_cycle(conds)
        except Exception, e:
            self.fail(str(e))

    def test_subfilter02(self): #cycle error (lenght = 0)
        efilter = EntityFilter.create(pk='test-filter02', name='Filter01', model=Contact, use_or=False)
        conds = [EntityFilterCondition.build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH,
                                                     name='first_name', values=['Spi']
                                                    ),
                 EntityFilterCondition.build_4_subfilter(efilter),
                ]
        self.assertRaises(EntityFilter.CycleError, efilter.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter.set_conditions, conds)

    def test_subfilter03(self): #cycle error (lenght = 1)
        build_4_field = EntityFilterCondition.build_4_field
        build_sf = EntityFilterCondition.build_4_subfilter

        efilter01 = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, use_or=True)
        efilter01.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS, name='last_name', values=['Spiegel'])])

        efilter02 = EntityFilter.create(pk='test-filter02', name='Filter02', model=Contact, use_or=False)
        self.assertEqual(set([efilter02.id]), efilter02.get_connected_filter_ids())

        efilter02.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name', values=['Spi']),
                                  build_sf(efilter01),
                                 ])

        conds = [build_4_field(model=Contact, operator=EntityFilterCondition.CONTAINS, name='first_name', values=['Faye']),
                 build_sf(efilter02),
                ]
        efilter01 = EntityFilter.objects.get(pk=efilter01.pk) #refresh
        self.assertEqual(set([efilter01.id, efilter02.id]), efilter01.get_connected_filter_ids())
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_subfilter04(self): #cycle error (lenght = 2)
        build_4_field = EntityFilterCondition.build_4_field
        build_sf = EntityFilterCondition.build_4_subfilter

        efilter01 = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact, use_or=True)
        efilter01.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS, name='last_name', values=['Spiegel'])])

        efilter02 = EntityFilter.create(pk='test-filter02', name='Filter02', model=Contact, use_or=False)
        efilter02.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, values=['Spi'], name='first_name'),
                                  build_sf(efilter01),
                                 ])

        efilter03 = EntityFilter.create(pk='test-filter03', name='Filter03', model=Contact, use_or=False)
        efilter03.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.ISTARTSWITH, values=['Misa'], name='first_name'),
                                  build_sf(efilter02),
                                 ])

        conds = [build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS, name='last_name', values=['Spiegel']),
                 build_sf(efilter03),
                ]
        efilter01 = EntityFilter.objects.get(pk=efilter01.pk) #refresh
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_properties01(self):
        ptype = CremePropertyType.create(str_pk='test-prop_kawaii', text=u'Kawaii')
        cute_ones = (2, 4, 5, 6)

        for girl_id in cute_ones:
            CremeProperty.objects.create(type=ptype, creme_entity=self.contacts[girl_id])

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_property(ptype=ptype, has=True)])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[i].id for i in cute_ones])

        efilter.set_conditions([EntityFilterCondition.build_4_property(ptype=ptype, has=False)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i not in cute_ones])

    def _aux_test_relations(self):
        self.loves, self.loved = RelationType.create(('test-subject_love', u'Is loving'),
                                                     ('test-object_love',  u'Is loved by')
                                                    )

        self.hates, self.hated = RelationType.create(('test-subject_hate', u'Is hating'),
                                                     ('test-object_hate',  u'Is hated by')
                                                    )

        bebop = Organisation.objects.create(user=self.user, name='Bebop')

        loves = self.loves
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
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True)])
        self.assertExpectedFiltered(efilter, Contact, in_love)

        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=False)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for c in self.contacts if c.id not in in_love])

    def test_relations02(self): #wanted ct
        loves = self._aux_test_relations()
        in_love = [self.contacts[2].id, self.contacts[7].id, self.contacts[9].id] # not 'jet' ('bebop' not is a Contact)

        efilter = EntityFilter.create(pk='test-filter01', name='Filter01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True, ct=self.contact_ct)])
        self.assertExpectedFiltered(efilter, Contact, in_love)

        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=False, ct=self.contact_ct)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for c in self.contacts if c.id not in in_love])

    def test_relations03(self): #wanted entity
        loves = self._aux_test_relations()
        in_love = [self.contacts[7].id, self.contacts[9].id]
        rei = self.contacts[4]

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True, entity=rei)])
        self.assertExpectedFiltered(efilter, Contact, in_love)

        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=False, entity=rei)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for c in self.contacts if c.id not in in_love])

    def test_relations04(self): #wanted entity is deleted
        loves = self._aux_test_relations()
        rei = self.contacts[4]

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_relation(rtype=loves, has=True, entity=rei)])

        try:
            Relation.objects.filter(object_entity=rei.id).delete()
            rei.delete()
        except Exception, e:
            self.fail('Problem with entity deletion:' + str(e))

        self.assertExpectedFiltered(efilter, Contact, [])

    def test_relations05(self): #RelationType is deleted
        loves = self._aux_test_relations()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        build = EntityFilterCondition.build_4_relation
        efilter.set_conditions([build(rtype=loves,      has=True, entity=self.contacts[4]),
                                build(rtype=self.loved, has=True, ct=self.contact_ct),
                                build(rtype=self.hates, has=True),
                               ])

        loves.delete()
        self.assertEqual([self.hates.id], [cond.name for cond in efilter.conditions.all()])

    def test_relations_subfilter01(self):
        loves = self._aux_test_relations()
        in_love = [self.contacts[7].id, self.contacts[9].id]

        sub_efilter = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=Contact)
        build_4_field = EntityFilterCondition.build_4_field
        sub_efilter.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='last_name',  values=['Ayanami']),
                                    build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,     name='first_name', values=['Rei'])
                                   ])
        self.assertExpectedFiltered(sub_efilter, Contact, [self.contacts[4].id])

        efilter = EntityFilter.create(pk='test-filter02', name='Filter Rei lovers', model=Contact)
        conds = [EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=True, subfilter=sub_efilter)]

        try:
            efilter.check_cycle(conds)
        except Exception, e:
            self.fail(str(e))

        efilter.set_conditions(conds)
        self.assertExpectedFiltered(efilter, Contact, in_love)

        efilter.set_conditions([EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=False, subfilter=sub_efilter)])
        self.assertExpectedFiltered(efilter, Contact, [c.id for c in self.contacts if c.id not in in_love])

    def test_relations_subfilter02(self): #cycle error (lenght = 0)
        loves = self._aux_test_relations()

        efilter = EntityFilter.create(pk='test-filter01', name='Filter Rei lovers', model=Contact)
        conds = [EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=True, subfilter=efilter)]

        self.assertRaises(EntityFilter.CycleError, efilter.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter.set_conditions, conds)

    def test_relations_subfilter03(self): #cycle error (lenght = 1)
        loves = self._aux_test_relations()

        efilter01 = EntityFilter.create(pk='test-filter01', name='Filter 01', model=Contact)
        efilter01.set_conditions([EntityFilterCondition.build_4_field(model=Contact, operator=EntityFilterCondition.EQUALS,
                                                                      name='last_name', values=['Ayanami'])
                                 ])

        efilter02 = EntityFilter.create(pk='test-filter02', name='Filter 02', model=Contact)
        efilter02.set_conditions([EntityFilterCondition.build_4_relation_subfilter(rtype=loves, has=True, subfilter=efilter01)])

        conds = [EntityFilterCondition.build_4_relation_subfilter(rtype=self.hates, has=False, subfilter=efilter02)]
        efilter01 = EntityFilter.objects.get(pk=efilter01.pk) #refresh
        self.assertRaises(EntityFilter.CycleError, efilter01.check_cycle, conds)
        self.assertRaises(EntityFilter.CycleError, efilter01.set_conditions, conds)

    def test_relations_subfilter04(self): #RelationType is deleted
        loves = self._aux_test_relations()
        build_4_field = EntityFilterCondition.build_4_field

        sub_efilter01 = EntityFilter.create(pk='test-filter01', name='Filter Rei', model=Contact)
        sub_efilter01.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='last_name',  values=['Ayanami'])])

        sub_efilter02 = EntityFilter.create(pk='test-filter02', name='Filter Rei', model=Contact)
        sub_efilter02.set_conditions([build_4_field(model=Contact, operator=EntityFilterCondition.STARTSWITH, name='first_name',  values=['Misa'])])

        efilter = EntityFilter.create(pk='test-filter03', name='Filter Rei lovers', model=Contact)
        build = EntityFilterCondition.build_4_relation_subfilter
        efilter.set_conditions([build(rtype=loves,      has=True, subfilter=sub_efilter01),
                                build(rtype=self.hates, has=True, subfilter=sub_efilter02),
                               ])

        loves.delete()
        self.assertEqual([self.hates.id], [cond.name for cond in efilter.conditions.all()])

    def test_date01(self): # GTE operator
        efilter = EntityFilter.create('test-filter01', 'After 2000-1-1', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                                   start=date(year=2000, month=1, day=1),
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[6].id, self.contacts[7].id])

    def test_date02(self): # LTE operator
        efilter = EntityFilter.create('test-filter01', 'Before 1999-12-31', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                                   end=date(year=1999, month=12, day=31),
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[5].id])

    def test_date03(self): #range
        efilter = EntityFilter.create('test-filter01', name='Between 2001-1-1 & 2001-12-1', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                                   start=date(year=2001, month=1, day=1),
                                                                   end=date(year=2001, month=12, day=1),
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id])

    def test_date04(self): #relative to now
        faye = self.contacts[2]
        future = date.today()
        future = future.replace(year=future.year + 100)
        faye.birthday = future
        faye.save()

        efilter = EntityFilter.create('test-filter01', name='In the future', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_date(model=Contact, name='birthday',
                                                                   date_range='in_future',
                                                                  )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [faye.id])

    def test_build_date(self): #errors
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_date,
                          model=Contact, name='unknown_field', start=date(year=2001, month=1, day=1)
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_date,
                          model=Contact, name='first_name', start=date(year=2001, month=1, day=1) #not a date
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_date,
                          model=Contact, name='birthday' #no date
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_date,
                          model=Contact, name='birthday', date_range='unknown_range',
                         )

    def test_customfield01(self): #INT, only one CustomField, LTE operator
        rei = self.contacts[4]

        custom_field = CustomField.objects.create(name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field.get_value_class()(custom_field=custom_field, entity=rei).set_value_n_save(150)
        custom_field.get_value_class()(custom_field=custom_field, entity=self.contacts[5]).set_value_n_save(170)
        self.assertEqual(2, CustomFieldInteger.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Small', model=Contact)
        cond = EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                         operator=EntityFilterCondition.LTE,
                                                         value=155
                                                        )
        self.assertEqual(EntityFilterCondition.EFC_CUSTOMFIELD, cond.type)

        efilter.set_conditions([cond])
        self.assertExpectedFiltered(efilter, Contact, [rei.id])

    def test_customfield02(self): #2 INT CustomFields (can interfere), GTE operator
        asuka = self.contacts[6]

        custom_field01 = CustomField.objects.create(name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field01.get_value_class()(custom_field=custom_field01, entity=self.contacts[4]).set_value_n_save(150)
        custom_field01.get_value_class()(custom_field=custom_field01, entity=asuka).set_value_n_save(160)

        #should not be retrieved, because fiklter is relative to 'custom_field01'
        custom_field02 = CustomField.objects.create(name='weight (pound)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field02.get_value_class()(custom_field=custom_field02, entity=self.contacts[0]).set_value_n_save(156)

        self.assertEqual(3, CustomFieldInteger.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Not so small', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field01,
                                                                          operator=EntityFilterCondition.GTE,
                                                                          value=155
                                                                         )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [asuka.id])

    def test_customfield03(self): #STR, CONTAINS_NOT operator (negate)
        custom_field = CustomField.objects.create(name='Eva', content_type=self.contact_ct, field_type=CustomField.STR)
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=self.contacts[4]).set_value_n_save('Eva-00')
        klass(custom_field=custom_field, entity=self.contacts[7]).set_value_n_save('Eva-01')
        klass(custom_field=custom_field, entity=self.contacts[5]).set_value_n_save('Eva-02')
        self.assertEqual(3, CustomFieldString.objects.count())

        efilter = EntityFilter.create('test-filter01', name='not 00', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                                          operator=EntityFilterCondition.CONTAINS_NOT,
                                                                          value='00'
                                                                         )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [c.id for i, c in enumerate(self.contacts) if i != 4])

    def test_customfield04(self): #2 INT CustomFields with 2 conditions
        asuka = self.contacts[6]
        spike = self.contacts[0]

        custom_field01 = CustomField.objects.create(name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        klass = custom_field01.get_value_class()
        klass(custom_field=custom_field01, entity=spike).set_value_n_save(180)
        klass(custom_field=custom_field01, entity=self.contacts[4]).set_value_n_save(150)
        klass(custom_field=custom_field01, entity=asuka).set_value_n_save(160)

        custom_field02 = CustomField.objects.create(name='weight (pound)', content_type=self.contact_ct, field_type=CustomField.INT)
        klass = custom_field02.get_value_class()
        klass(custom_field=custom_field02, entity=spike).set_value_n_save(156)
        klass(custom_field=custom_field02, entity=asuka).set_value_n_save(80)

        efilter = EntityFilter.create('test-filter01', name='Not so small but light', model=Contact)
        build_cond = EntityFilterCondition.build_4_customfield
        efilter.set_conditions([build_cond(custom_field=custom_field01,
                                           operator=EntityFilterCondition.GTE,
                                           value=155
                                          ),
                                build_cond(custom_field=custom_field02,
                                           operator=EntityFilterCondition.LTE,
                                           value=100
                                          ),
                               ])
        self.assertExpectedFiltered(efilter, Contact, [asuka.id])

    def test_customfield05(self): #FLOAT
        ed  = self.contacts[3]
        rei = self.contacts[4]

        custom_field = CustomField.objects.create(name='Weight (kg)', content_type=self.contact_ct, field_type=CustomField.FLOAT)
        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=ed).set_value_n_save('38.20')
        klass(custom_field=custom_field, entity=rei).set_value_n_save('40.00')
        klass(custom_field=custom_field, entity=self.contacts[6]).set_value_n_save('40.5')

        self.assertEqual(3, CustomFieldFloat.objects.count())

        efilter = EntityFilter.create('test-filter01', name='<= 40', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                         operator=EntityFilterCondition.LTE,
                                                         value='40'
                                                        )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [ed.id, rei.id])

    def test_customfield06(self): #ENUM
        rei = self.contacts[4]

        custom_field = CustomField.objects.create(name='Eva', content_type=self.contact_ct, field_type=CustomField.ENUM)
        create_evalue = CustomFieldEnumValue.objects.create
        eva00 = create_evalue(custom_field=custom_field, value='Eva-00')
        eva01 = create_evalue(custom_field=custom_field, value='Eva-01')
        eva02 = create_evalue(custom_field=custom_field, value='Eva-02')

        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=rei).set_value_n_save(eva00.id)
        klass(custom_field=custom_field, entity=self.contacts[6]).set_value_n_save(eva02.id)

        self.assertEqual(2, CustomFieldEnum.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Eva-00', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                         operator=EntityFilterCondition.EQUALS,
                                                         value=eva00.id #TODO: "value=eva00"
                                                        )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [rei.id])

    def test_customfield07(self): #BOOL
        rei = self.contacts[4]

        custom_field = CustomField.objects.create(name='cute ??', content_type=self.contact_ct, field_type=CustomField.BOOL)
        custom_field.get_value_class()(custom_field=custom_field, entity=rei).set_value_n_save(True)
        custom_field.get_value_class()(custom_field=custom_field, entity=self.contacts[1]).set_value_n_save(False)
        self.assertEqual(2, CustomFieldBoolean.objects.count())

        efilter = EntityFilter.create('test-filter01', name='Cuties', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_customfield(custom_field=custom_field,
                                                                          operator=EntityFilterCondition.EQUALS,
                                                                          value=True
                                                                         )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [rei.id])

    def test_customfield08(self): #CustomField is deleted
        rei = self.contacts[4]

        custom_field01 = CustomField.objects.create(name='Size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        custom_field02 = CustomField.objects.create(name='IQ',        content_type=self.contact_ct, field_type=CustomField.INT)

        efilter = EntityFilter.create('test-filter01', name='Small', model=Contact)
        build = EntityFilterCondition.build_4_customfield
        efilter.set_conditions([build(custom_field=custom_field01, operator=EntityFilterCondition.LTE, value=155),
                                build(custom_field=custom_field02, operator=EntityFilterCondition.LTE, value=155),
                               ])

        custom_field01.delete()
        self.assertEqual([unicode(custom_field02.id)], [cond.name for cond in efilter.conditions.all()])

    def test_build_customfield(self): #errors
        custom_field = CustomField.objects.create(name='size (cm)', content_type=self.contact_ct, field_type=CustomField.INT)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_customfield,
                          custom_field=custom_field, operator=1216, value=155 #invalid operator
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_customfield,
                          custom_field=custom_field, operator=EntityFilterCondition.CONTAINS, value='not an int'
                         )

        custom_field = CustomField.objects.create(name='Day', content_type=self.contact_ct, field_type=CustomField.DATE)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_customfield,
                          custom_field=custom_field, operator=EntityFilterCondition.EQUALS, value=2011 #DATE
                         )

        custom_field = CustomField.objects.create(name='Cute ?', content_type=self.contact_ct, field_type=CustomField.BOOL)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_customfield,
                          custom_field=custom_field, operator=EntityFilterCondition.CONTAINS, value=True #bad operator
                         )

    def _aux_test_datecf(self):
        custom_field = CustomField.objects.create(name='First fight', content_type=self.contact_ct, field_type=CustomField.DATE)

        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=self.contacts[4]).set_value_n_save(date(year=2015, month=3, day=14))
        klass(custom_field=custom_field, entity=self.contacts[7]).set_value_n_save(date(year=2015, month=4, day=21))
        klass(custom_field=custom_field, entity=self.contacts[6]).set_value_n_save(date(year=2015, month=5, day=3))

        self.assertEqual(3, CustomFieldDateTime.objects.count())

        return custom_field

    def test_datecustomfield01(self): # GTE operator
        custom_field = self._aux_test_datecf()

        year = 2015; month = 4; day = 1
        efilter = EntityFilter.create('test-filter01', 'After April', Contact)
        cond = EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                             start=date(year=year, month=month, day=day),
                                                            )
        self.assertEqual(EntityFilterCondition.EFC_DATECUSTOMFIELD, cond.type)

        efilter.set_conditions([cond])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[6].id, self.contacts[7].id])

    def test_datecustomfield02(self): # LTE operator
        custom_field = self._aux_test_datecf()

        year = 2015; month = 5; day = 1
        efilter = EntityFilter.create('test-filter01', 'Before May', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                                              end=date(year=year, month=month, day=day),
                                                                             )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[4].id, self.contacts[7].id])

    def test_datecustomfield03(self): #range
        custom_field = self._aux_test_datecf()

        efilter = EntityFilter.create('test-filter01', 'In April', Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                                              start=date(year=2015, month=4, day=1),
                                                                              end=date(year=2015, month=4, day=30),
                                                                             )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [self.contacts[7].id])

    def test_datecustomfield04(self): #relative to now
        custom_field = CustomField.objects.create(name='First flight', content_type=self.contact_ct, field_type=CustomField.DATE)

        spike = self.contacts[0]
        jet   = self.contacts[1]
        today = date.today()

        klass = custom_field.get_value_class()
        klass(custom_field=custom_field, entity=self.contacts[2]).set_value_n_save(date(year=2000, month=3, day=14))
        klass(custom_field=custom_field, entity=spike).set_value_n_save(today.replace(year=today.year + 100))
        klass(custom_field=custom_field, entity=jet).set_value_n_save(today.replace(year=today.year + 95))

        efilter = EntityFilter.create('test-filter01', name='In the future', model=Contact)
        efilter.set_conditions([EntityFilterCondition.build_4_datecustomfield(custom_field=custom_field,
                                                                              date_range='in_future'
                                                                             )
                               ])
        self.assertExpectedFiltered(efilter, Contact, [spike.id, jet.id])

    def test_datecustomfield05(self): #2 DATE CustomFields with 2 conditions
        shinji = self.contacts[7]
        custom_field01 = self._aux_test_datecf()
        custom_field02 = CustomField.objects.create(name='Last fight', content_type=self.contact_ct, field_type=CustomField.DATE)

        klass = custom_field02.get_value_class()
        klass(custom_field=custom_field02, entity=self.contacts[4]).set_value_n_save(date(year=2020, month=3, day=14))
        klass(custom_field=custom_field02, entity=shinji).set_value_n_save(date(year=2030, month=4, day=21))
        klass(custom_field=custom_field02, entity=self.contacts[6]).set_value_n_save(date(year=2040, month=5, day=3))

        efilter = EntityFilter.create('test-filter01', 'Cpmlex filter', Contact, use_or=False)
        build_cond = EntityFilterCondition.build_4_datecustomfield
        efilter.set_conditions([build_cond(custom_field=custom_field01, start=date(year=2015, month=4, day=1)),
                                build_cond(custom_field=custom_field02, end=date(year=2040, month=1, day=1))
                               ])
        self.assertExpectedFiltered(efilter, Contact, [shinji.id])

    def test_build_datecustomfield(self): #errors
        custom_field = CustomField.objects.create(name='First flight', content_type=self.contact_ct, field_type=CustomField.INT) #not a DATE
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_datecustomfield,
                          custom_field=custom_field, date_range='in_future'
                         )

        custom_field = CustomField.objects.create(name='Day', content_type=self.contact_ct, field_type=CustomField.DATE)
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_datecustomfield,
                          custom_field=custom_field, #no date
                         )
        self.assertRaises(EntityFilterCondition.ValueError,
                          EntityFilterCondition.build_4_datecustomfield,
                          custom_field=custom_field, date_range='unknown_range'
                         )
