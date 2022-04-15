from functools import partial

from django.utils.translation import gettext as _

from creme.creme_core.models import (
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    FakeProduct,
    Relation,
    RelationType,
    Workflow,
)
# from creme.creme_core.workflows import CreatedEntitySource, EditedEntitySource
# CreatedEntityIngredient
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

from ..constants import REL_SUB_HAS
from ..core.workflow import (
    EntityCreated,
    EntityEdited,
    RelationAdded,
    WorkflowActionSource,
    workflow_registry,
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

        # ---
        contact = FakeContact(first_name='Jed', last_name='Goshi')
        self.assertDictEqual(
            {'created': contact}, trigger.activate(EntityCreated(entity=contact)),
        )
        self.assertIsNone(trigger.activate(EntityEdited(entity=contact)))
        self.assertIsNone(
            trigger.activate(EntityCreated(entity=FakeOrganisation(name='Pineapple')))
        )

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

        # ---
        orga = FakeOrganisation(name='Pineapple')
        self.assertDictEqual(
            {'edited': orga}, trigger.activate(EntityEdited(entity=orga))
        )
        self.assertIsNone(trigger.activate(EntityCreated(entity=orga)))  # Bad event type
        self.assertIsNone(trigger.activate(  # Bad source model
            EntityEdited(entity=FakeContact(first_name='Jed', last_name='Goshi'))
        ))

    def test_trigger__relation_adding(self):
        type_id = 'creme_core-relation_adding'
        self.assertEqual(type_id, RelationAddingTrigger.type_id)
        self.assertEqual(
            _('A Relationship has been added'), RelationAddingTrigger.verbose_name,
        )

        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        subject_model_key = 'creme_core-fakeorganisation'
        object_model_key = 'creme_core-fakecontact'
        trigger = RelationAddingTrigger(
            subject_model=subject_model_key, rtype=rtype.id, object_model=object_model_key,
        )
        self.assertEqual(FakeOrganisation, trigger.subject_model)
        self.assertEqual(FakeContact,      trigger.object_model)

        with self.assertNumQueries(1):
            self.assertEqual(rtype, trigger.relation_type)

        # TODO
        # with self.assertNumQueries(0):
        #     trigger.relation_type  # NOQA

        self.assertDictEqual(
            {
                'type': type_id,
                'subject_model': subject_model_key,
                'rtype': rtype.id,
                'object_model': object_model_key,
            },
            trigger.to_dict(),
        )

        with self.assertNoException():
            RelationAddingTrigger(
                type=type_id,
                subject_model=subject_model_key, rtype=rtype.id, object_model=object_model_key,
            )

        self.assertEqual(
            _(
                'A relationship «{predicate}» has been added to a «{model}»'
            ).format(predicate=rtype.predicate, model='Test Contact'),
            trigger.description,
        )

        # ---
        orga = FakeOrganisation(name='Pineapple')
        contact = FakeContact(first_name='Jed', last_name='Goshi')
        product = FakeProduct(name='Rope')
        self.assertDictEqual(
            {'subject': orga, 'object': contact},
            trigger.activate(RelationAdded(
                relation=Relation(subject_entity=orga, type=rtype, object_entity=contact),
            )),
        )
        self.assertIsNone(trigger.activate(EntityCreated(entity=orga)))
        self.assertIsNone(trigger.activate(RelationAdded(
            relation=Relation(subject_entity=product, type=rtype, object_entity=contact),
        )))
        self.assertIsNone(trigger.activate(RelationAdded(
            relation=Relation(
                subject_entity=orga, type=rtype.symmetric_type, object_entity=contact,
            ),
        )))
        self.assertIsNone(trigger.activate(RelationAdded(
            relation=Relation(subject_entity=orga, type=rtype, object_entity=product),
        )))

    # def test_source__created_entity(self):
    #     id1 = 'created'
    #     model1 = FakeOrganisation
    #     source = CreatedEntitySource(id=id1, model=model1)
    #     self.assertEqual(id1,   source.id)
    #     self.assertEqual(model1, source.model)
    #     self.assertEqual(
    #         _('Created entity ({type})').format(type='Test Organisation'),
    #         source.label,
    #     )
    #
    #     create_orga = partial(FakeOrganisation.objects.create, user=self.get_root_user())
    #     entity1 = create_orga(name='Acme1')
    #     entity2 = create_orga(name='Acme2')
    #     self.assertEqual(entity1, source.extract({id1: entity1, 'other': entity2}))

    # def test_source__edited_entity(self):
    #     id1 = 'edited'
    #     model1 = FakeContact
    #     source = EditedEntitySource(id=id1, model=model1)
    #     self.assertEqual(id1,   source.id)
    #     self.assertEqual(model1, source.model)
    #     self.assertEqual(
    #         _('Modified entity ({type})').format(type='Test Contact'),
    #         source.label,
    #     )
    #
    # def test_source__relation_subject(self):
    #     ...

    def test_source__from_context(self):
        ctxt_key = 'created'
        source = FromContextSource(ctxt_key)
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('from_context', source.type_id)
        self.assertEqual(ctxt_key,       source.context_key)
        self.assertDictEqual(
            {'type': 'from_context', 'key': ctxt_key},
            source.to_dict(),
        )

        # create_orga = partial(FakeOrganisation.objects.create, user=self.get_root_user())
        # entity1 = create_orga(name='Acme1')
        # entity2 = create_orga(name='Acme2')
        entity1 = FakeOrganisation(name='Acme1')
        entity2 = FakeOrganisation(name='Acme2')
        self.assertEqual(entity1, source.extract({ctxt_key: entity1, 'other': entity2}))

        # ---
        ctxt_key2 = 'edited'
        deserialized = FromContextSource.from_dict(
            data={'key': ctxt_key2}, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, FromContextSource)
        self.assertEqual(ctxt_key2, deserialized.context_key)

        # TODO
        # self.assertEqual(
        #     # _('Created entity ({type})').format(type='Test Organisation'),
        #     _('Created entity),
        #     source.description(creation_trigger),
        # )
        # self.assertEqual(
        #     # _('Edited entity ({type})').format(type='Test Organisation'),
        #     _('Edited entity'),
        #     source2.description(edition_trigger),
        # )
        # self.assertEqual(
        #     _('Subject entity'),
        #     source3.description(relation_trigger),
        # )

    def test_source__fixed_entity(self):
        create_orga = partial(FakeOrganisation.objects.create, user=self.get_root_user())
        entity1 = create_orga(name='Acme1')

        source = FixedEntitySource(entity=str(entity1.uuid))  # TODO: accept entity too?
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('fixed_entity', source.type_id)
        self.assertEqual(entity1,        source.entity)
        self.assertDictEqual(
            {'type': 'fixed_entity', 'uuid': str(entity1.uuid)},
            source.to_dict(),
        )

        self.assertEqual(entity1, source.extract({'whatever': 'donotcare'}))

        # ---
        entity2 = create_orga(name='Acme2')
        deserialized = FixedEntitySource.from_dict(
            data={'uuid': str(entity2.uuid)}, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, FixedEntitySource)
        self.assertEqual(entity2, deserialized.entity)

        # TODO
        # self.assertEqual(
        #     # _('{type}: «{entity}»').format(type='Test Organisation', entity=entity.name),
        #     source.description(a_trigger),
        # )

    def test_source__instance_field(self):
        create_orga = partial(FakeOrganisation.objects.create, user=self.get_root_user())
        entity1 = create_orga(name='Acme1', phone='123456')

        field_name = 'phone'
        source = InstanceFieldSource(
            instance_source=FixedEntitySource(entity=str(entity1.uuid)),
            field_name=field_name,
        )
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('field', source.type_id)
        self.assertEqual(field_name, source.field_name)
        # self.assertEqual(..., source.instance_source)  TODO
        self.assertDictEqual(
            {
                'type': 'field',
                'instance': {'type': 'fixed_entity', 'uuid': str(entity1.uuid)},
                'field': field_name,
            },
            source.to_dict(),
        )

        self.assertEqual(entity1.phone, source.extract({'whatever': 'donotcare'}))

        # ---
        field_name2 = 'email'
        entity2 = create_orga(name='Acme2')
        deserialized = InstanceFieldSource.from_dict(
            data={
                'instance': {'type': 'fixed_entity', 'uuid': str(entity2.uuid)},
                'field': field_name2,
            },
            registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, InstanceFieldSource)
        self.assertEqual(field_name2, deserialized.field_name)

        sub_source = deserialized.instance_source
        self.assertIsInstance(sub_source, FixedEntitySource)
        self.assertEqual(entity2, sub_source.entity)

        # TODO
        # self.assertEqual(
        #     # _('Field «{field}» of ...').format(....),
        #     source.description(a_trigger),
        # )

    def test_action__property_adding(self):
        type_id = 'creme_core-property_adding'
        self.assertEqual(type_id, PropertyAddingAction.type_id)
        self.assertEqual(_('Adding a property'), PropertyAddingAction.verbose_name)

        # Instance ---
        ptype = CremePropertyType.objects.create(text='Is kawaiiii')
        # source = 'created'
        ctxt_key = 'created'
        source = FromContextSource(ctxt_key)
        action = PropertyAddingAction(source=source, ptype=str(ptype.uuid))
        self.assertEqual(source, action.source)

        with self.assertNumQueries(1):
            self.assertEqual(ptype, action.property_type)

        # TODO
        # with self.assertNumQueries(0):
        #     action.property_type  # NOQA

        self.assertDictEqual(
            {
                'type': type_id,
                # 'source': source,
                'source': {'type': FromContextSource.type_id, 'key': ctxt_key},
                'ptype': str(ptype.uuid),
            },
            action.to_dict(),
        )
        # TODO: indicate subject
        self.assertEqual(
            _('Adding the property «{}»').format(ptype.text), action.description,
        )

        # Execution ---
        entity = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        # action.execute(context={source: entity})
        action.execute(context={ctxt_key: entity})
        self.assertHasProperty(entity=entity, ptype=ptype)

    def test_action__property_adding__other_values(self):
        ptype = CremePropertyType.objects.create(text='Is swag')
        ctxt_key = 'edited'
        source = FromContextSource(ctxt_key)
        action = PropertyAddingAction(source=source, ptype=str(ptype.uuid))

        entity = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        action.execute(context={ctxt_key: entity})
        self.assertHasProperty(entity=entity, ptype=ptype)

    def test_action__relation_adding(self):
        type_id = 'creme_core-relation_adding'
        self.assertEqual(type_id, RelationAddingAction.type_id)
        self.assertEqual(
            _('Adding a relationship'), RelationAddingAction.verbose_name,
        )

        # Instance ---
        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        source = 'edited'
        action = RelationAddingAction(source=source, rtype=rtype.id)
        self.assertEqual(source, action.source)

        with self.assertNumQueries(1):
            self.assertEqual(rtype, action.relation_type)

        # TODO
        # with self.assertNumQueries(0):
        #     action.relation_type  # NOQA

        self.assertDictEqual(
            {'type': type_id, 'source': source, 'rtype': rtype.id},
            action.to_dict(),
        )
        # TODO: indicate subject & object?
        self.assertEqual(
            _('Adding the relationship «{}»').format(rtype.predicate),
            action.description,
        )

        # Execution ---
        entity1 = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        # entity2 = ...
        action.execute({source: entity1})
        self.fail('TODO')
        # TODO
        #   self.assertHaveRelation( subject=entity, type=rtype, object=entity2)

    # TODO: with conditions
    def test_middleware(self):
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is cool')
        Workflow.objects.smart_create(
            model=FakeOrganisation,
            trigger=EntityCreationTrigger(model='creme_core-fakeorganisation'),
            actions=[
                PropertyAddingAction(
                    source='created',  # TODO: EntityCreationTrigger.source_name??
                    ptype=str(ptype.uuid),
                ),
            ],
        )

        name = 'NERV'
        self.assertNoFormError(
            self.client.post(
                FakeOrganisation.get_create_absolute_url(),
                data={'user': user.id, 'name': name},
                # follow=True, we check that middleware has been executed with the POST request
            ),
            status=302,
        )
        orga = self.get_object_or_fail(FakeOrganisation, name=name)
        self.assertHasProperty(entity=orga, ptype=ptype)
