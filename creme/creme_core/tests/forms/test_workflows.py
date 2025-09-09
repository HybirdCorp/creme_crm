from json import dumps as json_dump
from json import loads as json_load

from django.contrib.contenttypes.models import ContentType
from django.forms import Field, ModelChoiceField
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.core.workflow import WorkflowRegistry
from creme.creme_core.forms.workflows import (
    CreatedEntitySourceField,
    EditedEntitySourceField,
    EntityCreationTriggerField,
    EntityEditionTriggerField,
    EntityFKSourceField,
    FirstRelatedEntitySourceField,
    FixedEntitySourceField,
    ObjectEntitySourceField,
    PropertyAddingActionForm,
    PropertyAddingTriggerField,
    RelationAddingActionForm,
    RelationAddingTriggerField,
    SourceField,
    SubjectEntitySourceField,
    TaggedEntitySourceField,
)
from creme.creme_core.models import (
    CremePropertyType,
    FakeActivity,
    FakeContact,
    FakeDocument,
    FakeImage,
    FakeOrganisation,
    RelationType,
    Workflow,
)
from creme.creme_core.tests.base import CremeTestCase
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


class TriggerFieldsTestCase(CremeTestCase):
    def test_EntityCreationTriggerField(self):
        model1 = FakeContact
        field1 = EntityCreationTriggerField(model=model1)
        self.assertFalse(field1.required)
        self.assertEqual(model1, field1.model)
        self.assertEqual(EntityCreationTrigger(model=model1), field1.clean(''))
        self.assertEqual(EntityCreationTrigger(model=model1), field1.clean('whatever'))

        model2 = FakeOrganisation
        self.assertEqual(
            EntityCreationTrigger(model=model2),
            EntityCreationTriggerField(model=model2).clean(''),
        )

    def test_EntityEditionTriggerField(self):
        model1 = FakeContact
        field1 = EntityEditionTriggerField(model=model1)
        self.assertFalse(field1.required)
        self.assertEqual(model1, field1.model)
        self.assertEqual(EntityEditionTrigger(model=model1), field1.clean(''))
        self.assertEqual(EntityEditionTrigger(model=model1), field1.clean('whatever'))

        model2 = FakeOrganisation
        self.assertEqual(
            EntityEditionTrigger(model=model2),
            EntityEditionTriggerField(model=model2).clean(''),
        )


class PropertyAddingTriggerFieldTestCase(CremeTestCase):
    def test_ok(self):
        model1 = FakeContact
        field1 = PropertyAddingTriggerField(model=model1)
        self.assertEqual(model1, field1.model)

        ptype1 = CremePropertyType.objects.create(text='Is cool')
        self.assertEqual(
            PropertyAddingTrigger(entity_model=model1, ptype=ptype1),
            field1.clean(f'{ptype1.id}'),
        )

        # ---
        model2 = FakeOrganisation
        field2 = PropertyAddingTriggerField(model=model2)
        self.assertEqual(model2, field2.model)

        ptype2 = CremePropertyType.objects.create(
            text='Is super cool',
        ).set_subject_ctypes(model2)
        self.assertEqual(
            PropertyAddingTrigger(entity_model=model2, ptype=ptype2),
            field2.clean(f'{ptype2.id}'),
        )

    def test_empty(self):
        field = PropertyAddingTriggerField(model=FakeContact, required=False)
        self.assertIsNone(field.clean(None))

    def test_empty_required(self):
        field = PropertyAddingTriggerField(model=FakeContact)
        self.assertTrue(field.required)

        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')

    def test_choices(self):
        model1 = FakeContact

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is cool').set_subject_ctypes(model1)
        ptype2 = create_ptype(text='Is not cool').set_subject_ctypes(FakeOrganisation)

        choices = PropertyAddingTriggerField(model=FakeContact).choices
        self.assertInChoices(value=ptype1.id, label=ptype1.text, choices=choices)
        self.assertNotInChoices(value=ptype2.id, choices=choices)


class RelationAddingTriggerFieldTestCase(CremeTestCase):
    @staticmethod
    def _build_value(rtype, model):
        return json_dump({
            'rtype': rtype if isinstance(rtype, str) else rtype.id,
            'ctype': ContentType.objects.get_for_model(model).id,
        })

    def test_ok(self):
        model1 = FakeContact
        field1 = RelationAddingTriggerField(model=model1)
        self.assertEqual(model1, field1.model)

        model2 = FakeOrganisation
        rtype1 = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is a client of', models=[model1],
        ).symmetric(
            id='creme_core-object_client', predicate='has a client', models=[model2],
        ).get_or_create()[0]
        trigger1 = RelationAddingTrigger(
            subject_model=model1, rtype=rtype1, object_model=model2,
        )
        value1 = self._build_value(rtype=rtype1, model=model2)
        self.assertEqual(trigger1, field1.clean(value1))

        # from_python() ---
        self.assertDictEqual(
            {
                'rtype': rtype1.id,
                'ctype': ContentType.objects.get_for_model(model2).id,
            },
            json_load(field1.from_python(trigger1)),
        )

        # ---
        field2 = RelationAddingTriggerField(model=model2)
        self.assertEqual(model2, field2.model)

        rtype2 = RelationType.objects.builder(
            id='creme_core-subject_concerned', predicate='is concerned by',
            is_internal=True,
        ).symmetric(id='creme_core-object_concerned', predicate='concerns').get_or_create()[0]
        self.assertEqual(
            RelationAddingTrigger(
                subject_model=model2, rtype=rtype2, object_model=FakeActivity,
            ),
            field2.clean(self._build_value(rtype=rtype2, model=FakeActivity)),
        )

    def test_empty(self):
        field = RelationAddingTriggerField(model=FakeContact, required=False)
        self.assertIsNone(field.clean(None))

    def test_empty_required(self):
        field = RelationAddingTriggerField(model=FakeContact)
        self.assertTrue(field.required)

        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='{}')

    def test_clean_invalid_json(self):
        self.assertFormfieldError(
            field=RelationAddingTriggerField(model=FakeContact),
            value='{"rtype":"creme_core-subject_whatever", "ctype":"12"',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_invalid_data_type(self):
        field = RelationAddingTriggerField(model=FakeContact)
        code = 'invalidtype'
        msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"this is a string"',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"[]"',
        )

    def test_clean_invalid_data(self):
        self.assertFormfieldError(
            field=RelationAddingTriggerField(model=FakeContact),
            messages=_('Invalid format'), codes='invalidformat',
            value=json_dump({'rtype': REL_SUB_HAS, 'ctype': 'not_an_int'}),
        )

    def test_clean_unknown_rtype(self):
        rtype_id = 'test-i_do_not_exist'

        code = 'rtypenotallowed'
        self.assertFormfieldError(
            field=RelationAddingTriggerField(model=FakeContact),
            value=self._build_value(rtype=rtype_id, model=FakeOrganisation),
            messages=RelationAddingTriggerField.default_error_messages[code] % {
                'rtype_id': rtype_id,
            },
            codes=code,
        )

    def test_clean_forbidden_rtype(self):
        model = FakeContact
        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is a client of',
            models=[FakeActivity],  # Not <model>
        ).symmetric(id='creme_core-object_client', predicate='has a client').get_or_create()[0]
        code = 'rtypenotallowed'
        self.assertFormfieldError(
            field=RelationAddingTriggerField(model=model),
            value=self._build_value(rtype=rtype, model=FakeOrganisation),
            messages=RelationAddingTriggerField.default_error_messages[code],
            codes=code,
        )

    def test_clean_disabled_rtype(self):
        model = FakeContact

        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is a client of',
            enabled=False,
        ).symmetric(
            id='creme_core-object_client', predicate='has a client',
        ).get_or_create()[0]

        code = 'rtypenotallowed'
        self.assertFormfieldError(
            field=RelationAddingTriggerField(model=model),
            value=self._build_value(rtype=rtype, model=model),
            messages=RelationAddingTriggerField.default_error_messages[code],
            codes=code,
        )

    def test_clean_ctype_errors(self):
        rtype = RelationType.objects.builder(
            id='creme_core-subject_concerned', predicate='is concerned by',
        ).symmetric(id='creme_core-object_concerned', predicate='concerns').get_or_create()[0]
        self.assertFormfieldError(
            field=RelationAddingTriggerField(model=FakeContact),
            value=json_dump({'rtype': rtype.id, 'ctype': self.UNUSED_PK}),
            messages=_('This content type does not exist.'),
            codes='ctypedoesnotexist',
        )
        self.assertFormfieldError(
            field=RelationAddingTriggerField(model=FakeContact),
            value=json_dump({'rtype': rtype.id}),  # 'ctype': ...
            messages=_('The content type is required.'),
            codes='ctyperequired',
        )

    def test_clean_forbidden_ctype(self):
        subject_model = FakeContact
        object_model = FakeOrganisation
        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is concerned by',
        ).symmetric(
            id='creme_core-object_client', predicate='concerns',
            models=[FakeActivity],  # Not <object_model>
        ).get_or_create()[0]
        code = 'forbiddenctype'
        self.assertFormfieldError(
            field=RelationAddingTriggerField(model=subject_model),
            value=self._build_value(rtype=rtype, model=object_model),
            messages=RelationAddingTriggerField.default_error_messages[code] % {
                'model': object_model._meta.verbose_name,
            },
            codes=code,
        )


class SourceFieldsTestCase(CremeTestCase):
    def test_CreatedEntitySourceField(self):
        model1 = FakeContact
        field1 = CreatedEntitySourceField(model=model1)
        self.assertFalse(field1.required)
        self.assertEqual(model1, field1.model)

        exp_source1 = CreatedEntitySource(model=model1)
        self.assertEqual(exp_source1, field1.clean(''))
        self.assertEqual(exp_source1, field1.clean('whatever'))

        self.assertEqual('', field1.prepare_value(None))
        self.assertEqual('', field1.prepare_value(exp_source1))

        # ---
        model2 = FakeOrganisation
        field2 = CreatedEntitySourceField(model=model2)
        self.assertEqual(CreatedEntitySource(model=model2), field2.clean(''))

    def test_EditedEntitySourceField(self):
        model1 = FakeContact
        field1 = EditedEntitySourceField(model=model1)
        self.assertFalse(field1.required)
        self.assertEqual(model1, field1.model)

        exp_source1 = EditedEntitySource(model=model1)
        self.assertEqual(exp_source1, field1.clean(''))
        self.assertEqual(exp_source1, field1.clean('whatever'))

        self.assertEqual('', field1.prepare_value(None))
        self.assertEqual('', field1.prepare_value(exp_source1))

        # ---
        model2 = FakeOrganisation
        field2 = EditedEntitySourceField(model=model2)
        self.assertEqual(EditedEntitySource(model=model2), field2.clean(''))

    def test_TaggedEntitySourceField(self):
        model1 = FakeContact
        field1 = TaggedEntitySourceField(model=model1)
        self.assertFalse(field1.required)
        self.assertEqual(model1, field1.model)

        exp_source1 = TaggedEntitySource(model=model1)
        self.assertEqual(exp_source1, field1.clean(''))
        self.assertEqual(exp_source1, field1.clean('whatever'))

        self.assertEqual('', field1.prepare_value(None))
        self.assertEqual('', field1.prepare_value(exp_source1))

        # ---
        model2 = FakeOrganisation
        field2 = TaggedEntitySourceField(model=model2)
        self.assertEqual(TaggedEntitySource(model=model2), field2.clean(''))

    def test_SubjectEntitySourceField(self):
        model1 = FakeContact
        field1 = SubjectEntitySourceField(model=model1)
        self.assertFalse(field1.required)
        self.assertEqual(model1, field1.model)

        exp_source1 = SubjectEntitySource(model=model1)
        self.assertEqual(exp_source1, field1.clean(''))
        self.assertEqual(exp_source1, field1.clean('whatever'))

        # ---
        model2 = FakeOrganisation
        field2 = SubjectEntitySourceField(model=model2)
        self.assertEqual(SubjectEntitySource(model=model2), field2.clean(''))

    def test_ObjectEntitySourceField(self):
        model1 = FakeContact
        field1 = ObjectEntitySourceField(model=model1)
        self.assertFalse(field1.required)
        self.assertEqual(model1, field1.model)

        exp_source1 = ObjectEntitySource(model=model1)
        self.assertEqual(exp_source1, field1.clean(''))
        self.assertEqual(exp_source1, field1.clean('whatever'))

        # ---
        model2 = FakeOrganisation
        field2 = ObjectEntitySourceField(model=model2)
        self.assertEqual(ObjectEntitySource(model=model2), field2.clean(''))

    def test_FixedEntitySourceField(self):
        user = self.get_root_user()

        field = FixedEntitySourceField(user=user)
        self.assertFalse(field.required)

        orga = FakeOrganisation.objects.create(user=user, name='Acme')
        serialized_data = json_dump({
            'ctype': {
                'create': reverse('creme_core__quick_form', args=[orga.entity_type_id]),
                'create_label': str(orga.creation_label),
                'id': orga.entity_type_id,
            },
            'entity': orga.id,
        })
        self.assertEqual(FixedEntitySource(entity=orga), field.clean(serialized_data))

        self.assertEqual('', field.from_python(None))
        self.assertEqual('', field.from_python(''))
        self.assertEqual(serialized_data, field.from_python(serialized_data))
        self.assertJSONEqual(
            serialized_data, field.from_python(FixedEntitySource(entity=orga)),
        )

    def test_FixedEntitySourceField__empty(self):
        field = FixedEntitySourceField(user=self.get_root_user(), required=False)
        self.assertFalse(field.required)
        self.assertIsNone(field.clean(json_dump({
            'ctype': {'id': str(ContentType.objects.get_for_model(FakeOrganisation).id)},
            'entity': '',
        })))


class EntityFKSourceFieldTestCase(CremeTestCase):
    def test_choices1(self):
        field = EntityFKSourceField(
            entity_source=CreatedEntitySource(model=FakeContact),
        )
        choices = field.choices
        self.assertInChoices(value='image', label=_('Photograph'), choices=choices)
        self.assertNotInChoices(value='first_name',      choices=choices)
        self.assertNotInChoices(value='user',            choices=choices)
        self.assertNotInChoices(value='cremeentity_ptr', choices=choices)

    def test_choices2(self):
        field = EntityFKSourceField(
            entity_source=EditedEntitySource(model=FakeDocument),
        )
        choices = field.choices
        self.assertInChoices(value='linked_folder', label=_('Folder'), choices=choices)
        self.assertNotInChoices(value='categories', choices=choices)

    def test_ok1(self):
        sub_source = CreatedEntitySource(model=FakeContact)
        field = EntityFKSourceField(entity_source=sub_source)
        self.assertEqual(sub_source, field.entity_source)

        field_name = 'image'
        source = EntityFKSource(entity_source=sub_source, field_name=field_name)
        self.assertEqual(source, field.clean(field_name))
        self.assertEqual(field_name, field.prepare_value(source))
        # TODO: None value => test clicka

    def test_ok2(self):
        sub_source = EditedEntitySource(model=FakeDocument)
        field = EntityFKSourceField(entity_source=sub_source)
        self.assertEqual(sub_source, field.entity_source)

        field_name = 'linked_folder'
        self.assertEqual(
            EntityFKSource(entity_source=sub_source, field_name=field_name),
            field.clean(field_name),
        )

    def test_empty__required(self):
        field = EntityFKSourceField(entity_source=CreatedEntitySource(model=FakeContact))
        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field,
            value='',
            messages=_('This field is required.'),
            codes='required',
        )

    def test_empty__not_required(self):
        field = EntityFKSourceField(
            entity_source=CreatedEntitySource(model=FakeContact),
            required=False,
        )
        self.assertFalse(field.required)
        self.assertIsNone(field.clean(''))


class FirstRelatedEntitySourceFieldTestCase(CremeTestCase):
    @staticmethod
    def _build_value(rtype: RelationType | str, model):
        return json_dump({
            'rtype': rtype if isinstance(rtype, str) else rtype.id,
            'ctype': ContentType.objects.get_for_model(model).id,
        })

    def test_ok(self):
        model1 = FakeContact
        model2 = FakeOrganisation

        subject_source1 = CreatedEntitySource(model=model1)
        field1 = FirstRelatedEntitySourceField(subject_source=subject_source1)
        self.assertEqual(subject_source1, field1.subject_source)

        rtype1 = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is a client of', models=[model1],
        ).symmetric(
            id='creme_core-object_client', predicate='has a client', models=[model2],
        ).get_or_create()[0]
        source1 = FirstRelatedEntitySource(
            subject_source=subject_source1, rtype=rtype1, object_model=model2,
        )
        value1 = self._build_value(rtype=rtype1, model=model2)
        self.assertEqual(source1, field1.clean(value1))

        # from_python() ---
        self.assertDictEqual(
            {
                'rtype': rtype1.id,
                'ctype': ContentType.objects.get_for_model(model2).id,
            },
            json_load(field1.from_python(source1)),
        )

        # ---
        subject_source2 = EditedEntitySource(model=model2)
        field2 = FirstRelatedEntitySourceField(subject_source=subject_source2)
        self.assertEqual(subject_source2, field2.subject_source)

        rtype2 = RelationType.objects.builder(
            id='creme_core-subject_concerned', predicate='is concerned by',
            is_internal=True,
        ).symmetric(id='creme_core-object_concerned', predicate='concerns').get_or_create()[0]
        self.assertEqual(
            FirstRelatedEntitySource(
                subject_source=subject_source2, rtype=rtype2, object_model=model1,
            ),
            field2.clean(self._build_value(rtype=rtype2, model=model1)),
        )

    def test_empty(self):
        field = FirstRelatedEntitySourceField(
            subject_source=EditedEntitySource(model=FakeContact),
            required=False,
        )
        self.assertIsNone(field.clean(None))

    def test_empty_required(self):
        field = FirstRelatedEntitySourceField(
            subject_source=EditedEntitySource(model=FakeContact),
        )
        self.assertTrue(field.required)

        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='{}')

    def test_clean_invalid_json(self):
        self.assertFormfieldError(
            field=FirstRelatedEntitySourceField(
                subject_source=EditedEntitySource(model=FakeContact),
            ),
            value='{"rtype":"creme_core-subject_whatever", "ctype":"12"',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_invalid_data_type(self):
        field = FirstRelatedEntitySourceField(
            subject_source=EditedEntitySource(model=FakeContact),
        )
        code = 'invalidtype'
        msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"this is a string"',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"[]"',
        )

    def test_clean_invalid_data(self):
        self.assertFormfieldError(
            field=FirstRelatedEntitySourceField(
                subject_source=EditedEntitySource(model=FakeContact),
            ),
            messages=_('Invalid format'), codes='invalidformat',
            value=json_dump({'rtype': REL_SUB_HAS, 'ctype': 'not_an_int'}),
        )

    def test_clean_unknown_rtype(self):
        rtype_id = 'test-i_do_not_exist'

        code = 'rtypenotallowed'
        self.assertFormfieldError(
            field=FirstRelatedEntitySourceField(
                subject_source=EditedEntitySource(model=FakeContact),
            ),
            value=self._build_value(rtype=rtype_id, model=FakeOrganisation),
            messages=FirstRelatedEntitySourceField.default_error_messages[code] % {
                'rtype_id': rtype_id,
            },
            codes=code,
        )

    def test_clean_forbidden_rtype(self):
        subject_model = FakeContact
        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is a client of',
            models=[FakeActivity],  # Not <subject_model>
        ).symmetric(id='creme_core-object_client', predicate='has a client').get_or_create()[0]
        code = 'rtypenotallowed'
        self.assertFormfieldError(
            field=FirstRelatedEntitySourceField(
                subject_source=EditedEntitySource(model=subject_model),
            ),
            value=self._build_value(rtype=rtype, model=FakeOrganisation),
            messages=RelationAddingTriggerField.default_error_messages[code],
            codes=code,
        )

    def test_clean_disabled_rtype(self):
        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is a client of', enabled=False,
        ).symmetric(id='creme_core-object_client', predicate='has a client').get_or_create()[0]

        code = 'rtypenotallowed'
        self.assertFormfieldError(
            field=FirstRelatedEntitySourceField(
                subject_source=EditedEntitySource(model=FakeContact),
            ),
            value=self._build_value(rtype=rtype, model=FakeOrganisation),
            messages=RelationAddingTriggerField.default_error_messages[code],
            codes=code,
        )

    def test_clean_ctype_errors(self):
        rtype = RelationType.objects.builder(
            id='creme_core-subject_concerned', predicate='is concerned by',
        ).symmetric(id='creme_core-object_concerned', predicate='concerns').get_or_create()[0]
        field = FirstRelatedEntitySourceField(
            subject_source=EditedEntitySource(model=FakeContact),
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump({'rtype': rtype.id, 'ctype': self.UNUSED_PK}),
            messages=_('This content type does not exist.'),
            codes='ctypedoesnotexist',
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump({'rtype': rtype.id}),  # 'ctype': ...
            messages=_('The content type is required.'),
            codes='ctyperequired',
        )

    def test_clean_forbidden_ctype(self):
        subject_model = FakeContact
        object_model = FakeOrganisation
        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is concerned by',
        ).symmetric(
            id='creme_core-object_client',  predicate='concerns',
            models=[FakeActivity],  # Not <object_model>
        ).get_or_create()[0]
        code = 'forbiddenctype'
        self.assertFormfieldError(
            field=FirstRelatedEntitySourceField(
                subject_source=EditedEntitySource(model=subject_model),
            ),
            value=self._build_value(rtype=rtype, model=object_model),
            messages=RelationAddingTriggerField.default_error_messages[code] % {
                'model': object_model._meta.verbose_name,
            },
            codes=code,
        )


class SourceFieldTestCase(CremeTestCase):
    def test_fields_choices(self):
        user = self.get_root_user()

        registry = WorkflowRegistry().register_sources(
            CreatedEntitySource,
            FixedEntitySource,
        )

        model = FakeContact
        field = SourceField(
            user=user, registry=registry,
            trigger=EntityCreationTrigger(model=model),
        )
        choices = field.fields_choices
        self.assertIsList(choices, length=2)

        kind_id1, field1 = choices[0]
        self.assertEqual('created_entity', kind_id1)
        self.assertIsInstance(field1, CreatedEntitySourceField)
        self.assertEqual(model, field1.model)

        kind_id2, field2 = choices[1]
        self.assertEqual('fixed_entity', kind_id2)
        self.assertIsInstance(field2, FixedEntitySourceField)
        self.assertEqual(user, field2.user)

    def test_fields_choices__empty(self):
        user = self.get_root_user()

        registry = WorkflowRegistry().register_sources(
            CreatedEntitySource, FixedEntitySource,
        )
        self.assertFalse(
            SourceField(
                # user=user,
                registry=registry,
                trigger=EntityCreationTrigger(model=FakeContact),
            ).fields_choices
        )
        self.assertFalse(
            SourceField(
                user=user,
                registry=registry,
                # trigger=EntityCreationTrigger(...),
            ).fields_choices
        )

    def test_fields_choices__user_property(self):
        user = self.get_root_user()
        registry = WorkflowRegistry().register_sources(
            CreatedEntitySource,
            FixedEntitySource,
            EntityFKSource,
            FirstRelatedEntitySource,
        )
        field = SourceField(
            # user=user,
            registry=registry,
            trigger=EntityCreationTrigger(model=FakeContact),
        )
        self.assertIsNone(field.user)
        self.assertFalse(field.fields_choices)

        field.user = user
        self.assertEqual(user, field.user)
        self.assertIsList(field.fields_choices, length=4)

    def test_fields_choices__trigger_property(self):
        user = self.get_root_user()
        registry = WorkflowRegistry().register_sources(
            CreatedEntitySource,
            FixedEntitySource,
            EntityFKSource,
            FirstRelatedEntitySource,
        )
        field = SourceField(
            user=user,
            registry=registry,
            # trigger=EntityCreationTrigger(model=model),
        )
        self.assertIsNone(field.trigger)
        self.assertFalse(field.fields_choices)

        trigger = EntityCreationTrigger(model=FakeContact)
        field.trigger = trigger
        self.assertEqual(trigger, field.trigger)
        self.assertIsList(field.fields_choices, length=4)

    def test_ok(self):
        user = self.get_root_user()

        registry = WorkflowRegistry().register_sources(
            CreatedEntitySource,
            FixedEntitySource,
            EntityFKSource,
            FirstRelatedEntitySource,
        )

        model = FakeContact
        trigger = EntityCreationTrigger(model=model)
        field = SourceField(user=user, registry=registry, trigger=trigger)
        self.assertEqual(user,    field.user)
        self.assertEqual(trigger, field.trigger)
        self.assertIs(registry, field.registry)

        # Clean ---
        orga = FakeOrganisation.objects.create(user=user, name='Acme')
        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is concerned by',
        ).symmetric(id='creme_core-object_client', predicate='concerns').get_or_create()[0]
        created_kind = 'created_entity'
        fixed_kind = 'fixed_entity'
        fk_kind = 'created_entity|entity_fk'
        related_kind = 'created_entity|first_related'
        sub_values = {
            created_kind: '',
            fixed_kind: json_dump({
                'ctype': {'id': str(orga.entity_type_id)},
                'entity': orga.id,
            }),
            fk_kind: 'image',
            related_kind: json_dump({
                'rtype': rtype.id,
                'ctype': orga.entity_type_id,
            }),
        }
        self.assertTupleEqual(
            (created_kind, CreatedEntitySource(model=model)),
            field.clean((created_kind, sub_values)),
        )
        self.assertTupleEqual(
            (fixed_kind, FixedEntitySource(entity=orga)),
            field.clean((fixed_kind, sub_values)),
        )
        self.assertTupleEqual(
            (
                fk_kind,
                EntityFKSource(
                    entity_source=CreatedEntitySource(model=model),
                    field_name='image',
                ),
            ),
            field.clean((fk_kind, sub_values)),
        )
        self.assertTupleEqual(
            (
                related_kind,
                FirstRelatedEntitySource(
                    subject_source=CreatedEntitySource(model=FakeContact),
                    rtype=rtype.id,
                    object_model=FakeOrganisation,
                )
            ),
            field.clean((related_kind, sub_values)),
        )

        # Prepare value ---
        self.assertIsNone(field.prepare_value(None))
        self.assertTupleEqual(
            (created_kind, {created_kind: ''}),
            field.prepare_value(CreatedEntitySource(model=model)),
        )
        self.assertTupleEqual(
            # TODO: to be fixed when prepare_value() is cleanly managed by our JSONFields...
            (fixed_kind, {fixed_kind: FixedEntitySource(entity=orga)}),
            field.prepare_value(FixedEntitySource(entity=orga)),
        )
        self.assertTupleEqual(
            (fk_kind, {fk_kind: 'image'}),
            field.prepare_value(EntityFKSource(
                entity_source=CreatedEntitySource(model=model), field_name='image',
            )),
        )

    def test_empty_required(self):
        field = SourceField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='')
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='[]')

    def test_empty_not_required(self):
        field = SourceField(required=False)
        self.assertIsNone(field.clean(None))
        self.assertIsNone(field.clean((None, None)))
        self.assertIsNone(field.clean(('', '')))

    def test_clean_invalid_data(self):
        self.assertFormfieldError(
            field=SourceField(),
            value=('unknown_id', {'created_entity': ''}),
            messages=_('This field is required.'),
            codes='required',
        )

    def test_incomplete_required(self):
        user = self.get_root_user()

        fixed_kind = 'created_entity|fixed_entity'
        sub_values = {
            fixed_kind: json_dump({
                'ctype': {'id': str(ContentType.objects.get_for_model(FakeContact).id)},
                'entity': '',
            }),
        }
        self.assertFormfieldError(
            field=SourceField(
                user=user, trigger=EntityCreationTrigger(model=FakeContact),
            ),
            value=(fixed_kind, sub_values),
            messages=_('This field is required.'),
            codes='required',
        )


class PropertyAddingActionFormTestCase(CremeTestCase):
    def test_init(self):
        form = PropertyAddingActionForm(
            user=self.get_root_user(),
            instance=Workflow(
                title='My WF',
                trigger=EntityCreationTrigger(model=FakeOrganisation),
            ),
        )
        self.assertCountEqual(['source', 'ptype'], form.fields.keys())
        self.assertIsNone(form.action_index)
        self.assertIsNone(form.action)

    def test_ptype_field(self):
        user = self.get_root_user()
        model = FakeOrganisation

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Property for all CT')
        ptype2 = create_ptype(text='Property for persons').set_subject_ctypes(model, FakeContact)
        ptype3 = create_ptype(text='Property for other').set_subject_ctypes(FakeActivity)
        ptype4 = create_ptype(text='Disabled type', enabled=False)

        wf = Workflow.objects.create(
            title='My WF',
            content_type=model,
            trigger=EntityCreationTrigger(model=model),
            actions=[
                PropertyAddingAction(
                    ptype=ptype1,
                    entity_source=CreatedEntitySource(model=model),
                ),
            ],
        )
        form1 = PropertyAddingActionForm(user=user, instance=wf)

        ptype_f1 = form1.fields.get('ptype')
        self.assertIsInstance(ptype_f1, ModelChoiceField)
        self.assertTrue(ptype_f1.required)
        self.assertIsNone(ptype_f1.initial)
        self.assertEqual(CremePropertyType, ptype_f1.queryset.model)

        choices = ptype_f1.choices
        self.assertInChoices(value=ptype1.id, label=ptype1.text, choices=choices)
        self.assertInChoices(value=ptype2.id, label=ptype2.text, choices=choices)
        # NB: we need the final source to know the final model for constraints
        # self.assertNotInChoices(value=ptype3.id, choices=choices)
        self.assertInChoices(value=ptype3.id, label=ptype3.text, choices=choices)
        self.assertNotInChoices(value=ptype4.id, choices=choices)

        # Initial ---
        form2 = PropertyAddingActionForm(user=user, instance=wf, action_index=0)
        self.assertEqual(0, form2.action_index)
        self.assertEqual(ptype1.id, form2.fields.get('ptype').initial)

    def test_source_field(self):
        user = self.get_root_user()
        model = FakeOrganisation
        trigger = EntityCreationTrigger(model=model)
        form = PropertyAddingActionForm(
            user=user, instance=Workflow(title='My WF', trigger=trigger),
        )

        source_f = form.fields.get('source')
        self.assertIsInstance(source_f, SourceField)
        self.assertEqual(user,    source_f.user)
        self.assertEqual(trigger, source_f.trigger)

    def test_clean__one_action(self):
        user = self.get_root_user()
        ptype = CremePropertyType.objects.create(text='Is cool')
        model = FakeOrganisation
        wf = Workflow(
            title='My WF', trigger=EntityCreationTrigger(model=model),
        )
        data = {
            'ptype': ptype.id,

            'source': 'created_entity',
            'source_created_entity': '',
        }
        form1 = PropertyAddingActionForm(user=user, instance=wf, data=data)
        self.assertTrue(form1.is_valid())
        expected_action_dicts = [
            PropertyAddingAction(
                entity_source=CreatedEntitySource(model=model), ptype=ptype,
            ).to_dict(),
        ]
        self.assertListEqual(expected_action_dicts, wf.json_actions)

        # Avoid duplicate ---
        form2 = PropertyAddingActionForm(user=user, instance=wf, data=data)
        self.assertTrue(form2.is_valid())
        self.assertListEqual(expected_action_dicts, wf.json_actions)

    def test_clean__two_actions(self):
        user = self.get_root_user()

        subject_model = FakeOrganisation
        object_model = FakeContact

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is cool')
        ptype2 = create_ptype(text='Is prosperous').set_subject_ctypes(
            subject_model, object_model,
        )

        rtype = RelationType.objects.builder(
            id='creme_core-subject_client', predicate='is concerned by',
        ).symmetric(id='creme_core-object_client', predicate='concerns').get_or_create()[0]

        wf = Workflow(
            title='My WF',
            trigger=RelationAddingTrigger(
                subject_model=subject_model,
                rtype=rtype,
                object_model=object_model,
            ),
            actions=[
                PropertyAddingAction(
                    entity_source=SubjectEntitySource(model=subject_model),
                    ptype=ptype1,
                ),
            ],
        )
        form = PropertyAddingActionForm(
            user=user, instance=wf,
            data={
                'ptype': ptype2.id,

                'source': 'object_entity',
                'source_object_entity': '',
            },
        )
        self.assertTrue(form.is_valid())
        self.assertListEqual(
            [
                PropertyAddingAction(
                    entity_source=SubjectEntitySource(model=subject_model), ptype=ptype1,
                ).to_dict(),
                PropertyAddingAction(
                    entity_source=ObjectEntitySource(model=object_model), ptype=ptype2,
                ).to_dict(),
            ],
            wf.json_actions,
        )

    def test_ptype_error(self):
        user = self.get_root_user()
        model = FakeOrganisation

        ptype = CremePropertyType.objects.create(
            text='Property for other',
        ).set_subject_ctypes(FakeActivity)

        wf = Workflow(
            title='My WF', trigger=EntityCreationTrigger(model=model),
        )
        form = PropertyAddingActionForm(
            user=user, instance=wf,
            data={
                'ptype': ptype.id,

                'source': 'created_entity',
                'source_created_entity': '',
            },
        )
        self.assertFormInstanceErrors(
            form,
            (
                'ptype',
                _('This property type is not compatible with the chosen type of entity.'),
            ),
        )
        self.assertFalse(wf.actions)


class RelationAddingActionFormTestCase(CremeTestCase):
    def test_fields(self):
        form = RelationAddingActionForm(
            user=self.get_root_user(),
            instance=Workflow(
                title='My WF',
                trigger=EntityCreationTrigger(model=FakeOrganisation),
            ),
        )
        self.assertCountEqual(
            ['subject_source', 'rtype', 'object_source'], form.fields.keys(),
        )

    def test_rtype_field(self):
        user = self.get_root_user()
        model = FakeOrganisation

        rtype1 = RelationType.objects.builder(
            id='test-subject_employee', predicate='is employed by',
        ).symmetric(id='test-object_employee', predicate='has employee').get_or_create()[0]
        rtype2 = rtype1.symmetric_type
        rtype3 = RelationType.objects.builder(
            id='test-subject_concerns', predicate='concerns', enabled=False,
        ).symmetric(id='test-object_concerns', predicate='is concerned by').get_or_create()[0]

        form = RelationAddingActionForm(
            user=user,
            instance=Workflow(
                title='My WF', trigger=EntityCreationTrigger(model=model),
            ),
        )

        rtype_f = form.fields.get('rtype')
        self.assertIsInstance(rtype_f, ModelChoiceField)
        self.assertTrue(rtype_f.required)
        self.assertEqual(RelationType, rtype_f.queryset.model)

        choices = rtype_f.choices
        self.assertInChoices(value=rtype1.id, label=str(rtype1), choices=choices)
        self.assertInChoices(value=rtype2.id, label=str(rtype2), choices=choices)
        self.assertNotInChoices(value=rtype3.id, choices=choices)

    def test_subject_source_field(self):
        user = self.get_root_user()
        model = FakeOrganisation
        trigger = EntityCreationTrigger(model=model)
        form = RelationAddingActionForm(
            user=user, instance=Workflow(title='My WF', trigger=trigger),
        )

        source_f = form.fields.get('subject_source')
        self.assertIsInstance(source_f, SourceField)
        self.assertEqual(user,    source_f.user)
        self.assertEqual(trigger, source_f.trigger)

    def test_object_source_field(self):
        user = self.get_root_user()
        model = FakeContact
        trigger = EntityEditionTrigger(model=model)
        form = RelationAddingActionForm(
            user=user, instance=Workflow(title='My WF', trigger=trigger),
        )

        source_f = form.fields.get('object_source')
        self.assertIsInstance(source_f, SourceField)
        self.assertEqual(user,    source_f.user)
        self.assertEqual(trigger, source_f.trigger)

    def test_clean(self):
        user = self.get_root_user()
        rtype = RelationType.objects.builder(
            id='test-subject_employee', predicate='is employed by',
        ).symmetric(id='test-object_employee', predicate='has employee').get_or_create()[0]
        fixed_orga = FakeOrganisation.objects.create(user=user, name='Acme')
        created_model = FakeContact
        wf = Workflow(
            title='My WF', trigger=EntityCreationTrigger(model=created_model),
        )

        form = RelationAddingActionForm(
            user=user, instance=wf,
            data={
                'rtype': rtype.id,

                'subject_source': 'created_entity',
                'subject_source_created_entity': '',

                'object_source': 'fixed_entity',
                'object_source_fixed_entity': json_dump({
                    'ctype': {'create': '', 'id': str(fixed_orga.entity_type_id)},
                    'entity': fixed_orga.id,
                }),
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertListEqual(
            [
                RelationAddingAction(
                    subject_source=CreatedEntitySource(model=created_model),
                    rtype=rtype,
                    object_source=FixedEntitySource(entity=fixed_orga),
                ).to_dict(),
            ],
            wf.json_actions,
        )

    def test_rtype_error__subject_model(self):
        user = self.get_root_user()
        created_model = FakeActivity

        rtype = RelationType.objects.builder(
            id='test-subject_employee', predicate='is employed by', models=[FakeContact],
        ).symmetric(id='test-object_employee', predicate='has employee').get_or_create()[0]
        fixed_orga = FakeOrganisation.objects.create(user=user, name='Acme')

        wf = Workflow(
            title='My WF', trigger=EntityCreationTrigger(model=created_model),
        )
        form = RelationAddingActionForm(
            user=user, instance=wf,
            data={
                'rtype': rtype.id,

                'subject_source': 'created_entity',
                'subject_source_created_entity': '',

                'object_source': 'fixed_entity',
                'object_source_fixed_entity': json_dump({
                    'ctype': {'create': '', 'id': str(fixed_orga.entity_type_id)},
                    'entity': fixed_orga.id,
                }),
            },
        )
        self.assertFormInstanceErrors(
            form,
            (
                'rtype',
                _(
                    'This relationship type is not compatible with the chosen '
                    'type of subject.'
                ),
            ),
        )
        self.assertFalse(wf.actions)

    def test_rtype_error__object_model(self):
        user = self.get_root_user()

        rtype = RelationType.objects.builder(
            id='test-subject_employee', predicate='is employed by',
        ).symmetric(
            id='test-object_employee', predicate='has employee', models=[FakeOrganisation],
        ).get_or_create()[0]
        fixed_img = FakeImage.objects.create(user=user, name='Image#1')

        wf = Workflow(
            title='My WF', trigger=EntityCreationTrigger(model=FakeContact),
        )
        form = RelationAddingActionForm(
            user=user, instance=wf,
            data={
                'rtype': rtype.id,

                'subject_source': 'created_entity',
                'subject_source_created_entity': '',

                'object_source': 'fixed_entity',
                'object_source_fixed_entity': json_dump({
                    'ctype': {'create': '', 'id': str(fixed_img.entity_type_id)},
                    'entity': fixed_img.id,
                }),
            },
        )
        self.assertFormInstanceErrors(
            form,
            (
                'rtype',
                _(
                    'This relationship type is not compatible with the chosen '
                    'type of object.'
                ),
            ),
        )
        self.assertFalse(wf.actions)

    def test_rtype_error__same_subject_n_object(self):
        user = self.get_root_user()
        rtype = RelationType.objects.builder(
            id='test-subject_employee', predicate='is employed by',
        ).symmetric(id='test-object_employee', predicate='has employee').get_or_create()[0]
        wf = Workflow(
            title='My WF', trigger=EntityCreationTrigger(model=FakeContact),
        )
        form = RelationAddingActionForm(
            user=user, instance=wf,
            data={
                'rtype': rtype.id,

                'subject_source': 'created_entity',
                'subject_source_created_entity': '',

                'object_source': 'created_entity',
                'object_source_created_entity': '',
            },
        )
        self.assertFormInstanceErrors(
            form, ('__all__', _('You cannot use the same subject & object.')),
        )
        self.assertFalse(wf.actions)
