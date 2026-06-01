from uuid import uuid4

from django.core.exceptions import FieldDoesNotExist
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import (
    FakeContact,
    FakeCountry,
    FakePosition,
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


class MinionTestCase(CremeTestCase):
    def test_manager__get_by_uuid(self):
        sector1, sector2 = FakeSector.objects.all()[:2]

        with self.assertNumQueries(1):
            sector_a = FakeSector.objects.get_by_uuid(sector1.uuid)
            self.assertEqual(sector1, sector_a)

        with self.assertNumQueries(1):
            sector_b = FakeSector.objects.get_by_uuid(str(sector2.uuid))
            self.assertEqual(sector2, sector_b)

        # Cache ---
        with self.assertNumQueries(0):
            FakeSector.objects.get_by_uuid(sector1.uuid)

        # Error ---
        with self.assertRaises(FakeSector.DoesNotExist):
            FakeSector.objects.get_by_uuid(uuid4())

        uid = uuid4()
        with self.assertRaises(ConflictError) as cm:
            FakeSector.objects.get_by_uuid(uid, conflict_error=True)
        self.assertEqual(
            _(
                'It seems the instance of model «{model}» with uuid "{uuid}" '
                'has been deleted; please contact your administrator.'
            ).format(model=FakeSector._meta.verbose_name, uuid=uid),
            str(cm.exception),
        )

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

    def test_get_enabled_label(self):
        sector = FakeSector(title='Industry')
        self.assertEqual(sector.title, sector.get_enabled_label())

        sector.disabled = now()
        self.assertEqual(
            _('{} (disabled)').format(sector.title), sector.get_enabled_label(),
        )

    def test_message_for_disabled(self):
        sector = FakeSector(title='Industry')
        msg_fmt = _('«{instance}» (of type «{model}») is disabled.').format
        self.assertEqual(
            msg_fmt(model=FakeSector._meta.verbose_name, instance=sector.title),
            sector.message_for_disabled,
        )

        # ---
        pos = FakePosition(title='Gardener')
        self.assertEqual(
            msg_fmt(model=FakePosition._meta.verbose_name, instance=pos.title),
            pos.message_for_disabled,
        )

    def test_is_enabled_or_die(self):
        sector = FakeSector.objects.create(title='Industry')
        with self.assertNoException():
            sector.is_enabled_or_die()

        # ---
        sector.disabled = now()
        with self.assertRaises(ConflictError) as cm:
            sector.is_enabled_or_die()
        self.assertEqual(sector.message_for_disabled, str(cm.exception))
