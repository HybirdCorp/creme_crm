from creme.creme_core.core.entity_filter import operators
from creme.creme_core.core.entity_filter.condition_handler import (
    PropertyConditionHandler,
    RegularFieldConditionHandler,
)
from creme.creme_core.models import (
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    RelationType,
    Workflow,
)
from creme.creme_core.workflows import (
    EntityCreationTrigger,
    PropertyAddingAction,
    RelationAddingAction,
    RelationAddingTrigger,
)

from ..base import CremeTestCase


class WorkflowTestCase(CremeTestCase):
    def test_manager_smart_create__trigger1(self):
        wf = Workflow.objects.smart_create(
            model=FakeContact,
            # TODO: we already know the model :think:
            trigger=EntityCreationTrigger(model='creme_core-fakecontact'),  # TODO: accept Model?
        )
        self.assertIsInstance(wf, Workflow)
        self.assertIsNotNone(wf.pk)
        self.assertEqual(FakeContact, wf.content_type.model_class())

        wf = self.refresh(wf)
        self.assertListEqual([], wf.conditions)
        self.assertListEqual([], wf.actions)

        trigger = wf.trigger
        self.assertIsInstance(trigger, EntityCreationTrigger)
        self.assertEqual(FakeContact, trigger.model)

    def test_manager_smart_create__trigger2(self):
        rtype = RelationType.objects.all()[0]

        wf = Workflow.objects.smart_create(
            model=FakeOrganisation,
            trigger=RelationAddingTrigger(rtype=rtype.id),  # TODO: accept RelationType?
        )
        self.assertIsInstance(wf, Workflow)
        self.assertIsNotNone(wf.pk)
        self.assertEqual(FakeOrganisation, wf.content_type.model_class())

        trigger = self.refresh(wf).trigger
        self.assertIsInstance(trigger, RelationAddingTrigger)
        self.assertEqual(rtype, trigger.relation_type)

    def test_manager_smart_create__conditions(self):
        cond_name1 = 'name'
        operator1 = operators.EQUALS
        values1 = ['Acme']

        ptype = CremePropertyType.objects.create(text='Kawaii')

        wf = Workflow.objects.smart_create(
            model=FakeOrganisation,
            trigger=EntityCreationTrigger(model='creme_core-fakeorganisation'),
            # TODO: use_or VS pass filter
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operator1, field_name=cond_name1, values=values1,
                ),
                PropertyConditionHandler.build_condition(
                    model=FakeOrganisation, ptype=ptype, has=True,
                ),
            ],
        )
        self.assertIsInstance(wf, Workflow)
        self.assertIsNotNone(wf.pk)
        self.assertEqual(FakeOrganisation, wf.content_type.model_class())

        wf = self.refresh(wf)
        conditions = wf.conditions
        self.assertIsList(conditions, length=2)

        condition1 = conditions[0]
        self.assertEqual(RegularFieldConditionHandler.type_id,           condition1.type)
        self.assertEqual(cond_name1,                                     condition1.name)
        self.assertDictEqual({'operator': operator1, 'values': values1}, condition1.value)

        condition2 = conditions[1]
        self.assertEqual(PropertyConditionHandler.type_id, condition2.type)
        self.assertEqual(str(ptype.uuid),                  condition2.name)
        self.assertDictEqual({'has': True},                condition2.value)

        self.assertListEqual([], wf.actions)

    def test_manager_smart_create__actions(self):
        ptype = CremePropertyType.objects.create(text='Is cool')
        rtype = RelationType.objects.all()[0]

        wf = Workflow.objects.smart_create(
            model=FakeOrganisation,
            trigger=EntityCreationTrigger(model='creme_core-fakeorganisation'),
            actions=[
                PropertyAddingAction(ptype=str(ptype.uuid)),  # TODO: accept CremePropertyType?
                RelationAddingAction(rtype=rtype.id),  # TODO: accept RelationType?
            ],
        )
        self.assertIsInstance(wf, Workflow)
        self.assertIsNotNone(wf.pk)
        self.assertEqual(FakeOrganisation, wf.content_type.model_class())

        wf = self.refresh(wf)
        self.assertListEqual([], wf.conditions)

        actions = wf.actions
        self.assertIsList(actions, length=2)

        action1 = actions[0]
        self.assertIsInstance(action1, PropertyAddingAction)
        self.assertEqual(ptype, action1.property_type)

        action2 = actions[1]
        self.assertIsInstance(action2, RelationAddingAction)
        self.assertEqual(rtype, action2.relation_type)
