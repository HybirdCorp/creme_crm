from functools import partial

from django.utils.translation import gettext as _

from creme.creme_core.models import (
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    RelationType,
)
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    EntityCreationTrigger,
    EntityEditionTrigger,
    PropertyAddingAction,
    RelationAddingAction,
    RelationAddingTrigger,
)

from .base import CremeTestCase


class WorkflowsTestCase(CremeTestCase):
    def test_trigger__entity_creation(self):
        type_id = 'creme_core-entity_creation'
        self.assertEqual(type_id, EntityCreationTrigger.type_id)
        self.assertEqual(
            _('An entity has been created'), EntityCreationTrigger.verbose_name,
        )

        model_key = 'creme_core-fakecontact'
        trigger = EntityCreationTrigger(model=model_key)
        self.assertEqual(FakeContact, trigger.model)
        self.assertDictEqual(
            {'type': type_id, 'model': model_key}, trigger.to_dict(),
        )
        self.assertEqual(
            _('A «{}» has been created').format('Test Contact'),
            trigger.description,
        )

        with self.assertNoException():
            EntityCreationTrigger(type=type_id, model=model_key)

    def test_trigger__entity_edition(self):
        type_id = 'creme_core-entity_edition'
        self.assertEqual(type_id, EntityEditionTrigger.type_id)
        self.assertEqual(
            _('An entity has been modified'), EntityEditionTrigger.verbose_name,
        )

        model_key = 'creme_core-fakeorganisation'
        trigger = EntityEditionTrigger(model=model_key)
        self.assertEqual(FakeOrganisation, trigger.model)
        self.assertDictEqual(
            {'type': type_id, 'model': model_key}, trigger.to_dict(),
        )
        self.assertEqual(
            _('A «{}» has been modified').format('Test Organisation'),
            trigger.description,
        )

    def test_trigger__relation_adding(self):
        type_id = 'creme_core-relation_adding'
        self.assertEqual(type_id, RelationAddingTrigger.type_id)
        self.assertEqual(
            _('A Relationship has been added'), RelationAddingTrigger.verbose_name,
        )

        rtype = RelationType.objects.all()[0]
        trigger = RelationAddingTrigger(rtype=rtype.id)

        with self.assertNumQueries(1):
            self.assertEqual(rtype, trigger.relation_type)

        # TODO
        # with self.assertNumQueries(0):
        #     trigger.relation_type  # NOQA

        self.assertDictEqual(
            {'type': type_id, 'rtype': rtype.id}, trigger.to_dict(),
        )

        with self.assertNoException():
            RelationAddingTrigger(type=type_id, rtype=rtype.id)

        # TODO: indicate entity model too?
        self.assertEqual(
            _('A relationship «{predicate}» has been added').format(predicate=rtype.predicate),
            trigger.description,
        )

    def test_source__created_entity(self):
        id1 = 'created'
        model1 = FakeOrganisation
        source = CreatedEntitySource(id=id1, model=model1)
        self.assertEqual(id1,   source.id)
        self.assertEqual(model1, source.model)
        self.assertEqual(
            _('Created entity ({type})').format(type='Test Organisation'),
            source.label,
        )

        create_orga = partial(FakeOrganisation.objects.create, user=self.get_root_user())
        entity1 = create_orga(name='Acme1')
        entity2 = create_orga(name='Acme2')
        self.assertEqual(entity1, source.extract({id1: entity1, 'other': entity2}))

    def test_source__edited_entity(self):
        id1 = 'edited'
        model1 = FakeContact
        source = EditedEntitySource(id=id1, model=model1)
        self.assertEqual(id1,   source.id)
        self.assertEqual(model1, source.model)
        self.assertEqual(
            _('Modified entity ({type})').format(type='Test Contact'),
            source.label,
        )

    # TODO
    # def test_source__relation_subject(self):
    #     id1 = 'subject'
    #     model1 = FakeOrganisation
    #     source = CreatedEntitySource(id=id1, model=model1)
    #     self.assertEqual(id1,   source.id)
    #     self.assertEqual(model1, source.model)
    #     # self.assertEqual(
    #     #     _('Created entity ({type})').format(type='Test Organisation'),
    #     #     source.label,
    #     # )

    def test_action__property_adding(self):
        type_id = 'creme_core-property_adding'
        self.assertEqual(type_id, PropertyAddingAction.type_id)
        self.assertEqual(_('Adding a property'), PropertyAddingAction.verbose_name)

        # Instance ---
        ptype = CremePropertyType.objects.create(text='Is kawaiiii')
        action = PropertyAddingAction(ptype=str(ptype.uuid))

        with self.assertNumQueries(1):
            self.assertEqual(ptype, action.property_type)

        # TODO
        # with self.assertNumQueries(0):
        #     action.property_type  # NOQA

        self.assertDictEqual(
            {'type': type_id, 'ptype': str(ptype.uuid)}, action.to_dict(),
        )
        # TODO: indicate subject?
        self.assertEqual(
            _('Adding the property «{}»').format(ptype.text), action.description,
        )

        # Execution ---
        entity = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        action.execute(source=entity)
        self.assertHasProperty(entity=entity, ptype=ptype)

    def test_action__relation_adding(self):
        type_id = 'creme_core-relation_adding'
        self.assertEqual(type_id, RelationAddingAction.type_id)
        self.assertEqual(
            _('Adding a relationship'), RelationAddingAction.verbose_name,
        )

        # Instance ---
        rtype = RelationType.objects.all()[0]
        action = RelationAddingAction(rtype=rtype.id)

        with self.assertNumQueries(1):
            self.assertEqual(rtype, action.relation_type)

        # TODO
        # with self.assertNumQueries(0):
        #     action.relation_type  # NOQA

        self.assertDictEqual(
            {'type': type_id, 'rtype': rtype.id}, action.to_dict(),
        )
        # TODO: indicate subject/object?
        self.assertEqual(
            _('Adding the relationship «{}»').format(rtype.predicate),
            action.description,
        )

        # Execution ---
        entity = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        action.execute(source=entity)
        # self.assertHaveRelation(
        #     subject=entity,
        #     type=rtype,
        #     object=TODO,
        # )
