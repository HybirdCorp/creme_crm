from functools import partial

from django.db.transaction import atomic
from django.utils.timezone import now

from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.core.workflow import WorkflowConditions, WorkflowEngine
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    FakeOrganisation,
    RelationType,
    Workflow,
)
from creme.creme_core.tests.base import CremeTestCase, CremeTransactionTestCase
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    EntityCreationTrigger,
    EntityEditionTrigger,
    FixedEntitySource,
    PropertyAddingAction,
    RelationAddingAction,
)


class WorkflowEngineTestCase(CremeTestCase):
    def test_simple(self):
        user1 = self.get_root_user()
        user2 = self.create_user()

        rtype = RelationType.objects.builder(
            id='test-subject_bought', predicate='is bought by',
        ).symmetric(id='test-object_bought', predicate='buys').get_or_create()[0]
        orga1 = FakeOrganisation.objects.create(user=user2, name='Acme')

        Workflow.objects.create(
            title='Created Organisations are cool',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            actions=[
                RelationAddingAction(
                    subject_source=CreatedEntitySource(model=FakeOrganisation),
                    rtype=rtype.id,
                    object_source=FixedEntitySource(entity=orga1),
                )
            ],
        )

        wf_engine = WorkflowEngine.get_current()
        self.assertIsInstance(wf_engine, WorkflowEngine)

        with wf_engine.run(user=user1):
            orga2 = FakeOrganisation.objects.create(user=user2, name='NERV')

        rel = self.assertHaveRelation(subject=orga2, type=rtype, object=orga1)
        self.assertEqual(user1, rel.user)

    def test_disabled(self):
        user = self.get_root_user()

        ptype = CremePropertyType.objects.create(text='Is cool')
        Workflow.objects.create(
            title='Created Organisations are cool',
            # enabled=False,
            disabled=now(),
            disabling_reason='Deprecated',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=FakeOrganisation),
                    ptype=ptype,
                ),
            ],
        )

        with WorkflowEngine.get_current().run(user=user):
            orga = FakeOrganisation.objects.create(user=user, name='NERV')
        self.assertHasNoProperty(entity=orga, ptype=ptype)

    def test_conditions__creation(self):
        user = self.get_root_user()

        ptype = CremePropertyType.objects.create(text='Is cool')
        source = CreatedEntitySource(model=FakeOrganisation)
        Workflow.objects.create(
            title='Created Corporations are cool',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.EndsWithOperator, field_name='name', values=[' Corp'],
                )],
            ),
            actions=[PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)

        with WorkflowEngine.get_current().run(user=None):
            orga1 = create_orga(name='NERV')
            orga2 = create_orga(name='Seele Corp')

        self.assertHasNoProperty(entity=orga1, ptype=ptype)
        self.assertHasProperty(entity=orga2, ptype=ptype)

    def test_conditions__edition__one_condition(self):
        user = self.get_root_user()

        ptype = CremePropertyType.objects.create(text='Is cool')
        suffix = ' Corp'

        model = FakeOrganisation
        create_orga = partial(model.objects.create, user=user)
        orga1 = create_orga(name='NERV')
        orga2 = create_orga(name=f'Seele{suffix}')

        source = EditedEntitySource(model=model)
        Workflow.objects.create(
            title='Edited Corporations are cool',
            content_type=model,
            trigger=EntityEditionTrigger(model=model),
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[condition_handler.RegularFieldConditionHandler.build_condition(
                    model=model,
                    operator=operators.EndsWithOperator, field_name='name', values=[suffix],
                )],
            ),
            actions=[PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        def edit_orga(orga, name, description):
            orga = self.refresh(orga)
            orga.name = name
            orga.description = description
            orga.save()

        self.clear_global_info()  # Empty the queue to allow edition events

        with WorkflowEngine.get_current().run(user=None):
            edit_orga(orga=orga1, name=f'{orga1.name}{suffix}', description='Build mechas')
            edit_orga(orga=orga2, name=orga2.name, description='Be evil')

        self.assertHasProperty(entity=orga1, ptype=ptype)
        self.assertHasNoProperty(entity=orga2, ptype=ptype)  # No change => no action

    def test_conditions__edition__two_conditions(self):
        user = self.get_root_user()

        ptype = CremePropertyType.objects.create(text='Is cool')
        name_suffix = ' Corp'
        email_suffix = '.org'

        model = FakeOrganisation
        source = EditedEntitySource(model=model)
        build_condition = partial(
            condition_handler.RegularFieldConditionHandler.build_condition,
            model=model, operator=operators.EndsWithOperator,
        )
        Workflow.objects.create(
            title='Edited Corporations are cool',
            content_type=model,
            trigger=EntityEditionTrigger(model=model),
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[
                    build_condition(field_name='name', values=[name_suffix]),
                    build_condition(field_name='email', values=[email_suffix]),
                ],
            ),
            actions=[PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        orga = self.refresh(model.objects.create(user=user, name='NERV'))
        self.clear_global_info()  # Empty the queue to allow edition events

        with WorkflowEngine.get_current().run(user=None):
            orga.name = f'{orga.name}{name_suffix}'
            orga.email = 'nerv@contact.jp'
            orga.save()

        self.assertHasProperty(entity=orga, ptype=ptype)

    def test_nested_contexts(self):
        user = self.get_root_user()

        ptype = CremePropertyType.objects.create(text='Is cool')
        source = CreatedEntitySource(model=FakeOrganisation)
        suffix = ' Corp'
        Workflow.objects.create(
            title='Created Corporations are cool',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.EndsWithOperator, field_name='name', values=[suffix],
                )],
            ),
            actions=[PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        create_orga = partial(FakeOrganisation.objects.create, user=user)

        self.clear_global_info()  # Empty the queue to test is length
        engine = WorkflowEngine.get_current()

        # with WorkflowEngine.get_current().run(user=None):
        with engine.run(user=None):
            orga1 = create_orga(name=f'NERV{suffix}')

            with WorkflowEngine.get_current().run(user=None):
                orga2 = create_orga(name=f'Seele{suffix}')
                self.assertEqual(2, len(engine._queue))  # Meh

            self.assertHasNoProperty(entity=orga1, ptype=ptype)
            self.assertHasProperty(entity=orga2, ptype=ptype)
            self.assertEqual(1, len(engine._queue))  # Meh

        self.assertHasProperty(entity=orga1, ptype=ptype)
        self.assertEqual(0, len(engine._queue))  # Meh


class WorkflowEngineRollbackTestCase(CremeTransactionTestCase):
    def test_creation(self):
        user = self.create_user()

        ptype = CremePropertyType.objects.create(text='Is cool')
        source = CreatedEntitySource(model=FakeOrganisation)
        Workflow.objects.create(
            title='Created Corporations are cool',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[condition_handler.RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.EndsWithOperator, field_name='name', values=[' Corp'],
                )],
            ),
            actions=[PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        orga_count = FakeOrganisation.objects.count()
        create_orga = partial(FakeOrganisation.objects.create, user=user)

        try:
            with atomic(), WorkflowEngine.get_current().run(user=None):
                create_orga(name='NERV')
                create_orga(name='Seele Corp')
                raise ValueError('Rollback now!!')
        except ValueError:
            pass
        else:
            self.fail('??')  # pragma: no cover

        self.assertEqual(orga_count, FakeOrganisation.objects.count())
        self.assertFalse(CremeProperty.objects.filter(type=ptype))

    def test_edition(self):
        user = self.create_user()

        ptype = CremePropertyType.objects.create(text='Is cool')
        suffix = ' Corp'

        model = FakeOrganisation
        name1 = 'NERV'
        name2 = f'Seele{suffix}'

        create_orga = partial(model.objects.create, user=user)
        orga1 = create_orga(name=name1)
        orga2 = create_orga(name=name2)

        source = EditedEntitySource(model=model)
        Workflow.objects.create(
            title='Edited Corporations are cool',
            content_type=model,
            trigger=EntityEditionTrigger(model=model),
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[condition_handler.RegularFieldConditionHandler.build_condition(
                    model=model,
                    operator=operators.EndsWithOperator, field_name='name', values=[suffix],
                )],
            ),
            actions=[PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        def edit_orga(orga, name, description):
            orga = self.refresh(orga)
            orga.name = name
            orga.description = description
            orga.save()

        self.clear_global_info()  # Empty the queue to allow edition events

        engine = WorkflowEngine.get_current()

        try:
            with atomic(), engine.run(user=None):
                edit_orga(orga=orga1, name=f'{orga1.name}{suffix}', description='Build mechas')
                edit_orga(orga=orga2, name=orga2.name, description='Be evil')
                raise ValueError('Rollback now!!')
        except ValueError:
            pass
        else:
            self.fail('??')  # pragma: no cover

        self.assertEqual(0, len(engine._queue))  # Meh

        orga1 = self.refresh(orga1)
        self.assertEqual(name1, orga1.name)

        orga2 = self.refresh(orga2)
        self.assertEqual(name2, orga2.name)

        self.assertHasNoProperty(entity=orga1, ptype=ptype)
        # self.assertHasNoProperty(entity=orga2, ptype=ptype)  # No change => no action
