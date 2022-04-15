from functools import partial

from creme.creme_core.core.workflow import (
    SingleEntitySource,
    WorkflowRegistry,
    workflow_registry,
)
from creme.creme_core.models import (
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    RelationType,
)
from creme.creme_core.workflows import (
    EntityCreationTrigger,
    EntityEditionTrigger,
    PropertyAddingAction,
    RelationAddingAction,
    RelationAddingTrigger,
)

from ..base import CremeTestCase


class WorkflowTestCase(CremeTestCase):
    def test_source__single_entity(self):
        id1 = 'created'
        model1 = FakeOrganisation
        source = SingleEntitySource(id=id1, model=model1)
        self.assertEqual(id1,   source.id)
        self.assertEqual(model1, source.model)
        self.assertEqual('Test Organisation', source.label)

        create_orga = partial(FakeOrganisation.objects.create, user=self.get_root_user())
        entity1 = create_orga(name='Acme1')
        entity2 = create_orga(name='Acme2')
        self.assertEqual(entity1, source.extract({id1: entity1, 'other': entity2}))

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

        rtype = RelationType.objects.all()[0]
        trigger2 = registry.build_trigger(RelationAddingTrigger(rtype=rtype.id).to_dict())
        self.assertIsInstance(trigger2, RelationAddingTrigger)
        self.assertEqual(rtype, trigger2.relation_type)

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

    def test_registry__build_action(self):
        registry = WorkflowRegistry().register_actions(PropertyAddingAction, RelationAddingAction)

        ptype = CremePropertyType.objects.create(text='Is kawaiiii')
        # TODO: several actions at once?
        action1 = registry.build_action(PropertyAddingAction(ptype=str(ptype.uuid)).to_dict())
        self.assertIsInstance(action1, PropertyAddingAction)
        self.assertEqual(ptype, action1.property_type)

        rtype = RelationType.objects.all()[0]
        action2 = registry.build_action(RelationAddingAction(rtype=rtype.id).to_dict())
        self.assertIsInstance(action2, RelationAddingAction)
        self.assertEqual(rtype, action2.relation_type)

    def test_registry__global(self):
        triggers = {*workflow_registry.trigger_classes}
        self.assertIn(EntityCreationTrigger, triggers)
        self.assertIn(EntityEditionTrigger,  triggers)
        self.assertIn(RelationAddingTrigger, triggers)

        actions = {*workflow_registry.action_classes}
        self.assertIn(PropertyAddingAction, actions)
        self.assertIn(RelationAddingAction, actions)
