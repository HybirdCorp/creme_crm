from functools import partial

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.workflow import (
    EntityCreated,
    EntityEdited,
    PropertyAdded,
    RelationAdded,
    WorkflowEvent,
)
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    Relation,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase


class WorkflowEventsTestCase(CremeTestCase):
    def test_entity_created(self):
        user = self.get_root_user()
        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity1 = create_orga(name='Acme1')

        evt = EntityCreated(entity=entity1)
        self.assertIsInstance(evt, WorkflowEvent)
        self.assertEqual(entity1, evt.entity)
        self.assertEqual(f'EntityCreated(entity=FakeOrganisation(id={entity1.id}))', repr(evt))

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
        self.assertEqual(
            f'PropertyAdded(creme_property=CremeProperty('
            f'type=CremePropertyType(text="Is cool"), '
            f'creme_entity=FakeOrganisation(id={entity1.id})'
            f'))',
            repr(evt),
        )

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
        self.maxDiff = None
        self.assertEqual(
            f'RelationAdded(relation=Relation('
            f'user=CremeUser(username="root"), '
            f'subject_entity={entity1!r}, '
            f'type=RelationType(predicate="{rtype.predicate}"), '
            f'object_entity=FakeOrganisation(id={entity2.id})'
            f'))',
            repr(evt),
        )

        # eq ---
        self.assertEqual(RelationAdded(relation=rel), evt)
        self.assertNotEqual(
            RelationAdded(relation=create_rel(
                subject_entity=entity1, type=rtype, object_entity=create_orga(name='Acme2'),
            )),
            evt,
        )
        self.assertNotEqual(evt, EntityCreated(entity=entity1))
