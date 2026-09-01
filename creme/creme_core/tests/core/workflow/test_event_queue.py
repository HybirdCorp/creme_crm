from functools import partial

from django.db.utils import IntegrityError

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.workflow import (
    EntityCreated,
    EntityEdited,
    PropertyAdded,
    RelationAdded,
    WorkflowEngine,
    WorkflowEventQueue,
)
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    Language,
    Relation,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase


class WorkflowEventQueueTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        user = cls.get_root_user()
        cls.entity1 = FakeOrganisation.objects.create(user=user, name='Acme')
        cls.entity2 = FakeContact.objects.create(
            user=user, first_name='Bugs', last_name='Bunny',
        )

    def test_basic(self):
        queue = WorkflowEventQueue()
        self.assertFalse(queue)
        self.assertEqual(0, len(queue))
        self.assertListEqual([], queue.pickup())

        # ---
        queue.append(EntityCreated(entity=self.entity1)).append(EntityEdited(entity=self.entity2))
        self.assertTrue(queue)
        self.assertEqual(2, len(queue))
        self.assertListEqual(
            [EntityCreated(entity=self.entity1), EntityEdited(entity=self.entity2)],
            queue.pickup(),
        )
        self.assertListEqual([], queue.pickup())

    def test_slice(self):
        queue = WorkflowEventQueue()
        self.assertListEqual([], queue.pickup(start=1))

        # ---
        queue.append(EntityCreated(entity=self.entity1)).append(EntityEdited(entity=self.entity2))
        self.assertListEqual(
            [EntityEdited(entity=self.entity2)], queue.pickup(start=1),
        )
        self.assertListEqual(
            [EntityCreated(entity=self.entity1)], queue.pickup(start=0),
        )
        self.assertListEqual([], queue.pickup())

    def test_duplicate(self):
        queue = WorkflowEventQueue().append(
            EntityCreated(entity=self.entity1)
        ).append(
            EntityEdited(entity=self.entity2)
        ).append(
            EntityCreated(entity=self.entity1)  # Should not be appended
        )
        self.assertListEqual(
            [EntityCreated(entity=self.entity1), EntityEdited(entity=self.entity2)],
            queue.pickup(),
        )

    def test_inhibited(self):
        queue = WorkflowEventQueue().append(
            EntityCreated(entity=self.entity1)
        ).append(
            EntityEdited(entity=self.entity2)
        ).append(
            EntityEdited(entity=self.entity1)  # Should not be appended
        )
        self.assertListEqual(
            [EntityCreated(entity=self.entity1), EntityEdited(entity=self.entity2)],
            queue.pickup(),
        )


class SignalHandlersTestCase(CremeTestCase):
    def test_entity_created(self):
        queue = WorkflowEngine.get_current()._queue  # TODO: meh
        queue.pickup()

        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        events = queue.pickup()

        event = self.get_alone_element(events)
        self.assertIsInstance(event, EntityCreated)
        self.assertEqual(orga, event.entity)

    def test_entity_created__error(self):
        queue = WorkflowEngine.get_current()._queue  # TODO: meh
        queue.pickup()

        with self.assertRaises(IntegrityError):
            FakeOrganisation.objects.create(
                # user=...,
                name='Acme',
            )
        self.assertFalse(queue.pickup())

    def test_entity_edited(self):
        queue = WorkflowEngine.get_current()._queue  # TODO: meh

        orga = self.refresh(
            FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        )
        queue.pickup()

        orga.email = 'contact@acme.com'
        orga.save()
        events = queue.pickup()

        event = self.get_alone_element(events)
        self.assertIsInstance(event, EntityEdited)
        self.assertEqual(orga, event.entity)

    def test_entity_edited__m2m(self):
        queue = WorkflowEngine.get_current()._queue  # TODO: meh

        l1, l2 = Language.objects.all()[:2]
        contact = self.refresh(FakeContact.objects.create(
            user=self.get_root_user(), first_name='Bugs', last_name='Bunny',
        ))
        queue.pickup()

        contact.languages.set([l1])
        expected = EntityEdited(entity=contact)
        self.assertEqual(expected, self.get_alone_element(queue.pickup()))

        # ----
        contact.languages.add(l2)
        self.assertEqual(expected, self.get_alone_element(queue.pickup()))

        # ----
        contact.languages.remove(l1)
        self.assertEqual(expected, self.get_alone_element(queue.pickup()))

        # ----
        contact.languages.clear()
        self.assertEqual(expected, self.get_alone_element(queue.pickup()))

    def test_property_added(self):
        queue = WorkflowEngine.get_current()._queue  # TODO: meh

        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')

        ptype = CremePropertyType.objects.create(text='Important')
        queue.pickup()

        prop = CremeProperty.objects.create(creme_entity=orga, type=ptype)
        events = queue.pickup()

        event = self.get_alone_element(events)
        self.assertIsInstance(event, PropertyAdded)
        self.assertEqual(prop, event.creme_property)

    def test_relation_added(self):
        queue = WorkflowEngine.get_current()._queue  # TODO: meh

        user = self.get_root_user()
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Acme1')
        orga2 = create_orga(name='Acme2')

        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        queue.pickup()

        rel = Relation.objects.create(
            user=user, subject_entity=orga1, type=rtype, object_entity=orga2,
        )
        events = queue.pickup()
        self.assertEqual(2, len(events), events)

        event1 = events[0]
        self.assertIsInstance(event1, RelationAdded)
        self.assertEqual(rel, event1.relation)

        event2 = events[1]
        self.assertIsInstance(event2, RelationAdded)
        self.assertEqual(rel.symmetric_relation, event2.relation)
