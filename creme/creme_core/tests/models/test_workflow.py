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
    EntityEditionTrigger,
    FixedEntitySource,
    FromContextSource,
    PropertyAddingAction,
    RelationAddingAction,
    RelationAddingTrigger,
)

from ..base import CremeTestCase


class WorkflowTestCase(CremeTestCase):
    def test_trigger(self):
        wf = self.refresh(
            Workflow.objects.create(
                content_type=FakeContact,
                trigger=EntityEditionTrigger(model=FakeOrganisation),
            )
        )
        self.assertEqual(EntityEditionTrigger(model=FakeOrganisation), wf.trigger)

    def test_manager_smart_create__trigger1(self):
        wf = Workflow.objects.smart_create(
            model=FakeContact,
            # TODO: we already know the model => check?
            trigger=EntityCreationTrigger(model=FakeContact),
        )
        self.assertIsInstance(wf, Workflow)
        self.assertIsNotNone(wf.pk)
        self.assertEqual(FakeContact, wf.content_type.model_class())

        wf = self.refresh(wf)
        self.assertListEqual([], wf.conditions)
        self.assertListEqual([], wf.actions)
        self.assertEqual(EntityCreationTrigger(model=FakeContact), wf.trigger)

    def test_manager_smart_create__trigger2(self):
        rtype = RelationType.objects.all()[0]

        wf = Workflow.objects.smart_create(
            model=FakeOrganisation,
            trigger=RelationAddingTrigger(
                subject_model=FakeOrganisation,
                rtype=rtype,
                object_model=FakeContact,
            ),
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
            trigger=EntityCreationTrigger(model=FakeOrganisation),
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
        entity = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        ptype = CremePropertyType.objects.create(text='Is cool')
        rtype = RelationType.objects.all()[0]

        wf = Workflow.objects.smart_create(
            model=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            actions=[
                PropertyAddingAction(
                    entity_source=FromContextSource(EntityCreationTrigger.CREATED),
                    ptype=ptype,
                ),
                RelationAddingAction(
                    subject_source=FromContextSource(EntityCreationTrigger.CREATED),
                    rtype=rtype,
                    object_source=FixedEntitySource(entity=entity),
                ),
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
        self.assertEqual(
            FromContextSource(EntityCreationTrigger.CREATED),
            action1.entity_source,
        )

        action2 = actions[1]
        self.assertIsInstance(action2, RelationAddingAction)
        self.assertEqual(rtype, action2.relation_type)
        # TODO: need __eq__
        # self.assertListEqual(
        #     [
        #         PropertyAddingAction(
        #             entity_source=FromContextSource(EntityCreationTrigger.CREATED),
        #             ptype=ptype,
        #         ),
        #         RelationAddingAction(
        #             subject_source=FromContextSource(EntityCreationTrigger.CREATED),
        #             rtype=rtype,
        #             object_source=FixedEntitySource(entity=entity),
        #         ),
        #     ],
        #     wf.actions,
        # )
