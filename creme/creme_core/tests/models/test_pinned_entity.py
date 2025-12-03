from functools import partial

from django.db import IntegrityError
from django.db.transaction import atomic
from django.test.utils import override_settings
from django.utils.timezone import now

from creme.creme_core.models import FakeContact, FakeOrganisation, PinnedEntity
from creme.creme_core.models.pinned_entity import PinnedEntities

from ..base import CremeTestCase


class PinnedEntityTestCase(CremeTestCase):
    def test_create(self):
        user = self.get_root_user()
        contact = FakeContact.objects.create(
            user=user, first_name='Sherlock', last_name='Holmes',
        )
        orga = FakeOrganisation.objects.create(user=user, name='Moriarty corp')

        pinned1 = PinnedEntity.objects.create(user=user, real_entity=contact)
        self.assertEqual(user, pinned1.user)
        self.assertEqual(contact.entity_type, pinned1.entity_ctype)
        self.assertEqual(contact,             pinned1.entity.get_real_entity())
        self.assertEqual(contact,             pinned1.real_entity)
        self.assertDatetimesAlmostEqual(pinned1.created, now())

        pinned2 = PinnedEntity.objects.create(user=user, real_entity=orga)
        self.assertEqual(orga.entity_type, pinned2.entity_ctype)
        self.assertEqual(orga,             pinned2.real_entity)

        # Uniqueness ---
        with self.assertRaises(IntegrityError):
            with atomic():
                PinnedEntity.objects.create(user=user, real_entity=contact)

        # Other user ---
        other_user = self.create_user()
        other_pinned = PinnedEntity.objects.create(user=other_user, real_entity=contact)
        self.assertEqual(other_user, other_pinned.user)
        self.assertEqual(contact,    other_pinned.real_entity)

    def test_delete_entity(self):
        user = self.get_root_user()
        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')

        create_pinned = partial(PinnedEntity.objects.create, user=user)
        pinned1 = create_pinned(real_entity=contact1)
        pinned2 = create_pinned(real_entity=contact2)

        contact2.delete()
        self.assertDoesNotExist(contact2)
        self.assertDoesNotExist(pinned2)
        self.assertStillExists(pinned1)

    def test_manager__safe_create(self):
        user = self.get_root_user()
        contact = FakeContact.objects.create(
            user=user, first_name='Sherlock', last_name='Holmes',
        )

        PinnedEntity.objects.safe_create(user=user, real_entity=contact)
        pinned = self.get_alone_element(PinnedEntity.objects.all())
        self.assertEqual(user, pinned.user)
        self.assertEqual(contact.entity_type, pinned.entity_ctype)
        self.assertEqual(contact,             pinned.entity.get_real_entity())
        self.assertEqual(contact,             pinned.real_entity)
        self.assertDatetimesAlmostEqual(pinned.created, now())

        with self.assertLogs(level='ERROR'):
            with self.assertNoException():
                PinnedEntity.objects.safe_create(user=user, real_entity=contact)

    @override_settings(PINNED_ENTITIES_SIZE=3)
    def test_pinned_entities__empty(self):
        user = self.get_root_user()
        entities = PinnedEntities(user=user)
        self.assertFalse([*entities])
        self.assertEqual(user, entities.user)
        self.assertIs(entities.max_is_reached, False)

    @override_settings(PINNED_ENTITIES_SIZE=3)
    def test_pinned_entities__max_not_reached(self):
        user = self.get_root_user()
        other_user = self.create_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')

        orga = FakeOrganisation.objects.create(user=user, name='Moriarty corp')

        create_pinned = PinnedEntity.objects.create
        pinned1 = create_pinned(user=user, real_entity=contact1)
        pinned2 = create_pinned(user=user, real_entity=orga)
        other_pinned = create_pinned(user=other_user, real_entity=contact2)

        with override_settings(PINNED_ENTITIES_SIZE=3):
            # 3: 1 for PinnedEntity, 2 to prefetch FakeContact & FakeOrganisation
            with self.assertNumQueries(3):
                all_pinned = PinnedEntities(user=user)

        content = [*all_pinned]
        self.assertListEqual([pinned1, pinned2], content)

        with self.assertNumQueries(0):
            self.assertEqual(2, len([*all_pinned]))

        with self.assertNumQueries(0):
            self.assertIs(all_pinned.max_is_reached, False)

        with self.assertNumQueries(0):
            self.assertIs(all_pinned.is_pinned(contact1), True)
            self.assertIs(all_pinned.is_pinned(orga), True)
            self.assertIs(all_pinned.is_pinned(contact2), False)

        with self.assertNumQueries(0):
            self.assertEqual(contact1, content[0].real_entity)

        # Other user ---
        other_user_pinned = PinnedEntities(user=other_user)
        self.assertEqual(other_user, other_user_pinned.user)
        self.assertListEqual([other_pinned], [*other_user_pinned])

    @override_settings(PINNED_ENTITIES_SIZE=2)
    def test_pinned_entities__max_is_reached(self):
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')
        contact3 = create_contact(first_name='Mycroft', last_name='Holmes')

        create_pinned = PinnedEntity.objects.create
        pinned1 = create_pinned(user=user, real_entity=contact1)
        pinned2 = create_pinned(user=user, real_entity=contact2)

        all_pinned = PinnedEntities(user=user)
        self.assertListEqual([pinned1, pinned2], [*all_pinned])
        self.assertIs(all_pinned.max_is_reached, True)

        with self.assertNumQueries(0):
            self.assertIs(all_pinned.is_pinned(contact1), True)
            self.assertIs(all_pinned.is_pinned(contact2), True)
            self.assertIs(all_pinned.is_pinned(contact3), False)

    @override_settings(PINNED_ENTITIES_SIZE=9)
    def test_pinned_entities__explicit_size(self):
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')

        create_pinned = partial(PinnedEntity.objects.create, user=user)
        pinned1 = create_pinned(real_entity=contact1)
        pinned2 = create_pinned(real_entity=contact2)

        all_pinned = PinnedEntities(user=user, max_size=2)
        self.assertListEqual([pinned1, pinned2], [*all_pinned])
        self.assertIs(all_pinned.max_is_reached, True)

    def test_pinned_entities__limited(self):
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Sherlock', last_name='Holmes')
        contact2 = create_contact(first_name='John', last_name='Watson')
        contact3 = create_contact(first_name='Mycroft', last_name='Holmes')

        orga = FakeOrganisation.objects.create(user=user, name='Moriarty corp')

        create_pinned = partial(PinnedEntity.objects.create, user=user)
        pinned1 = create_pinned(real_entity=contact1)
        pinned2 = create_pinned(real_entity=contact2)
        create_pinned(real_entity=contact3)
        create_pinned(real_entity=orga, user=self.create_user())

        with self.assertLogs(level='WARNING'):
            all_pinned = PinnedEntities(user=user, max_size=2)

        self.assertListEqual([pinned1, pinned2], [*all_pinned])
        self.assertIs(all_pinned.max_is_reached, True)

        with self.assertNumQueries(0):
            self.assertIs(all_pinned.is_pinned(contact1), True)
            self.assertIs(all_pinned.is_pinned(contact2), True)

        with self.assertNumQueries(1):
            self.assertIs(all_pinned.is_pinned(contact3), True)

        with self.assertNumQueries(1):
            self.assertIs(all_pinned.is_pinned(orga), False)

    def test_pinned_entities__get_for_user(self):
        user = self.login_as_root_and_get()

        with self.assertNumQueries(1):
            my_pinned = PinnedEntities.get_for_user(user)
        self.assertIsInstance(my_pinned, PinnedEntities)
        self.assertEqual(user, my_pinned.user)

        with self.assertNumQueries(0):
            self.assertIs(my_pinned, PinnedEntities.get_for_user(user))
