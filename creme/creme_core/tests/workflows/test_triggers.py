from uuid import uuid4

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.constants import REL_OBJ_HAS, REL_SUB_HAS
from creme.creme_core.core.workflow import (
    EntityCreated,
    EntityEdited,
    PropertyAdded,
    RelationAdded,
    WorkflowBrokenData,
)
from creme.creme_core.forms import workflows as wf_forms
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    FakeProduct,
    Relation,
    RelationType,
)
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    EntityCreationTrigger,
    EntityEditionTrigger,
    ObjectEntitySource,
    PropertyAddingTrigger,
    RelationAddingTrigger,
    SubjectEntitySource,
    TaggedEntitySource,
)

from ..base import CremeTestCase


class EntityCreationTriggerTestCase(CremeTestCase):
    def test_main(self):
        type_id = 'creme_core-entity_creation'
        self.assertEqual(type_id, EntityCreationTrigger.type_id)
        self.assertEqual(
            _('An entity has been created'), EntityCreationTrigger.verbose_name,
        )

        trigger = EntityCreationTrigger(model=FakeContact)
        self.assertEqual(FakeContact, trigger.model)

        model_key = 'creme_core.fakecontact'
        serialized = {'type': type_id, 'model': model_key}
        self.assertDictEqual(serialized, trigger.to_dict())
        self.assertEqual(
            # _('A «{}» has been created').format('Test Contact'),
            _('A «{model}» has been created').format(model='Test Contact'),
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

    def test_eq(self):
        trigger1 = EntityCreationTrigger(model=FakeContact)
        self.assertEqual(trigger1, EntityCreationTrigger(model=FakeContact))
        self.assertNotEqual(trigger1, EntityCreationTrigger(model=FakeOrganisation))
        self.assertNotEqual(trigger1, EntityEditionTrigger(model=FakeContact))

    def test_error(self):
        with self.assertRaises(WorkflowBrokenData):
            EntityCreationTrigger.from_dict({
                'type': EntityCreationTrigger.type_id,
                'model': 'uninstalled_app.whatever',
            })


class EntityEditionTriggerTestCase(CremeTestCase):
    def test_main(self):
        type_id = 'creme_core-entity_edition'
        self.assertEqual(type_id, EntityEditionTrigger.type_id)
        self.assertEqual(
            _('An entity has been modified'), EntityEditionTrigger.verbose_name,
        )

        trigger = EntityEditionTrigger(model=FakeOrganisation)
        self.assertEqual(FakeOrganisation, trigger.model)
        model_key = 'creme_core.fakeorganisation'
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

    def test_eq(self):
        trigger1 = EntityEditionTrigger(model=FakeContact)
        self.assertEqual(trigger1, EntityEditionTrigger(model=FakeContact))
        self.assertNotEqual(trigger1, EntityEditionTrigger(model=FakeOrganisation))
        self.assertNotEqual(trigger1, EntityCreationTrigger(model=FakeContact))

    def test_error(self):
        with self.assertRaises(WorkflowBrokenData):
            EntityEditionTrigger.from_dict({
                'type': EntityEditionTrigger.type_id,
                'model': 'uninstalled_app.whatever',
            })


class PropertyAddingTriggerTestCase(CremeTestCase):
    def test_str_uuid(self):
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

        model_key = 'creme_core.fakeorganisation'

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

    def test_ptype_instance(self):
        ptype = CremePropertyType.objects.create(text='Nice')
        trigger = PropertyAddingTrigger(entity_model=FakeContact, ptype=ptype)
        self.assertEqual(FakeContact, trigger.entity_model)

        with self.assertNumQueries(0):
            self.assertEqual(ptype, trigger.property_type)

    def test_eq(self):
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

    def test_ptype_error(self):
        trigger = PropertyAddingTrigger.from_dict({
            'type': PropertyAddingTrigger.type_id,
            'entity_model': 'creme_core.fakeorganisation',
            'ptype': str(uuid4()),
        })

        with self.assertNumQueries(1):
            with self.assertRaises(WorkflowBrokenData) as cm:
                trigger.property_type  # NOQA
        self.assertEqual(
            _('The property type does not exist anymore'), str(cm.exception),
        )

        with self.assertNumQueries(0):
            with self.assertRaises(WorkflowBrokenData):
                trigger.property_type  # NOQA

        self.assertHTMLEqual(
            '{label}<p class="errorlist">{error}</p>'.format(
                label=_('A property has been added'),
                error=_('The property type does not exist anymore'),
            ),
            trigger.description,
        )

    def test_model_error(self):
        with self.assertRaises(WorkflowBrokenData):
            PropertyAddingTrigger.from_dict({
                'type': PropertyAddingTrigger.type_id,
                'entity_model': 'unknown.invalid',
                'ptype': str(uuid4()),
            })

    def test_activation_queries(self):
        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='Pineapple')
        ptype = CremePropertyType.objects.create(text='Nice')
        prop = CremeProperty(creme_entity=orga, type=ptype)

        ContentType.objects.get_for_model(FakeOrganisation)  # Fill the cache

        with self.assertNumQueries(0):
            trigger = PropertyAddingTrigger.from_dict({
                'type': PropertyAddingTrigger.type_id,
                'entity_model': 'creme_core.fakeorganisation',
                'ptype': str(ptype.uuid),
            })

        with self.assertNumQueries(0):
            ctxt = trigger.activate(PropertyAdded(creme_property=prop))
        self.assertIsInstance(ctxt, dict)


class RelationAddingTriggerTestCase(CremeTestCase):
    def test_str_id(self):
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

        subject_model_key = 'creme_core.fakeorganisation'
        object_model_key = 'creme_core.fakecontact'
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

    def test_rtype_instance(self):
        rtype = RelationType.objects.get(id=REL_OBJ_HAS)
        trigger = RelationAddingTrigger(
            subject_model=FakeContact, rtype=rtype, object_model=FakeOrganisation,
        )
        self.assertEqual(FakeContact,      trigger.subject_model)
        self.assertEqual(FakeOrganisation, trigger.object_model)

        with self.assertNumQueries(0):
            self.assertEqual(rtype, trigger.relation_type)

    def test_eq(self):
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

    def test_model_errors(self):
        with self.assertRaises(WorkflowBrokenData):
            RelationAddingTrigger.from_dict({
                'type': RelationAddingTrigger.type_id,
                'subject_model': 'unknown.invalid',
                'rtype': str(uuid4()),
                'object_model': 'creme_core.fakecontact',
            })

        with self.assertRaises(WorkflowBrokenData):
            RelationAddingTrigger.from_dict({
                'type': RelationAddingTrigger.type_id,
                'subject_model': 'creme_core.fakecontact',
                'rtype': str(uuid4()),
                'object_model': 'unknown.invalid',
            })

    def test_relation_adding__rtype_error(self):
        trigger = RelationAddingTrigger.from_dict({
            'type': RelationAddingTrigger.type_id,
            'subject_model': 'creme_core.fakecontact',
            'rtype': str(uuid4()),
            'object_model': 'creme_core.fakeorganisation',
        })

        with self.assertNumQueries(1):
            with self.assertRaises(WorkflowBrokenData) as cm:
                trigger.relation_type  # NOQA
        self.assertEqual(
            _('The relation type does not exist anymore'), str(cm.exception),
        )

        with self.assertNumQueries(0):
            with self.assertRaises(WorkflowBrokenData):
                trigger.relation_type  # NOQA

        self.assertHTMLEqual(
            '{label}<p class="errorlist">{error}</p>'.format(
                label=_('A relation has been added'),
                error=_('The relation type does not exist anymore'),
            ),
            trigger.description,
        )
