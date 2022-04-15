from functools import partial

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.workflow import (
    EntityCreated,
    EntityEdited,
    RelationAdded,
    WorkflowEvent,
    WorkflowEventQueue,
    WorkflowRegistry,
    workflow_registry,
)
from creme.creme_core.models import (
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    Relation,
    RelationType,
)
from creme.creme_core.workflows import (
    EntityCreationTrigger,
    EntityEditionTrigger,
    FixedEntitySource,
    FromContextSource,
    InstanceFieldSource,
    PropertyAddingAction,
    RelationAddingAction,
    RelationAddingTrigger,
)

from ..base import CremeTestCase


class WorkflowTestCase(CremeTestCase):
    def test_event__entity_created(self):
        entity = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')

        evt = EntityCreated(entity=entity)
        self.assertIsInstance(evt, WorkflowEvent)
        self.assertEqual(entity, evt.entity)

    def test_event__entity_edited(self):
        entity = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')

        evt = EntityEdited(entity=entity)
        self.assertIsInstance(evt, WorkflowEvent)
        self.assertEqual(entity, evt.entity)

    def test_event__relation_added(self):
        user = self.get_root_user()
        entity1 = FakeOrganisation.objects.create(user=user, name='Acme')
        entity2 = FakeContact.objects.create(user=user, first_name='Bugs', last_name='Bunny')
        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        rel = Relation.objects.create(
            subject_entity=entity1, type=rtype, object_entity=entity2, user=user,
        )

        evt = RelationAdded(relation=rel)
        self.assertIsInstance(evt, WorkflowEvent)
        self.assertEqual(rel, evt.relation)

    def test_event_queue(self):
        queue = WorkflowEventQueue()
        self.assertListEqual([], queue.pickup())

        # ---
        user = self.get_root_user()
        entity1 = FakeOrganisation.objects.create(user=user, name='Acme')
        entity2 = FakeContact.objects.create(user=user, first_name='Bugs', last_name='Bunny')

        queue.append(EntityCreated(entity=entity1)).append(EntityEdited(entity=entity2))

        events = queue.pickup()
        self.assertIsList(events, length=2)
        self.assertListEqual([], queue.pickup())

        evt1, evt2 = events
        self.assertIsInstance(evt1, EntityCreated)
        self.assertEqual(entity1, evt1.entity)
        self.assertIsInstance(evt2, EntityEdited)
        self.assertEqual(entity2, evt2.entity)

        # ---
        global_queue = WorkflowEventQueue.get_current()
        self.assertIsInstance(global_queue, WorkflowEventQueue)
        self.assertIs(global_queue, WorkflowEventQueue.get_current())

    def test_signal_handler__entity_created(self):
        queue = WorkflowEventQueue.get_current()
        queue.pickup()

        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        events = queue.pickup()
        self.assertEqual(1, len(events), events)

        event = events[0]
        self.assertIsInstance(event, EntityCreated)
        self.assertEqual(orga, event.entity)

    def test_signal_handler__entity_edited(self):
        queue = WorkflowEventQueue.get_current()

        orga = self.refresh(
            FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        )
        queue.pickup()

        orga.email = 'contact@acme.com'
        orga.save()
        events = queue.pickup()
        self.assertEqual(1, len(events), events)

        event = events[0]
        self.assertIsInstance(event, EntityEdited)
        self.assertEqual(orga, event.entity)

    def test_signal_handler__relation_added(self):
        queue = WorkflowEventQueue.get_current()

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

    def test_registry__register_triggers(self):
        registry = WorkflowRegistry()
        self.assertFalse([*registry.trigger_classes])

        registry.register_triggers(EntityCreationTrigger, RelationAddingTrigger)
        self.assertCountEqual(
            [EntityCreationTrigger, RelationAddingTrigger],
            [*registry.trigger_classes],
        )

        registry.unregister_triggers(EntityCreationTrigger)
        self.assertListEqual([RelationAddingTrigger], [*registry.trigger_classes])

    def test_registry__build_trigger(self):
        registry = WorkflowRegistry().register_triggers(
            EntityCreationTrigger, RelationAddingTrigger,
        )

        trigger1 = registry.build_trigger(
            EntityCreationTrigger(model='creme_core-fakecontact').to_dict()
        )
        self.assertIsInstance(trigger1, EntityCreationTrigger)
        self.assertEqual(FakeContact, trigger1.model)

        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        trigger2 = registry.build_trigger(
            RelationAddingTrigger(
                subject_model='creme_core-fakecontact',
                rtype=rtype.id,
                object_model='creme_core-fakeorganisation'
            ).to_dict()
        )
        self.assertIsInstance(trigger2, RelationAddingTrigger)
        self.assertEqual(FakeContact,      trigger2.subject_model)
        self.assertEqual(FakeOrganisation, trigger2.object_model)
        self.assertEqual(rtype,            trigger2.relation_type)

    def test_registry__register_action_sources(self):
        registry = WorkflowRegistry()
        self.assertFalse([*registry.action_source_classes])

        registry.register_action_sources(FromContextSource, FixedEntitySource)
        self.assertCountEqual(
            [FromContextSource, FixedEntitySource],
            [*registry.action_source_classes],
        )

        registry.unregister_action_sources(FromContextSource)
        self.assertListEqual([FixedEntitySource], [*registry.action_source_classes])

    def test_registry__register_actions(self):
        registry = WorkflowRegistry()
        self.assertFalse([*registry.action_classes])

        registry.register_actions(PropertyAddingAction, RelationAddingAction)
        self.assertCountEqual(
            [PropertyAddingAction, RelationAddingAction],
            [*registry.action_classes],
        )

        registry.unregister_actions(PropertyAddingAction)
        self.assertListEqual([RelationAddingAction], [*registry.action_classes])

    # TODO: test errors
    def test_registry__build_action_source(self):
        registry = WorkflowRegistry().register_action_sources(
            FromContextSource, FixedEntitySource, InstanceFieldSource,
        )

        context_key = 'modified'
        source1 = registry.build_action_source(
            FromContextSource(context_key=context_key).to_dict()
        )
        self.assertIsInstance(source1, FromContextSource)
        self.assertEqual(context_key, source1.context_key)

        # ---
        entity = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme1')
        source2 = registry.build_action_source(
            FixedEntitySource(entity=str(entity.uuid)).to_dict()
        )
        self.assertIsInstance(source2, FixedEntitySource)
        self.assertEqual(entity, source2.entity)

        # ---
        field_name = 'phone'
        context_key2 = 'subject'
        source3 = registry.build_action_source(
            InstanceFieldSource(
                field_name=field_name,
                instance_source=FromContextSource(context_key=context_key2),
            ).to_dict()
        )
        self.assertIsInstance(source3, InstanceFieldSource)
        self.assertEqual(field_name, source3.field_name)

        sub_source = source3.instance_source
        self.assertIsInstance(sub_source, FromContextSource)
        self.assertEqual(context_key2, sub_source.context_key)

    def test_registry__build_action(self):
        registry = WorkflowRegistry().register_actions(PropertyAddingAction, RelationAddingAction)

        ptype = CremePropertyType.objects.create(text='Is kawaiiii')
        ctxt_key = 'created'
        # TODO: several actions at once?
        action1 = registry.build_action(
            PropertyAddingAction(
                source=FromContextSource(ctxt_key),
                ptype=str(ptype.uuid),
            ).to_dict()
        )
        self.assertIsInstance(action1, PropertyAddingAction)
        self.assertEqual(ptype, action1.property_type)

        source1 = action1.source
        self.assertIsInstance(source1, FromContextSource)
        self.assertEqual(ctxt_key, source1.context_key)

        self.fail('complete')
        # rtype = RelationType.objects.get(id=REL_SUB_HAS)
        # action2 = registry.build_action(RelationAddingAction(rtype=rtype.id).to_dict())
        # self.assertIsInstance(action2, RelationAddingAction)
        # self.assertEqual(rtype, action2.relation_type)

    def test_registry__global(self):
        triggers = {*workflow_registry.trigger_classes}
        self.assertIn(EntityCreationTrigger, triggers)
        self.assertIn(EntityEditionTrigger,  triggers)
        self.assertIn(RelationAddingTrigger, triggers)

        action_sources = {*workflow_registry.action_source_classes}
        self.assertIn(FromContextSource,   action_sources)
        self.assertIn(FixedEntitySource,   action_sources)
        self.assertIn(InstanceFieldSource, action_sources)

        actions = {*workflow_registry.action_classes}
        self.assertIn(PropertyAddingAction, actions)
        self.assertIn(RelationAddingAction, actions)
