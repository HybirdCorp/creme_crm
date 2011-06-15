# -*- coding: utf-8 -*-

from datetime import datetime
from decimal import Decimal
from tempfile import NamedTemporaryFile

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models.deletion import ProtectedError

from creme_core.models import *
from creme_core.tests.base import CremeTestCase

from persons.models import Contact, Organisation, Civility, Position, Sector, Address

from media_managers.models import Image, MediaCategory

from activities.models.activity import Activity, ActivityType, Status, Meeting
from activities.constants import REL_SUB_PART_2_ACTIVITY


__all__ = ('EntityTestCase',)


class EntityTestCase(CremeTestCase):
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

    def test_property01(self): #TODO: create a test case for CremeProperty ???
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
        image.categories = MediaCategory.objects.all()
        image.save()

        image2 = image.clone()
        self.assertNotEqual(image.pk, image2.pk)

        for attr in ['user', 'name', 'image', 'description']:
            self.assertEqual(getattr(image, attr), getattr(image2, attr))

        self.assertEqual(set(image.categories.values_list('pk', flat=True)),
                         set(image2.categories.values_list('pk', flat=True))
                        )

    def test_delete01(self):
        """Simple delete"""
        ce = CremeEntity.objects.create(user=self.user)
        ce.delete()
        self.assertRaises(CremeEntity.DoesNotExist, CremeEntity.objects.get, id=ce.id)

    def test_delete02(self):
        """Can't delete entities linked by a relation"""
        self._setUpClone()
        ce1 = CremeEntity.objects.create(user=self.user)
        ce2 = CremeEntity.objects.create(user=self.user)

        Relation.objects.create(user=self.user, type=self.rtype1, subject_entity=ce1, object_entity=ce2)

        self.assertRaises(ProtectedError, ce1.delete)
        self.assertRaises(ProtectedError, ce2.delete)
