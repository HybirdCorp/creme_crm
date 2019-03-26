# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.db.models.fields import FieldDoesNotExist

    from ..base import CremeTestCase

    from creme.creme_core.core.enumerable import _EnumerableRegistry, Enumerator
    from creme.creme_core.models import (Language,
        FakeContact, FakeOrganisation, FakeCivility, FakeAddress,
        FakeImageCategory, FakeImage, FakeReport)
    from creme.creme_core.models.fields import CTypeForeignKey, EntityCTypeForeignKey
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class EnumerableTestCase(CremeTestCase):
    def test_basic_choices_fk(self):
        user = self.login()
        registry = _EnumerableRegistry()

        enum1 = registry.enumerator_by_fieldname(model=FakeContact, field_name='civility')
        expected = [{'value': id, 'label': title}
                        for id, title in FakeCivility.objects.values_list('id', 'title')
                   ]
        self.assertEqual(expected, enum1.choices(user))

        # --
        field = FakeContact._meta.get_field('civility')
        enum2 = registry.enumerator_by_field(field=field)
        self.assertEqual(expected, enum2.choices(user))

    def test_basic_choices_m2m(self):
        user = self.login()
        registry = _EnumerableRegistry()

        enum1 = registry.enumerator_by_fieldname(model=FakeImage, field_name='categories')
        expected = [
            {'value': id, 'label': name}
                for id, name in FakeImageCategory.objects.values_list('id', 'name')
        ]
        self.assertEqual(expected, enum1.choices(user))

        # --
        field = FakeImage._meta.get_field('categories')
        enum2 = registry.enumerator_by_field(field)
        self.assertEqual(expected, enum2.choices(user))

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
            registry.enumerator_by_fieldname(model=FakeAddress, field_name='entity')

        self.assertEqual(
            'This model is not a CremeEntity: creme.creme_core.tests.fake_models.FakeAddress',
            str(error_ctxt1.exception)
        )

        # --
        field = FakeAddress._meta.get_field('entity')

        with self.assertRaises(ValueError) as error_ctxt2:
            registry.enumerator_by_field(field)

        self.assertEqual(
            'This model is not a CremeEntity: creme.creme_core.tests.fake_models.FakeAddress',
            str(error_ctxt2.exception)
        )

    def test_choices_field_does_not_exist(self):
        registry = _EnumerableRegistry()

        with self.assertRaises(FieldDoesNotExist):
            registry.enumerator_by_fieldname(model=FakeContact, field_name='unknown')

    def test_choices_field_not_enumerable(self):
        registry = _EnumerableRegistry()

        with self.assertRaises(ValueError) as error_ctxt1:
            registry.enumerator_by_fieldname(model=FakeContact, field_name='address')

        self.assertEqual('This field is not enumerable: creme_core.FakeContact.address',
                         str(error_ctxt1.exception)
                        )

        # --
        field = FakeContact._meta.get_field('address')
        with self.assertRaises(ValueError) as error_ctxt2:
            registry.enumerator_by_field(field)

        self.assertEqual(
            'This field is not enumerable: creme_core.FakeContact.address',
            str(error_ctxt2.exception)
        )

    def test_register_related_model(self):
        class FakeCivilityEnumerator1(Enumerator):
            pass

        registry = _EnumerableRegistry()
        registry.register_related_model(FakeCivility, FakeCivilityEnumerator1)

        enumerator = partial(registry.enumerator_by_fieldname, model=FakeContact)
        self.assertIsInstance(enumerator(field_name='civility'),
                              FakeCivilityEnumerator1
                             )
        self.assertNotIsInstance(enumerator(field_name='sector'),
                                 FakeCivilityEnumerator1
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
        registry.register_field(FakeContact, field_name='sector',
                                enumerator_class=FakeContactSectorEnumerator1,
                               )

        enumerator1 = registry.enumerator_by_fieldname
        self.assertIsInstance(enumerator1(model=FakeContact, field_name='sector'),
                              FakeContactSectorEnumerator1
                             )
        self.assertNotIsInstance(enumerator1(model=FakeOrganisation, field_name='sector'),
                                 FakeContactSectorEnumerator1
                                )

        # --
        field = FakeContact._meta.get_field('sector')
        self.assertIsInstance(registry.enumerator_by_field(field),
                              FakeContactSectorEnumerator1
                             )

        # Field registered
        class FakeContactSectorEnumerator2(Enumerator):
            pass

        with self.assertRaises(registry.RegistrationError):
            registry.register_field(FakeContact, field_name='sector',
                                    enumerator_class=FakeContactSectorEnumerator2,
                                   )

    def test_register_field_type01(self):
        class EntityCTypeForeignKeyEnumerator(Enumerator):
            pass

        registry = _EnumerableRegistry()
        registry.register_field_type(EntityCTypeForeignKey,
                                     enumerator_class=EntityCTypeForeignKeyEnumerator,
                                    )

        self.assertIsInstance(registry.enumerator_by_fieldname(model=FakeReport, field_name='ctype'),
                              EntityCTypeForeignKeyEnumerator
                             )

    def test_register_field_type02(self):
        "Inheritance"
        class CTypeForeignKeyEnumerator(Enumerator):
            pass

        registry = _EnumerableRegistry()
        registry.register_field_type(CTypeForeignKey,
                                     enumerator_class=CTypeForeignKeyEnumerator,
                                    )

        self.assertIsInstance(registry.enumerator_by_fieldname(model=FakeReport, field_name='ctype'),
                              CTypeForeignKeyEnumerator
                             )

    def test_convert_choices(self):
        self.assertEqual(
            [{'value': 1, 'label': 'Bad'},
             {'value': 2, 'label': 'Not bad'},
             {'value': 3, 'label': 'Great'},
            ],
            list(Enumerator.convert_choices(
                [(1, 'Bad'), (2, 'Not bad'), (3, 'Great')]
            ))
        )

    def test_convert_choices_with_group(self):
        self.assertEqual(
            [{'value': 'vinyl',   'label': 'Vinyl',    'group': 'Audio'},
             {'value': 'cd',      'label': 'CD',       'group': 'Audio'},
             {'value': 'vhs',     'label': 'VHS Tape', 'group': 'Video'},
             {'value': 'dvd',     'label': 'DVD',      'group': 'Video'},
             {'value': 'unknown', 'label': 'Unknown'},

            ],
            list(Enumerator.convert_choices(
                [('Audio',
                    (('vinyl', 'Vinyl'),
                     ('cd',    'CD'),
                    )
                 ),
                 ('Video',
                    (('vhs', 'VHS Tape'),
                     ('dvd', 'DVD'),
                    )
                 ),
                 ('unknown', 'Unknown'),
                ]
            ))
        )
