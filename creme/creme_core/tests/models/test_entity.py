# -*- coding: utf-8 -*-

from decimal import Decimal
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db.models.deletion import ProtectedError
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.core.field_tags import FieldTag, InvalidFieldTag
from creme.creme_core.core.function_field import (
    FunctionField,
    FunctionFieldResultsList,
    function_field_registry,
)
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldBoolean,
    CustomFieldDateTime,
    CustomFieldEnum,
    CustomFieldEnumValue,
    CustomFieldFloat,
    CustomFieldInteger,
    CustomFieldMultiEnum,
    CustomFieldString,
    FakeCivility,
    FakeContact,
    FakeImage,
    FakeImageCategory,
    FakeOrganisation,
    FakeSector,
    Language,
    Relation,
    RelationType,
)

from ..base import CremeTestCase


class EntityTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_entity01(self):
        with self.assertNoException():
            entity = CremeEntity.objects.create(user=self.user)

        now_value = now()
        self.assertDatetimesAlmostEqual(now_value, entity.created)
        self.assertDatetimesAlmostEqual(now_value, entity.modified)

    def test_manager01(self):
        "Ordering NULL values as 'low'"
        # NB: we should not use NULL & '' values at the same time, because they are
        # separated by the ordering, but they are equal for the users.
        create_contact = partial(FakeContact.objects.create, user=self.user)
        c1 = create_contact(
            first_name='Naruto', last_name='Uzumaki',
            # email='n.uzumaki@konoha.jp',
            phone='445566',
        )
        c2 = create_contact(first_name='Sasuke', last_name='Uchiwa')
        c3 = create_contact(
            first_name='Sakura', last_name='Haruno',
            # email='',
            phone='',
        )
        c4 = create_contact(
            first_name='Kakashi', last_name='Hatake',
            # email='k.hatake@konoha.jp'
            phone='112233',
        )

        qs = FakeContact.objects.filter(pk__in=[c1.id, c2.id, c3.id, c4.id])
        expected = [c2, c3, c4, c1]
        self.assertListEqual(
            # expected, [*qs.order_by('email', 'last_name')],
            expected, [*qs.order_by('phone', 'last_name')],
        )
        self.assertListEqual(
            # [*reversed(expected)], [*qs.order_by('-email', 'last_name')],
            [*reversed(expected)], [*qs.order_by('-phone', 'last_name')],
        )

    def test_manager02(self):
        "Ordering NULL values as 'low' (FK)"
        create_sector = FakeSector.objects.create
        s1 = create_sector(title='Hatake')
        s2 = create_sector(title='Uzumaki')

        create_contact = partial(FakeContact.objects.create, user=self.user)
        c1 = create_contact(first_name='Naruto',  last_name='Uzumaki', sector=s2)
        c2 = create_contact(first_name='Sasuke',  last_name='Uchiwa')
        c3 = create_contact(first_name='Sakura',  last_name='Haruno')
        c4 = create_contact(first_name='Kakashi', last_name='Hatake', sector=s1)

        qs = FakeContact.objects.filter(pk__in=[c1.id, c2.id, c3.id, c4.id])
        expected = [c3, c2, c4, c1]
        self.assertListEqual(
            expected, [*qs.order_by('sector', 'last_name')]
        )
        self.assertListEqual(
            [*reversed(expected)], [*qs.order_by('-sector', '-last_name')]
        )

    def _build_rtypes_n_ptypes(self):
        create_rtype = RelationType.objects.smart_update_or_create
        self.rtype1, self.rtype2 = create_rtype(
            ('test-subject_loving', 'is loving'),
            ('test-object_loving',  'is loved by'),
        )
        self.rtype3, self.rtype4 = create_rtype(
            ('test-subject_hating', 'is hating'),
            ('test-object_hating',  'is hated by'),
            is_internal=True,
        )

        create_ptype = CremePropertyType.objects.smart_update_or_create
        self.ptype01 = create_ptype(str_pk='test-prop_foobar01', text='wears strange hats')
        self.ptype02 = create_ptype(str_pk='test-prop_foobar02', text='wears strange pants')

    def test_fieldtags_clonable(self):
        naruto = FakeContact.objects.create(
            user=self.user, first_name='Naruto', last_name='Uzumaki',
        )
        get_field = naruto._meta.get_field

        self.assertFalse(get_field('created').get_tag('clonable'))
        self.assertFalse(get_field('created').get_tag(FieldTag.CLONABLE))
        self.assertFalse(get_field('modified').get_tag(FieldTag.CLONABLE))

        field = get_field('first_name')
        self.assertTrue(field.get_tag(FieldTag.CLONABLE))
        self.assertRaises(InvalidFieldTag, field.get_tag, 'stuff')

        self.assertFalse(get_field('id').get_tag(FieldTag.CLONABLE))
        self.assertFalse(get_field('cremeentity_ptr').get_tag(FieldTag.CLONABLE))

        self.assertRaises(InvalidFieldTag, field.set_tags, stuff=True)

    def test_fieldtags_viewable(self):
        naruto = FakeContact.objects.create(
            user=self.user, first_name='Naruto', last_name='Uzumaki',
        )
        get_field = naruto._meta.get_field

        self.assertTrue(get_field('modified').get_tag('viewable'))
        self.assertTrue(get_field('modified').get_tag(FieldTag.VIEWABLE))
        self.assertTrue(get_field('first_name').get_tag(FieldTag.VIEWABLE))

        self.assertFalse(get_field('id').get_tag('viewable'))
        self.assertFalse(get_field('id').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('cremeentity_ptr').get_tag(FieldTag.VIEWABLE))

    def test_fieldtags_optional(self):
        naruto = FakeContact.objects.create(
            user=self.user, first_name='Naruto', last_name='Uzumaki',
        )
        get_field = naruto._meta.get_field

        self.assertFalse(get_field('modified').get_tag('optional'))
        self.assertFalse(get_field('modified').get_tag(FieldTag.OPTIONAL))
        self.assertFalse(get_field('last_name').get_tag(FieldTag.OPTIONAL))

    def test_fieldtags_user(self):
        get_field = self.user._meta.get_field

        self.assertTrue(get_field('username').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('id').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('password').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('is_active').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('is_superuser').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('is_staff').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('last_login').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('date_joined').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('role').get_tag(FieldTag.VIEWABLE))

    def test_clone01(self):
        user = self.user
        self._build_rtypes_n_ptypes()

        created = modified = now()
        entity1 = CremeEntity.objects.create(user=user)
        original_ce = CremeEntity.objects.create(
            created=created, modified=modified, is_deleted=False, user=user,
        )

        create_rel = partial(
            Relation.objects.create, user=user,
            subject_entity=original_ce, object_entity=entity1,
        )
        create_rel(type=self.rtype1)
        create_rel(type=self.rtype3)  # Internal

        create_prop = partial(CremeProperty.objects.create, creme_entity=original_ce)
        create_prop(type=self.ptype01)
        create_prop(type=self.ptype02)

        clone_ce = original_ce.clone()
        self.assertIsNotNone(clone_ce.pk)
        self.assertNotEqual(original_ce.pk, clone_ce.pk)

        self.assertNotEqual(original_ce.created,  clone_ce.created)
        self.assertNotEqual(original_ce.modified, clone_ce.modified)

        self.assertEqual(original_ce.is_deleted,  clone_ce.is_deleted)
        self.assertEqual(original_ce.entity_type, clone_ce.entity_type)
        self.assertEqual(original_ce.user,        clone_ce.user)
        self.assertEqual(
            original_ce.header_filter_search_field,
            clone_ce.header_filter_search_field,
        )

        self.assertSameRelationsNProperties(original_ce, clone_ce)
        self.assertFalse(clone_ce.relations.filter(type__is_internal=True))

    def test_clone02(self):
        "Clone regular fields"
        user = self.user
        self._build_rtypes_n_ptypes()

        civility = FakeCivility.objects.all()[0]
        language = Language.objects.all()[0]
        sasuke  = CremeEntity.objects.create(user=self.user)
        sakura  = CremeEntity.objects.create(user=self.user)

        image = FakeImage.objects.create(user=user, name='Naruto selfie')

        naruto = FakeContact.objects.create(
            user=user, civility=civility,
            first_name='Naruto', last_name='Uzumaki',
            description='Ninja', birthday=now(),
            phone='123456', mobile='+81 0 0 0 00 01',
            email='naruto.uzumaki@konoha.jp',
            image=image,
        )
        naruto.language = [language]

        CremeProperty.objects.create(type=self.ptype01, creme_entity=naruto)

        create_rel = partial(Relation.objects.create, user=self.user, subject_entity=naruto)
        create_rel(type=self.rtype1, object_entity=sasuke)
        create_rel(type=self.rtype2, object_entity=sakura)

        count = FakeContact.objects.count()
        kage_bunshin = naruto.clone()
        self.assertEqual(count + 1, FakeContact.objects.count())

        self.assertNotEqual(kage_bunshin.pk, naruto.pk)
        self.assertSameRelationsNProperties(naruto, kage_bunshin)

        for attr in ['civility', 'first_name', 'last_name', 'description',
                     'birthday', 'image']:
            self.assertEqual(getattr(naruto, attr), getattr(kage_bunshin, attr))

        self.assertSetEqual({*naruto.languages.all()}, {*kage_bunshin.languages.all()})

    def test_clone03(self):
        create_cf = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
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

        orga = FakeOrganisation.objects.create(name='Konoha', user=self.user)

        CustomFieldInteger.objects.create(custom_field=cf_int, entity=orga, value=50)
        CustomFieldFloat.objects.create(custom_field=cf_float, entity=orga, value=Decimal('10.5'))
        CustomFieldBoolean.objects.create(custom_field=cf_bool, entity=orga, value=True)
        CustomFieldString.objects.create(custom_field=cf_str, entity=orga, value='kunai')
        CustomFieldDateTime.objects.create(custom_field=cf_date, entity=orga, value=now())
        CustomFieldEnum.objects.create(custom_field=cf_enum, entity=orga, value=enum1)
        CustomFieldMultiEnum(
            custom_field=cf_multi_enum, entity=orga,
        ).set_value_n_save([m_enum1, m_enum2])

        clone = orga.clone()

        def get_cf_values(cf, entity):
            return cf.value_class.objects.get(custom_field=cf, entity=entity)

        self.assertEqual(get_cf_values(cf_int,   orga).value, get_cf_values(cf_int,   clone).value)
        self.assertEqual(get_cf_values(cf_float, orga).value, get_cf_values(cf_float, clone).value)
        self.assertEqual(get_cf_values(cf_bool,  orga).value, get_cf_values(cf_bool,  clone).value)
        self.assertEqual(get_cf_values(cf_str,   orga).value, get_cf_values(cf_str,   clone).value)
        self.assertEqual(get_cf_values(cf_date,  orga).value, get_cf_values(cf_date,  clone).value)

        self.assertEqual(get_cf_values(cf_enum, orga).value, get_cf_values(cf_enum, clone).value)

        self.assertTrue(get_cf_values(cf_multi_enum, orga).value.exists())
        self.assertSetEqual(
            {*get_cf_values(cf_multi_enum, orga).value.values_list('pk', flat=True)},
            {*get_cf_values(cf_multi_enum, clone).value.values_list('pk', flat=True)},
        )

    def test_clone04(self):
        "ManyToMany"
        image1 = FakeImage.objects.create(user=self.user, name='Konoha by night')
        categories = [*FakeImageCategory.objects.all()]
        self.assertTrue(categories)
        image1.categories.set(categories)

        image2 = image1.clone()
        self.assertNotEqual(image1.pk, image2.pk)

        for attr in ('user', 'name'):
            self.assertEqual(getattr(image1, attr), getattr(image2, attr))

        self.assertSetEqual(
            {*image1.categories.values_list('pk', flat=True)},
            {*image2.categories.values_list('pk', flat=True)}
        )

    def test_delete01(self):
        "Simple delete"
        ce = CremeEntity.objects.create(user=self.user)
        ce.delete()
        self.assertRaises(CremeEntity.DoesNotExist, CremeEntity.objects.get, id=ce.id)

    def test_delete02(self):
        "Can delete entities linked by a not internal relation"
        self._build_rtypes_n_ptypes()
        user = self.user
        ce1 = CremeEntity.objects.create(user=user)
        ce2 = CremeEntity.objects.create(user=user)

        Relation.objects.create(user=user, type=self.rtype1, subject_entity=ce1, object_entity=ce2)

        with self.assertNoException():
            ce1.delete()

        self.assertDoesNotExist(ce1)
        self.assertStillExists(ce2)

    def test_delete03(self):
        "Can't delete entities linked by an internal relation"
        self._build_rtypes_n_ptypes()
        user = self.user
        ce1 = CremeEntity.objects.create(user=user)
        ce2 = CremeEntity.objects.create(user=user)

        Relation.objects.create(
            user=user, type=self.rtype3, subject_entity=ce1, object_entity=ce2,
        )

        self.assertRaises(ProtectedError, ce1.delete)
        self.assertRaises(ProtectedError, ce2.delete)

    def test_properties_functionfield01(self):
        user = self.user
        entity = CremeEntity.objects.create(user=user)

        pp_ff = function_field_registry.get(CremeEntity, 'get_pretty_properties')
        self.assertIsNotNone(pp_ff)
        self.assertIsInstance(pp_ff, FunctionField)

        self.assertEqual(_('Properties'), str(pp_ff.verbose_name))
        self.assertFalse(pp_ff.is_hidden)

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_awesome', text='Awesome')
        CremeProperty.objects.create(type=ptype1, creme_entity=entity)

        ptype2 = create_ptype(str_pk='test-prop_wonderful', text='Wonderful')
        CremeProperty.objects.create(type=ptype2, creme_entity=entity)

        with self.assertNumQueries(1):
            result = pp_ff(entity, user)

        self.assertIsInstance(result, FunctionFieldResultsList)
        self.assertEqual(
            f'<ul>'
            f'<li><a href="{ptype1.get_absolute_url()}">{ptype1.text}</a>'
            f'</li><li><a href="{ptype2.get_absolute_url()}">{ptype2.text}</a></li>'
            f'</ul>',
            result.for_html(),
        )
        self.assertEqual('Awesome/Wonderful', result.for_csv())

    def test_properties_functionfield02(self):  # Prefetch with populate_entities()
        user = self.user
        create_entity = CremeEntity.objects.create
        entity1 = create_entity(user=user)
        entity2 = create_entity(user=user)

        pp_ff = function_field_registry.get(CremeEntity, 'get_pretty_properties')

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_awesome',   text='Awesome')
        ptype2 = create_ptype(str_pk='test-prop_wonderful', text='Wonderful')

        create_prop = CremeProperty.objects.create
        create_prop(type=ptype1, creme_entity=entity1)
        create_prop(type=ptype2, creme_entity=entity1)
        create_prop(type=ptype2, creme_entity=entity2)

        pp_ff.populate_entities([entity1, entity2], user)

        with self.assertNumQueries(0):
            result1 = pp_ff(entity1, user)
            result2 = pp_ff(entity2, user)

        self.assertHTMLEqual(
            f'<ul>'
            f'<li><a href="{ptype1.get_absolute_url()}">{ptype1.text}</a></li>'
            f'<li><a href="{ptype2.get_absolute_url()}">{ptype2.text}</a></li>'
            f'</ul>',
            result1.for_html(),
        )
        self.assertHTMLEqual(
            f'<ul><li><a href="{ptype2.get_absolute_url()}">{ptype2.text}</a></li></ul>',
            result2.for_html(),
        )

    def test_customfield_value(self):
        create_field = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        field_A = create_field(name='A', field_type=CustomField.INT)
        field_B = create_field(name='B', field_type=CustomField.INT)
        field_C = create_field(name='C', field_type=CustomField.INT)

        orga = FakeOrganisation.objects.create(name='Konoha', user=self.user)

        create_cf = CustomFieldInteger.objects.create
        value_A = create_cf(custom_field=field_A, entity=orga, value=50)
        value_B = create_cf(custom_field=field_B, entity=orga, value=100)

        # Empty cache
        self.assertDictEqual(orga._cvalues_map, {})

        self.assertEqual(value_A, orga.get_custom_value(field_A))
        self.assertDictEqual(orga._cvalues_map, {field_A.pk: value_A})

        self.assertEqual(value_B, orga.get_custom_value(field_B))
        self.assertDictEqual(
            {field_A.pk: value_A, field_B.pk: value_B},
            orga._cvalues_map,
        )

        self.assertIsNone(orga.get_custom_value(field_C))
        self.assertDictEqual(
            {
                field_A.pk: value_A,
                field_B.pk: value_B,
                field_C.pk: None,
            },
            orga._cvalues_map,
        )
