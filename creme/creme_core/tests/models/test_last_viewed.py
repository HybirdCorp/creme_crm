from datetime import timedelta
from functools import partial

from django.test.utils import override_settings
from django.utils.timezone import now

from creme.creme_core.models import (
    FakeContact,
    FakeOrganisation,
    LastViewedEntity,
)

from ..base import CremeTestCase


@override_settings(LAST_ENTITIES_SIZE=3)
class LastViewedEntityTestCase(CremeTestCase):
    @staticmethod
    def _offset_viewed(lve, delta):
        LastViewedEntity.objects.filter(id=lve.id).update(viewed=now() - delta)

    def test_create(self):
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')
        contact3 = create_contact(first_name='Mycroft', last_name='Holmes')

        orga = FakeOrganisation.objects.create(user=user, name='Moriarty corp')

        now_value = now()
        lve1 = LastViewedEntity.objects.create(user=user, real_entity=contact1)
        self.assertEqual(user, lve1.user)
        self.assertEqual(contact1.entity_type, lve1.entity_ctype)
        self.assertEqual(contact1,             lve1.entity.get_real_entity())
        self.assertEqual(contact1,             lve1.real_entity)
        self.assertDatetimesAlmostEqual(lve1.viewed, now_value)

        lve2 = LastViewedEntity.objects.create(user=user, real_entity=contact2)
        self.assertEqual(user,     lve2.user)
        self.assertEqual(contact2, lve2.real_entity)

        lve3 = LastViewedEntity.objects.create(user=user, real_entity=orga)
        self.assertEqual(orga.entity_type, lve3.entity_ctype)
        self.assertEqual(orga,             lve3.real_entity)

        self.assertEqual(3, LastViewedEntity.objects.filter(user=user).count())

        self._offset_viewed(lve1, delta=timedelta(minutes=10))
        self._offset_viewed(lve2, delta=timedelta(minutes=5))
        self._offset_viewed(lve3, delta=timedelta(minutes=3))

        lve4 = LastViewedEntity.objects.create(user=user, real_entity=contact3)
        self.assertEqual(contact3, lve4.real_entity)
        self.assertDatetimesAlmostEqual(lve4.viewed, now())

        self.assertEqual(3, LastViewedEntity.objects.filter(user=user).count())
        self.assertEqual(lve1.pk, lve4.pk)

        # Other user ---
        other_user = self.create_user()
        lve_other = LastViewedEntity.objects.create(user=other_user, real_entity=contact2)
        self.assertEqual(other_user, lve_other.user)
        self.assertEqual(contact2,   lve_other.real_entity)

        self.assertEqual(1, LastViewedEntity.objects.filter(user=other_user).count())
        self.assertEqual(3, LastViewedEntity.objects.filter(user=user).count())

    def test_create__already_exists(self):
        "View an entity already is the list => update item."
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')

        lve1 = LastViewedEntity.objects.create(user=user, real_entity=contact1)
        lve2 = LastViewedEntity.objects.create(user=user, real_entity=contact2)

        self._offset_viewed(lve1, delta=timedelta(minutes=10))
        self._offset_viewed(lve2, delta=timedelta(minutes=5))

        lve1_again = LastViewedEntity.objects.create(user=user, real_entity=contact1)
        self.assertEqual(2, LastViewedEntity.objects.filter(user=user).count())
        self.assertDatetimesAlmostEqual(lve1_again.viewed, now())

    def test_create__too_much_items(self):
        "The settings value is set lower."
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')
        contact3 = create_contact(first_name='Mycroft', last_name='Holmes')

        orga = FakeOrganisation.objects.create(user=user, name='Moriarty corp')

        create_lve = partial(LastViewedEntity.objects.create, user=user)
        lve1 = create_lve(real_entity=contact1)
        lve2 = create_lve(real_entity=contact2)
        lve3 = create_lve(real_entity=contact3)

        self._offset_viewed(lve1, delta=timedelta(minutes=10))
        self._offset_viewed(lve2, delta=timedelta(minutes=5))
        self._offset_viewed(lve3, delta=timedelta(minutes=1))

        with override_settings(LAST_ENTITIES_SIZE=2):
            lve4 = LastViewedEntity.objects.create(user=user, real_entity=orga)
        self.assertCountEqual(
            [lve3, lve4],  # 2 items, not 3
            [*LastViewedEntity.objects.order_by('id')],
        )

    def test_create__deleted_entity(self):
        "Slots with entity marked as deleted are recycled in priority."
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')
        contact3 = create_contact(first_name='Mycroft', last_name='Holmes')

        create_lve = partial(LastViewedEntity.objects.create, user=user)
        lve1 = create_lve(real_entity=contact1)
        lve2 = create_lve(real_entity=contact2)

        self._offset_viewed(lve1, delta=timedelta(minutes=10))
        self._offset_viewed(lve2, delta=timedelta(minutes=5))

        contact2.trash()

        lve3 = create_lve(real_entity=contact3)
        self.assertEqual(lve3.real_entity, contact3)
        self.assertDatetimesAlmostEqual(lve3.viewed, now())
        self.assertEqual(2, LastViewedEntity.objects.filter(user=user).count())
        self.assertEqual(lve2.pk, lve3.pk)  # Instance has been recycled

    def test_delete_entity(self):
        user = self.get_root_user()
        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')

        create_lve = partial(LastViewedEntity.objects.create, user=user)
        lve1 = create_lve(real_entity=contact1)
        lve2 = create_lve(real_entity=contact2)

        contact2.delete()
        self.assertDoesNotExist(contact2)

        lve2 = self.assertStillExists(lve2)
        self.assertIsNone(lve2.entity_id)
        self.assertIsNone(lve2.entity)
        self.assertIsNone(lve2.real_entity)

        # Slots with NULL entity are replaced in priority ---
        self._offset_viewed(lve1, delta=timedelta(minutes=10))
        self._offset_viewed(lve2, delta=timedelta(minutes=5))

        contact3 = create_contact(first_name='Mycroft', last_name='Holmes')
        lve3 = create_lve(real_entity=contact3)
        self.assertEqual(lve3.real_entity, contact3)
        self.assertDatetimesAlmostEqual(lve3.viewed, now())
        self.assertEqual(2, LastViewedEntity.objects.filter(user=user).count())
        self.assertEqual(lve2.pk, lve3.pk)  # Instance has been recycled
