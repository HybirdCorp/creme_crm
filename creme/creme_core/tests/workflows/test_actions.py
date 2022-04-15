from functools import partial
from uuid import uuid4

from django.utils.safestring import SafeString
from django.utils.translation import gettext as _

from creme.creme_core.constants import REL_OBJ_HAS, REL_SUB_HAS
from creme.creme_core.core.workflow import (
    WorkflowBrokenData,
    workflow_registry,
)
from creme.creme_core.models import (
    CremePropertyType,
    FakeContact,
    FakeOrganisation,
    FakeProduct,
    RelationType,
)
from creme.creme_core.workflows import (
    CreatedEntitySource,
    FixedEntitySource,
    ObjectEntitySource,
    PropertyAddingAction,
    RelationAddingAction,
    SubjectEntitySource,
)

from ..base import CremeTestCase


class PropertyAddingActionTestCase(CremeTestCase):
    def test_str_uuid(self):
        user = self.get_root_user()
        type_id = 'creme_core-property_adding'
        self.assertEqual(type_id, PropertyAddingAction.type_id)
        self.assertEqual(_('Adding a property'), PropertyAddingAction.verbose_name)

        # Instance ---
        ptype = CremePropertyType.objects.create(text='Is kawaiiii')
        source = CreatedEntitySource(model=FakeOrganisation)
        action = PropertyAddingAction(entity_source=source, ptype=str(ptype.uuid))
        self.assertEqual(_('Adding a property'), str(action))
        self.assertEqual(source, action.entity_source)

        with self.assertNumQueries(1):
            self.assertEqual(ptype, action.property_type)

        with self.assertNumQueries(0):
            action.property_type  # NOQA

        serialized = {
            'type': type_id,
            'entity': {
                'type': CreatedEntitySource.type_id,
                'model': 'creme_core.fakeorganisation',
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

    def test_ptype_instance(self):
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

    def test_config_form_class(self):
        from creme.creme_core.forms.workflows import PropertyAddingActionForm
        self.assertIs(
            PropertyAddingActionForm, PropertyAddingAction.config_form_class(),
        )

    def test_eq(self):
        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is kawaiiii')

        action1 = PropertyAddingAction(
            entity_source=CreatedEntitySource(model=FakeOrganisation),
            ptype=str(ptype1.uuid),
        )
        self.assertEqual(
            PropertyAddingAction(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                ptype=str(ptype1.uuid),
            ),
            action1,
        )
        self.assertEqual(
            PropertyAddingAction(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                ptype=ptype1,
            ),
            action1,
        )
        self.assertNotEqual(None, action1)
        self.assertNotEqual(
            PropertyAddingAction(
                entity_source=CreatedEntitySource(model=FakeContact),
                ptype=ptype1,
            ),
            action1,
        )

        ptype2 = create_ptype(text='Is cool')
        self.assertNotEqual(
            PropertyAddingAction(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                ptype=ptype2,
            ),
            action1,
        )

    def test_broken_ptype(self):
        action = PropertyAddingAction.from_dict(
            data={
                'type': PropertyAddingAction.type_id,
                'entity': {
                    'type': CreatedEntitySource.type_id,
                    'model': 'creme_core.fakeorganisation',
                },
                'ptype': str(uuid4()),
            },
            registry=workflow_registry,
        )

        with self.assertNumQueries(1):
            with self.assertRaises(WorkflowBrokenData) as cm:
                action.property_type  # NOQA
        err_msg = _('The property type does not exist anymore')
        self.assertEqual(err_msg, str(cm.exception))

        with self.assertNumQueries(0):
            with self.assertRaises(WorkflowBrokenData):
                action.property_type  # NOQA

        self.assertHTMLEqual(
            '{label}<p class="errorlist">{error}</p>'.format(
                label=_('Adding a property'), error=err_msg,
            ),
            action.render(user=self.get_root_user()),
        )

        # TODO
        # # ---
        # user = self.get_root_user()
        # orga = FakeOrganisation.objects.create(user=user, name='Acme')
        #
        # with self.assertNoException():  # TODO: assertRaises/assertLogs/...
        #     action.execute(context={CreatedEntitySource.type_id: orga})


class RelationAddingActionTestCase(CremeTestCase):
    def test_str_id(self):
        user = self.get_root_user()
        type_id = 'creme_core-relation_adding'
        self.assertEqual(type_id, RelationAddingAction.type_id)
        self.assertEqual(_('Adding a relationship'), RelationAddingAction.verbose_name)

        # Instance ---
        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        source1 = SubjectEntitySource(model=FakeContact)
        source2 = ObjectEntitySource(model=FakeOrganisation)
        action = RelationAddingAction(
            subject_source=source1, rtype=rtype.id, object_source=source2,
        )
        self.assertEqual(_('Adding a relationship'), str(action))
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

    def test_rtype_instance(self):
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

    def test_config_form_class(self):
        from creme.creme_core.forms.workflows import RelationAddingActionForm

        self.assertIs(
            RelationAddingActionForm, RelationAddingAction.config_form_class(),
        )

    def test_eq(self):
        rtype = RelationType.objects.get(id=REL_OBJ_HAS)
        action1 = RelationAddingAction(
            subject_source=SubjectEntitySource(model=FakeContact),
            rtype=rtype,
            object_source=ObjectEntitySource(model=FakeOrganisation),
        )

        self.assertEqual(
            RelationAddingAction(
                subject_source=SubjectEntitySource(model=FakeContact),
                rtype=rtype,
                object_source=ObjectEntitySource(model=FakeOrganisation),
            ),
            action1,
        )
        self.assertEqual(
            RelationAddingAction(
                subject_source=SubjectEntitySource(model=FakeContact),
                rtype=rtype.id,
                object_source=ObjectEntitySource(model=FakeOrganisation),
            ),
            action1,
        )

        self.assertNotEqual(
            RelationAddingAction(
                subject_source=SubjectEntitySource(model=FakeProduct),  # <==
                rtype=rtype.id,
                object_source=ObjectEntitySource(model=FakeOrganisation),
            ),
            action1,
        )
        self.assertNotEqual(
            RelationAddingAction(
                subject_source=SubjectEntitySource(model=FakeContact),
                rtype=rtype.symmetric_type,  # <==
                object_source=ObjectEntitySource(model=FakeOrganisation),
            ),
            action1,
        )
        self.assertNotEqual(
            RelationAddingAction(
                subject_source=SubjectEntitySource(model=FakeContact),
                rtype=rtype,
                object_source=ObjectEntitySource(model=FakeProduct),  # <==
            ),
            action1,
        )
        self.assertNotEqual(None, action1)

    def test_broken_rtype(self):
        action = RelationAddingAction.from_dict(
            data={
                'type': RelationAddingAction.type_id,
                'subject': {
                    'type': SubjectEntitySource.type_id,
                    'model': 'creme_core.fakeorganisation',
                },
                'object': {
                    'type': ObjectEntitySource.type_id,
                    'model': 'creme_core.fakecontact',
                },
                'rtype': 'uninstalled_app-subject_predicate',
            },
            registry=workflow_registry,
        )

        with self.assertNumQueries(1):
            with self.assertRaises(WorkflowBrokenData) as cm:
                action.relation_type  # NOQA
        err_msg = _('The relationship type does not exist anymore')
        self.assertEqual(err_msg, str(cm.exception))

        with self.assertNumQueries(0):
            with self.assertRaises(WorkflowBrokenData):
                action.relation_type  # NOQA

        self.assertHTMLEqual(
            '{label}<p class="errorlist">{error}</p>'.format(
                label=_('Adding a relationship'), error=err_msg,
            ),
            action.render(user=self.get_root_user()),
        )

        # TODO
        # # ---
        # user = self.get_root_user()
        # orga = FakeOrganisation.objects.create(user=user, name='Acme')
        #
        # with self.assertNoException():  # TODO: assertRaises/assertLogs/...
        #     action.execute(context={....})
