from functools import partial

from django.db.transaction import atomic
from django.db.utils import IntegrityError
from django.utils.translation import gettext as _

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.entity_filter import condition_handler
from creme.creme_core.core.entity_filter.operators import EndsWithOperator
from creme.creme_core.core.workflow import (
    BrokenAction,
    BrokenSource,
    BrokenTrigger,
    EntityCreated,
    EntityEdited,
    PropertyAdded,
    RelationAdded,
    WorkflowAction,
    WorkflowBrokenData,
    WorkflowConditions,
    WorkflowEngine,
    WorkflowEvent,
    WorkflowEventQueue,
    WorkflowRegistry,
    WorkflowSource,
    WorkflowTrigger,
    model_as_key,
    model_from_key,
    workflow_registry,
)
from creme.creme_core.forms.workflows import (
    CreatedEntitySourceField,
    EditedEntitySourceField,
    EntityFKSourceField,
    FirstRelatedEntitySourceField,
    FixedEntitySourceField,
    ObjectEntitySourceField,
    SubjectEntitySourceField,
)
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    Language,
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

from ..base import CremeTestCase, CremeTransactionTestCase


class UtilsTestCase(CremeTestCase):
    def test_model_to_key(self):
        self.assertEqual('creme_core.fakecontact', model_as_key(FakeContact))
        self.assertEqual('creme_core.fakeorganisation', model_as_key(FakeOrganisation))

    def test_key_to_model(self):
        self.assertEqual(FakeContact, model_from_key('creme_core.fakecontact'))
        self.assertEqual(FakeOrganisation, model_from_key('creme_core.fakeorganisation'))

    def test_key_to_model__error(self):
        key = 'uninstalled_app.model'
        with self.assertRaises(WorkflowBrokenData) as cm:
            model_from_key(key)
        self.assertEqual(
            _('The model «{key}» is invalid').format(key=key), str(cm.exception)
        )

        self.assertRaises(WorkflowBrokenData, model_from_key, '')
        self.assertRaises(WorkflowBrokenData, model_from_key, 'creme_core')
        self.assertRaises(WorkflowBrokenData, model_from_key, 'creme_core.fakecontact.suffix')


class WorkflowEventsTestCase(CremeTestCase):
    def test_entity_created(self):
        user = self.get_root_user()
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='Acme1')

        evt = EntityCreated(entity=entity1)
        self.assertIsInstance(evt, WorkflowEvent)
        self.assertEqual(entity1, evt.entity)

        # eq ---
        entity2 = create_orga(name='Acme2')
        self.assertEqual(EntityCreated(entity=entity1), evt)
        self.assertNotEqual(EntityCreated(entity=entity2), evt)
        self.assertNotEqual(EntityEdited(entity=entity1), evt)

        # inhibit ---
        self.assertIs(evt.inhibits(EntityCreated(entity=entity2)), False)
        self.assertIs(evt.inhibits(EntityEdited(entity=entity2)), False)
        self.assertIs(evt.inhibits(EntityEdited(entity=entity1)), True)

    def test_entity_edited(self):
        user = self.get_root_user()
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='Acme1')

        evt = EntityEdited(entity=entity1)
        self.assertIsInstance(evt, WorkflowEvent)
        self.assertEqual(entity1, evt.entity)

        # eq ---
        self.assertEqual(EntityEdited(entity=entity1), evt)
        self.assertNotEqual(EntityEdited(entity=create_orga(name='Acme2')), evt)
        self.assertNotEqual(EntityCreated(entity=entity1), evt)

    def test_property_added(self):
        user = self.get_root_user()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='Acme1')
        entity2 = create_orga(name='Acme2')

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is cool')
        ptype2 = create_ptype(text='Is very cool')

        create_prop = CremeProperty.objects.create
        prop11 = create_prop(creme_entity=entity1, type=ptype1)

        evt = PropertyAdded(creme_property=prop11)
        self.assertIsInstance(evt, WorkflowEvent)
        self.assertEqual(prop11, evt.creme_property)

        # eq ---
        self.assertEqual(PropertyAdded(creme_property=prop11), evt)
        self.assertNotEqual(
            PropertyAdded(creme_property=create_prop(creme_entity=entity2, type=ptype1)),
            evt,
        )
        self.assertNotEqual(
            PropertyAdded(creme_property=create_prop(creme_entity=entity1, type=ptype2)),
            evt,
        )
        self.assertNotEqual(evt, EntityCreated(entity=entity1))

    def test_relation_added(self):
        user = self.get_root_user()
        entity1 = FakeContact.objects.create(user=user, first_name='Bugs', last_name='Bunny')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity2 = create_orga(name='Acme1')

        rtype = RelationType.objects.get(id=REL_SUB_HAS)

        create_rel = partial(Relation.objects.create, user=user)
        rel = create_rel(subject_entity=entity1, type=rtype, object_entity=entity2)

        evt = RelationAdded(relation=rel)
        self.assertIsInstance(evt, WorkflowEvent)
        self.assertEqual(rel, evt.relation)

        # eq ---
        self.assertEqual(RelationAdded(relation=rel), evt)
        self.assertNotEqual(
            RelationAdded(relation=create_rel(
                subject_entity=entity1, type=rtype, object_entity=create_orga(name='Acme2'),
            )),
            evt,
        )
        self.assertNotEqual(evt, EntityCreated(entity=entity1))


class WorkflowEventQueueTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        user = cls.get_root_user()
        cls.entity1 = FakeOrganisation.objects.create(user=user, name='Acme')
        cls.entity2 = FakeContact.objects.create(
            user=user, first_name='Bugs', last_name='Bunny',
        )

    def test_basic(self):
        queue = WorkflowEventQueue()
        self.assertFalse(queue)
        self.assertEqual(0, len(queue))
        self.assertListEqual([], queue.pickup())

        # ---
        queue.append(EntityCreated(entity=self.entity1)).append(EntityEdited(entity=self.entity2))
        self.assertTrue(queue)
        self.assertEqual(2, len(queue))
        self.assertListEqual(
            [EntityCreated(entity=self.entity1), EntityEdited(entity=self.entity2)],
            queue.pickup(),
        )
        self.assertListEqual([], queue.pickup())

    def test_slice(self):
        queue = WorkflowEventQueue()
        self.assertListEqual([], queue.pickup(start=1))

        # ---
        queue.append(EntityCreated(entity=self.entity1)).append(EntityEdited(entity=self.entity2))
        self.assertListEqual(
            [EntityEdited(entity=self.entity2)], queue.pickup(start=1),
        )
        self.assertListEqual(
            [EntityCreated(entity=self.entity1)], queue.pickup(start=0),
        )
        self.assertListEqual([], queue.pickup())

    def test_duplicate(self):
        queue = WorkflowEventQueue().append(
            EntityCreated(entity=self.entity1)
        ).append(
            EntityEdited(entity=self.entity2)
        ).append(
            EntityCreated(entity=self.entity1)  # Should not be appended
        )
        self.assertListEqual(
            [EntityCreated(entity=self.entity1), EntityEdited(entity=self.entity2)],
            queue.pickup(),
        )

    def test_inhibited(self):
        queue = WorkflowEventQueue().append(
            EntityCreated(entity=self.entity1)
        ).append(
            EntityEdited(entity=self.entity2)
        ).append(
            EntityEdited(entity=self.entity1)  # Should not be appended
        )
        self.assertListEqual(
            [EntityCreated(entity=self.entity1), EntityEdited(entity=self.entity2)],
            queue.pickup(),
        )


class SignalHandlersTestCase(CremeTestCase):
    def test_entity_created(self):
        queue = WorkflowEngine.get_current()._queue  # TODO: meh
        queue.pickup()

        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        events = queue.pickup()

        event = self.get_alone_element(events)
        self.assertIsInstance(event, EntityCreated)
        self.assertEqual(orga, event.entity)

    def test_entity_created__error(self):
        queue = WorkflowEngine.get_current()._queue  # TODO: meh
        queue.pickup()

        with self.assertRaises(IntegrityError):
            FakeOrganisation.objects.create(
                # user=...,
                name='Acme',
            )
        self.assertFalse(queue.pickup())

    def test_entity_edited(self):
        queue = WorkflowEngine.get_current()._queue  # TODO: meh

        orga = self.refresh(
            FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        )
        queue.pickup()

        orga.email = 'contact@acme.com'
        orga.save()
        events = queue.pickup()

        event = self.get_alone_element(events)
        self.assertIsInstance(event, EntityEdited)
        self.assertEqual(orga, event.entity)

    def test_entity_edited__m2m(self):
        queue = WorkflowEngine.get_current()._queue  # TODO: meh

        l1, l2 = Language.objects.all()[:2]
        contact = self.refresh(FakeContact.objects.create(
            user=self.get_root_user(), first_name='Bugs', last_name='Bunny',
        ))
        queue.pickup()

        contact.languages.set([l1])
        expected = EntityEdited(entity=contact)
        self.assertEqual(expected, self.get_alone_element(queue.pickup()))

        # ----
        contact.languages.add(l2)
        self.assertEqual(expected, self.get_alone_element(queue.pickup()))

        # ----
        contact.languages.remove(l1)
        self.assertEqual(expected, self.get_alone_element(queue.pickup()))

        # ----
        contact.languages.clear()
        self.assertEqual(expected, self.get_alone_element(queue.pickup()))

    def test_property_added(self):
        queue = WorkflowEngine.get_current()._queue  # TODO: meh

        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')

        ptype = CremePropertyType.objects.create(text='Important')
        queue.pickup()

        prop = CremeProperty.objects.create(creme_entity=orga, type=ptype)
        events = queue.pickup()

        event = self.get_alone_element(events)
        self.assertIsInstance(event, PropertyAdded)
        self.assertEqual(prop, event.creme_property)

    def test_relation_added(self):
        queue = WorkflowEngine.get_current()._queue  # TODO: meh

        user = self.get_root_user()
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Acme1')
        orga2 = create_orga(name='Acme2')

        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        queue.pickup()

        rel = Relation.objects.create(
            user=user, subject_entity=orga1, type=rtype, object_entity=orga2,
        )
        events = queue.pickup()
        self.assertEqual(2, len(events), events)

        event1 = events[0]
        self.assertIsInstance(event1, RelationAdded)
        self.assertEqual(rel, event1.relation)

        event2 = events[1]
        self.assertIsInstance(event2, RelationAdded)
        self.assertEqual(rel.symmetric_relation, event2.relation)


class WorkflowRegistryTestCase(CremeTestCase):
    def test_broken_trigger(self):
        message = 'Model is invalid'
        trigger = BrokenTrigger(message=message)
        self.assertIsInstance(trigger, WorkflowTrigger)
        self.assertEqual('',      trigger.type_id)
        self.assertEqual(message, trigger.message)
        self.assertIsNone(trigger.activate(EntityCreated(entity=FakeContact())))
        self.assertHTMLEqual(
            f'<p class="errorlist">{message}</p>', trigger.description,
        )

    def test_broken_source(self):
        message = 'Model is invalid'
        source = BrokenSource(message=message)
        self.assertIsInstance(source, WorkflowSource)
        self.assertEqual('', source.type_id)
        self.assertEqual(message, source.message)
        self.assertIsNone(source.extract({}))

        user = self.get_root_user()
        self.assertEqual(
            _('Error ({message})').format(message=message),
            source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            f'<p class="errorlist">{message}</p>',
            source.render(user=user, mode=source.RenderMode.HTML),
        )

        with self.assertRaises(WorkflowBrokenData) as cm:
            source.model  # NOQA
        self.assertEqual(message, str(cm.exception))

    def test_broken_action(self):
        message = 'Model is invalid'
        action = BrokenAction(message=message)
        self.assertIsInstance(action, WorkflowAction)
        self.assertEqual('', action.type_id)
        self.assertEqual(message, action.message)
        self.assertHTMLEqual(
            f'<p class="errorlist">{message}</p>',
            action.render(user=self.get_root_user()),
        )

        with self.assertNoException():
            action.execute({})

    def test_register_triggers(self):
        registry = WorkflowRegistry()
        self.assertFalse([*registry.trigger_classes])

        registry.register_triggers(EntityCreationTrigger, RelationAddingTrigger)
        self.assertCountEqual(
            [EntityCreationTrigger, RelationAddingTrigger],
            [*registry.trigger_classes],
        )

        registry.unregister_triggers(EntityCreationTrigger)
        self.assertListEqual([RelationAddingTrigger], [*registry.trigger_classes])

    def test_register_triggers__empty_id(self):
        registry = WorkflowRegistry()

        class EmptyIDTrigger(EntityCreationTrigger):
            type_id = ''

        with self.assertRaises(registry.RegistrationError):
            registry.register_triggers(EmptyIDTrigger)

    def test_register_triggers__duplicated_id(self):
        class DuplicatedIDTrigger(EntityCreationTrigger):
            pass

        registry = WorkflowRegistry().register_triggers(EntityCreationTrigger)

        with self.assertRaises(registry.RegistrationError):
            registry.register_triggers(DuplicatedIDTrigger)

    def test_unregister_triggers_error(self):
        registry = WorkflowRegistry()

        with self.assertRaises(registry.UnRegistrationError):
            registry.unregister_triggers(EntityCreationTrigger)

    def test_build_trigger(self):
        registry = WorkflowRegistry().register_triggers(
            EntityCreationTrigger, RelationAddingTrigger,
        )

        trigger1 = registry.build_trigger(
            EntityCreationTrigger(model=FakeContact).to_dict()
        )
        self.assertIsInstance(trigger1, EntityCreationTrigger)
        self.assertEqual(FakeContact, trigger1.model)

        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        trigger2 = registry.build_trigger(
            RelationAddingTrigger(
                subject_model=FakeContact, rtype=rtype.id,
                object_model=FakeOrganisation,
            ).to_dict()
        )
        self.assertIsInstance(trigger2, RelationAddingTrigger)
        self.assertEqual(FakeContact,      trigger2.subject_model)
        self.assertEqual(FakeOrganisation, trigger2.object_model)
        self.assertEqual(rtype,            trigger2.relation_type)

    def test_build_trigger__invalid_id(self):
        type_id = 'invalid'
        trigger = WorkflowRegistry().build_trigger({'type': type_id})
        self.assertIsInstance(trigger, BrokenTrigger)
        self.assertEqual(
            _(
                'The type of trigger «{type}» is invalid (uninstalled app?)'
            ).format(type=type_id),
            trigger.message,
        )

    def test_build_trigger__fatal(self):
        msg = 'The key "foobar" was not found.'

        class ExplodingTrigger(WorkflowTrigger):
            type_id = 'exploding'
            verbose_name = 'Explosion!!'

            @classmethod
            def from_dict(cls, data):
                raise KeyError(msg)

        registry = WorkflowRegistry().register_triggers(ExplodingTrigger)
        trigger = registry.build_trigger({'type': ExplodingTrigger.type_id})
        self.assertIsInstance(trigger, BrokenTrigger)
        self.assertEqual(
            _(
                'The trigger «{name}» is broken (original error: {error})'
            ).format(name=ExplodingTrigger.verbose_name, error=f"'{msg}'"),
            trigger.message,
        )

    def test_register_sources(self):
        registry = WorkflowRegistry()
        self.assertFalse([*registry.source_classes])

        registry.register_sources(CreatedEntitySource, FixedEntitySource)
        self.assertCountEqual(
            [CreatedEntitySource, FixedEntitySource],
            [*registry.source_classes],
        )

        registry.unregister_sources(CreatedEntitySource)
        self.assertListEqual([FixedEntitySource], [*registry.source_classes])

    def test_register_sources__empty_id(self):
        class EmptyIDSource(CreatedEntitySource):
            type_id = ''

        registry = WorkflowRegistry()

        with self.assertRaises(registry.RegistrationError):
            registry.register_sources(EmptyIDSource)

    def test_register_sources__duplicated_id(self):
        class DuplicatedIDSource(CreatedEntitySource):
            pass

        registry = WorkflowRegistry().register_sources(CreatedEntitySource)

        with self.assertRaises(registry.RegistrationError):
            registry.register_sources(DuplicatedIDSource)

    def test_register_sources__invalid_char_in_id(self):
        class InvalidIDSource(CreatedEntitySource):
            type_id = 'type_with_p|pe'

        registry = WorkflowRegistry().register_sources(CreatedEntitySource)

        with self.assertRaises(registry.RegistrationError):
            registry.register_sources(InvalidIDSource)

    def test_unregister_sources__error(self):
        registry = WorkflowRegistry()

        with self.assertRaises(registry.UnRegistrationError):
            registry.unregister_sources(CreatedEntitySource)

    def test_register_actions(self):
        registry = WorkflowRegistry()
        self.assertFalse([*registry.action_classes])
        self.assertIsNone(registry.get_action_class(PropertyAddingAction.type_id))

        registry.register_actions(PropertyAddingAction, RelationAddingAction)
        self.assertCountEqual(
            [PropertyAddingAction, RelationAddingAction],
            [*registry.action_classes],
        )
        self.assertEqual(
            PropertyAddingAction,
            registry.get_action_class(PropertyAddingAction.type_id),
        )
        self.assertEqual(
            RelationAddingAction,
            registry.get_action_class(RelationAddingAction.type_id),
        )

        registry.unregister_actions(PropertyAddingAction)
        self.assertListEqual([RelationAddingAction], [*registry.action_classes])

    def test_register_actions__empty_id(self):
        class EmptyIDAction(PropertyAddingAction):
            type_id = ''

        registry = WorkflowRegistry()

        with self.assertRaises(registry.RegistrationError):
            registry.register_actions(EmptyIDAction)

    def test_register_actions__duplicated_id(self):
        class DuplicatedIDAction(PropertyAddingAction):
            pass

        registry = WorkflowRegistry().register_actions(PropertyAddingAction)

        with self.assertRaises(registry.RegistrationError):
            registry.register_actions(DuplicatedIDAction)

    def test_unregister_actions_error(self):
        registry = WorkflowRegistry()

        with self.assertRaises(registry.UnRegistrationError):
            registry.unregister_actions(PropertyAddingAction)

    def test_build_source(self):
        registry = WorkflowRegistry().register_sources(
            CreatedEntitySource, EditedEntitySource,
            FixedEntitySource, EntityFKSource,
        )

        self.assertEqual(
            CreatedEntitySource(model=FakeContact),
            registry.build_source(CreatedEntitySource(model=FakeContact).to_dict()),
        )

        # ---
        entity = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme1')
        source2 = registry.build_source(FixedEntitySource(entity=entity).to_dict())
        self.assertIsInstance(source2, FixedEntitySource)
        self.assertEqual(entity, source2.entity)

        # ---
        field_name = 'image'
        source3 = registry.build_source(
            EntityFKSource(
                field_name=field_name,
                entity_source=EditedEntitySource(model=FakeOrganisation),
            ).to_dict()
        )
        self.assertIsInstance(source3, EntityFKSource)
        self.assertEqual(field_name,                                 source3.field_name)
        self.assertEqual(EditedEntitySource(model=FakeOrganisation), source3.sub_source)

    def test_build_source__invalid_id(self):
        type_id = 'invalid'
        source = WorkflowRegistry().build_source({'type': type_id})
        self.assertIsInstance(source, BrokenSource)
        self.assertEqual(
            _(
                'The type of source «{type}» is invalid (uninstalled app?)'
            ).format(type=type_id),
            source.message,
        )

    def test_build_source__fatal(self):
        msg = 'The key "foobar" was not found.'

        class ExplodingSource(WorkflowSource):
            type_id = 'exploding'
            verbose_name = 'Explosion!!'

            @classmethod
            def from_dict(cls, data, registry):
                raise KeyError(msg)

        registry = WorkflowRegistry().register_sources(ExplodingSource)
        action = registry.build_source({'type': ExplodingSource.type_id})
        self.assertIsInstance(action, BrokenSource)
        self.assertEqual(
            _(
                'The source «{name}» is broken (original error: {error})'
            ).format(name=ExplodingSource.verbose_name, error=f"'{msg}'"),
            action.message,
        )

    def test_build_action(self):
        registry = WorkflowRegistry().register_sources(
            CreatedEntitySource, FixedEntitySource,
        ).register_actions(PropertyAddingAction, RelationAddingAction)

        ptype = CremePropertyType.objects.create(text='Is kawaiiii')
        # TODO: several actions at once?
        action1 = registry.build_action(
            PropertyAddingAction(
                entity_source=CreatedEntitySource(model=FakeContact),
                ptype=str(ptype.uuid),
            ).to_dict(),
        )
        self.assertIsInstance(action1, PropertyAddingAction)
        self.assertEqual(ptype,                                  action1.property_type)
        self.assertEqual(CreatedEntitySource(model=FakeContact), action1.entity_source)

        # ---
        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='Acme')
        action2 = registry.build_action(
            RelationAddingAction(
                subject_source=CreatedEntitySource(model=FakeContact),
                rtype=rtype.id,
                object_source=FixedEntitySource(entity=orga),
            ).to_dict(),
        )
        self.assertIsInstance(action2, RelationAddingAction)
        self.assertEqual(rtype,                                  action2.relation_type)
        self.assertEqual(CreatedEntitySource(model=FakeContact), action2.subject_source)
        self.assertEqual(FixedEntitySource(entity=orga),         action2.object_source)

    def test_build_action__invalid_id(self):
        type_id = 'invalid'
        action = WorkflowRegistry().build_action({'type': type_id})
        self.assertIsInstance(action, BrokenAction)
        self.assertEqual(
            _(
                'The type of action «{type}» is invalid (uninstalled app?)'
            ).format(type=type_id),
            action.message,
        )

    def test_build_action__fatal(self):
        msg = 'The key "foobar" was not found.'

        class ExplodingAction(WorkflowAction):
            type_id = 'exploding'
            verbose_name = 'Explosion!!'

            @classmethod
            def from_dict(cls, data, registry):
                raise KeyError(msg)

        registry = WorkflowRegistry().register_actions(ExplodingAction)
        action = registry.build_action({'type': ExplodingAction.type_id})
        self.assertIsInstance(action, BrokenAction)
        self.assertEqual(
            _(
                'The action «{name}» is broken (original error: {error})'
            ).format(name=ExplodingAction.verbose_name, error=f"'{msg}'"),
            action.message,
        )

    def test_source_formfields(self):
        user = self.get_root_user()
        registry = WorkflowRegistry()
        self.assertListEqual(
            [], registry.source_formfields(root_sources=[], user=user)
        )

        # ---
        ffields = registry.source_formfields(
            root_sources=[CreatedEntitySource(model=FakeContact)],
            user=user,
        )
        self.assertIsList(ffields, length=1)

        kind_id, ffield = ffields[0]
        self.assertEqual('created_entity', kind_id)
        self.assertIsInstance(ffield, CreatedEntitySourceField)
        self.assertEqual(FakeContact, ffield.model)

    def test_source_formfields__extended1(self):
        user = self.get_root_user()
        registry = WorkflowRegistry().register_sources(
            FirstRelatedEntitySource,
            CreatedEntitySource,
        )

        ffields = registry.source_formfields(
            root_sources=[EditedEntitySource(model=FakeOrganisation)],
            user=user,
        )
        self.assertIsList(ffields, length=2)

        kind_id1, ffield1 = ffields[0]
        self.assertEqual('edited_entity', kind_id1)
        self.assertIsInstance(ffield1, EditedEntitySourceField)
        self.assertEqual(FakeOrganisation, ffield1.model)

        kind_id2, ffield2 = ffields[1]
        self.assertEqual('edited_entity|first_related', kind_id2)
        self.assertIsInstance(ffield2, FirstRelatedEntitySourceField)

    def test_source_formfields__extended2(self):
        user = self.get_root_user()
        registry = WorkflowRegistry().register_sources(
            CreatedEntitySource,  # Not used at root => no formfield
            EditedEntitySource,   # Not used at root => no formfield
            SubjectEntitySource,  # Root source => 1 formfield
            ObjectEntitySource,   # Root source => 1 formfield
            FixedEntitySource,    # Should produce 1 formfield (not 2!)
            EntityFKSource,  # Should produce 1 formfield per root source (so, 2)
        )

        ffields = registry.source_formfields(
            root_sources=[
                SubjectEntitySource(model=FakeOrganisation),
                ObjectEntitySource(model=FakeContact),
            ],
            user=user,
        )
        self.assertIsList(ffields, length=5)

        kind_id1, ffield1 = ffields[0]
        self.assertEqual('subject_entity', kind_id1)
        self.assertIsInstance(ffield1, SubjectEntitySourceField)
        self.assertEqual(FakeOrganisation, ffield1.model)

        kind_id2, ffield2 = ffields[1]
        self.assertEqual('object_entity', kind_id2)
        self.assertIsInstance(ffield2, ObjectEntitySourceField)
        self.assertEqual(FakeContact, ffield2.model)

        kind_id3, ffield3 = ffields[2]
        self.assertEqual('fixed_entity', kind_id3)
        self.assertIsInstance(ffield3, FixedEntitySourceField)

        kind_id4, ffield4 = ffields[3]
        self.assertEqual('subject_entity|entity_fk', kind_id4)
        self.assertIsInstance(ffield4, EntityFKSourceField)
        self.assertEqual(
            SubjectEntitySource(model=FakeOrganisation), ffield4.entity_source,
        )

        kind_id5, ffield6 = ffields[4]
        self.assertEqual('object_entity|entity_fk', kind_id5)
        self.assertIsInstance(ffield6, EntityFKSourceField)
        self.assertEqual(ObjectEntitySource(model=FakeContact), ffield6.entity_source)

    def test_global(self):
        triggers = {*workflow_registry.trigger_classes}
        self.assertIn(EntityCreationTrigger, triggers)
        self.assertIn(EntityEditionTrigger,  triggers)
        self.assertIn(PropertyAddingTrigger, triggers)
        self.assertIn(RelationAddingTrigger, triggers)

        sources = {*workflow_registry.source_classes}
        self.assertIn(CreatedEntitySource,      sources)
        self.assertIn(EditedEntitySource,       sources)
        self.assertIn(TaggedEntitySource,       sources)
        self.assertIn(SubjectEntitySource,      sources)
        self.assertIn(ObjectEntitySource,       sources)
        self.assertIn(FixedEntitySource,        sources)
        self.assertIn(EntityFKSource,           sources)
        self.assertIn(FirstRelatedEntitySource, sources)

        actions = {*workflow_registry.action_classes}
        self.assertIn(PropertyAddingAction, actions)
        self.assertIn(RelationAddingAction, actions)


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
                    operator=EndsWithOperator, field_name='name', values=[' Corp'],
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
                    operator=EndsWithOperator, field_name='name', values=[suffix],
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
            model=model, operator=EndsWithOperator,
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
                    operator=EndsWithOperator, field_name='name', values=[suffix],
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
                    operator=EndsWithOperator, field_name='name', values=[' Corp'],
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
            self.fail('??')

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
                    operator=EndsWithOperator, field_name='name', values=[suffix],
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
            self.fail('??')

        self.assertEqual(0, len(engine._queue))  # Meh

        orga1 = self.refresh(orga1)
        self.assertEqual(name1, orga1.name)

        orga2 = self.refresh(orga2)
        self.assertEqual(name2, orga2.name)

        self.assertHasNoProperty(entity=orga1, ptype=ptype)
        # self.assertHasNoProperty(entity=orga2, ptype=ptype)  # No change => no action
