from functools import partial
from uuid import uuid4

from django.utils.safestring import SafeString
from django.utils.translation import gettext as _

from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    FakeContact,
    FakeImage,
    FakeOrganisation,
    FakeProduct,
    Relation,
    RelationType,
    Workflow,
)
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    EntityCreationTrigger,
    EntityEditionTrigger,
    EntityFKSource,
    FirstRelatedEntitySource,
    FixedEntitySource,
    ObjectEntitySource,
    PropertyAddingAction,
    PropertyAddingTrigger,
    RelationAddingAction,
    RelationAddingTrigger,
    SubjectEntitySource,
    TaggedEntitySource,
)

from ..constants import REL_OBJ_HAS, REL_SUB_HAS
from ..core.workflow import (
    EntityCreated,
    EntityEdited,
    PropertyAdded,
    RelationAdded,
    WorkflowActionSource,
    workflow_registry,
)
from ..forms import workflows as wf_forms
from .base import CremeTestCase


class TriggersTestCase(CremeTestCase):
    def test_entity_creation(self):
        type_id = 'creme_core-entity_creation'
        self.assertEqual(type_id, EntityCreationTrigger.type_id)
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
            {'created_entity': contact}, trigger.activate(EntityCreated(entity=contact)),
        )
        self.assertIsNone(trigger.activate(EntityEdited(entity=contact)))
        self.assertIsNone(
            trigger.activate(EntityCreated(entity=FakeOrganisation(name='Pineapple')))
        )

        # Trigger config ---
        field = EntityCreationTrigger.config_formfield(model=FakeContact)
        self.assertIsInstance(field, wf_forms.EntityCreationTriggerField)
        self.assertEqual(FakeContact,                     field.model)
        self.assertEqual(_('An entity has been created'), field.label)

        # Action config ---
        self.assertListEqual(
            [CreatedEntitySource(model=FakeContact)], trigger.root_sources(),
        )

    def test_entity_creation__eq(self):
        trigger1 = EntityCreationTrigger(model=FakeContact)
        self.assertEqual(trigger1, EntityCreationTrigger(model=FakeContact))
        self.assertNotEqual(trigger1, EntityCreationTrigger(model=FakeOrganisation))
        self.assertNotEqual(trigger1, EntityEditionTrigger(model=FakeContact))

    def test_entity_edition(self):
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
            _('A «{model}» has been modified').format(model='Test Organisation'),
            trigger.description,
        )

        # Deserialization ---
        deserialized = EntityEditionTrigger.from_dict(serialized)
        self.assertIsInstance(deserialized, EntityEditionTrigger)
        self.assertEqual(FakeOrganisation, deserialized.model)

        # Activation ---
        orga = FakeOrganisation(name='Pineapple')
        self.assertDictEqual(
            {'edited_entity': orga}, trigger.activate(EntityEdited(entity=orga))
        )
        self.assertIsNone(trigger.activate(EntityCreated(entity=orga)))  # Bad event type
        self.assertIsNone(trigger.activate(  # Bad source model
            EntityEdited(entity=FakeContact(first_name='Jed', last_name='Goshi'))
        ))

        # Trigger config ---
        field = EntityEditionTrigger.config_formfield(model=FakeContact)
        self.assertIsInstance(field, wf_forms.EntityEditionTriggerField)
        self.assertEqual(FakeContact,                      field.model)
        self.assertEqual(_('An entity has been modified'), field.label)

        # Action config ---
        self.assertListEqual(
            [EditedEntitySource(model=FakeOrganisation)], trigger.root_sources(),
        )

    def test_entity_edition__eq(self):
        trigger1 = EntityEditionTrigger(model=FakeContact)
        self.assertEqual(trigger1, EntityEditionTrigger(model=FakeContact))
        self.assertNotEqual(trigger1, EntityEditionTrigger(model=FakeOrganisation))
        self.assertNotEqual(trigger1, EntityCreationTrigger(model=FakeContact))

    def test_property_adding__str_uuid(self):
        type_id = 'creme_core-property_adding'
        self.assertEqual(type_id, PropertyAddingTrigger.type_id)
        self.assertEqual(
            _('A property has been added'), PropertyAddingTrigger.verbose_name,
        )

        ptype = CremePropertyType.objects.create(text='Is kawaiiii')
        trigger = PropertyAddingTrigger(
            entity_model=FakeOrganisation, ptype=str(ptype.uuid),
        )
        self.assertEqual(FakeOrganisation, trigger.entity_model)

        with self.assertNumQueries(1):
            self.assertEqual(ptype, trigger.property_type)

        with self.assertNumQueries(0):
            trigger.property_type  # NOQA

        model_key = 'creme_core-fakeorganisation'

        serialized = {
            'type': type_id,
            'entity_model': model_key,
            'ptype': str(ptype.uuid),
        }
        self.assertDictEqual(serialized, trigger.to_dict())

        self.assertEqual(
            _('A property «{label}» has been added').format(label=ptype.text),
            trigger.description,
        )

        # Deserialization ---
        deserialized = PropertyAddingTrigger.from_dict(serialized)
        self.assertIsInstance(deserialized, PropertyAddingTrigger)
        self.assertEqual(FakeOrganisation, deserialized.entity_model)
        self.assertEqual(ptype,            deserialized.property_type)

        # Activation ---
        orga = FakeOrganisation(name='Pineapple')
        product = FakeProduct(name='Rope')
        self.assertDictEqual(
            {'tagged_entity': orga},
            trigger.activate(PropertyAdded(
                creme_property=CremeProperty(creme_entity=orga, type=ptype),
            )),
        )
        self.assertIsNone(trigger.activate(EntityCreated(entity=orga)))
        self.assertIsNone(trigger.activate(PropertyAdded(
            creme_property=CremeProperty(creme_entity=product, type=ptype),
        )))
        self.assertIsNone(trigger.activate(PropertyAdded(
            creme_property=CremeProperty(
                creme_entity=orga,
                type=CremePropertyType.objects.create(text='Another property'),
            ),
        )))

        # Trigger config ---
        field = PropertyAddingTrigger.config_formfield(model=FakeContact)
        self.assertIsInstance(field, wf_forms.PropertyAddingTriggerField)
        self.assertEqual(FakeContact,                    field.model)
        self.assertEqual(_('A property has been added'), field.label)

        # Action config ---
        self.assertListEqual(
            [TaggedEntitySource(model=FakeOrganisation)],
            trigger.root_sources(),
        )

    def test_property_adding__rtype_instance(self):
        ptype = CremePropertyType.objects.create(text='Nice')
        trigger = PropertyAddingTrigger(entity_model=FakeContact, ptype=ptype)
        self.assertEqual(FakeContact, trigger.entity_model)

        with self.assertNumQueries(0):
            self.assertEqual(ptype, trigger.property_type)

    def test_property_adding__eq(self):
        ptype1 = CremePropertyType.objects.create(text='Strong')
        trigger1 = PropertyAddingTrigger(entity_model=FakeContact, ptype=ptype1)
        self.assertEqual(
            trigger1, PropertyAddingTrigger(entity_model=FakeContact, ptype=ptype1),
        )
        self.assertNotEqual(
            trigger1,
            PropertyAddingTrigger(
                entity_model=FakeOrganisation,  # <==
                ptype=ptype1,
            ),
        )
        self.assertNotEqual(
            trigger1,
            PropertyAddingTrigger(
                entity_model=FakeContact,
                ptype=CremePropertyType.objects.create(text='Fast'),  # <===
            ),
        )
        self.assertNotEqual(trigger1, None)

    def test_relation_adding__str_id(self):
        type_id = 'creme_core-relation_adding'
        self.assertEqual(type_id, RelationAddingTrigger.type_id)
        self.assertEqual(
            _('A relationship has been added'), RelationAddingTrigger.verbose_name,
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
            {'subject_entity': orga, 'object_entity': contact},
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

        # Trigger config ---
        field = RelationAddingTrigger.config_formfield(model=FakeContact)
        self.assertIsInstance(field, wf_forms.RelationAddingTriggerField)
        self.assertEqual(FakeContact,                        field.model)
        self.assertEqual(_('A relationship has been added'), field.label)

        # Action config ---
        self.assertListEqual(
            [
                SubjectEntitySource(model=FakeOrganisation),
                ObjectEntitySource(model=FakeContact),
            ],
            trigger.root_sources(),
        )

    def test_relation_adding__rtype_instance(self):
        rtype = RelationType.objects.get(id=REL_OBJ_HAS)
        trigger = RelationAddingTrigger(
            subject_model=FakeContact, rtype=rtype, object_model=FakeOrganisation,
        )
        self.assertEqual(FakeContact,      trigger.subject_model)
        self.assertEqual(FakeOrganisation, trigger.object_model)

        with self.assertNumQueries(0):
            self.assertEqual(rtype, trigger.relation_type)

    def test_relation_adding__eq(self):
        rtype1 = RelationType.objects.get(id=REL_OBJ_HAS)
        trigger1 = RelationAddingTrigger(
            subject_model=FakeContact, rtype=rtype1, object_model=FakeOrganisation,
        )
        self.assertEqual(
            trigger1,
            RelationAddingTrigger(
                subject_model=FakeContact, rtype=rtype1, object_model=FakeOrganisation,
            ),
        )
        self.assertNotEqual(
            trigger1,
            RelationAddingTrigger(
                subject_model=FakeOrganisation,  # <==
                rtype=rtype1, object_model=FakeOrganisation,
            ),
        )
        self.assertNotEqual(
            trigger1,
            RelationAddingTrigger(
                subject_model=FakeContact, rtype=rtype1,
                object_model=FakeContact,  # <==
            ),
        )
        self.assertNotEqual(
            trigger1,
            RelationAddingTrigger(
                subject_model=FakeContact,
                rtype=rtype1.symmetric_type,  # <==
                object_model=FakeOrganisation,
            ),
        )
        self.assertNotEqual(trigger1, None)


class SourcesTestCase(CremeTestCase):
    def test_created_entity(self):
        source = CreatedEntitySource(model=FakeOrganisation)
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('created_entity', source.type_id)
        self.assertEqual(FakeOrganisation,  source.model)
        self.assertDictEqual(
            {'type': 'created_entity', 'model': 'creme_core-fakeorganisation'},
            source.to_dict(),
        )

        user = self.get_root_user()
        label = _('Created entity ({type})').format(type='Test Organisation')
        self.assertEqual(label, source.render(user=user, mode=source.TEXT_PLAIN))
        self.assertEqual(label, source.render(user=user, mode=source.HTML))

        entity1 = FakeOrganisation(name='Acme1')
        entity2 = FakeOrganisation(name='Acme2')
        self.assertEqual(
            entity1, source.extract({source.type_id: entity1, 'other': entity2}),
        )

        # Deserialization ---
        deserialized = CreatedEntitySource.from_dict(
            data={'model': 'creme_core-fakecontact'},
            registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, CreatedEntitySource)
        self.assertEqual(FakeContact, deserialized.model)

        # Configuration ---
        from creme.creme_core.forms.workflows import CreatedEntitySourceField
        ffield = deserialized.config_formfield(user=user)
        self.assertIsInstance(ffield, CreatedEntitySourceField)
        self.assertEqual(FakeContact, ffield.model)
        self.assertEqual(
            _('Created entity ({type})').format(type='Test Contact'),
            ffield.label,
        )

    def test_created_entity__eq(self):
        source1 = CreatedEntitySource(model=FakeContact)
        self.assertEqual(source1, CreatedEntitySource(model=FakeContact))
        self.assertNotEqual(source1, CreatedEntitySource(model=FakeOrganisation))
        self.assertNotEqual(source1, None)

    def test_edited_entity(self):
        source = EditedEntitySource(model=FakeContact)
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('edited_entity', source.type_id)
        self.assertEqual(FakeContact,     source.model)
        self.assertDictEqual(
            {'type': 'edited_entity', 'model': 'creme_core-fakecontact'},
            source.to_dict(),
        )

        user = self.get_root_user()
        label = _('Modified entity ({type})').format(type='Test Contact')
        self.assertEqual(label, source.render(user=user, mode=source.TEXT_PLAIN))
        self.assertEqual(label, source.render(user=user, mode=source.HTML))

        entity1 = FakeOrganisation(name='Acme1')
        entity2 = FakeOrganisation(name='Acme2')
        self.assertEqual(
            entity1, source.extract({source.type_id: entity1, 'other': entity2}),
        )

        # Deserialization ---
        deserialized = EditedEntitySource.from_dict(
            data={'model': 'creme_core-fakeorganisation'},
            registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, EditedEntitySource)
        self.assertEqual(FakeOrganisation, deserialized.model)

        # Configuration ---
        from creme.creme_core.forms.workflows import EditedEntitySourceField
        ffield = deserialized.config_formfield(user=user)
        self.assertIsInstance(ffield, EditedEntitySourceField)
        self.assertEqual(FakeOrganisation, ffield.model)
        self.assertEqual(
            _('Modified entity ({type})').format(type='Test Organisation'),
            ffield.label,
        )

    def test_edited_entity__eq(self):
        source1 = EditedEntitySource(model=FakeContact)
        self.assertEqual(source1, EditedEntitySource(model=FakeContact))
        self.assertNotEqual(source1, EditedEntitySource(model=FakeOrganisation))
        self.assertNotEqual(source1, CreatedEntitySource(model=FakeContact))
        self.assertNotEqual(source1, None)

    def test_tagged_entity(self):
        source = TaggedEntitySource(model=FakeContact)
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('tagged_entity', source.type_id)
        self.assertEqual(FakeContact,      source.model)
        self.assertDictEqual(
            {'type': 'tagged_entity', 'model': 'creme_core-fakecontact'},
            source.to_dict(),
        )

        user = self.get_root_user()
        label = _('Received a new property ({type})').format(type='Test Contact')
        self.assertEqual(label, source.render(user=user, mode=source.TEXT_PLAIN))
        self.assertEqual(label, source.render(user=user, mode=source.HTML))

        # Configuration ---
        from creme.creme_core.forms.workflows import TaggedEntitySourceField
        ffield = source.config_formfield(user=user)
        self.assertIsInstance(ffield, TaggedEntitySourceField)
        self.assertEqual(FakeContact, ffield.model)
        self.assertEqual(label, ffield.label)

    def test_subject_entity(self):
        source = SubjectEntitySource(model=FakeContact)
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('subject_entity', source.type_id)
        self.assertEqual(FakeContact,      source.model)
        self.assertDictEqual(
            {'type': 'subject_entity', 'model': 'creme_core-fakecontact'},
            source.to_dict(),
        )

        user = self.get_root_user()
        label = _('Subject of the created relationship ({type})').format(type='Test Contact')
        self.assertEqual(label, source.render(user=user, mode=source.TEXT_PLAIN))
        self.assertEqual(label, source.render(user=user, mode=source.HTML))

        # Configuration ---
        from creme.creme_core.forms.workflows import SubjectEntitySourceField
        ffield = source.config_formfield(user=user)
        self.assertIsInstance(ffield, SubjectEntitySourceField)
        self.assertEqual(FakeContact, ffield.model)
        self.assertEqual(label, ffield.label)

    def test_object_entity(self):
        source = ObjectEntitySource(model=FakeContact)
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('object_entity', source.type_id)
        self.assertEqual(FakeContact,     source.model)
        self.assertDictEqual(
            {'type': 'object_entity', 'model': 'creme_core-fakecontact'},
            source.to_dict(),
        )

        user = self.get_root_user()
        label = _('Object of the created relationship ({type})').format(type='Test Contact')
        self.assertEqual(label, source.render(user=user, mode=source.TEXT_PLAIN))
        self.assertEqual(label, source.render(user=user, mode=source.HTML))

        # Configuration ---
        from creme.creme_core.forms.workflows import ObjectEntitySourceField
        ffield = source.config_formfield(user=user)
        self.assertIsInstance(ffield, ObjectEntitySourceField)
        self.assertEqual(FakeContact, ffield.model)
        self.assertEqual(label, ffield.label)

    def test_fixed_entity__str_uuid(self):
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

        # Deserialization ---
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

        # Configuration ---
        with self.assertRaises(ValueError) as cm:
            source.config_formfield(user=user)
        self.assertEqual(
            'This type of source cannot be used as root source',
            str(cm.exception),
        )

        self.assertIsNone(FixedEntitySource.composed_config_formfield(
            sub_source=CreatedEntitySource(model=FakeContact), user=user,
        ))

        from creme.creme_core.forms.workflows import FixedEntitySourceField
        ffield = FixedEntitySource.standalone_config_formfield(user=user)
        self.assertIsInstance(ffield, FixedEntitySourceField)
        self.assertEqual(_('Specific entity'), ffield.label)
        self.assertEqual(user,                 ffield.user)

    def test_fixed_entity__entity_instance(self):
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

    def test_fixed_entity__eq(self):
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
        self.assertNotEqual(source1, None)

    def test_fixed_entity__render__entity_instance(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')
        source = FixedEntitySource(entity=orga)
        self.assertEqual(
            _('Fixed entity «{entity}»').format(entity=orga.name),
            source.render(user=user, mode=source.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            f'<span>'
            f'<a href="{orga.get_absolute_url()}" target="_self">{orga.name}</a>'
            f'{_("(fixed entity)")}'
            f'</span>',
            source.render(user=user, mode=source.HTML),
        )

        orga.trash()
        self.assertEqual(
            _('Fixed entity «{entity}» [deleted]').format(entity=orga.name),
            source.render(user=user, mode=source.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            f'<span>'
            f'<a href="{orga.get_absolute_url()}" class="is_deleted" target="_self">'
            f'{orga.name}'
            f'</a>'
            f'{_("(fixed entity)")}'
            f'</span>',
            source.render(user=user, mode=source.HTML),
        )

    def test_fixed_entity__render__str_uuid(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')
        source = FixedEntitySource(model=FakeOrganisation, entity=str(orga.uuid))
        self.assertEqual(
            _('Fixed entity «{entity}»').format(entity=orga.name),
            source.render(user=user, mode=source.TEXT_PLAIN),
        )

    def test_entity_fk(self):
        user = self.get_root_user()
        img = FakeImage.objects.create(user=user, name='Acme logo')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Acme1', image=img)

        field_name = 'image'
        fixed_source = FixedEntitySource(entity=orga1)
        source = EntityFKSource(entity_source=fixed_source, field_name=field_name)
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('entity_fk', source.type_id)
        self.assertEqual(field_name, source.field_name)
        self.assertEqual(FakeImage, source.model)
        self.assertDictEqual(
            {
                'type': 'entity_fk',
                'entity': fixed_source.to_dict(),
                'field': field_name,
            },
            source.to_dict(),
        )
        self.assertEqual(img, source.extract({'whatever': 'donotcare'}))

        # Deserialization ---
        field_name2 = 'email'
        entity2 = create_orga(name='Acme2')
        deserialized = EntityFKSource.from_dict(
            data={
                'type': 'entity_fk',
                'entity': FixedEntitySource(entity=entity2).to_dict(),
                'field': field_name2,
            },
            registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, EntityFKSource)
        self.assertEqual(field_name2, deserialized.field_name)

        sub_source = deserialized.entity_source
        self.assertIsInstance(sub_source, FixedEntitySource)
        self.assertEqual(entity2, sub_source.entity)

        # Configuration ---
        with self.assertRaises(ValueError) as cm:
            source.config_formfield(user=user)
        self.assertEqual(
            'This type of source cannot be used as root source',
            str(cm.exception),
        )

        sub_source = CreatedEntitySource(model=FakeContact)
        ffield = EntityFKSource.composed_config_formfield(sub_source=sub_source, user=user)
        from creme.creme_core.forms.workflows import EntityFKSourceField
        self.assertIsInstance(ffield, EntityFKSourceField)
        self.assertEqual(sub_source, ffield.entity_source)
        self.assertEqual(
            _('Field of: {source}').format(
                source=_('Created entity ({type})').format(type='Test Contact'),
            ),
            ffield.label,
        )

    def test_entity_fk__empty(self):
        instance_source = CreatedEntitySource(model=FakeContact)
        source = EntityFKSource(entity_source=instance_source, field_name='phone')
        self.assertIsNone(source.extract({instance_source.type_id: None}))

    def test_entity_fk__useless_formfield(self):
        "No FK is available."
        self.assertIsNone(EntityFKSource.composed_config_formfield(
            sub_source=CreatedEntitySource(model=FakeImage),
            user=self.get_root_user(),
        ))

    def test_entity_fk__eq(self):
        create_orga = partial(FakeOrganisation.objects.create, user=self.get_root_user())
        entity1 = create_orga(name='Acme1', phone='123456')

        field_name1 = 'phone'
        source1 = EntityFKSource(
            entity_source=FixedEntitySource(entity=entity1),
            field_name=field_name1,
        )
        self.assertEqual(
            source1,
            EntityFKSource(
                entity_source=FixedEntitySource(entity=entity1),
                field_name=field_name1,
            ),
        )
        self.assertNotEqual(
            source1,
            EntityFKSource(
                entity_source=FixedEntitySource(entity=entity1),
                field_name='email',  # <==
            ),
        )
        self.assertNotEqual(
            source1,
            EntityFKSource(
                entity_source=FixedEntitySource(
                    entity=create_orga(name='Acme2', phone='123456'),
                ),
                field_name=field_name1,
            ),
        )
        self.assertNotEqual(source1, None)

    def test_entity_fk__render1(self):
        instance_source = CreatedEntitySource(model=FakeContact)
        source = EntityFKSource(
            entity_source=instance_source,
            field_name='image',
        )
        user = self.get_root_user()
        self.assertEqual(
            _('Field «{field}» of: {source}').format(
                field=_('Photograph'),
                source=instance_source.render(user=user, mode=source.TEXT_PLAIN),
            ),
            source.render(user=user, mode=source.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            '<span>{}</span>'.format(
                _('Field «{field}» of: {source}').format(
                    field=_('Photograph'),
                    source=instance_source.render(user=user, mode=source.HTML),
                )
            ),
            source.render(user=user, mode=source.HTML),
        )

    def test_entity_fk__render2(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')
        instance_source = FixedEntitySource(entity=orga)
        source = EntityFKSource(entity_source=instance_source, field_name='image')
        self.assertEqual(
            _('Field «{field}» of: {source}').format(
                field=_('Logo'),
                source=instance_source.render(user=user, mode=source.TEXT_PLAIN),
            ),
            source.render(user=user, mode=source.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            '<span>{}</span>'.format(
                _('Field «{field}» of: {source}').format(
                    field=_('Logo'),
                    source=instance_source.render(user=user, mode=source.HTML),
                )
            ),
            source.render(user=user, mode=source.HTML),
        )

    def test_first_related_entity__str_id(self):
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

        subject_source1 = CreatedEntitySource(model=FakeOrganisation)
        source = FirstRelatedEntitySource(
            subject_source=subject_source1,
            rtype=rtype.id,
            object_model=FakeOrganisation,
        )
        self.assertIsInstance(source, WorkflowActionSource)
        self.assertEqual('first_related',  source.type_id)
        self.assertEqual(subject_source1,  source.subject_source)
        self.assertEqual(FakeOrganisation, source.object_model)
        self.assertEqual(FakeOrganisation, source.model)

        with self.assertNumQueries(1):
            self.assertEqual(rtype, source.relation_type)

        with self.assertNumQueries(0):
            source.relation_type  # NOQA

        self.assertDictEqual(
            {
                'type': 'first_related',
                'subject': subject_source1.to_dict(),
                'rtype': rtype.id,
                'object_model': 'creme_core-fakeorganisation',
            },
            source.to_dict(),
        )

        # NB: 'orga2' is the first related FakeOrganisation instance
        ctxt_key1 = CreatedEntitySource.type_id
        self.assertEqual(orga2, source.extract({ctxt_key1: contact1}))

        # Empty result
        self.assertIsNone(source.extract({ctxt_key1: None}))
        self.assertIsNone(source.extract({ctxt_key1: contact2}))

        # Deserialization ---
        subject_source2 = EditedEntitySource(model=FakeOrganisation)
        deserialized = FirstRelatedEntitySource.from_dict(
            data={
                'type': FirstRelatedEntitySource.type_id,
                'subject': subject_source2.to_dict(),
                'rtype': rtype.symmetric_type_id,
                'object_model': 'creme_core-fakecontact',
            },
            registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, FirstRelatedEntitySource)
        self.assertEqual(subject_source2,      deserialized.subject_source)
        self.assertEqual(FakeContact,          deserialized.object_model)
        self.assertEqual(rtype.symmetric_type, deserialized.relation_type)

        # Configuration ---
        with self.assertRaises(ValueError) as cm:
            source.config_formfield(user=user)
        self.assertEqual(
            'This type of source cannot be used as root source',
            str(cm.exception),
        )

        ffield = FirstRelatedEntitySource.composed_config_formfield(
            sub_source=CreatedEntitySource(model=FakeContact), user=user,
        )
        from creme.creme_core.forms import workflows as wf_forms
        self.assertIsInstance(ffield, wf_forms.FirstRelatedEntitySourceField)
        self.assertEqual(
            _('First related entity to: {source}').format(
                source=_('Created entity ({type})').format(type='Test Contact'),
            ),
            ffield.label,
        )

    def test_first_related_entity__rtype_instance(self):
        rtype = RelationType.objects.get(id=REL_SUB_HAS)

        subject_source = CreatedEntitySource(model=FakeContact)
        source = FirstRelatedEntitySource(
            subject_source=subject_source,
            rtype=rtype,
            object_model=FakeOrganisation,
        )

        with self.assertNumQueries(0):
            self.assertEqual(rtype, source.relation_type)

        self.assertDictEqual(
            {
                'type': 'first_related',
                'subject': subject_source.to_dict(),
                'rtype': rtype.id,
                'object_model': 'creme_core-fakeorganisation',
            },
            source.to_dict(),
        )

    def test_first_related_entity__eq(self):
        rtype = RelationType.objects.get(id=REL_SUB_HAS)

        source1 = FirstRelatedEntitySource(
            subject_source=CreatedEntitySource(model=FakeContact),
            rtype=rtype,
            object_model=FakeOrganisation,
        )
        self.assertEqual(
            source1,
            FirstRelatedEntitySource(
                subject_source=CreatedEntitySource(model=FakeContact),
                rtype=rtype,
                object_model=FakeOrganisation,
            ),
        )
        self.assertEqual(
            source1,
            FirstRelatedEntitySource(
                subject_source=CreatedEntitySource(model=FakeContact),
                rtype=rtype.id,
                object_model=FakeOrganisation,
            ),
        )
        self.assertNotEqual(
            source1,
            FirstRelatedEntitySource(
                subject_source=EditedEntitySource(model=FakeContact),  # <===
                rtype=rtype.id,
                object_model=FakeOrganisation,
            ),
        )
        self.assertNotEqual(
            source1,
            FirstRelatedEntitySource(
                subject_source=CreatedEntitySource(model=FakeContact),
                rtype=rtype.symmetric_type,  # <===
                object_model=FakeOrganisation,
            ),
        )
        self.assertNotEqual(
            source1,
            FirstRelatedEntitySource(
                subject_source=CreatedEntitySource(model=FakeContact),
                rtype=rtype,
                object_model=FakeContact,  # <===
            ),
        )
        self.assertNotEqual(source1, None)

    def test_first_related_entity__render1(self):
        rtype = RelationType.objects.get(id=REL_SUB_HAS)

        subject_source = CreatedEntitySource(model=FakeContact)
        source = FirstRelatedEntitySource(
            subject_source=subject_source,
            rtype=rtype,
            object_model=FakeOrganisation,
        )

        user = self.get_root_user()
        self.assertEqual(
            _('First related «{type}» by «{predicate}» to: {source}').format(
                type='Test Organisation',
                predicate=rtype.predicate,
                source=subject_source.render(user=user, mode=source.TEXT_PLAIN),
            ),
            source.render(user=user, mode=source.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            '<span>{}</span>'.format(
                _('First related «{type}» by «{predicate}» to: {source}').format(
                    type='Test Organisation',
                    predicate=rtype.predicate,
                    source=subject_source.render(user=user, mode=source.TEXT_PLAIN),
                )
            ),
            source.render(user=user, mode=source.HTML),
        )

    def test_first_related_entity__render2(self):
        user = self.get_root_user()
        rtype = RelationType.objects.get(id=REL_OBJ_HAS)
        orga = FakeOrganisation.objects.create(user=user, name='Acme')

        subject_source = FixedEntitySource(entity=orga)
        source = FirstRelatedEntitySource(
            subject_source=subject_source,
            rtype=rtype,
            object_model=FakeContact,
        )

        self.assertEqual(
            _('First related «{type}» by «{predicate}» to: {source}').format(
                type='Test Contact',
                predicate=rtype.predicate,
                source=subject_source.render(user=user, mode=source.TEXT_PLAIN),
            ),
            source.render(user=user, mode=source.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            '<span>{}</span>'.format(
                _('First related «{type}» by «{predicate}» to: {source}').format(
                    type='Test Contact',
                    predicate=rtype.predicate,
                    source=subject_source.render(user=user, mode=source.HTML),
                )
            ),
            source.render(user=user, mode=source.HTML),
        )


class ActionsTestCase(CremeTestCase):
    def test_property_adding__str_uuid(self):
        user = self.get_root_user()
        type_id = 'creme_core-property_adding'
        self.assertEqual(type_id, PropertyAddingAction.type_id)
        self.assertEqual(_('Adding a property'), PropertyAddingAction.verbose_name)

        # Instance ---
        ptype = CremePropertyType.objects.create(text='Is kawaiiii')
        source = CreatedEntitySource(model=FakeOrganisation)
        action = PropertyAddingAction(entity_source=source, ptype=str(ptype.uuid))
        self.assertEqual(source, action.entity_source)

        with self.assertNumQueries(1):
            self.assertEqual(ptype, action.property_type)

        with self.assertNumQueries(0):
            action.property_type  # NOQA

        serialized = {
            'type': type_id,
            'entity': {
                'type': CreatedEntitySource.type_id,
                'model': 'creme_core-fakeorganisation',
            },
            'ptype': str(ptype.uuid),
        }
        self.assertDictEqual(serialized, action.to_dict())
        self.assertHTMLEqual(
            _('Adding the property «{property}» to: {source}').format(
                property=ptype.text,
                source=source.render(user=user, mode=source.HTML),
            ),
            action.render(user=user),
        )

        # De-serialisation ---
        deserialized = PropertyAddingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, PropertyAddingAction)
        self.assertEqual(ptype, deserialized.property_type)
        self.assertEqual(
            CreatedEntitySource(model=FakeOrganisation),
            deserialized.entity_source,
        )

        # Execution ---
        entity = FakeOrganisation.objects.create(user=user, name='Acme')
        ctxt_key = source.type_id
        deserialized.execute(context={ctxt_key: entity})
        self.assertHasProperty(entity=entity, ptype=ptype)

        # Execute twice => beware of property uniqueness
        with self.assertNoException():
            deserialized.execute(context={ctxt_key: entity})

        # With empty source
        with self.assertNoException():
            deserialized.execute(context={ctxt_key: None})

        # Configuration
        from creme.creme_core.forms.workflows import PropertyAddingActionForm
        self.assertIs(
            PropertyAddingActionForm, PropertyAddingAction.config_form_class(),
        )

    def test_property_adding__ptype_instance(self):
        user = self.get_root_user()
        ptype = CremePropertyType.objects.create(text='Is swag')
        entity = FakeOrganisation.objects.create(user=user, name='Acme')
        source = FixedEntitySource(entity=entity)
        action = PropertyAddingAction(entity_source=source, ptype=ptype)

        action.execute(context={})
        self.assertHasProperty(entity=entity, ptype=ptype)

        with self.assertNumQueries(0):
            self.assertEqual(ptype, action.property_type)

        # Render ---
        output = action.render(user=user)
        self.assertHTMLEqual(
            _('Adding the property «{property}» to: {source}').format(
                property=ptype.text,
                source=source.render(user=user, mode=source.HTML),
            ),
            output,
        )
        self.assertIsInstance(output, SafeString)

    def test_relation_adding__str_id(self):
        user = self.get_root_user()
        type_id = 'creme_core-relation_adding'
        self.assertEqual(type_id, RelationAddingAction.type_id)
        self.assertEqual(
            _('Adding a relationship'), RelationAddingAction.verbose_name,
        )

        # Instance ---
        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        source1 = SubjectEntitySource(model=FakeContact)
        source2 = ObjectEntitySource(model=FakeOrganisation)
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
            'subject': source1.to_dict(),
            'rtype': rtype.id,
            'object': source2.to_dict(),
        }
        self.assertDictEqual(serialized, action.to_dict())
        self.assertHTMLEqual(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{subject}</li>'
            '  <li>{object}</li>'
            ' </ul>'
            '</div>'.format(
                label=_('Adding the relationship «{predicate}» between:').format(
                    predicate=rtype.predicate,
                ),
                subject=source1.render(user=user, mode=source1.HTML),
                object=source2.render(user=user, mode=source2.HTML),
            ),
            action.render(user=user),
        )

        # De-serialisation ---
        deserialized = RelationAddingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, RelationAddingAction)
        self.assertEqual(rtype,   deserialized.relation_type)
        self.assertEqual(source1, deserialized.subject_source)
        self.assertEqual(source2, deserialized.object_source)

        # Execution ---
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='Acme1')
        entity2 = create_orga(name='Acme2')
        ctxt_key1 = source1.type_id
        ctxt_key2 = source2.type_id
        deserialized.execute({ctxt_key1: entity1, ctxt_key2: entity2})
        self.assertHaveRelation(subject=entity1, type=rtype, object=entity2)

        # Execute twice => beware of property uniqueness
        with self.assertNoException():
            deserialized.execute(context={ctxt_key1: entity1, ctxt_key2: entity2})

        # With empty source
        with self.assertNoException():
            deserialized.execute(context={ctxt_key1: None,    ctxt_key2: entity2})
            deserialized.execute(context={ctxt_key1: entity1, ctxt_key2: None})

        # Configuration ---
        from creme.creme_core.forms.workflows import RelationAddingActionForm
        self.assertIs(
            RelationAddingActionForm, RelationAddingAction.config_form_class(),
        )

    def test_relation_adding__rtype_instance(self):
        rtype = RelationType.objects.get(id=REL_OBJ_HAS)
        action = RelationAddingAction(
            subject_source=CreatedEntitySource(model=FakeContact),
            rtype=rtype,
            object_source=FixedEntitySource(
                entity=FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme'),
            ),
        )

        with self.assertNumQueries(0):
            self.assertEqual(rtype, action.relation_type)


class MiddlewareTestCase(CremeTestCase):
    def test_simple(self):
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is cool')
        Workflow.objects.create(
            title='Created Organisations are cool',
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=FakeOrganisation),
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

    def test_disabled(self):
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is cool')
        Workflow.objects.create(
            title='Created Organisations are cool',
            enabled=False,
            content_type=FakeOrganisation,
            trigger=EntityCreationTrigger(model=FakeOrganisation),
            actions=[
                PropertyAddingAction(
                    entity_source=CreatedEntitySource(model=FakeOrganisation),
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
        self.assertHasNoProperty(entity=orga, ptype=ptype)

    # TODO: middleware + conditions
