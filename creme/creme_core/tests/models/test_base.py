from uuid import uuid4

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.utils.translation import gettext as _

from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.models import (
    FakeContact,
    FakeCountry,
    FakeOrganisation,
    FakeSector,
    Language,
)

from ..base import CremeTestCase


class ContentTypeTestCase(CremeTestCase):
    def test_ordering(self):
        self.assertListEqual(['id'], ContentType._meta.ordering)

    def test_str(self):
        get_ct = ContentType.objects.get_for_model
        self.assertEqual('Test Organisation', str(get_ct(FakeOrganisation)))
        self.assertEqual('Test Contact',      str(get_ct(FakeContact)))
        self.assertEqual(_('Language'),       str(get_ct(Language)))

    def test_fields(self):
        get_field = ContentType._meta.get_field
        with self.assertNoException():
            app_label_f = get_field('app_label')
        self.assertFalse(app_label_f.get_tag(FieldTag.VIEWABLE))

        with self.assertNoException():
            model_f = get_field('model')
        self.assertFalse(model_f.get_tag(FieldTag.VIEWABLE))

    def test_portable_key(self):
        ct = ContentType.objects.get_for_model(FakeOrganisation)

        with self.assertNoException():
            key = ct.portable_key()
        self.assertEqual('creme_core.fakeorganisation', key)

        # ---
        with self.assertNoException():
            got_ct = ContentType.objects.get_by_portable_key(key)
        self.assertEqual(ct, got_ct)


class GetM2MValuesTestCase(CremeTestCase):
    def test_one_field(self):
        al = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Alphonse', last_name='Elric',
        )

        # Empty ---
        with self.assertNumQueries(1):
            self.assertEqual([], al.get_m2m_values('languages'))

        with self.assertNumQueries(0):
            al.get_m2m_values('languages')  # NOQA

        # Initial add ----
        create_language = Language.objects.create
        l1 = create_language(name='English')
        l2 = create_language(name='French')
        l3 = create_language(name='Japanese')

        al.languages.set([l1, l3])
        with self.assertNumQueries(1):
            self.assertListEqual([l1, l3], al.get_m2m_values('languages'))

        with self.assertNumQueries(0):
            al.get_m2m_values('languages')  # NOQA

        # Update ----
        al.languages.remove(l1)
        al.languages.add(l2)
        al.languages.add(l2)  # duplicate

        with self.assertNumQueries(1):
            self.assertListEqual([l2, l3], al.get_m2m_values('languages'))

        with self.assertNumQueries(0):
            al.get_m2m_values('languages') # NOQA

        # Clear ----
        al.languages.clear()

        with self.assertNumQueries(0):
            self.assertListEqual([], al.get_m2m_values('languages'))

    def test_two_fields(self):
        al = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Alphonse', last_name='Elric',
        )

        with self.assertNumQueries(2):
            self.assertEqual([], al.get_m2m_values('languages'))
            self.assertEqual([], al.get_m2m_values('preferred_countries'))

        # ----
        create_language = Language.objects.create
        l1 = create_language(name='English')
        l2 = create_language(name='French')

        create_country = FakeCountry.objects.create
        c1 = create_country(name='Amestris')
        c2 = create_country(name='Xing')

        al.languages.set([l1, l2])
        al.preferred_countries.set([c1, c2])

        with self.assertNumQueries(2):
            self.assertListEqual([l1, l2], al.get_m2m_values('languages'))
            self.assertListEqual([c1, c2], al.get_m2m_values('preferred_countries'))

        # Clear ----
        al.preferred_countries.clear()

        with self.assertNumQueries(0):
            self.assertListEqual([l1, l2], al.get_m2m_values('languages'))
            self.assertListEqual([],       al.get_m2m_values('preferred_countries'))

    def test_error(self):
        al = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Alphonse', last_name='Elric',
        )

        with self.assertRaises(FieldDoesNotExist):
            al.get_m2m_values('invalid')  # NOQA

        with self.assertRaises(TypeError):
            al.get_m2m_values('first_name')  # NOQA


class IsReferencedTestCase(CremeTestCase):
    def test_FK(self):
        sector1, sector2 = FakeSector.objects.all()[:2]
        FakeContact.objects.create(
            user=self.get_root_user(), first_name='Alphonse', last_name='Elric',
            sector=sector2,
        )

        self.assertIs(sector1.is_referenced, False)
        self.assertIs(sector2.is_referenced, True)

    def test_M2M(self):
        create_language = Language.objects.create
        l1 = create_language(name='English')
        l2 = create_language(name='French')

        al = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Alphonse', last_name='Elric',
        )
        al.languages.add(l2)

        self.assertIs(l1.is_referenced, False)
        self.assertIs(l2.is_referenced, True)


class MinionTestCase(CremeTestCase):
    def test_portable_key(self):
        sector1, sector2 = FakeSector.objects.all()[:2]

        with self.assertNoException():
            key1 = sector1.portable_key()
        self.assertIsInstance(key1, str)
        self.assertUUIDEqual(sector1.uuid, key1)

        key2 = sector2.portable_key()
        self.assertUUIDEqual(sector2.uuid, key2)

        # ---
        with self.assertNoException():
            got_sector1 = FakeSector.objects.get_by_portable_key(key1)
        self.assertEqual(sector1, got_sector1)

        self.assertEqual(sector2, FakeSector.objects.get_by_portable_key(key2))

        with self.assertRaises(FakeSector.DoesNotExist):
            FakeSector.objects.get_by_portable_key(uuid4())
