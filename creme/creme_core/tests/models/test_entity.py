from datetime import timedelta
# from decimal import Decimal
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db.models.deletion import ProtectedError
from django.test import skipUnlessDBFeature
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.core.field_tags import FieldTag, InvalidFieldTag
from creme.creme_core.core.function_field import (
    FunctionField,
    FunctionFieldResultsList,
    function_field_registry,
)
from creme.creme_core.gui.view_tag import ViewTag
# from creme.creme_core.models import (
#     CustomFieldBoolean,
#     CustomFieldDateTime,
#     CustomFieldEnum,
#     CustomFieldEnumValue,
#     CustomFieldFloat,
#     CustomFieldMultiEnum,
#     CustomFieldString,
#     FakeCivility,
#     FakeCountry,
#     FakeImage,
#     FakeImageCategory,
#     Language,
# )
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    CremeUser,
    CustomField,
    CustomFieldInteger,
    FakeContact,
    FakeOrganisation,
    FakeSector,
    Relation,
    RelationType,
)

from ..base import CremeTestCase


class EntityTestCase(CremeTestCase):
    def test_entity01(self):
        user = self.get_root_user()

        with self.assertNoException():
            entity = CremeEntity.objects.create(user=user)

        now_value = now()
        self.assertDatetimesAlmostEqual(now_value, entity.created)
        self.assertDatetimesAlmostEqual(now_value, entity.modified)

    def test_entity_save01(self):
        "No update_fields."
        user = self.get_root_user()

        orga = FakeOrganisation.objects.create(user=user, name='Nerv')
        FakeOrganisation.objects.filter(id=orga.id).update(
            modified=orga.modified - timedelta(days=10),
        )

        orga.description = description = 'whatever'
        orga.name += ' inc.'
        orga.save()  # Should update 'modified' & 'header_filter_search_field'

        orga.refresh_from_db()
        self.assertDatetimesAlmostEqual(now(), orga.modified)
        self.assertEqual('Nerv inc.', orga.header_filter_search_field)
        self.assertEqual(description, orga.description)

    def test_entity_save02(self):
        "With update_fields."
        user = self.get_root_user()

        orga = FakeOrganisation.objects.create(user=user, name='Nerv')
        FakeOrganisation.objects.filter(id=orga.id).update(
            modified=orga.modified - timedelta(days=10),
        )

        orga.description = 'whatever'
        orga.name += ' inc.'
        # Should update 'modified' & 'header_filter_search_field'
        orga.save(update_fields=['name'])

        orga.refresh_from_db()
        self.assertDatetimesAlmostEqual(now(), orga.modified)
        self.assertEqual('Nerv inc.', orga.header_filter_search_field)
        self.assertFalse(orga.description)

    def test_entity_extra_data01(self):
        "Single tag."
        user = self.get_root_user()

        def create_orga(name, tag=None):
            orga = FakeOrganisation(user=user, name=name)
            if tag:
                orga.extra_data['tag'] = tag
            orga.save()

            return orga

        orga1 = create_orga(name='Nerv', tag=1)
        orga1.refresh_from_db()
        self.assertDictEqual({'tag': 1}, orga1.extra_data)

        orga2 = create_orga(name='Seele', tag=2)
        self.assertDictEqual({'tag': 2}, orga2.extra_data)

        orga3 = create_orga(name='Acme', tag=1)

        orga4 = create_orga(name='Foobar')
        self.assertIsNone(orga4.extra_data.get('tag'))

        self.assertCountEqual(
            [orga1, orga3],
            FakeOrganisation.objects.filter(extra_data__tag=1),
        )

        create_orga(name='Foo', tag=3)
        self.assertCountEqual(
            [orga1, orga2, orga3],
            FakeOrganisation.objects.filter(extra_data__tag__in=[1, 2]),
        )

    @skipUnlessDBFeature('supports_json_field_contains')
    def test_entity_extra_data02(self):
        "Multi tags."
        user = self.get_root_user()

        def create_orga(name, *tags):
            orga = FakeOrganisation(user=user, name=name)
            if tags:
                orga.extra_data['tags'] = [*tags]
            orga.save()

            return orga

        orga1 = create_orga('Nerv', 1)
        orga1.refresh_from_db()
        self.assertDictEqual({'tags': [1]}, orga1.extra_data)

        orga2 = create_orga('Seele', 2)
        self.assertDictEqual({'tags': [2]}, orga2.extra_data)

        orga3 = create_orga('Acme', 1)

        orga4 = create_orga('Foobar')
        self.assertIsNone(orga4.extra_data.get('tags'))

        self.assertCountEqual(
            [orga1, orga3],
            FakeOrganisation.objects.filter(extra_data__tags__contains=1),
        )

    def test_manager01(self):
        "Ordering NULL values as 'low'."
        user = self.get_root_user()

        # NB: we should not use NULL & '' values at the same time, because they are
        # separated by the ordering, but they are equal for the users.
        create_contact = partial(FakeContact.objects.create, user=user)
        c1 = create_contact(
            first_name='Naruto', last_name='Uzumaki', phone='445566',
        )
        c2 = create_contact(first_name='Sasuke', last_name='Uchiwa')
        c3 = create_contact(
            first_name='Sakura', last_name='Haruno', phone='',
        )
        c4 = create_contact(
            first_name='Kakashi', last_name='Hatake', phone='112233',
        )

        qs = FakeContact.objects.filter(pk__in=[c1.id, c2.id, c3.id, c4.id])
        expected = [c2, c3, c4, c1]
        self.assertListEqual(
            expected, [*qs.order_by('phone', 'last_name')],
        )
        self.assertListEqual(
            [*reversed(expected)], [*qs.order_by('-phone', 'last_name')],
        )

    def test_manager02(self):
        "Ordering NULL values as 'low' (FK)."
        user = self.get_root_user()

        create_sector = FakeSector.objects.create
        s1 = create_sector(title='Hatake')
        s2 = create_sector(title='Uzumaki')

        create_contact = partial(FakeContact.objects.create, user=user)
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
        self.rtype1 = RelationType.objects.builder(
            id='test-subject_loving', predicate='is loving',
        ).symmetric(id='test-object_loving', predicate='is loved by').get_or_create()[0]
        self.rtype2 = self.rtype1.symmetric_type

        self.rtype3 = RelationType.objects.builder(
            id='test-subject_hating', predicate='is hating',
            is_internal=True,
        ).symmetric(id='test-object_hating', predicate='is hated by').get_or_create()[0]
        self.rtype4 = self.rtype3.symmetric_type

        create_ptype = CremePropertyType.objects.create
        self.ptype01 = create_ptype(text='wears strange hats')
        self.ptype02 = create_ptype(text='wears strange pants')

    def test_fieldtags_clonable(self):
        user = self.get_root_user()
        naruto = FakeContact.objects.create(
            user=user, first_name='Naruto', last_name='Uzumaki',
        )
        get_field = naruto._meta.get_field

        self.assertFalse(get_field('created').get_tag('clonable'))
        self.assertFalse(get_field('created').get_tag(FieldTag.CLONABLE))
        self.assertFalse(get_field('modified').get_tag(FieldTag.CLONABLE))

        field = get_field('first_name')
        self.assertTrue(field.get_tag(FieldTag.CLONABLE))
        self.assertRaises(InvalidFieldTag, field.get_tag, 'stuff')
        self.assertRaises(InvalidFieldTag, field.set_tags, stuff=True)

        self.assertFalse(get_field('id').get_tag(FieldTag.CLONABLE))
        self.assertFalse(get_field('cremeentity_ptr').get_tag(FieldTag.CLONABLE))

        self.assertTrue(get_field('languages').get_tag(FieldTag.CLONABLE))
        self.assertFalse(get_field('preferred_countries').get_tag(FieldTag.CLONABLE))

    def test_fieldtags_viewable(self):
        user = self.get_root_user()
        naruto = FakeContact.objects.create(
            user=user, first_name='Naruto', last_name='Uzumaki',
        )
        get_field = naruto._meta.get_field

        self.assertTrue(get_field('modified').get_tag('viewable'))
        self.assertTrue(get_field('modified').get_tag(FieldTag.VIEWABLE))
        self.assertTrue(get_field('first_name').get_tag(FieldTag.VIEWABLE))

        self.assertFalse(get_field('id').get_tag('viewable'))
        self.assertFalse(get_field('id').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('cremeentity_ptr').get_tag(FieldTag.VIEWABLE))

    def test_fieldtags_optional(self):
        user = self.get_root_user()
        naruto = FakeContact.objects.create(
            user=user, first_name='Naruto', last_name='Uzumaki',
        )
        get_field = naruto._meta.get_field

        self.assertFalse(get_field('modified').get_tag('optional'))
        self.assertFalse(get_field('modified').get_tag(FieldTag.OPTIONAL))
        self.assertFalse(get_field('last_name').get_tag(FieldTag.OPTIONAL))

    def test_fieldtags_user(self):
        get_field = CremeUser._meta.get_field

        self.assertTrue(get_field('username').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('id').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('password').get_tag(FieldTag.VIEWABLE))
        self.assertTrue(get_field('is_active').get_tag(FieldTag.VIEWABLE))
        self.assertTrue(get_field('is_superuser').get_tag(FieldTag.VIEWABLE))
        self.assertFalse(get_field('is_staff').get_tag(FieldTag.VIEWABLE))
        self.assertTrue(get_field('last_login').get_tag(FieldTag.VIEWABLE))
        self.assertTrue(get_field('date_joined').get_tag(FieldTag.VIEWABLE))
        self.assertTrue(get_field('role').get_tag(FieldTag.VIEWABLE))

    # def test_clone01(self):  # DEPRECATED
    #     user = self.get_root_user()
    #     self._build_rtypes_n_ptypes()
    #
    #     created = modified = now()
    #     entity1 = CremeEntity.objects.create(user=user)
    #     original_ce = CremeEntity.objects.create(
    #         created=created, modified=modified, is_deleted=False, user=user,
    #     )
    #
    #     create_rel = partial(
    #         Relation.objects.create, user=user,
    #         subject_entity=original_ce, object_entity=entity1,
    #     )
    #     create_rel(type=self.rtype1)
    #     create_rel(type=self.rtype3)  # Internal
    #
    #     create_prop = partial(CremeProperty.objects.create, creme_entity=original_ce)
    #     create_prop(type=self.ptype01)
    #     create_prop(type=self.ptype02)
    #
    #     clone_ce = original_ce.clone()
    #     self.assertIsNotNone(clone_ce.pk)
    #     self.assertNotEqual(original_ce.pk, clone_ce.pk)
    #
    #     self.assertNotEqual(original_ce.created,  clone_ce.created)
    #     self.assertNotEqual(original_ce.modified, clone_ce.modified)
    #
    #     self.assertEqual(original_ce.is_deleted,  clone_ce.is_deleted)
    #     self.assertEqual(original_ce.entity_type, clone_ce.entity_type)
    #     self.assertEqual(original_ce.user,        clone_ce.user)
    #     self.assertEqual(
    #         original_ce.header_filter_search_field,
    #         clone_ce.header_filter_search_field,
    #     )
    #
    #     self.assertSameRelationsNProperties(original_ce, clone_ce)
    #     self.assertFalse(clone_ce.relations.filter(type__is_internal=True))
    #
    # def test_clone02(self):  # DEPRECATED
    #     "Clone regular fields."
    #     user = self.get_root_user()
    #     self._build_rtypes_n_ptypes()
    #
    #     civility = FakeCivility.objects.all()[0]
    #     language = Language.objects.all()[0]
    #     sasuke  = CremeEntity.objects.create(user=user)
    #     sakura  = CremeEntity.objects.create(user=user)
    #
    #     image = FakeImage.objects.create(user=user, name='Naruto selfie')
    #     create_country = FakeCountry.objects.create
    #     countries = [
    #         create_country(name='Land of Fire'),
    #         create_country(name='Land of Wind'),
    #     ]
    #     naruto = FakeContact.objects.create(
    #         user=user, civility=civility,
    #         first_name='Naruto', last_name='Uzumaki',
    #         description='Ninja', birthday=now(),
    #         phone='123456', mobile='+81 0 0 0 00 01',
    #         email='naruto.uzumaki@konoha.jp',
    #         image=image,
    #     )
    #     naruto.languages.add(language)
    #     naruto.preferred_countries.set(countries)
    #
    #     CremeProperty.objects.create(type=self.ptype01, creme_entity=naruto)
    #
    #     create_rel = partial(Relation.objects.create, user=user, subject_entity=naruto)
    #     create_rel(type=self.rtype1, object_entity=sasuke)
    #     create_rel(type=self.rtype2, object_entity=sakura)
    #
    #     count = FakeContact.objects.count()
    #     kage_bunshin = naruto.clone()
    #     self.assertEqual(count + 1, FakeContact.objects.count())
    #
    #     self.assertNotEqual(kage_bunshin.pk, naruto.pk)
    #     self.assertSameRelationsNProperties(naruto, kage_bunshin)
    #
    #     for attr in ['civility', 'first_name', 'last_name', 'description',
    #                  'birthday', 'image']:
    #         self.assertEqual(getattr(naruto, attr), getattr(kage_bunshin, attr))
    #
    #     self.assertCountEqual([language], kage_bunshin.languages.all())
    #     self.assertFalse(kage_bunshin.preferred_countries.all())  # Not clonable
    #
    # def test_clone03(self):  # DEPRECATED
    #     user = self.get_root_user()
    #
    #     create_cf = partial(
    #         CustomField.objects.create,
    #         content_type=ContentType.objects.get_for_model(FakeOrganisation),
    #     )
    #     cf_int        = create_cf(name='int',        field_type=CustomField.INT)
    #     cf_float      = create_cf(name='float',      field_type=CustomField.FLOAT)
    #     cf_bool       = create_cf(name='bool',       field_type=CustomField.BOOL)
    #     cf_str        = create_cf(name='str',        field_type=CustomField.STR)
    #     cf_date       = create_cf(name='date',       field_type=CustomField.DATETIME)
    #     cf_enum       = create_cf(name='enum',       field_type=CustomField.ENUM)
    #     cf_multi_enum = create_cf(name='multi_enum', field_type=CustomField.MULTI_ENUM)
    #
    #     enum1 = CustomFieldEnumValue.objects.create(custom_field=cf_enum, value='Enum1')
    #
    #     m_enum1 = CustomFieldEnumValue.objects.create(custom_field=cf_multi_enum, value='MEnum1')
    #     m_enum2 = CustomFieldEnumValue.objects.create(custom_field=cf_multi_enum, value='MEnum2')
    #
    #     orga = FakeOrganisation.objects.create(name='Konoha', user=user)
    #
    #     CustomFieldInteger.objects.create(custom_field=cf_int, entity=orga, value=50)
    #     CustomFieldFloat.objects.create(
    #       custom_field=cf_float, entity=orga, value=Decimal('10.5'))
    #     CustomFieldBoolean.objects.create(custom_field=cf_bool, entity=orga, value=True)
    #     CustomFieldString.objects.create(custom_field=cf_str, entity=orga, value='kunai')
    #     CustomFieldDateTime.objects.create(custom_field=cf_date, entity=orga, value=now())
    #     CustomFieldEnum.objects.create(custom_field=cf_enum, entity=orga, value=enum1)
    #     CustomFieldMultiEnum(
    #         custom_field=cf_multi_enum, entity=orga,
    #     ).set_value_n_save([m_enum1, m_enum2])
    #
    #     clone = orga.clone()
    #
    #     def get_cf_values(cf, entity):
    #         return cf.value_class.objects.get(custom_field=cf, entity=entity)
    #
    #     self.assertEqual(get_cf_values(cf_int,   orga).value,
    #      get_cf_values(cf_int,   clone).value)
    #     self.assertEqual(get_cf_values(cf_float, orga).value,
    #      get_cf_values(cf_float, clone).value)
    #     self.assertEqual(get_cf_values(cf_bool,  orga).value,
    #      get_cf_values(cf_bool,  clone).value)
    #     self.assertEqual(get_cf_values(cf_str,   orga).value,
    #      get_cf_values(cf_str,   clone).value)
    #     self.assertEqual(get_cf_values(cf_date,  orga).value,
    #      get_cf_values(cf_date,  clone).value)
    #
    #     self.assertEqual(get_cf_values(cf_enum, orga).value, get_cf_values(cf_enum, clone).value)
    #
    #     self.assertTrue(get_cf_values(cf_multi_enum, orga).value.exists())
    #     self.assertSetEqual(
    #         {*get_cf_values(cf_multi_enum, orga).value.values_list('pk', flat=True)},
    #         {*get_cf_values(cf_multi_enum, clone).value.values_list('pk', flat=True)},
    #     )
    #
    # def test_clone04(self):  # DEPRECATED
    #     "ManyToMany"
    #     user = self.get_root_user()
    #
    #     image1 = FakeImage.objects.create(user=user, name='Konoha by night')
    #     categories = [*FakeImageCategory.objects.all()]
    #     self.assertTrue(categories)
    #     image1.categories.set(categories)
    #
    #     image2 = image1.clone()
    #     self.assertNotEqual(image1.pk, image2.pk)
    #
    #     for attr in ('user', 'name'):
    #         self.assertEqual(getattr(image1, attr), getattr(image2, attr))
    #
    #     self.assertSetEqual(
    #         {*image1.categories.values_list('pk', flat=True)},
    #         {*image2.categories.values_list('pk', flat=True)},
    #     )

    def test_delete01(self):
        "Simple delete."
        user = self.get_root_user()

        ce = CremeEntity.objects.create(user=user)
        ce.delete()
        self.assertRaises(CremeEntity.DoesNotExist, CremeEntity.objects.get, id=ce.id)

    def test_delete02(self):
        "Can delete entities linked by a not internal relation"
        user = self.get_root_user()
        self._build_rtypes_n_ptypes()
        ce1 = CremeEntity.objects.create(user=user)
        ce2 = CremeEntity.objects.create(user=user)

        Relation.objects.create(user=user, type=self.rtype1, subject_entity=ce1, object_entity=ce2)

        with self.assertNoException():
            ce1.delete()

        self.assertDoesNotExist(ce1)
        self.assertStillExists(ce2)

    def test_delete03(self):
        "Can't delete entities linked by an internal relation"
        user = self.get_root_user()
        self._build_rtypes_n_ptypes()
        ce1 = CremeEntity.objects.create(user=user)
        ce2 = CremeEntity.objects.create(user=user)

        Relation.objects.create(
            user=user, type=self.rtype3, subject_entity=ce1, object_entity=ce2,
        )

        self.assertRaises(ProtectedError, ce1.delete)
        self.assertRaises(ProtectedError, ce2.delete)

    def test_properties_functionfield01(self):
        user = self.get_root_user()
        entity = CremeEntity.objects.create(user=user)

        pp_ff = function_field_registry.get(CremeEntity, 'get_pretty_properties')
        self.assertIsNotNone(pp_ff)
        self.assertIsInstance(pp_ff, FunctionField)

        self.assertEqual(_('Properties'), str(pp_ff.verbose_name))
        self.assertFalse(pp_ff.is_hidden)

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Awesome')
        CremeProperty.objects.create(type=ptype1, creme_entity=entity)

        ptype2 = create_ptype(text='Wonderful')
        CremeProperty.objects.create(type=ptype2, creme_entity=entity)

        with self.assertNumQueries(1):
            result = pp_ff(entity, user)

        self.assertIsInstance(result, FunctionFieldResultsList)
        self.assertHTMLEqual(
            f'<ul class="limited-list">'
            f' <li><a href="{ptype1.get_absolute_url()}">{ptype1.text}</a></li>'
            f' <li><a href="{ptype2.get_absolute_url()}">{ptype2.text}</a></li>'
            f'</ul>',
            result.render(ViewTag.HTML_LIST),
        )
        self.assertEqual('Awesome/Wonderful', result.render(ViewTag.TEXT_PLAIN))

    def test_properties_functionfield02(self):  # Prefetch with populate_entities()
        user = self.get_root_user()
        create_entity = CremeEntity.objects.create
        entity1 = create_entity(user=user)
        entity2 = create_entity(user=user)

        pp_ff = function_field_registry.get(CremeEntity, 'get_pretty_properties')

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Awesome')
        ptype2 = create_ptype(text='Wonderful')

        create_prop = CremeProperty.objects.create
        create_prop(type=ptype1, creme_entity=entity1)
        create_prop(type=ptype2, creme_entity=entity1)
        create_prop(type=ptype2, creme_entity=entity2)

        pp_ff.populate_entities([entity1, entity2], user)

        with self.assertNumQueries(0):
            result1 = pp_ff(entity1, user)
            result2 = pp_ff(entity2, user)

        self.assertHTMLEqual(
            # f'<ul>'
            f'<ul class="limited-list">'
            f' <li><a href="{ptype1.get_absolute_url()}">{ptype1.text}</a></li>'
            f' <li><a href="{ptype2.get_absolute_url()}">{ptype2.text}</a></li>'
            f'</ul>',
            result1.render(ViewTag.HTML_LIST),
        )
        self.assertHTMLEqual(
            f'<a href="{ptype2.get_absolute_url()}">{ptype2.text}</a>',
            result2.render(ViewTag.HTML_LIST),
        )

    def test_customfield_value(self):
        user = self.get_root_user()

        create_field = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeOrganisation),
        )
        field_A = create_field(name='A', field_type=CustomField.INT)
        field_B = create_field(name='B', field_type=CustomField.INT)
        field_C = create_field(name='C', field_type=CustomField.INT)

        orga = FakeOrganisation.objects.create(name='Konoha', user=user)

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

    def test_portable_key(self):
        orga = FakeOrganisation.objects.create(name='Konoha', user=self.get_root_user())

        with self.assertNoException():
            key = orga.portable_key()
        self.assertIsInstance(key, str)
        self.assertUUIDEqual(orga.uuid, key)

        # ---
        with self.assertNoException():
            got_orga = FakeOrganisation.objects.get_by_portable_key(key)
        self.assertEqual(orga, got_orga)
