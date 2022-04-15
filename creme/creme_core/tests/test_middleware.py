from functools import partial

from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.core.workflow import WorkflowConditions
from creme.creme_core.models import (
    CremePropertyType,
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

from .base import CremeTestCase


class WorkflowMiddlewareTestCase(CremeTestCase):
    def test_simple(self):
        user1 = self.login_as_root_and_get()
        user2 = self.create_user()

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_bought', 'is bought by'),
            ('test-object_bought',  'buys'),
        )[0]
        orga1 = FakeOrganisation.objects.create(user=user2)

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

        name = 'NERV'
        self.assertNoFormError(
            self.client.post(
                FakeOrganisation.get_create_absolute_url(),
                data={'user': user2.id, 'name': name},
                # follow=True, we check that middleware has been executed with the POST request
            ),
            status=302,
        )
        orga2 = self.get_object_or_fail(FakeOrganisation, name=name)

        rel = self.assertHaveRelation(subject=orga2, type=rtype, object=orga1)
        self.assertEqual(user1, rel.user)

    def test_conditions__creation(self):
        user = self.login_as_root_and_get()

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
                    operator=operators.ENDSWITH, field_name='name', values=[' Corp'],
                )],
            ),
            actions=[PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        def create_orga(name):
            self.assertNoFormError(
                self.client.post(
                    FakeOrganisation.get_create_absolute_url(),
                    data={'user': user.id, 'name': name},
                    # NB: we check that middleware has been executed with the POST request
                    # follow=True,
                ),
                status=302,
            )
            return self.get_object_or_fail(FakeOrganisation, name=name)

        self.assertHasNoProperty(entity=create_orga('NERV'), ptype=ptype)
        self.assertHasProperty(entity=create_orga('Seele Corp'), ptype=ptype)

    def test_conditions__edition(self):
        user = self.login_as_root_and_get()

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
                    operator=operators.ENDSWITH, field_name='name', values=[suffix],
                )],
            ),
            actions=[PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        def edit_orga(orga, name, description):
            self.assertNoFormError(
                self.client.post(
                    orga.get_edit_absolute_url(),
                    data={'user': user.id, 'name': name, 'description': description},
                    # NB: we check that middleware has been executed with the POST request
                    # follow=True,
                ),
                status=302,
            )
            return self.refresh(orga)

        self.assertHasProperty(
            entity=edit_orga(
                orga=orga1,
                name=f'{orga1.name}{suffix}', description='Build mechas',
            ),
            ptype=ptype,
        )
        # No change => no action
        self.assertHasNoProperty(
            entity=edit_orga(
                orga=orga2, name=orga2.name, description='Be evil',
            ),
            ptype=ptype,
        )
