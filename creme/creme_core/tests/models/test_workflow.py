import uuid

from django.utils.translation import gettext as _

from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.core.workflow import WorkflowConditions
from creme.creme_core.models import (
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    RelationType,
    Workflow,
)
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    EntityCreationTrigger,
    EntityEditionTrigger,
    FixedEntitySource,
    PropertyAddingAction,
    RelationAddingAction,
)

from ..base import CremeTestCase


class WorkflowTestCase(CremeTestCase):
    def test_create(self):
        title = 'My awesome workflow'
        wf = self.refresh(
            Workflow.objects.create(
                title=title,
                content_type=FakeContact,
                trigger=EntityEditionTrigger(model=FakeOrganisation),
            )
        )
        self.assertEqual(title, wf.title)
        self.assertEqual(title, str(wf))
        self.assertIsInstance(wf.uuid, uuid.UUID)
        self.assertIs(wf.enabled, True)
        self.assertIs(wf.is_custom, True)
        self.assertEqual(EntityEditionTrigger(model=FakeOrganisation), wf.trigger)
        self.assertTupleEqual((), wf.actions)

        conditions = wf.conditions
        self.assertIsInstance(conditions, WorkflowConditions)
        self.assertFalse([*conditions.descriptions(user=self.get_root_user())])

    def test_create__disabled(self):
        "Enabled=False, other model..."
        wf = Workflow.objects.create(
            title='Organisation flow',
            content_type=FakeOrganisation,
            enabled=False,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
        )
        self.assertIsInstance(wf, Workflow)
        self.assertIsNotNone(wf.pk)
        self.assertFalse(wf.enabled)
        self.assertEqual(FakeOrganisation, wf.content_type.model_class())

    def test_trigger(self):
        wf = self.refresh(
            Workflow.objects.create(
                title='My workflow',
                content_type=FakeContact,
                trigger=EntityCreationTrigger(model=FakeContact),
            )
        )

        trigger1 = wf.trigger
        self.assertEqual(EntityCreationTrigger(model=FakeContact), trigger1)
        self.assertIs(trigger1, wf.trigger)  # Test cache

        # Set --
        wf.trigger = EntityEditionTrigger(model=FakeContact)
        self.assertEqual(EntityEditionTrigger(model=FakeContact), wf.trigger)

    def test_actions(self):
        entity = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        ptype = CremePropertyType.objects.create(text='Is cool')
        rtype = RelationType.objects.all()[0]

        wf = Workflow.objects.create(
            title='Organisation flow',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=FakeOrganisation),
                    ptype=ptype,
                ),
                RelationAddingAction(
                    subject_source=CreatedEntitySource(model=FakeOrganisation),
                    rtype=rtype,
                    object_source=FixedEntitySource(entity=entity),
                ),
            ],
        )

        wf = self.refresh(wf)
        stored_actions = wf.actions
        self.assertTupleEqual(
            (
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=FakeOrganisation),
                    ptype=ptype,
                ),
                RelationAddingAction(
                    subject_source=CreatedEntitySource(model=FakeOrganisation),
                    rtype=rtype,
                    object_source=FixedEntitySource(entity=entity),
                ),
            ),
            stored_actions,
        )
        self.assertIs(stored_actions, wf.actions)  # Test cache

        # Set ---
        wf.actions = [
            PropertyAddingAction(
                entity_source=EditedEntitySource(model=FakeOrganisation),
                ptype=ptype,
            ),
        ]
        self.assertTupleEqual(
            (
                PropertyAddingAction(
                    entity_source=EditedEntitySource(model=FakeOrganisation),
                    ptype=ptype,
                ),
            ),
            wf.actions,
        )

    def test_conditions(self):
        source = CreatedEntitySource(model=FakeOrganisation)

        def cond_for_value(value):
            return condition_handler.RegularFieldConditionHandler.build_condition(
                model=FakeOrganisation,
                operator=operators.EQUALS, field_name='name', values=[value],
            )

        def desc_for_value(value):
            return (
                '{label}'
                '<ul>'
                ' <li>{condition}</li>'
                '</ul>'
            ).format(
                label=_('Conditions on «{source}»:').format(
                    source=source.render(user=user, mode=source.RenderMode.HTML),
                ),
                condition=_('«{field}» is {values}').format(
                    field=_('Name'),
                    values=_('«{enum_value}»').format(enum_value=value),
                ),
            )

        cond_value1 = 'Acme'
        wf = Workflow.objects.create(
            title='My WF',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            conditions=WorkflowConditions().add(
                source=source, conditions=[cond_for_value(cond_value1)],
            ),
        )

        wf = self.refresh(wf)
        conditions = wf.conditions
        self.assertIsInstance(conditions, WorkflowConditions)

        user = self.get_root_user()
        descriptions1 = [*conditions.descriptions(user=user)]
        self.assertEqual(1, len(descriptions1), descriptions1)

        self.assertHTMLEqual(desc_for_value(cond_value1), descriptions1[0])

        # Cache
        self.assertIs(conditions, wf.conditions)

        # Invalid cache
        cond_value2 = 'AcmeCorp'
        wf.conditions = WorkflowConditions().add(
            source=source, conditions=[cond_for_value(cond_value2)],
        )

        descriptions2 = [*wf.conditions.descriptions(user=user)]
        self.assertEqual(1, len(descriptions2), descriptions2)
        self.assertHTMLEqual(desc_for_value(cond_value2), descriptions2[0])
