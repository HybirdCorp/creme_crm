from django.core.exceptions import FieldDoesNotExist

from creme.creme_core.models import (
    FakeContact,
    FakeCountry,
    FakeSector,
    Language,
)

from ..base import CremeTestCase


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
