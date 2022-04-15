from functools import partial
from uuid import uuid4

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
from creme.creme_core.workflows import (
    EntityCreationTrigger,
    EntityEditionTrigger,
    FirstRelatedEntitySource,
    FixedEntitySource,
    FromContextSource,
    InstanceFieldSource,
    PropertyAddingAction,
    RelationAddingAction,
    RelationAddingTrigger,
)

from ..constants import REL_OBJ_HAS, REL_SUB_HAS
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
        self.assertEqual(type_id,   EntityCreationTrigger.type_id)
        self.assertEqual('created', EntityCreationTrigger.CREATED)
        self.assertEqual(
            _('An entity has been created'), EntityCreationTrigger.verbose_name,
        )

        trigger = EntityCreationTrigger(model=FakeContact)
        self.assertEqual(FakeContact, trigger.model)

        model_key = 'creme_core-fakecontact'
        serialized = {'type': type_id, 'model': model_key}
        self.assertDictEqual(serialized, trigger.to_dict())
        self.assertEqual(
            _('A «{}» has been created').format('Test Contact'),
            trigger.description,
        )

        # Deserialization ---
        deserialized = EntityCreationTrigger.from_dict(serialized)
        self.assertIsInstance(deserialized, EntityCreationTrigger)
        self.assertEqual(FakeContact, deserialized.model)

        # Activation ---
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

        trigger = EntityEditionTrigger(model=FakeOrganisation)
        self.assertEqual(FakeOrganisation, trigger.model)
        model_key = 'creme_core-fakeorganisation'
        serialized = {'type': type_id, 'model': model_key}
        self.assertDictEqual(serialized, trigger.to_dict())
        self.assertEqual(
            _('A «{}» has been modified').format('Test Organisation'),
            trigger.description,
        )

        # Deserialization ---
        deserialized = EntityEditionTrigger.from_dict(serialized)
        self.assertIsInstance(deserialized, EntityEditionTrigger)
        self.assertEqual(FakeOrganisation, deserialized.model)

        # Activation ---
        orga = FakeOrganisation(name='Pineapple')
        self.assertDictEqual(
            {'edited': orga}, trigger.activate(EntityEdited(entity=orga))
        )
        self.assertIsNone(trigger.activate(EntityCreated(entity=orga)))  # Bad event type
        self.assertIsNone(trigger.activate(  # Bad source model
            EntityEdited(entity=FakeContact(first_name='Jed', last_name='Goshi'))
        ))

    def test_trigger__relation_adding__str_id(self):
        type_id = 'creme_core-relation_adding'
        self.assertEqual(type_id, RelationAddingTrigger.type_id)
        self.assertEqual(
            _('A Relationship has been added'), RelationAddingTrigger.verbose_name,
        )

        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        trigger = RelationAddingTrigger(
            subject_model=FakeOrganisation, rtype=rtype.id, object_model=FakeContact,
        )
        self.assertEqual(FakeOrganisation, trigger.subject_model)
        self.assertEqual(FakeContact,      trigger.object_model)

        with self.assertNumQueries(1):
            self.assertEqual(rtype, trigger.relation_type)

        with self.assertNumQueries(0):
            trigger.relation_type  # NOQA

        subject_model_key = 'creme_core-fakeorganisation'
        object_model_key = 'creme_core-fakecontact'
        serialized = {
            'type': type_id,
            'subject_model': subject_model_key,
            'rtype': rtype.id,
            'object_model': object_model_key,
        }
        self.assertDictEqual(serialized, trigger.to_dict())

        self.assertEqual(
            _(
                'A relationship «{predicate}» has been added to a «{model}»'
            ).format(predicate=rtype.predicate, model='Test Contact'),
            trigger.description,
        )

        # Deserialization ---
        deserialized = RelationAddingTrigger.from_dict(serialized)
        self.assertIsInstance(deserialized, RelationAddingTrigger)
        self.assertEqual(FakeOrganisation, deserialized.subject_model)
        self.assertEqual(FakeContact,      deserialized.object_model)

        # Activation ---
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

    def test_trigger__relation_adding__rtype_instance(self):
        rtype = RelationType.objects.get(id=REL_OBJ_HAS)
        trigger = RelationAddingTrigger(
            subject_model=FakeContact, rtype=rtype, object_model=FakeOrganisation,
        )
        self.assertEqual(FakeContact,      trigger.subject_model)
        self.assertEqual(FakeOrganisation, trigger.object_model)

        with self.assertNumQueries(0):
            self.assertEqual(rtype, trigger.relation_type)

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

        entity1 = FakeOrganisation(name='Acme1')
        entity2 = FakeOrganisation(name='Acme2')
        self.assertEqual(
            entity1, source.extract({ctxt_key: entity1, 'other': entity2}),
        )

        # Deserialization ---
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

    def test_source__from_context__eq(self):
        source1 = FromContextSource('created')
        self.assertEqual(source1, FromContextSource('created'))
        self.assertNotEqual(source1, FromContextSource('edited'))

        class TestSource(WorkflowActionSource):
            def __init__(self, key):
                self._key = key

        self.assertNotEqual(source1, TestSource('created'))

    def test_source__fixed_entity__str_uuid(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')

        source = FixedEntitySource(model=FakeOrganisation, entity=str(orga.uuid))
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('fixed_entity', source.type_id)
        self.assertEqual(FakeOrganisation, source.model)
        self.assertDictEqual(
            {
                'type': 'fixed_entity',
                'model': 'creme_core-fakeorganisation',
                'uuid': str(orga.uuid),
            },
            source.to_dict(),
        )

        with self.assertNumQueries(1):
            self.assertEqual(orga, source.entity)

        with self.assertNumQueries(0):
            source.entity  # NOQA

        self.assertEqual(orga, source.extract({'whatever': 'donotcare'}))

        # ---
        contact = FakeContact.objects.create(user=user, first_name='Jed', last_name='Goshi')
        deserialized = FixedEntitySource.from_dict(
            data={
                'model': 'creme_core-fakecontact',
                'uuid': str(contact.uuid),
            },
            registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, FixedEntitySource)
        self.assertEqual(contact, deserialized.entity)

        # TODO
        # self.assertEqual(
        #     # _('{type}: «{entity}»').format(type='Test Organisation', entity=entity.name),
        #     source.description(a_trigger),
        # )

    def test_source__fixed_entity__entity_instance(self):
        contact = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Jed', last_name='Goshi',
        )

        source1 = FixedEntitySource(entity=contact)
        self.assertEqual(FakeContact, source1.model)

        with self.assertNumQueries(0):
            self.assertEqual(contact, source1.entity)

        self.assertDictEqual(
            {
                'type': 'fixed_entity',
                'model': 'creme_core-fakecontact',
                'uuid': str(contact.uuid),
            },
            source1.to_dict(),
        )

        # Real entity ---
        source2 = FixedEntitySource(entity=contact.cremeentity_ptr)
        self.assertEqual(FakeContact, source2.model)

        with self.assertNumQueries(0):
            self.assertEqual(contact, source2.entity)

    def test_source__fixed_entity__eq(self):
        contact = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Jed', last_name='Goshi',
        )
        self.maxDiff = None
        str_uuid1 = str(contact.uuid)
        source1 = FixedEntitySource(model=FakeContact, entity=str_uuid1)
        self.assertEqual(source1, FixedEntitySource(entity=str_uuid1, model=FakeContact))
        self.assertEqual(source1, FixedEntitySource(entity=contact))
        self.assertNotEqual(
            source1, FixedEntitySource(entity=str(uuid4()), model=FakeContact),
        )

        class TestSource(WorkflowActionSource):
            def __init__(self, uuid_):
                self._entity_uuid = uuid_

        self.assertNotEqual(source1, TestSource(str_uuid1))

    def test_source__instance_field(self):
        create_orga = partial(FakeOrganisation.objects.create, user=self.get_root_user())
        entity1 = create_orga(name='Acme1', phone='123456')

        field_name = 'phone'
        source = InstanceFieldSource(
            instance_source=FixedEntitySource(entity=entity1),
            field_name=field_name,
        )
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('field', source.type_id)
        self.assertEqual(field_name, source.field_name)

        sub_src_as_dict = {
            'type': 'fixed_entity',
            'model': 'creme_core-fakeorganisation', 'uuid': str(entity1.uuid),
        }
        self.assertDictEqual(
            sub_src_as_dict,
            source.instance_source.to_dict(),
        )
        self.assertDictEqual(
            {
                'type': 'field',
                'instance': sub_src_as_dict,
                'field': field_name,
            },
            source.to_dict(),
        )

        self.assertEqual(entity1.phone, source.extract({'whatever': 'donotcare'}))

        # Deserialization ---
        field_name2 = 'email'
        entity2 = create_orga(name='Acme2')
        deserialized = InstanceFieldSource.from_dict(
            data={
                'type': 'field',
                'instance': FixedEntitySource(entity=entity2).to_dict(),
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

    def test_source__instance_field__empty(self):
        ctxt_key = 'created'
        source = InstanceFieldSource(
            instance_source=FromContextSource(ctxt_key),
            field_name='phone',
        )
        self.assertIsNone(source.extract({ctxt_key: None}))

    def test_source__instance_field__eq(self):
        create_orga = partial(FakeOrganisation.objects.create, user=self.get_root_user())
        entity1 = create_orga(name='Acme1', phone='123456')

        field_name1 = 'phone'
        source1 = InstanceFieldSource(
            instance_source=FixedEntitySource(entity=entity1),
            field_name=field_name1,
        )
        self.assertEqual(
            source1,
            InstanceFieldSource(
                instance_source=FixedEntitySource(entity=entity1),
                field_name=field_name1,
            ),
        )
        self.assertNotEqual(
            source1,
            InstanceFieldSource(
                instance_source=FixedEntitySource(entity=entity1),
                field_name='email',  # <==
            ),
        )

        entity2 = create_orga(name='Acme2', phone='123456')
        self.assertNotEqual(
            source1,
            InstanceFieldSource(
                instance_source=FixedEntitySource(entity=entity2),
                field_name=field_name1,
            ),
        )

        class TestSource(WorkflowActionSource):
            type_id = 'field'

            def __init__(self, source, field_name):
                self._instance_source = source
                self._field_name = field_name

        self.assertNotEqual(
            source1,
            TestSource(
                source=FixedEntitySource(entity=entity1),
                field_name=field_name1,
            ),
        )

    def test_source__first_related_entity__str_id(self):
        user = self.get_root_user()
        rtype = RelationType.objects.get(id=REL_SUB_HAS)

        create_contact = partial(FakeContact.objects.create, user=user)
        contact1 = create_contact(first_name='Babs',   last_name='Bunny')
        contact2 = create_contact(first_name='Buster', last_name='Bunny')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Looniversity')
        orga2 = create_orga(name='Acme')

        create_rel = partial(Relation.objects.create, user=user, type=rtype)
        create_rel(subject_entity=contact1, object_entity=contact2)
        create_rel(subject_entity=contact1, object_entity=orga1)
        create_rel(subject_entity=contact1, object_entity=orga2)

        ctxt_key1 = 'created'
        source = FirstRelatedEntitySource(
            subject_source=FromContextSource(ctxt_key1),
            rtype=rtype.id,
            object_model=FakeOrganisation,
        )
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('first_related', source.type_id)
        self.assertEqual(FromContextSource('created'), source.subject_source)
        self.assertEqual(FakeOrganisation,             source.object_model)

        with self.assertNumQueries(1):
            self.assertEqual(rtype, source.relation_type)

        with self.assertNumQueries(0):
            source.relation_type  # NOQA

        self.assertDictEqual(
            {
                'type': 'first_related',
                'subject': {'key': ctxt_key1, 'type': FromContextSource.type_id},
                'rtype': rtype.id,
                'object_model': 'creme_core-fakeorganisation',
            },
            source.to_dict(),
        )

        # NB: 'orga2' is the first related FakeOrganisation instance
        self.assertEqual(orga2, source.extract({ctxt_key1: contact1}))

        # Empty result
        self.assertIsNone(source.extract({ctxt_key1: None}))
        self.assertIsNone(source.extract({ctxt_key1: contact2}))

        # Deserialization ---
        ctxt_key2 = 'edited'
        deserialized = FirstRelatedEntitySource.from_dict(
            data={
                'type': FirstRelatedEntitySource.type_id,
                'subject': {'key': ctxt_key2, 'type': FromContextSource.type_id},
                'rtype': rtype.symmetric_type_id,
                'object_model': 'creme_core-fakecontact',
            },
            registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, FirstRelatedEntitySource)
        self.assertEqual(FromContextSource(ctxt_key2), deserialized.subject_source)
        self.assertEqual(FakeContact,                  deserialized.object_model)
        self.assertEqual(rtype.symmetric_type,         deserialized.relation_type)

        # TODO
        # self.assertEqual(
        #     # _('...'),
        #     source.description(a_trigger),
        # )

    def test_source__first_related_entity__rtype_instance(self):
        rtype = RelationType.objects.get(id=REL_SUB_HAS)

        ctxt_key = 'created'
        source = FirstRelatedEntitySource(
            subject_source=FromContextSource(ctxt_key),
            rtype=rtype,
            object_model=FakeOrganisation,
        )

        with self.assertNumQueries(0):
            self.assertEqual(rtype, source.relation_type)

        self.assertDictEqual(
            {
                'type': 'first_related',
                'subject': {'key': ctxt_key, 'type': FromContextSource.type_id},
                'rtype': rtype.id,
                'object_model': 'creme_core-fakeorganisation',
            },
            source.to_dict(),
        )

    def test_source__first_related_entity__eq(self):
        rtype = RelationType.objects.get(id=REL_SUB_HAS)

        ctxt_key = 'created'
        source1 = FirstRelatedEntitySource(
            subject_source=FromContextSource(ctxt_key),
            rtype=rtype,
            object_model=FakeOrganisation,
        )
        self.assertEqual(
            source1,
            FirstRelatedEntitySource(
                subject_source=FromContextSource(ctxt_key),
                rtype=rtype,
                object_model=FakeOrganisation,
            ),
        )
        self.assertEqual(
            source1,
            FirstRelatedEntitySource(
                subject_source=FromContextSource(ctxt_key),
                rtype=rtype.id,
                object_model=FakeOrganisation,
            ),
        )
        self.assertNotEqual(
            source1,
            FirstRelatedEntitySource(
                subject_source=FromContextSource('edited'),  # <===
                rtype=rtype.id,
                object_model=FakeOrganisation,
            ),
        )
        self.assertNotEqual(
            source1,
            FirstRelatedEntitySource(
                subject_source=FromContextSource(ctxt_key),
                rtype=rtype.symmetric_type,  # <===
                object_model=FakeOrganisation,
            ),
        )
        self.assertNotEqual(
            source1,
            FirstRelatedEntitySource(
                subject_source=FromContextSource(ctxt_key),
                rtype=rtype,
                object_model=FakeContact,  # <===
            ),
        )

        class TestSource(WorkflowActionSource):
            def __init__(self, key, rtype_id, model):
                self._subject_source = FromContextSource(key)
                self._rtype_id = rtype_id
                self._object_model = model

        self.assertNotEqual(
            source1, TestSource(ctxt_key, rtype_id=rtype.id, model=FakeOrganisation),
        )

    def test_action__property_adding__str_uuid(self):
        type_id = 'creme_core-property_adding'
        self.assertEqual(type_id, PropertyAddingAction.type_id)
        self.assertEqual(_('Adding a property'), PropertyAddingAction.verbose_name)

        # Instance ---
        ptype = CremePropertyType.objects.create(text='Is kawaiiii')
        ctxt_key = 'created'
        source = FromContextSource(ctxt_key)
        action = PropertyAddingAction(entity_source=source, ptype=str(ptype.uuid))
        self.assertEqual(source, action.entity_source)

        with self.assertNumQueries(1):
            self.assertEqual(ptype, action.property_type)

        with self.assertNumQueries(0):
            action.property_type  # NOQA

        serialized = {
            'type': type_id,
            'entity': {'type': FromContextSource.type_id, 'key': ctxt_key},
            'ptype': str(ptype.uuid),
        }
        self.assertDictEqual(serialized, action.to_dict())
        # TODO: indicate subject
        self.assertEqual(
            _('Adding the property «{}»').format(ptype.text), action.description,
        )

        # De-serialisation ---
        deserialized = PropertyAddingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, PropertyAddingAction)
        self.assertEqual(ptype, deserialized.property_type)
        self.assertDictEqual(
            {'type': FromContextSource.type_id, 'key': ctxt_key},
            deserialized.entity_source.to_dict(),
        )

        # Execution ---
        entity = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        deserialized.execute(context={ctxt_key: entity})
        self.assertHasProperty(entity=entity, ptype=ptype)

        # Execute twice => beware of property uniqueness
        with self.assertNoException():
            deserialized.execute(context={ctxt_key: entity})

        # With empty source
        with self.assertNoException():
            deserialized.execute(context={ctxt_key: None})

    def test_action__property_adding__ptype_instance(self):
        ptype = CremePropertyType.objects.create(text='Is swag')
        ctxt_key = 'edited'
        source = FromContextSource(ctxt_key)
        action = PropertyAddingAction(entity_source=source, ptype=ptype)

        entity = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        action.execute(context={ctxt_key: entity})
        self.assertHasProperty(entity=entity, ptype=ptype)

        with self.assertNumQueries(0):
            self.assertEqual(ptype, action.property_type)

    def test_action__relation_adding__str_id(self):
        type_id = 'creme_core-relation_adding'
        self.assertEqual(type_id, RelationAddingAction.type_id)
        self.assertEqual(
            _('Adding a relationship'), RelationAddingAction.verbose_name,
        )

        # Instance ---
        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        ctxt_key1 = 'edited'
        ctxt_key2 = 'related'
        source1 = FromContextSource(ctxt_key1)
        source2 = FromContextSource(ctxt_key2)
        action = RelationAddingAction(
            subject_source=source1, rtype=rtype.id, object_source=source2,
        )
        self.assertEqual(source1, action.subject_source)
        self.assertEqual(source2, action.object_source)

        with self.assertNumQueries(1):
            self.assertEqual(rtype, action.relation_type)

        with self.assertNumQueries(0):
            action.relation_type  # NOQA

        serialized = {
            'type': type_id,
            'subject': {'key': ctxt_key1, 'type': FromContextSource.type_id},
            'rtype': rtype.id,
            'object': {'key': ctxt_key2, 'type': FromContextSource.type_id},
        }
        self.assertDictEqual(serialized, action.to_dict())
        # TODO: indicate subject & object?
        self.assertEqual(
            _('Adding the relationship «{}»').format(rtype.predicate),
            action.description,
        )

        # De-serialisation ---
        deserialized = RelationAddingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, RelationAddingAction)
        self.assertEqual(rtype, deserialized.relation_type)
        self.assertDictEqual(
            {'type': FromContextSource.type_id, 'key': ctxt_key1},
            deserialized.subject_source.to_dict(),
        )
        self.assertDictEqual(
            {'type': FromContextSource.type_id, 'key': ctxt_key2},
            deserialized.object_source.to_dict(),
        )

        # Execution ---
        create_orga = partial(FakeOrganisation.objects.create, user=self.get_root_user())
        entity1 = create_orga(name='Acme1')
        entity2 = create_orga(name='Acme2')
        deserialized.execute({ctxt_key1: entity1, ctxt_key2: entity2})
        self.assertHaveRelation(subject=entity1, type=rtype, object=entity2)

        # Execute twice => beware of property uniqueness
        with self.assertNoException():
            deserialized.execute(context={ctxt_key1: entity1, ctxt_key2: entity2})

        # With empty source
        with self.assertNoException():
            deserialized.execute(context={ctxt_key1: None,    ctxt_key2: entity2})
            deserialized.execute(context={ctxt_key1: entity1, ctxt_key2: None})

    def test_action__relation_adding__rtype_instance(self):
        rtype = RelationType.objects.get(id=REL_OBJ_HAS)
        action = RelationAddingAction(
            subject_source=FromContextSource('edited'),
            rtype=rtype,
            object_source=FromContextSource('related'),
        )

        with self.assertNumQueries(0):
            self.assertEqual(rtype, action.relation_type)

    # TODO: with conditions
    def test_middleware(self):
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is cool')
        Workflow.objects.smart_create(
            model=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            actions=[
                PropertyAddingAction(
                    entity_source=FromContextSource(EntityCreationTrigger.CREATED),
                    ptype=ptype,
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
