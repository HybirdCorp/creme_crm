from functools import partial
from uuid import uuid4

from django.utils.translation import gettext as _

from creme.creme_core.constants import REL_OBJ_HAS, REL_SUB_HAS
from creme.creme_core.core.workflow import (
    BrokenSource,
    WorkflowBrokenData,
    WorkflowSource,
    workflow_registry,
)
from creme.creme_core.models import (
    FakeContact,
    FakeImage,
    FakeOrganisation,
    Relation,
    RelationType,
)
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    EntityFKSource,
    FirstRelatedEntitySource,
    FixedEntitySource,
    ObjectEntitySource,
    SubjectEntitySource,
    TaggedEntitySource,
)

from ..base import CremeTestCase
from ..fake_models import FakeFolder


class FromContextEntitySourceTestCase(CremeTestCase):
    def test_created_entity(self):
        self.assertEqual('created_entity', CreatedEntitySource.config_formfield_kind_id())

        source = CreatedEntitySource(model=FakeOrganisation)
        self.assertIsInstance(source, WorkflowSource)
        self.assertEqual('created_entity', source.type_id)
        self.assertEqual(FakeOrganisation,  source.model)
        self.assertIsNone(source.sub_source)
        self.assertDictEqual(
            {'type': 'created_entity', 'model': 'creme_core.fakeorganisation'},
            source.to_dict(),
        )

        user = self.get_root_user()
        label = _('Created entity ({type})').format(type='Test Organisation')
        self.assertEqual(label, source.render(user=user, mode=source.RenderMode.TEXT_PLAIN))
        self.assertEqual(label, source.render(user=user, mode=source.RenderMode.HTML))

        entity1 = FakeOrganisation(name='Acme1')
        entity2 = FakeOrganisation(name='Acme2')
        self.assertEqual(
            entity1, source.extract({source.type_id: entity1, 'other': entity2}),
        )

        # Deserialization ---
        deserialized = CreatedEntitySource.from_dict(
            data={'model': 'creme_core.fakecontact'},
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

    def test_created_entity__error(self):
        with self.assertRaises(WorkflowBrokenData):
            CreatedEntitySource.from_dict(
                data={
                    'type': CreatedEntitySource.type_id,
                    'model': 'uninstalled_app.whatever',
                },
                registry=workflow_registry,
            )

    def test_edited_entity(self):
        self.assertEqual('edited_entity', EditedEntitySource.config_formfield_kind_id())

        source = EditedEntitySource(model=FakeContact)
        self.assertIsInstance(source, WorkflowSource)
        self.assertEqual('edited_entity', source.type_id)
        self.assertEqual(FakeContact,     source.model)
        self.assertDictEqual(
            {'type': 'edited_entity', 'model': 'creme_core.fakecontact'},
            source.to_dict(),
        )

        user = self.get_root_user()
        label = _('Modified entity ({type})').format(type='Test Contact')
        self.assertEqual(label, source.render(user=user, mode=source.RenderMode.TEXT_PLAIN))
        self.assertEqual(label, source.render(user=user, mode=source.RenderMode.HTML))

        entity1 = FakeOrganisation(name='Acme1')
        entity2 = FakeOrganisation(name='Acme2')
        self.assertEqual(
            entity1, source.extract({source.type_id: entity1, 'other': entity2}),
        )

        # Deserialization ---
        deserialized = EditedEntitySource.from_dict(
            data={'model': 'creme_core.fakeorganisation'},
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
        self.assertIsInstance(source, WorkflowSource)
        self.assertEqual('tagged_entity', source.type_id)
        self.assertEqual(FakeContact,      source.model)
        self.assertDictEqual(
            {'type': 'tagged_entity', 'model': 'creme_core.fakecontact'},
            source.to_dict(),
        )

        user = self.get_root_user()
        label = _('Received a new property ({type})').format(type='Test Contact')
        self.assertEqual(label, source.render(user=user, mode=source.RenderMode.TEXT_PLAIN))
        self.assertEqual(label, source.render(user=user, mode=source.RenderMode.HTML))

        # Configuration ---
        from creme.creme_core.forms.workflows import TaggedEntitySourceField
        ffield = source.config_formfield(user=user)
        self.assertIsInstance(ffield, TaggedEntitySourceField)
        self.assertEqual(FakeContact, ffield.model)
        self.assertEqual(label, ffield.label)

    def test_subject_entity(self):
        source = SubjectEntitySource(model=FakeContact)
        self.assertIsInstance(source, WorkflowSource)
        self.assertEqual('subject_entity', source.type_id)
        self.assertEqual(FakeContact,      source.model)
        self.assertDictEqual(
            {'type': 'subject_entity', 'model': 'creme_core.fakecontact'},
            source.to_dict(),
        )

        user = self.get_root_user()
        label = _('Subject of the created relationship ({type})').format(type='Test Contact')
        self.assertEqual(label, source.render(user=user, mode=source.RenderMode.TEXT_PLAIN))
        self.assertEqual(label, source.render(user=user, mode=source.RenderMode.HTML))

        # Configuration ---
        from creme.creme_core.forms.workflows import SubjectEntitySourceField
        ffield = source.config_formfield(user=user)
        self.assertIsInstance(ffield, SubjectEntitySourceField)
        self.assertEqual(FakeContact, ffield.model)
        self.assertEqual(label, ffield.label)

    def test_object_entity(self):
        source = ObjectEntitySource(model=FakeContact)
        self.assertIsInstance(source, WorkflowSource)
        self.assertEqual('object_entity', source.type_id)
        self.assertEqual(FakeContact,     source.model)
        self.assertDictEqual(
            {'type': 'object_entity', 'model': 'creme_core.fakecontact'},
            source.to_dict(),
        )

        user = self.get_root_user()
        label = _('Object of the created relationship ({type})').format(type='Test Contact')
        self.assertEqual(label, source.render(user=user, mode=source.RenderMode.TEXT_PLAIN))
        self.assertEqual(label, source.render(user=user, mode=source.RenderMode.HTML))

        # Configuration ---
        from creme.creme_core.forms.workflows import ObjectEntitySourceField
        ffield = source.config_formfield(user=user)
        self.assertIsInstance(ffield, ObjectEntitySourceField)
        self.assertEqual(FakeContact, ffield.model)
        self.assertEqual(label, ffield.label)


class FixedEntitySourceTestCase(CremeTestCase):
    def test_str_uuid(self):
        self.assertEqual('fixed_entity', FixedEntitySource.config_formfield_kind_id())

        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')

        source = FixedEntitySource(model=FakeOrganisation, entity=str(orga.uuid))
        self.assertIsInstance(source, WorkflowSource)
        self.assertEqual('fixed_entity', source.type_id)
        self.assertEqual(FakeOrganisation, source.model)
        self.assertIsNone(source.sub_source)
        self.assertDictEqual(
            {
                'type': 'fixed_entity',
                'model': 'creme_core.fakeorganisation',
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
                'model': 'creme_core.fakecontact',
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
        self.assertEqual(_('Fixed entity'), ffield.label)
        self.assertEqual(user,              ffield.user)

    def test_entity_instance(self):
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
                'model': 'creme_core.fakecontact',
                'uuid': str(contact.uuid),
            },
            source1.to_dict(),
        )

        # Real entity ---
        source2 = FixedEntitySource(entity=contact.cremeentity_ptr)
        self.assertEqual(FakeContact, source2.model)

        with self.assertNumQueries(0):
            self.assertEqual(contact, source2.entity)

    def test_eq(self):
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

    def test_render__entity_instance(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')
        source = FixedEntitySource(entity=orga)
        self.assertEqual(
            _('Fixed entity «{entity}»').format(entity=orga.name),
            source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            f'<span>'
            f'<a href="{orga.get_absolute_url()}" target="_self">{orga.name}</a>'
            f'{_("(fixed entity)")}'
            f'</span>',
            source.render(user=user, mode=source.RenderMode.HTML),
        )

        orga.trash()
        self.assertEqual(
            _('Fixed entity «{entity}» [deleted]').format(entity=orga.name),
            source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            f'<span>'
            f'<a href="{orga.get_absolute_url()}" class="is_deleted" target="_self">'
            f'{orga.name}'
            f'</a>'
            f'{_("(fixed entity)")}'
            f'</span>',
            source.render(user=user, mode=source.RenderMode.HTML),
        )

    def test_render__str_uuid(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')
        source = FixedEntitySource(model=FakeOrganisation, entity=str(orga.uuid))
        self.assertEqual(
            _('Fixed entity «{entity}»').format(entity=orga.name),
            source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
        )

    def test_error__model(self):
        with self.assertRaises(WorkflowBrokenData):
            FixedEntitySource.from_dict(
                data={
                    'type': FixedEntitySource.type_id,
                    'uuid': str(uuid4()),
                    'model': 'uninstalled.model',
                },
                registry=workflow_registry,
            )

    def test_error__entity(self):
        source = FixedEntitySource.from_dict(
            data={
                'type': FixedEntitySource.type_id,
                'uuid': str(uuid4()),
                'model': 'creme_core.fakeorganisation',
            },
            registry=workflow_registry,
        )

        with self.assertNumQueries(1):
            with self.assertRaises(WorkflowBrokenData) as cm:
                source.entity  # NOQA
        self.assertEqual(
            _('The «{model}» does not exist anymore').format(
                model='Test Organisation',
            ),
            str(cm.exception),
        )

        with self.assertNumQueries(0):
            with self.assertRaises(WorkflowBrokenData):
                source.entity  # NOQA

        user = self.get_root_user()
        self.assertEqual(
            _('The fixed «{model}» does not exist anymore').format(
                model='Test Organisation',
            ),
            source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            '{label}<p class="errorlist">{error}</p>'.format(
                label=_('A fixed «{model}»').format(model='Test Organisation'),
                error=_('It does not exist anymore'),
            ),
            source.render(user=user, mode=source.RenderMode.HTML),
        )

        with self.assertNumQueries(0):
            self.assertIsNone(source.extract({}))


class EntityFKSourceTestCase(CremeTestCase):
    def test_main(self):
        user = self.get_root_user()
        img = FakeImage.objects.create(user=user, name='Acme logo')
        orga = FakeOrganisation.objects.create(user=user, name='Acme1', image=img)
        field_name = 'image'
        fixed_source = FixedEntitySource(entity=orga)

        self.assertEqual(
            'fixed_entity|entity_fk',
            EntityFKSource.config_formfield_kind_id(sub_source=fixed_source),
        )

        source = EntityFKSource(entity_source=fixed_source, field_name=field_name)
        self.assertIsInstance(source, WorkflowSource)
        self.assertEqual('entity_fk',  source.type_id)
        self.assertEqual(fixed_source, source.sub_source)
        self.assertEqual(field_name,   source.field_name)
        self.assertEqual(FakeImage,    source.model)
        self.assertDictEqual(
            {
                'type': 'entity_fk',
                'entity': fixed_source.to_dict(),
                'field': field_name,
            },
            source.to_dict(),
        )
        self.assertEqual(img, source.extract({'whatever': 'donotcare'}))

    def test_from_dict(self):
        field_name = 'parent'
        deserialized = EntityFKSource.from_dict(
            data={
                'type': 'entity_fk',
                'entity': CreatedEntitySource(model=FakeFolder).to_dict(),
                'field': field_name,
            },
            registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, EntityFKSource)
        self.assertEqual(field_name, deserialized.field_name)

        # sub_source = deserialized.entity_source
        sub_source = deserialized.sub_source
        self.assertIsInstance(sub_source, CreatedEntitySource)
        self.assertEqual(FakeFolder, sub_source.model)

    def test_configuration(self):
        from creme.creme_core.forms.workflows import EntityFKSourceField

        user = self.get_root_user()
        source = EntityFKSource(
            entity_source=CreatedEntitySource(model=FakeContact),
            field_name='image',
        )

        with self.assertRaises(ValueError) as cm:
            source.config_formfield(user=user)
        self.assertEqual(
            'This type of source cannot be used as root source',
            str(cm.exception),
        )

        sub_source = CreatedEntitySource(model=FakeContact)
        ffield = EntityFKSource.composed_config_formfield(sub_source=sub_source, user=user)

        self.assertIsInstance(ffield, EntityFKSourceField)
        self.assertEqual(sub_source, ffield.entity_source)
        self.assertEqual(
            _('Field of: {source}').format(
                source=_('Created entity ({type})').format(type='Test Contact'),
            ),
            ffield.label,
        )

    def test_empty(self):
        instance_source = CreatedEntitySource(model=FakeContact)
        source = EntityFKSource(entity_source=instance_source, field_name='image')
        self.assertIsNone(source.extract({instance_source.type_id: None}))

    def test_useless_formfield(self):
        "No FK is available."
        self.assertIsNone(EntityFKSource.composed_config_formfield(
            sub_source=CreatedEntitySource(model=FakeImage),
            user=self.get_root_user(),
        ))

    def test_eq(self):
        create_orga = partial(FakeOrganisation.objects.create, user=self.get_root_user())
        orga1 = create_orga(name='Acme1')

        field_name = 'image'
        source1 = EntityFKSource(
            entity_source=FixedEntitySource(entity=orga1),
            field_name=field_name,
        )
        self.assertEqual(
            source1,
            EntityFKSource(
                entity_source=FixedEntitySource(entity=orga1),
                field_name=field_name,
            ),
        )
        # TODO: need a fake model with 2 FK to CremeEntity
        # self.assertNotEqual(
        #     source1,
        #     EntityFKSource(
        #         entity_source=FixedEntitySource(entity=orga1),
        #         field_name='other_fk',  # <==
        #     ),
        # )
        self.assertNotEqual(
            source1,
            EntityFKSource(
                entity_source=FixedEntitySource(entity=create_orga(name='Acme2')),
                field_name=field_name,
            ),
        )
        self.assertNotEqual(source1, None)

    def test_render1(self):
        instance_source = CreatedEntitySource(model=FakeContact)
        source = EntityFKSource(
            entity_source=instance_source,
            field_name='image',
        )
        user = self.get_root_user()
        self.assertEqual(
            _('Field «{field}» of: {source}').format(
                field=_('Photograph'),
                source=instance_source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
            ),
            source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            '<span>{}</span>'.format(
                _('Field «{field}» of: {source}').format(
                    field=_('Photograph'),
                    source=instance_source.render(user=user, mode=source.RenderMode.HTML),
                )
            ),
            source.render(user=user, mode=source.RenderMode.HTML),
        )

    def test_render2(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(user=user, name='Acme')
        instance_source = FixedEntitySource(entity=orga)
        source = EntityFKSource(entity_source=instance_source, field_name='image')
        self.assertEqual(
            _('Field «{field}» of: {source}').format(
                field=_('Logo'),
                source=instance_source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
            ),
            source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            '<span>{}</span>'.format(
                _('Field «{field}» of: {source}').format(
                    field=_('Logo'),
                    source=instance_source.render(user=user, mode=source.RenderMode.HTML),
                )
            ),
            source.render(user=user, mode=source.RenderMode.HTML),
        )

    def test_broken_source(self):
        model_key = 'uninstalled.model'

        with self.assertRaises(WorkflowBrokenData) as cm:
            EntityFKSource.from_dict(
                data={
                    'type': EntityFKSource.type_id,
                    'entity': {
                        'type': CreatedEntitySource.type_id,
                        'model': model_key,  # <==
                    },
                    'field': 'image',
                },
                registry=workflow_registry,
            )

        self.assertEqual(
            _(
                'The source «{name}» is broken (original error: {error})'
            ).format(
                name=_('Created entity'),
                error=_('The model «{key}» is invalid').format(key=model_key),
            ),
            str(cm.exception),
        )

    def test_invalid_field(self):
        field = 'invalid'

        with self.assertRaises(WorkflowBrokenData) as cm:
            EntityFKSource.from_dict(
                data={
                    'type': EntityFKSource.type_id,
                    'entity': {
                        'type': CreatedEntitySource.type_id,
                        'model': 'creme_core.fakeorganisation',
                    },
                    'field': field,
                },
                registry=workflow_registry,
            )

        self.assertEqual(
            _('The field «{field}» is invalid in model «{model}»').format(
                field=field, model='Test Organisation',
            ),
            str(cm.exception),
        )

    def test_not_fk(self):
        with self.assertRaises(WorkflowBrokenData) as cm:
            EntityFKSource(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                field_name='name',
            )

        self.assertEqual(
            _('The field «{field}» does not reference an entity').format(
                field=_('Name'),
            ),
            str(cm.exception),
        )

    def test_not_fk_to_entity(self):
        with self.assertRaises(WorkflowBrokenData) as cm:
            EntityFKSource(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                field_name='sector',
            )

        self.assertEqual(
            _('The field «{field}» does not reference an entity').format(
                field=_('Sector'),
            ),
            str(cm.exception),
        )


class FirstRelatedEntitySourceTestCase(CremeTestCase):
    def test_str_id(self):
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
        self.assertIsInstance(source, WorkflowSource)
        self.assertEqual('first_related',  source.type_id)
        # self.assertEqual(subject_source1,  source.subject_source)
        self.assertEqual(subject_source1,  source.sub_source)
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
                'object_model': 'creme_core.fakeorganisation',
            },
            source.to_dict(),
        )

        # NB: 'orga2' is the first related FakeOrganisation instance
        ctxt_key1 = CreatedEntitySource.type_id
        self.assertEqual(orga2, source.extract({ctxt_key1: contact1}))

        # Empty result
        self.assertIsNone(source.extract({ctxt_key1: None}))
        self.assertIsNone(source.extract({ctxt_key1: contact2}))

    def test_rtype_instance(self):
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
                'object_model': 'creme_core.fakeorganisation',
            },
            source.to_dict(),
        )

    def test_from_dict(self):
        rtype = RelationType.objects.get(id=REL_SUB_HAS)
        subject_source = EditedEntitySource(model=FakeOrganisation)
        deserialized = FirstRelatedEntitySource.from_dict(
            data={
                'type': FirstRelatedEntitySource.type_id,
                'subject': subject_source.to_dict(),
                'rtype': rtype.symmetric_type_id,
                'object_model': 'creme_core.fakecontact',
            },
            registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, FirstRelatedEntitySource)
        # self.assertEqual(subject_source,      deserialized.subject_source)
        self.assertEqual(subject_source,      deserialized.sub_source)
        self.assertEqual(FakeContact,          deserialized.object_model)
        self.assertEqual(rtype.symmetric_type, deserialized.relation_type)

    def test_configuration(self):
        user = self.get_root_user()
        source = FirstRelatedEntitySource(
            subject_source=CreatedEntitySource(model=FakeOrganisation),
            rtype=REL_SUB_HAS,
            object_model=FakeOrganisation,
        )

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

    def test_eq(self):
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

    def test_render1(self):
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
                source=subject_source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
            ),
            source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            '<span>{}</span>'.format(
                _('First related «{type}» by «{predicate}» to: {source}').format(
                    type='Test Organisation',
                    predicate=rtype.predicate,
                    source=subject_source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
                )
            ),
            source.render(user=user, mode=source.RenderMode.HTML),
        )

    def test_render2(self):
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
                source=subject_source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
            ),
            source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
        )
        self.assertHTMLEqual(
            '<span>{}</span>'.format(
                _('First related «{type}» by «{predicate}» to: {source}').format(
                    type='Test Contact',
                    predicate=rtype.predicate,
                    source=subject_source.render(user=user, mode=source.RenderMode.HTML),
                )
            ),
            source.render(user=user, mode=source.RenderMode.HTML),
        )

    def test_broken_object_model(self):
        model_key = 'uninstalled.model'

        with self.assertRaises(WorkflowBrokenData) as cm:
            FirstRelatedEntitySource.from_dict(
                data={
                    'type': FirstRelatedEntitySource.type_id,
                    'subject': CreatedEntitySource(model=FakeOrganisation).to_dict(),
                    'rtype': REL_OBJ_HAS,
                    'object_model': model_key,  # <==
                },
                registry=workflow_registry,
            )

        self.assertEqual(
            _('The model «{key}» is invalid').format(key=model_key),
            str(cm.exception),
        )

    def test_broken_subject_source(self):
        source = FirstRelatedEntitySource.from_dict(
            data={
                'type': FirstRelatedEntitySource.type_id,
                'subject': {
                    'type': CreatedEntitySource.type_id,
                    'model': 'uninstalled.model',
                },
                'rtype': REL_OBJ_HAS,
                'object_model': 'creme_core.fakecontact',
            },
            registry=workflow_registry,
        )
        self.assertIsInstance(source.sub_source, BrokenSource)
        self.assertIsNone(source.extract({}))

        with self.assertNoException():
            source.render(user=self.get_root_user(), mode=source.RenderMode.TEXT_PLAIN)

    def test_broken_rtype(self):
        source = FirstRelatedEntitySource.from_dict(
            data={
                'type': FirstRelatedEntitySource.type_id,
                'subject': CreatedEntitySource(model=FakeOrganisation).to_dict(),
                'rtype': 'uninstalled.subject_predicate',  # <==
                'object_model': 'creme_core.fakecontact',
            },
            registry=workflow_registry,
        )

        with self.assertNumQueries(1):
            with self.assertRaises(WorkflowBrokenData) as cm:
                source.relation_type  # NOQA
        self.assertEqual(
            _('The relationship type does not exist anymore'), str(cm.exception),
        )

        with self.assertNumQueries(0):
            with self.assertRaises(WorkflowBrokenData):
                source.relation_type  # NOQA

        user = self.get_root_user()
        error_msg = _('The relationship type does not exist anymore')
        self.assertEqual(
            _('{error} (first related entity)').format(error=error_msg),
            source.render(user=user, mode=source.RenderMode.TEXT_PLAIN)
        )
        self.assertHTMLEqual(
            '{label}<p class="errorlist">{error}</p>'.format(
                label=_('First related entity'),
                error=error_msg,
            ),
            source.render(user=user, mode=source.RenderMode.HTML)
        )

        self.assertIsNone(
            source.extract({CreatedEntitySource.type_id: FakeOrganisation()})
        )
