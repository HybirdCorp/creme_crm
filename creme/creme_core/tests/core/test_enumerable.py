from functools import partial
from unittest.case import skipIf

from django.core.exceptions import FieldDoesNotExist
from django.db import connection, models
from django.utils.translation import gettext as _

from creme.creme_core import enumerators
from creme.creme_core.core.enumerable import (
    EnumerableRegistry,
    Enumerator,
    QSEnumerator,
    enumerable_registry,
    get_enum_search_fields,
)
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.models import (
    CremeModel,
    FakeCivility,
    FakeContact,
    FakeImage,
    FakeImageCategory,
    FakeOrganisation,
    FakeReport,
    FakeTodo,
    Language,
    MinionModel,
)
from creme.creme_core.models.fields import (
    CTypeForeignKey,
    EntityCTypeForeignKey,
)

from ..base import CremeTestCase


class GetEnumSearchFieldsTestCase(CremeTestCase):
    def test_get_enum_search_fields(self):
        class FakeRelatedSearchFields(CremeModel):
            _search_fields = ('field_a', 'field_b')

            title = models.CharField('title', max_length=100)
            help = models.CharField('help', max_length=100)

        class FakeRelatedFirstCharField(CremeModel):
            title = models.CharField('title', max_length=100)
            help = models.CharField('help', max_length=100)

        class FakeRelatedFirstVisibleCharField(CremeModel):
            title = models.CharField('title', max_length=100).set_tags(viewable=False)
            help = models.CharField('help', max_length=100)

        class FakeRelatedNoCharField(CremeModel):
            title = models.CharField('title', max_length=100).set_tags(viewable=False)

        class FakeModel(CremeModel):
            searchfields = models.ForeignKey(
                FakeRelatedSearchFields, verbose_name=_('Related'),
                blank=True, null=True, related_name='fakes',
                on_delete=models.CASCADE,
            )

            first_charfield = models.ForeignKey(
                FakeRelatedFirstCharField, verbose_name=_('Related'),
                blank=True, null=True, related_name='fakes',
                on_delete=models.CASCADE,
            )

            visible_charfield = models.ForeignKey(
                FakeRelatedFirstVisibleCharField, verbose_name=_('Related'),
                blank=True, null=True, related_name='fakes',
                on_delete=models.CASCADE,
            )

            no_charfield = models.ForeignKey(
                FakeRelatedNoCharField, verbose_name=_('Related'),
                blank=True, null=True, related_name='fakes',
                on_delete=models.CASCADE,
            )

        self.assertListEqual(
            ['field_a', 'field_b'],
            [*get_enum_search_fields(FakeModel._meta.get_field('searchfields'))],
        )

        self.assertListEqual(
            ['title'],
            [*get_enum_search_fields(FakeModel._meta.get_field('first_charfield'))],
        )

        self.assertListEqual(
            ['help'],
            [*get_enum_search_fields(FakeModel._meta.get_field('visible_charfield'))],
        )

        self.assertListEqual(
            [],
            [*get_enum_search_fields(FakeModel._meta.get_field('no_charfield'))],
        )


class QSEnumeratorTestCase(CremeTestCase):
    def test_limit_choices_to(self):
        user = self.get_root_user()

        class _Enumerator(QSEnumerator):
            limit_choices_to = {'title__icontains': 'Mi'}

        enum = QSEnumerator(FakeContact._meta.get_field('civility'))

        self.assertIsNone(enum.limit_choices_to)
        self.assertListEqual(
            [
                {'value': id, 'label': title}
                for id, title in FakeCivility.objects.values_list('id', 'title')
            ],
            enum.choices(user),
        )

        # ---
        limited_enum = _Enumerator(FakeContact._meta.get_field('civility'))
        self.assertDictEqual(
            {'title__icontains': 'Mi'}, limited_enum.limit_choices_to,
        )
        self.assertListEqual(
            [
                {'value': id, 'label': title}
                for id, title in FakeCivility.objects.filter(title__icontains='Mi')
                                                     .values_list('id', 'title')
            ],
            limited_enum.choices(user),
        )

        # ---
        custom_limited_enum = _Enumerator(
            FakeContact._meta.get_field('civility'),
            limit_choices_to={'title': 'Miss'},
        )
        self.assertDictEqual({'title': 'Miss'}, custom_limited_enum.limit_choices_to)
        self.assertListEqual(
            [
                {'value': id, 'label': title}
                for id, title in FakeCivility.objects.filter(title='Miss')
                                                     .values_list('id', 'title')
            ],
            custom_limited_enum.choices(user),
        )


class EnumerableRegistryTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.get_root_user()

    def test_basic_choices_fk(self):
        user = self.user
        registry = EnumerableRegistry()
        self.assertEqual('_EnumerableRegistry:', str(registry))

        enum1 = registry.enumerator_by_fieldname(model=FakeContact, field_name='civility')
        expected = [
            {'value': id, 'label': title}
            for id, title in FakeCivility.objects.values_list('id', 'title')
        ]
        self.assertListEqual(expected, enum1.choices(user))
        self.assertEqual(
            '_EnumerableRegistry:\n'
            '  * Field types:\n'
            '    - django.db.models.fields.related.ForeignKey -> None\n'
            '  * Related models:\n'
            '    - creme_core.FakeCivility -> None',
            str(registry),
        )

        # --
        field = FakeContact._meta.get_field('civility')
        enum2 = registry.enumerator_by_field(field=field)
        self.assertEqual(expected, enum2.choices(user))

    def test_basic_choices_fk__limit(self):
        user = self.user
        registry = EnumerableRegistry()

        enum = registry.enumerator_by_fieldname(model=FakeContact, field_name='civility')
        expected = [
            {'value': id, 'label': title}
            for id, title in FakeCivility.objects.values_list('id', 'title')
        ]

        self.assertListEqual(expected[:2], enum.choices(user, limit=2))
        self.assertListEqual(expected, enum.choices(user, limit=100))

    def test_basic_choices_fk__only(self):
        registry = EnumerableRegistry()

        enum = registry.enumerator_by_fieldname(model=FakeContact, field_name='civility')
        only = [1, 3]
        self.assertListEqual(
            [
                {'value': id, 'label': title}
                for id, title in FakeCivility.objects.filter(pk__in=only)
                                                     .values_list('id', 'title')
            ],
            enum.choices(self.user, only=only),
        )

    def test_basic_choices_fk__term(self):
        registry = EnumerableRegistry()
        enum = registry.enumerator_by_fieldname(model=FakeContact, field_name='civility')
        self.assertListEqual(
            ['Miss', 'Mister'],
            [c['label'] for c in enum.choices(self.user, term='Mi')],
        )

    @skipIf(
        connection.vendor != 'mysql',
        'Skip if database does not support unaccent feature',
    )
    def test_basic_choices_fk__term__diacritics(self):
        user = self.user
        registry = EnumerableRegistry()

        create_civility = FakeCivility.objects.create
        create_civility(title='Môssïeur',  shortcut='Mr.')
        create_civility(title='Mïssy',   shortcut='Ms.')
        create_civility(title='Mâdâme', shortcut='Mme.')

        enum = registry.enumerator_by_fieldname(model=FakeContact, field_name='civility')
        self.assertListEqual(
            ['Madam', 'Mâdâme'],
            [c['label'] for c in enum.choices(user, term='Mada')],
        )
        self.assertListEqual(
            ['Miss', 'Mïssy', 'Mister'],
            [c['label'] for c in enum.choices(user, term='Mi')],
        )
        self.assertListEqual(
            ['Miss', 'Mïssy', 'Mister', 'Môssïeur'],
            [c['label'] for c in enum.choices(user, term='ï')],
        )

    def test_basic_choices_m2m(self):
        user = self.user
        registry = EnumerableRegistry()

        enum1 = registry.enumerator_by_fieldname(model=FakeImage, field_name='categories')
        expected = [
            {'value': id, 'label': name}
            for id, name in FakeImageCategory.objects.values_list('id', 'name')
        ]
        self.assertListEqual(expected, enum1.choices(user))

        # --
        field = FakeImage._meta.get_field('categories')
        enum2 = registry.enumerator_by_field(field)
        self.assertListEqual(expected, enum2.choices(user))

    def test_basic_choices_m2m__only(self):
        registry = EnumerableRegistry()

        enum = registry.enumerator_by_fieldname(model=FakeImage, field_name='categories')
        only = [1, 3]
        self.assertListEqual(
            [
                {'value': id, 'label': title}
                for id, title in FakeImageCategory.objects.filter(pk__in=only)
                                                          .values_list('id', 'name')
            ],
            enum.choices(self.user, only=only),
        )

    def test_basic_choices_m2m__limit(self):
        user = self.create_user()
        registry = EnumerableRegistry()

        enum = registry.enumerator_by_fieldname(model=FakeImage, field_name='categories')
        expected = [
            {'value': id, 'label': name}
            for id, name in FakeImageCategory.objects.values_list('id', 'name')
        ]

        self.assertListEqual(expected[:2], enum.choices(user, limit=2))
        self.assertListEqual(expected, enum.choices(user, limit=100))

    def test_basic_choices_m2m__term(self):
        registry = EnumerableRegistry()

        enum = registry.enumerator_by_fieldname(model=FakeImage, field_name='categories')
        # only the first category "Product image" matches the search
        self.assertListEqual(
            ['Product image'],
            [c['label'] for c in enum.choices(self.user, term='image')],
        )

    def test_basic_choices_limited_choices_to(self):
        user = self.user
        registry = EnumerableRegistry()

        create_lang = Language.objects.create
        lang1 = create_lang(name='Klingon [deprecated]')
        lang2 = create_lang(name='Namek')

        enum1 = registry.enumerator_by_fieldname(model=FakeContact, field_name='languages')
        choices = enum1.choices(user)
        ids = {t['value'] for t in choices}
        self.assertIn(lang2.id, ids)
        self.assertNotIn(lang1.id, ids)

        # --
        field = FakeContact._meta.get_field('languages')
        enum2 = registry.enumerator_by_field(field)
        self.assertEqual(choices, enum2.choices(user))

    def test_choices_not_entity_model(self):
        registry = EnumerableRegistry()

        with self.assertRaises(ValueError) as error_ctxt1:
            registry.enumerator_by_fieldname(model=FakeTodo, field_name='categories')

        self.assertEqual(
            'This model is not a CremeEntity: creme.creme_core.tests.fake_models.FakeTodo',
            str(error_ctxt1.exception),
        )

        # --
        field = FakeTodo._meta.get_field('categories')

        with self.assertRaises(ValueError) as error_ctxt2:
            registry.enumerator_by_field(field)

        self.assertEqual(
            'This model is not a CremeEntity: creme.creme_core.tests.fake_models.FakeTodo',
            str(error_ctxt2.exception),
        )

    def test_choices_field_not_entity_model__registered(self):
        class FakeTodoCategoriesEnumerator(Enumerator):
            pass

        registry = EnumerableRegistry().register_field(
            FakeTodo, 'categories', FakeTodoCategoriesEnumerator
        )

        field = FakeTodo._meta.get_field('categories')
        enum = registry.enumerator_by_field(field)

        self.assertIsInstance(enum, FakeTodoCategoriesEnumerator)

    def test_choices_field_does_not_exist(self):
        registry = EnumerableRegistry()

        with self.assertRaises(FieldDoesNotExist):
            registry.enumerator_by_fieldname(model=FakeContact, field_name='unknown')

    def test_choices_field_not_enumerable(self):
        registry = EnumerableRegistry()

        with self.assertRaises(ValueError) as error_ctxt1:
            registry.enumerator_by_fieldname(model=FakeContact, field_name='address')

        self.assertEqual(
            'This field is not enumerable: creme_core.FakeContact.address',
            str(error_ctxt1.exception),
        )

        # --
        field = FakeContact._meta.get_field('address')
        with self.assertRaises(ValueError) as error_ctxt2:
            registry.enumerator_by_field(field)

        self.assertEqual(
            'This field is not enumerable: creme_core.FakeContact.address',
            str(error_ctxt2.exception),
        )

    def test_choices_field_not_visible(self):
        registry = EnumerableRegistry()

        field = FakeTodo._meta.get_field('entity')
        with self.assertRaises(ValueError) as error:
            registry.enumerator_by_field(field)

        self.assertEqual(
            'This field is not viewable: creme_core.FakeTodo.entity',
            str(error.exception),
        )

    def test_choices_field_not_visible__registered(self):
        class FakeTodoEntityEnumerator(Enumerator):
            pass

        registry = EnumerableRegistry()

        registry.register_field(
            model=FakeTodo, field_name='entity',
            enumerator_class=FakeTodoEntityEnumerator,
        )

        field = FakeTodo._meta.get_field('entity')
        self.assertFalse(field.get_tag(FieldTag.VIEWABLE))

        enum = registry.enumerator_by_field(field)
        self.assertIsInstance(enum, FakeTodoEntityEnumerator)

    def test_register_related_model(self):
        class FakeCivilityEnumerator1(Enumerator):
            pass

        registry = EnumerableRegistry()
        registry.register_related_model(FakeCivility, FakeCivilityEnumerator1)
        self.assertEqual(
            '_EnumerableRegistry:\n'
            '  * Related models:\n'
            '    - creme_core.FakeCivility -> '
            'creme.creme_core.tests.core.test_enumerable.EnumerableRegistryTestCase'
            '.test_register_related_model.<locals>.FakeCivilityEnumerator1',
            str(registry),
        )

        enumerator = partial(registry.enumerator_by_fieldname, model=FakeContact)
        self.assertIsInstance(
            enumerator(field_name='civility'), FakeCivilityEnumerator1,
        )
        self.assertNotIsInstance(
            enumerator(field_name='sector'), FakeCivilityEnumerator1,
        )

        # Model already registered
        class FakeCivilityEnumerator2(Enumerator):
            pass

        # with self.assertRaises(registry.RegistrationError):
        #     registry.register_related_model(FakeCivility, FakeCivilityEnumerator2)
        registry.register_related_model(FakeCivility, FakeCivilityEnumerator2)
        self.assertIsInstance(
            enumerator(field_name='civility'), FakeCivilityEnumerator2,
        )

    def test_register_related_model__inheritance(self):
        class FakeMinionEnumerator(Enumerator):
            pass

        registry = EnumerableRegistry().register_related_model(
            model=MinionModel, enumerator_class=FakeMinionEnumerator,
        )

        enumerator = partial(registry.enumerator_by_fieldname, model=FakeContact)
        self.assertIsInstance(
            enumerator(field_name='civility'), FakeMinionEnumerator,
        )
        self.assertIsInstance(
            enumerator(field_name='sector'), FakeMinionEnumerator,
        )
        self.assertNotIsInstance(
            enumerator(field_name='image'), FakeMinionEnumerator,
        )

        # ---
        class FakeCivilityEnumerator(Enumerator):
            pass

        registry.register_related_model(
            model=FakeCivility, enumerator_class=FakeCivilityEnumerator,
        )
        self.assertIsInstance(
            enumerator(field_name='civility'), FakeCivilityEnumerator,
        )
        self.assertIsInstance(
            enumerator(field_name='sector'), FakeMinionEnumerator,
        )

    def test_register_specific_field(self):
        class FakeContactSectorEnumerator1(Enumerator):
            pass

        registry = EnumerableRegistry()
        registry.register_field(
            FakeContact,
            field_name='sector', enumerator_class=FakeContactSectorEnumerator1,
        )

        enumerator1 = registry.enumerator_by_fieldname
        self.assertIsInstance(
            enumerator1(model=FakeContact, field_name='sector'),
            FakeContactSectorEnumerator1,
        )
        self.assertNotIsInstance(
            enumerator1(model=FakeOrganisation, field_name='sector'),
            FakeContactSectorEnumerator1,
        )

        # --
        field = FakeContact._meta.get_field('sector')
        self.assertIsInstance(
            registry.enumerator_by_field(field),
            FakeContactSectorEnumerator1,
        )

        # Field registered
        class FakeContactSectorEnumerator2(Enumerator):
            pass

        with self.assertRaises(registry.RegistrationError):
            registry.register_field(
                FakeContact,
                field_name='sector',
                enumerator_class=FakeContactSectorEnumerator2,
            )

    def test_register_field_type(self):
        class EntityCTypeForeignKeyEnumerator(Enumerator):
            pass

        registry = EnumerableRegistry()
        registry.register_field_type(
            EntityCTypeForeignKey,
            enumerator_class=EntityCTypeForeignKeyEnumerator,
        )
        self.assertIsInstance(
            registry.enumerator_by_fieldname(model=FakeReport, field_name='ctype'),
            EntityCTypeForeignKeyEnumerator,
        )
        self.assertEqual(
            '_EnumerableRegistry:\n'
            '  * Field types:\n'
            '    - creme.creme_core.models.fields.EntityCTypeForeignKey -> '
            'creme.creme_core.tests.core.test_enumerable.EnumerableRegistryTestCase.'
            'test_register_field_type.<locals>.EntityCTypeForeignKeyEnumerator',
            str(registry),
        )

    def test_register_field_type__inheritance(self):
        class CTypeForeignKeyEnumerator(Enumerator):
            pass

        registry = EnumerableRegistry()
        registry.register_field_type(
            CTypeForeignKey, enumerator_class=CTypeForeignKeyEnumerator,
        )

        self.assertIsInstance(
            registry.enumerator_by_fieldname(model=FakeReport, field_name='ctype'),
            CTypeForeignKeyEnumerator,
        )

    def test_convert_choices(self):
        self.assertEqual(
            [
                {'value': 1, 'label': 'Bad'},
                {'value': 2, 'label': 'Not bad'},
                {'value': 3, 'label': 'Great'},
            ],
            [*Enumerator.convert_choices(
                [(1, 'Bad'), (2, 'Not bad'), (3, 'Great')]
            )],
        )

    def test_convert_choices_with_group(self):
        self.assertEqual(
            [
                {'value': 'vinyl',   'label': 'Vinyl',    'group': 'Audio'},
                {'value': 'cd',      'label': 'CD',       'group': 'Audio'},
                {'value': 'vhs',     'label': 'VHS Tape', 'group': 'Video'},
                {'value': 'dvd',     'label': 'DVD',      'group': 'Video'},
                {'value': 'unknown', 'label': 'Unknown'},
            ],
            [
                *Enumerator.convert_choices([
                    (
                        'Audio',
                        (
                            ('vinyl', 'Vinyl'),
                            ('cd',    'CD'),
                        ),
                    ),
                    (
                        'Video',
                        (
                            ('vhs', 'VHS Tape'),
                            ('dvd', 'DVD'),
                        ),
                    ),
                    ('unknown', 'Unknown'),
                ])
            ],
        )

    def test_global_registry(self):
        self.assertIsInstance(
            enumerable_registry.enumerator_by_fieldname(
                model=FakeReport, field_name='ctype',
            ),
            enumerators.CTypeForeignKeyEnumerator,
        )

        self.assertIsInstance(
            enumerable_registry.enumerator_by_fieldname(
                model=FakeContact, field_name='image',
            ),
            enumerators.EntityEnumerator,
        )
        self.assertIsInstance(
            enumerable_registry.enumerator_by_fieldname(
                model=FakeContact, field_name='sector',
            ),
            enumerators.MinionEnumerator,
        )
