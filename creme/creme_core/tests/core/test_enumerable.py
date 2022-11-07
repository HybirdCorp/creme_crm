from decimal import Decimal
from functools import partial
from unittest.case import skipIf

from django.core.exceptions import FieldDoesNotExist
from django.db import connection, models
from django.utils.translation import gettext as _

from creme.creme_core import enumerators
from creme.creme_core.core.entity_filter import EF_CREDENTIALS
from creme.creme_core.core.enumerable import (
    Enumerator,
    QSEnumerator,
    _EnumerableRegistry,
    get_enum_search_fields,
)
from creme.creme_core.models import (
    CremeModel,
    CremeUser,
    EntityFilter,
    FakeCivility,
    FakeContact,
    FakeImage,
    FakeImageCategory,
    FakeInvoiceLine,
    FakeOrganisation,
    FakeReport,
    FakeTodo,
    Language,
    Vat,
)
from creme.creme_core.models.fields import (
    CTypeForeignKey,
    EntityCTypeForeignKey,
)

from ..base import CremeTestCase


class EnumerableTestCase(CremeTestCase):
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
            list(get_enum_search_fields(FakeModel._meta.get_field('searchfields')))
        )

        self.assertListEqual(
            ['title'],
            list(get_enum_search_fields(FakeModel._meta.get_field('first_charfield')))
        )

        self.assertListEqual(
            ['help'],
            list(get_enum_search_fields(FakeModel._meta.get_field('visible_charfield')))
        )

        self.assertListEqual(
            [],
            list(get_enum_search_fields(FakeModel._meta.get_field('no_charfield')))
        )

    def test_qs_enumerable_limit_choices_to(self):
        user = self.create_user()

        class _Enumerator(QSEnumerator):
            limit_choices_to = {'title__icontains': 'Mi'}

        enum = QSEnumerator(FakeContact._meta.get_field('civility'))

        self.assertEqual(None, enum.limit_choices_to)
        self.assertEqual([
            {'value': id, 'label': title}
            for id, title in FakeCivility.objects.values_list('id', 'title')
        ], enum.choices(user))

        limited_enum = _Enumerator(FakeContact._meta.get_field('civility'))

        self.assertEqual({'title__icontains': 'Mi'}, limited_enum.limit_choices_to)
        self.assertEqual([
            {'value': id, 'label': title}
            for id, title in FakeCivility.objects.filter(title__icontains='Mi')
                                                 .values_list('id', 'title')
        ], limited_enum.choices(user))

        limited_enum = _Enumerator(
            FakeContact._meta.get_field('civility'),
            limit_choices_to={'title': 'Miss'}
        )

        self.assertEqual({'title': 'Miss'}, limited_enum.limit_choices_to)
        self.assertEqual([
            {'value': id, 'label': title}
            for id, title in FakeCivility.objects.filter(title='Miss')
                                                 .values_list('id', 'title')
        ], limited_enum.choices(user))

    def test_basic_choices_fk(self):
        user = self.login()
        registry = _EnumerableRegistry()
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
            '    - django.db.models.fields.related.ForeignKey -> None',
            str(registry),
        )

        # --
        field = FakeContact._meta.get_field('civility')
        enum2 = registry.enumerator_by_field(field=field)
        self.assertEqual(expected, enum2.choices(user))

    def test_basic_choices_fk__limit(self):
        user = self.create_user()
        registry = _EnumerableRegistry()

        enum = registry.enumerator_by_fieldname(model=FakeContact, field_name='civility')
        expected = [
            {'value': id, 'label': title}
            for id, title in FakeCivility.objects.values_list('id', 'title')
        ]

        self.assertListEqual(expected[:2], enum.choices(user, limit=2))
        self.assertListEqual(expected, enum.choices(user, limit=100))

    def test_basic_choices_fk__only(self):
        user = self.create_user()
        registry = _EnumerableRegistry()

        enum = registry.enumerator_by_fieldname(model=FakeContact, field_name='civility')
        only = [1, 3]
        expected = [
            {'value': id, 'label': title}
            for id, title in FakeCivility.objects.filter(pk__in=only).values_list('id', 'title')
        ]

        self.assertListEqual(expected, enum.choices(user, only=only))

    def test_basic_choices_fk__term(self):
        user = self.create_user()
        registry = _EnumerableRegistry()

        enum = registry.enumerator_by_fieldname(model=FakeContact, field_name='civility')

        self.assertListEqual(
            ['Miss', 'Mister'],
            [c['label'] for c in enum.choices(user, term='Mi')]
        )

    @skipIf(
        connection.vendor != 'mysql',
        'Skip if database does not support unaccent feature',
    )
    def test_basic_choices_fk__term__diacritics(self):
        user = self.create_user()
        registry = _EnumerableRegistry()

        create_civility = FakeCivility.objects.create
        create_civility(title='Môssïeur',  shortcut='Mr.')
        create_civility(title='Mïssy',   shortcut='Ms.')
        create_civility(title='Mâdâme', shortcut='Mme.')

        enum = registry.enumerator_by_fieldname(model=FakeContact, field_name='civility')

        self.assertListEqual(
            ['Madam', 'Mâdâme'],
            [c['label'] for c in enum.choices(user, term='Mada')]
        )

        self.assertListEqual(
            ['Miss', 'Mïssy', 'Mister'],
            [c['label'] for c in enum.choices(user, term='Mi')]
        )

        self.assertListEqual(
            ['Miss', 'Mïssy', 'Mister', 'Môssïeur'],
            [c['label'] for c in enum.choices(user, term='ï')]
        )

    def test_basic_choices_m2m(self):
        user = self.login()
        registry = _EnumerableRegistry()

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
        user = self.create_user()
        registry = _EnumerableRegistry()

        enum = registry.enumerator_by_fieldname(model=FakeImage, field_name='categories')
        only = [1, 3]
        expected = [
            {'value': id, 'label': title} for id, title in FakeImageCategory.objects.filter(
                pk__in=only
            ).values_list('id', 'name')
        ]

        self.assertListEqual(expected, enum.choices(user, only=only))

    def test_basic_choices_m2m__limit(self):
        user = self.create_user()
        registry = _EnumerableRegistry()

        enum = registry.enumerator_by_fieldname(model=FakeImage, field_name='categories')
        expected = [
            {'value': id, 'label': name}
            for id, name in FakeImageCategory.objects.values_list('id', 'name')
        ]

        self.assertListEqual(expected[:2], enum.choices(user, limit=2))
        self.assertListEqual(expected, enum.choices(user, limit=100))

    def test_basic_choices_m2m__term(self):
        user = self.create_user()
        registry = _EnumerableRegistry()

        enum = registry.enumerator_by_fieldname(model=FakeImage, field_name='categories')

        # only the first cateogory "Product image" matches the search
        self.assertListEqual(
            ['Product image'],
            [c['label'] for c in enum.choices(user, term='image')]
        )

    def test_basic_choices_limited_choices_to(self):
        user = self.login()
        registry = _EnumerableRegistry()

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
        registry = _EnumerableRegistry()

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

        registry = _EnumerableRegistry().register_field(
            FakeTodo, 'categories', FakeTodoCategoriesEnumerator
        )

        field = FakeTodo._meta.get_field('categories')
        enum = registry.enumerator_by_field(field)

        self.assertIsInstance(enum, FakeTodoCategoriesEnumerator)

    def test_choices_field_does_not_exist(self):
        registry = _EnumerableRegistry()

        with self.assertRaises(FieldDoesNotExist):
            registry.enumerator_by_fieldname(model=FakeContact, field_name='unknown')

    def test_choices_field_not_enumerable(self):
        registry = _EnumerableRegistry()

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
        registry = _EnumerableRegistry()

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

        registry = _EnumerableRegistry()

        registry.register_field(
            FakeTodo, 'entity', FakeTodoEntityEnumerator
        )

        field = FakeTodo._meta.get_field('entity')
        enum = registry.enumerator_by_field(field)

        self.assertIsInstance(enum, FakeTodoEntityEnumerator)

    def test_register_related_model(self):
        class FakeCivilityEnumerator1(Enumerator):
            pass

        registry = _EnumerableRegistry()
        registry.register_related_model(FakeCivility, FakeCivilityEnumerator1)
        self.assertEqual(
            '_EnumerableRegistry:\n'
            '  * Related models:\n'
            '    - creme_core.FakeCivility -> '
            'creme.creme_core.tests.core.test_enumerable.EnumerableTestCase'
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

        with self.assertRaises(registry.RegistrationError):
            registry.register_related_model(FakeCivility, FakeCivilityEnumerator2)

    def test_register_specific_field(self):
        class FakeContactSectorEnumerator1(Enumerator):
            pass

        registry = _EnumerableRegistry()
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

    def test_register_field_type01(self):
        class EntityCTypeForeignKeyEnumerator(Enumerator):
            pass

        registry = _EnumerableRegistry()
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
            'creme.creme_core.tests.core.test_enumerable.EnumerableTestCase.'
            'test_register_field_type01.<locals>.EntityCTypeForeignKeyEnumerator',
            str(registry),
        )

    def test_register_field_type02(self):
        "Inheritance."
        class CTypeForeignKeyEnumerator(Enumerator):
            pass

        registry = _EnumerableRegistry()
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

    def test_user_enumerator(self):
        user = self.login()
        other_user = self.other_user

        # Alphabetically-first user (__str__, not username)
        first_user = CremeUser.objects.create_user(
            username='noir', email='chloe@noir.jp',
            first_name='Chloe', last_name='Noir',
            password='uselesspw',
        )
        self.assertGreater(str(user), str(first_user))

        team_name = 'Team#1'
        team = CremeUser.objects.create(username=team_name, is_team=True)
        team.teammates = [user, other_user]

        inactive = CremeUser.objects.create(username='deunan', is_active=False)

        e = enumerators.UserEnumerator(FakeContact._meta.get_field('user'))
        choices = e.choices(user)
        self.assertIsList(choices)

        first_choice = choices[0]
        self.assertIsInstance(first_choice, dict)
        self.assertIn('value', first_choice)

        def find_user_dict(u):
            user_as_dicts = [
                (i, c) for i, c in enumerate(choices) if c['value'] == u.id
            ]
            self.assertEqual(1, len(user_as_dicts))
            return user_as_dicts[0]

        user_index, user_dict = find_user_dict(user)
        self.assertDictEqual(
            {'value': user.pk, 'label': str(user)},
            user_dict,
        )

        other_index, other_dict = find_user_dict(other_user)
        self.assertEqual(
            {'value': other_user.pk, 'label': str(other_user)},
            other_dict,
        )

        first_index, first_dict = find_user_dict(first_user)
        self.assertDictEqual(
            {'value': first_user.pk, 'label': str(first_user)},
            first_dict,
        )

        self.assertGreater(other_index, user_index)
        self.assertGreater(user_index,  first_index)

        self.assertDictEqual(
            {'value': team.pk, 'label': team_name, 'group': _('Teams')},
            find_user_dict(team)[1]
        )
        self.assertEqual(
            {
                'value': inactive.pk,
                'label': str(inactive),
                'group': _('Inactive users'),
            },
            find_user_dict(inactive)[1]
        )

    def test_user_enumerator__limit(self):
        user = self.login()

        # Alphabetically-first user (__str__, not username)
        CremeUser.objects.create_user(
            username='noir', email='chloe@noir.jp',
            first_name='Chloe', last_name='Noir',
            password='uselesspw',
        )

        enum = enumerators.UserEnumerator(FakeContact._meta.get_field('user'))

        all_choices = enum.choices(user)

        self.assertListEqual(all_choices[:2], enum.choices(user, limit=2))
        self.assertListEqual(all_choices, enum.choices(user, limit=100))

    def test_user_enumerator__only(self):
        user = self.login()

        chloe = CremeUser.objects.create_user(
            username='noir', email='chloe@noir.jp',
            first_name='Chloe', last_name='Noir',
            password='uselesspw',
        )

        enum = enumerators.UserEnumerator(FakeContact._meta.get_field('user'))

        self.assertListEqual(
            [{'value': chloe.pk, 'label': str(chloe)}],
            enum.choices(user, only=[chloe.pk])
        )

    def test_user_enumerator__term(self):
        user = self.login()

        # Alphabetically-first user (__str__, not username)
        first_user = CremeUser.objects.create_user(
            username='noir', email='chloe@noir.jp',
            first_name='Chloe', last_name='Noir',
            password='uselesspw',
        )

        enum = enumerators.UserEnumerator(FakeContact._meta.get_field('user'))

        self.assertListEqual(
            [str(first_user)],
            [c['label'] for c in enum.choices(user, term='noir')]
        )
        self.assertListEqual(
            [str(user)],
            [c['label'] for c in enum.choices(user, term='kirika')]
        )

    def test_efilter_enumerator(self):
        user = CremeUser.objects.create_user(
            username='Kanna', email='kanna@century.jp',
            first_name='Kanna', last_name='Gendou',
            password='uselesspw',
        )

        create_filter = EntityFilter.objects.create
        efilter1 = create_filter(
            id='test-filter01',
            name='Filter 01',
            entity_type=FakeContact,
            is_custom=True,
        )
        efilter2 = create_filter(
            id='test-filter02',
            name='Filter 02',
            entity_type=FakeOrganisation,
            is_custom=True, user=user, is_private=True,
        )
        efilter3 = create_filter(
            id='test-filter03',
            name='Filter 01',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,  # <==
        )

        e = enumerators.EntityFilterEnumerator(FakeReport._meta.get_field('efilter'))
        choices = e.choices(user)
        self.assertIsList(choices)

        first_choice = choices[0]
        self.assertIsInstance(first_choice, dict)
        self.assertIn('value', first_choice)

        def find_efilter_dict(efilter):
            efilter_as_dicts = [c for c in choices if c['value'] == efilter.id]
            self.assertEqual(1, len(efilter_as_dicts))
            return efilter_as_dicts[0]

        self.assertDictEqual(
            {
                'value': efilter1.pk,
                'label': efilter1.name,
                'help': '',
                'group': 'Test Contact',
            },
            find_efilter_dict(efilter1)
        )
        self.assertDictEqual(
            {
                'value': efilter2.pk,
                'label': efilter2.name,
                'help': _('Private ({})').format(user),
                'group': 'Test Organisation',
            },
            find_efilter_dict(efilter2)
        )
        self.assertFalse(
            [c for c in choices if c['value'] == efilter3.id]
        )

    def test_efilter_enumerator__only(self):
        user = CremeUser.objects.create_user(
            username='Kanna', email='kanna@century.jp',
            first_name='Kanna', last_name='Gendou',
            password='uselesspw',
        )

        create_filter = partial(
            EntityFilter.objects.create, entity_type=FakeContact,
            is_custom=True,
        )

        filter_01 = create_filter(id='test-filter01', name='Filter 01')
        create_filter(id='test-filter02', name='Filter 02')
        filter_03 = create_filter(id='test-filter03', name='Filter 03')

        enum = enumerators.EntityFilterEnumerator(FakeReport._meta.get_field('efilter'))

        self.assertListEqual([
            {
                'value': filter_01.pk,
                'label': filter_01.name,
                'group': str(filter_01.entity_type),
                'help': ''
            }
        ], enum.choices(user, only=['test-filter01']))

        self.assertListEqual([
            {
                'value': filter_01.pk,
                'label': filter_01.name,
                'group': str(filter_01.entity_type),
                'help': ''
            },
            {
                'value': filter_03.pk,
                'label': filter_03.name,
                'group': str(filter_03.entity_type),
                'help': ''
            }
        ], enum.choices(user, only=['test-filter01', 'test-filter03']))

    def test_efilter_enumerator__limit(self):
        user = CremeUser.objects.create_user(
            username='Kanna', email='kanna@century.jp',
            first_name='Kanna', last_name='Gendou',
            password='uselesspw',
        )

        create_filter = EntityFilter.objects.create
        create_filter(
            id='test-filter01',
            name='Filter 01',
            entity_type=FakeContact,
            is_custom=True,
        )
        create_filter(
            id='test-filter02',
            name='Filter 02',
            entity_type=FakeOrganisation,
            is_custom=True, user=user, is_private=True,
        )
        create_filter(
            id='test-filter03',
            name='Filter 01',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,  # <==
        )

        enum = enumerators.EntityFilterEnumerator(FakeReport._meta.get_field('efilter'))
        all_choices = enum.choices(user)

        self.assertListEqual(all_choices[:2], enum.choices(user, limit=2))
        self.assertListEqual(all_choices, enum.choices(user, limit=100))

    def test_efilter_enumerator__term(self):
        user = CremeUser.objects.create_user(
            username='Kanna', email='kanna@century.jp',
            first_name='Kanna', last_name='Gendou',
            password='uselesspw',
        )

        create_filter = EntityFilter.objects.create
        create_filter(
            id='test-filter01',
            name='Filter 01',
            entity_type=FakeContact,
            is_custom=True,
        )
        create_filter(
            id='test-filter02',
            name='Filter 02',
            entity_type=FakeContact,
            is_custom=True, user=user, is_private=True,
        )
        create_filter(
            id='test-filter03',
            name='Filter 03',
            entity_type=FakeContact,
            is_custom=True,
        )

        enum = enumerators.EntityFilterEnumerator(FakeReport._meta.get_field('efilter'))

        self.assertListEqual(
            ['Filter 01', 'Filter 02', 'Filter 03'],
            [c['label'] for c in enum.choices(user, term='Filter')]
        )
        self.assertListEqual(
            ['Filter 03'],
            [c['label'] for c in enum.choices(user, term='03')]
        )

    def test_vat_enumerator(self):
        user = self.create_user()
        enum = enumerators.VatEnumerator(FakeInvoiceLine._meta.get_field('vat_value'))

        vats = Vat.objects.order_by('value')

        self.assertListEqual([
            {'label': str(vat), 'value': vat.pk} for vat in vats
        ], list(enum.choices(user)))

        vat_200 = Vat.objects.get(value=Decimal('20.00'))
        vat_212 = Vat.objects.get(value=Decimal('21.20'))

        # SQLite seems to compare the floating value so '20' will match '20.00' only
        if connection.vendor == 'sqlite':
            self.assertListEqual([
                {'label': '20.00', 'value': vat_200.pk},
            ], list(enum.choices(user, term='20')))
        # The other databases are using a native decimal value so '20' will match
        # both '20.00' & '21.20'
        else:
            self.assertListEqual([
                {'label': '20.00', 'value': vat_200.pk},
                {'label': '21.20', 'value': vat_212.pk},
            ], list(enum.choices(user, term='20')))
