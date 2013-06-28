# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial
    #from tempfile import NamedTemporaryFile

    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType
    from django.db.models.deletion import ProtectedError
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _

    from ..base import CremeTestCase
    from creme.creme_core.models import *
    from creme.creme_core.core.function_field import FunctionField, FunctionFieldResult, FunctionFieldResultsList
    from creme.creme_core.core.field_tags import InvalidFieldTag

    from creme.persons.models import Contact, Organisation, Civility

    from creme.media_managers.models import MediaCategory #Image

    from creme.activities.models import Activity, ActivityType, Status
    from creme.activities.constants import REL_SUB_PART_2_ACTIVITY, ACTIVITYTYPE_MEETING
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('EntityTestCase',)


class EntityTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'media_managers', 'persons', 'activities')

    def setUp(self):
        self.user = User.objects.create(username='name')

    def test_entity01(self):
        with self.assertNoException():
            entity = CremeEntity.objects.create(user=self.user)

        now_value = now()
        self.assertLess((now_value - entity.created).seconds,  10)
        self.assertLess((now_value - entity.modified).seconds, 10)

    def test_property01(self): #TODO: create a test case for CremeProperty ???
        text = 'TEXT'

        with self.assertNoException():
            ptype  = CremePropertyType.create(str_pk='test-prop_foobar', text=text)
            entity = CremeEntity.objects.create(user=self.user)
            CremeProperty.objects.create(type=ptype, creme_entity=entity)

        self.assertEqual(text, ptype.text)

    def _setUpClone(self):
        create_rtype = RelationType.create
        self.rtype1, self.rtype2 = create_rtype(('test-subject_loving', 'is loving'),
                                                ('test-object_loving',  'is loved by'),
                                               )
        self.rtype3, self.rtype4 = create_rtype(('test-subject_hating', 'is hating'),
                                                ('test-object_hating',  'is hated by'),
                                                is_internal=True
                                               )

        create_ptype = CremePropertyType.create
        self.ptype01 = create_ptype(str_pk='test-prop_foobar01', text='wears strange hats')
        self.ptype02 = create_ptype(str_pk='test-prop_foobar02', text='wears strange pants')

    def test_fieldtags_clonable(self):
        naruto = Contact.objects.create(user=self.user, first_name=u'Naruto', last_name=u'Uzumaki')
        get_field = lambda name: naruto._meta.get_field_by_name(name)[0]

        self.assertFalse(get_field('created').get_tag('clonable'))
        self.assertFalse(get_field('modified').get_tag('clonable'))

        field = get_field('first_name')
        self.assertTrue(field.get_tag('clonable'))
        self.assertRaises(InvalidFieldTag, field.get_tag, 'stuff')

        self.assertFalse(get_field('id').get_tag('clonable'))
        self.assertFalse(get_field('cremeentity_ptr').get_tag('clonable'))

        self.assertRaises(InvalidFieldTag, field.set_tags, stuff=True)

    def test_fieldtags_viewable(self):
        naruto = Contact.objects.create(user=self.user, first_name=u'Naruto', last_name=u'Uzumaki')
        get_field = lambda name: naruto._meta.get_field_by_name(name)[0]

        self.assertTrue(get_field('modified').get_tag('viewable'))
        self.assertTrue(get_field('first_name').get_tag('viewable'))

        self.assertFalse(get_field('id').get_tag('viewable'))
        self.assertFalse(get_field('cremeentity_ptr').get_tag('viewable'))

    def test_fieldtags_user(self):
        get_field = lambda name: self.user._meta.get_field_by_name(name)[0]

        self.assertTrue(get_field('username').get_tag('viewable'))
        self.assertFalse(get_field('id').get_tag('viewable'))
        self.assertFalse(get_field('password').get_tag('viewable'))
        self.assertFalse(get_field('is_active').get_tag('viewable'))
        self.assertFalse(get_field('is_superuser').get_tag('viewable'))
        self.assertFalse(get_field('is_staff').get_tag('viewable'))
        self.assertFalse(get_field('last_login').get_tag('viewable'))
        self.assertFalse(get_field('date_joined').get_tag('viewable'))
        self.assertFalse(get_field('groups').get_tag('viewable'))
        self.assertFalse(get_field('user_permissions').get_tag('viewable'))

    def assertSameRelationsNProperties(self, entity1, entity2):
        self.assertSameProperties(entity1, entity2)
        self.assertSameRelations(entity1, entity2)

    def assertSameRelations(self, entity1, entity2):
        "Not internal relations"
        relations_desc = lambda entity: list((r.type_id, r.object_entity_id) for r in entity.relations.exclude(type__is_internal=True))
        rd1 = relations_desc(entity1)
        rd2 = relations_desc(entity2)
        self.assertEqual(len(rd1), len(rd2))
        self.assertEqual(set(rd1), set(rd2))

    def assertSameProperties(self, entity1, entity2):
        properties_desc  = lambda entity: list(p.type_id for p in entity.properties.all())
        pd1 = properties_desc(entity1)
        pd2 = properties_desc(entity2)
        self.assertEqual(len(pd1), len(pd2))
        self.assertEqual(set(pd1), set(pd2))

    #def create_image(self, ident=1):
        #tmpfile = NamedTemporaryFile()
        #tmpfile.width = tmpfile.height = 0
        #tmpfile._committed = True
        #tmpfile.path = 'upload/file_%s.jpg' % ident

        #return Image.objects.create(user=self.user, image=tmpfile,
                                    #name=u'Image #%s' % ident,
                                    #description=u"Desc"
                                   #)

    def test_clone01(self):
        self._setUpClone()

        created = modified = now()
        entity1 = CremeEntity.objects.create(user=self.user)
        original_ce = CremeEntity.objects.create(created=created, modified=modified, is_deleted=False, is_actived=True, user=self.user)

        create_rel = partial(Relation.objects.create, user=self.user,
                             subject_entity=original_ce, object_entity=entity1,
                            )
        create_rel(type=self.rtype1)
        create_rel(type=self.rtype3) #internal

        create_prop = partial(CremeProperty.objects.create, creme_entity=original_ce)
        create_prop(type=self.ptype01)
        create_prop(type=self.ptype02)

        clone_ce = original_ce.clone()
        self.assertIsNotNone(clone_ce.pk)
        self.assertNotEqual(original_ce.pk, clone_ce.pk)

        self.assertNotEqual(original_ce.created,  clone_ce.created)
        self.assertNotEqual(original_ce.modified, clone_ce.modified)

        self.assertEqual(original_ce.is_deleted,  clone_ce.is_deleted)
        self.assertEqual(original_ce.is_actived,  clone_ce.is_actived)
        self.assertEqual(original_ce.entity_type, clone_ce.entity_type)
        self.assertEqual(original_ce.user,        clone_ce.user)
        self.assertEqual(original_ce.header_filter_search_field, clone_ce.header_filter_search_field)

        self.assertSameRelationsNProperties(original_ce, clone_ce)
        self.assertFalse(clone_ce.relations.filter(type__is_internal=True))

    def test_clone02(self):
        "Clone regular fields"
        self._setUpClone()

        civility = Civility.objects.all()[0]
        language = Language.objects.all()[0]
        sasuke  = CremeEntity.objects.create(user=self.user)
        sakura  = CremeEntity.objects.create(user=self.user)

        image = self.create_image()

        naruto = Contact.objects.create(user=self.user, civility=civility,
                                        first_name=u'Naruto', last_name=u'Uzumaki',
                                        description=u"Ninja", birthday=now(),
                                        mobile=u"+81 0 0 0 00 01", email=u"naruto.uzumaki@konoha.jp",
                                        image=image,
                                       )
        naruto.language = [language]

        CremeProperty.objects.create(type=self.ptype01, creme_entity=naruto)

        create_rel = Relation.objects.create
        create_rel(user=self.user, type=self.rtype1, subject_entity=naruto, object_entity=sasuke)
        create_rel(user=self.user, type=self.rtype2, subject_entity=naruto, object_entity=sakura)

        count = Contact.objects.count()
        kage_bunshin = naruto.clone()
        self.assertEqual(count + 1, Contact.objects.count())

        self.assertNotEqual(kage_bunshin.pk, naruto.pk)
        self.assertSameRelationsNProperties(naruto, kage_bunshin)

        for attr in ['civility', 'first_name', 'last_name', 'description',
                     'birthday', 'mobile', 'email', 'image']:
            self.assertEqual(getattr(naruto, attr), getattr(kage_bunshin, attr))

        self.assertEqual(set(naruto.language.all()), set(kage_bunshin.language.all()))

    def test_clone03(self):
        create_cf = partial(CustomField.objects.create,
                            content_type=ContentType.objects.get_for_model(Organisation),
                           )
        cf_int        = create_cf(name='int',        field_type=CustomField.INT)
        cf_float      = create_cf(name='float',      field_type=CustomField.FLOAT)
        cf_bool       = create_cf(name='bool',       field_type=CustomField.BOOL)
        cf_str        = create_cf(name='str',        field_type=CustomField.STR)
        cf_date       = create_cf(name='date',       field_type=CustomField.DATETIME)
        cf_enum       = create_cf(name='enum',       field_type=CustomField.ENUM)
        cf_multi_enum = create_cf(name='multi_enum', field_type=CustomField.MULTI_ENUM)

        enum1 = CustomFieldEnumValue.objects.create(custom_field=cf_enum, value='Enum1')

        m_enum1 = CustomFieldEnumValue.objects.create(custom_field=cf_multi_enum, value='MEnum1')
        m_enum2 = CustomFieldEnumValue.objects.create(custom_field=cf_multi_enum, value='MEnum2')

        orga = Organisation.objects.create(name=u"Konoha", user=self.user)

        CustomFieldInteger.objects.create(custom_field=cf_int, entity=orga, value=50)
#        CustomFieldValue.save_values_for_entities(cf_int, [orga], 50)
        CustomFieldFloat.objects.create(custom_field=cf_float, entity=orga, value=Decimal("10.5"))
        CustomFieldBoolean.objects.create(custom_field=cf_bool, entity=orga, value=True)
        CustomFieldString.objects.create(custom_field=cf_str, entity=orga, value="kunai")
        CustomFieldDateTime.objects.create(custom_field=cf_date, entity=orga, value=now())
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

        self.assertTrue(get_cf_values(cf_multi_enum, orga).value.exists())
        self.assertEqual(set(get_cf_values(cf_multi_enum, orga).value.values_list('pk', flat=True)),
                         set(get_cf_values(cf_multi_enum, clone).value.values_list('pk', flat=True))
                        )

    def test_clone04(self):
        self._setUpClone()

        #ct_activity = ContentType.objects.get_for_model(Activity)
        act_type = ActivityType.objects.all()[0]
        activity1 = Activity.objects.create(user=self.user, type=act_type)
        activity2 = activity1.clone()
        self.assertNotEqual(activity1.pk, activity2.pk)

        for attr in ['user', 'title', 'start', 'end', 'description', 'minutes', 'type', 'is_all_day', 'status', 'busy']:
            self.assertEqual(getattr(activity1, attr), getattr(activity2, attr))

    def test_clone05(self):
        #ct_activity = ContentType.objects.get_for_model(Activity)
        #act_type = ActivityType.objects.all()[0]
        act_status = Status.objects.all()[0]#Import status as ActivityStatus ?
        rtype_participant = RelationType.objects.get(pk=REL_SUB_PART_2_ACTIVITY)

        activity1 = Activity.objects.create(user=self.user, type_id=ACTIVITYTYPE_MEETING, title='Meeting',
                                            start=now(), end=now(), #TODO: timedelta for end
                                            description='Desc', minutes='123', is_all_day=False,
                                            status=act_status, busy=True, place='Here',
                                           )
        contact1 = Contact.objects.create(user=self.user)
        contact2 = contact1.clone()

        create_rel = partial(Relation.objects.create, user=self.user, type=rtype_participant, object_entity=activity1)
        create_rel(subject_entity=contact1)
        create_rel(subject_entity=contact2)

        activity2 = activity1.clone().clone().clone().clone().clone().clone().clone()
        self.assertNotEqual(activity1.pk, activity2.pk)

        for attr in ['user', 'title', 'start', 'end', 'description', 'minutes', 'type', 'is_all_day', 'status', 'place']:
            self.assertEqual(getattr(activity1, attr), getattr(activity2, attr))

        self.assertNotEqual(activity1.busy, activity2.busy)
        self.assertSameRelationsNProperties(activity1, activity2)

    def test_clone06(self):
        image = self.create_image()
        image.categories = MediaCategory.objects.all()

        image2 = image.clone()
        self.assertNotEqual(image.pk, image2.pk)

        for attr in ['user', 'name', 'image', 'description']:
            self.assertEqual(getattr(image, attr), getattr(image2, attr))

        self.assertEqual(set(image.categories.values_list('pk', flat=True)),
                         set(image2.categories.values_list('pk', flat=True))
                        )

    def test_delete01(self):
        "Simple delete"
        ce = CremeEntity.objects.create(user=self.user)
        ce.delete()
        self.assertRaises(CremeEntity.DoesNotExist, CremeEntity.objects.get, id=ce.id)

    def test_delete02(self):
        "Can't delete entities linked by a relation"
        self._setUpClone()
        ce1 = CremeEntity.objects.create(user=self.user)
        ce2 = CremeEntity.objects.create(user=self.user)

        Relation.objects.create(user=self.user, type=self.rtype1, subject_entity=ce1, object_entity=ce2)

        self.assertRaises(ProtectedError, ce1.delete)
        self.assertRaises(ProtectedError, ce2.delete)

    def test_functionfields(self):
        with self.assertNoException():
            ff_mngr = CremeEntity.function_fields
            all_ff = list(ff_mngr)

        for funf in all_ff:
            self.assertIsInstance(funf, FunctionField)

            if funf.name == 'get_pretty_properties':
                pp_ff = funf
                break
        else:
            self.fail('No "get_pretty_properties" function field found')

        self.assertEqual(_(u'Properties'), unicode(pp_ff.verbose_name))
        self.assertFalse(pp_ff.has_filter)
        self.assertFalse(pp_ff.is_hidden)
        self.assertIsNone(pp_ff.choices)

    def test_prettypropertiesfield01(self):
        entity = CremeEntity.objects.create(user=self.user)

        pp_ff = CremeEntity.function_fields.get('get_pretty_properties')
        self.assertIsNotNone(pp_ff)
        self.assertIsInstance(pp_ff, FunctionField)

        ptype1 = CremePropertyType.create(str_pk='test-prop_awesome', text='Awesome')
        CremeProperty.objects.create(type=ptype1, creme_entity=entity)

        ptype2 = CremePropertyType.create(str_pk='test-prop_wonderful', text='Wonderful')
        CremeProperty.objects.create(type=ptype2, creme_entity=entity)

        with self.assertNumQueries(1):
            result = pp_ff(entity)

        self.assertIsInstance(result, FunctionFieldResult)
        self.assertIsInstance(result, FunctionFieldResultsList)
        self.assertEqual('<ul><li>Awesome</li><li>Wonderful</li></ul>', result.for_html())
        self.assertEqual('Awesome/Wonderful',                           result.for_csv())

    def test_prettypropertiesfield02(self): #prefetch with populate_entities()
        entity1 = CremeEntity.objects.create(user=self.user)
        entity2 = CremeEntity.objects.create(user=self.user)

        pp_ff = CremeEntity.function_fields.get('get_pretty_properties')

        ptype1 = CremePropertyType.create(str_pk='test-prop_awesome',   text='Awesome')
        ptype2 = CremePropertyType.create(str_pk='test-prop_wonderful', text='Wonderful')

        CremeProperty.objects.create(type=ptype1, creme_entity=entity1)
        CremeProperty.objects.create(type=ptype2, creme_entity=entity1)
        CremeProperty.objects.create(type=ptype2, creme_entity=entity2)

        pp_ff.populate_entities([entity1, entity2])

        with self.assertNumQueries(0):
            result1 = pp_ff(entity1)
            result2 = pp_ff(entity2)

        self.assertEqual('<ul><li>Awesome</li><li>Wonderful</li></ul>', result1.for_html())
        self.assertEqual('<ul><li>Wonderful</li></ul>',                 result2.for_html())
