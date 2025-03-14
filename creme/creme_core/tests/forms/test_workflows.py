from json import dumps as json_dump
from json import loads as json_load

from django.contrib.contenttypes.models import ContentType
from django.forms import Field, ModelChoiceField
from django.utils.translation import gettext as _

from creme.creme_config.forms.workflow import SourceField
from creme.creme_core.constants import REL_SUB_HAS
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
    RelationAddingActionForm,
    RelationAddingTriggerField,
    SubjectEntitySourceField,
)
from creme.creme_core.models import (
    CremePropertyType,
    FakeActivity,
    FakeContact,
    FakeDocument,
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
    RelationAddingTrigger,
    SubjectEntitySource,
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
        rtype1 = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_client', 'is a client of', [model1]),
            ('creme_core-object_client', 'has a client',    [model2]),
        )[0]
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

        rtype2 = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_concerned', 'is concerned by'),
            ('creme_core-object_concerned', 'concerns'),
            is_internal=True,
        )[0]
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
        rtype = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_client', 'is a client of', [FakeActivity]),  # Not model
            ('creme_core-object_client', 'has a client'),
        )[0]
        code = 'rtypenotallowed'
        self.assertFormfieldError(
            field=RelationAddingTriggerField(model=model),
            value=self._build_value(rtype=rtype, model=FakeOrganisation),
            messages=RelationAddingTriggerField.default_error_messages[code],
            codes=code,
        )

    def test_clean_disabled_rtype(self):
        model = FakeContact

        rtype = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_client', 'is a client of'),
            ('creme_core-object_client', 'has a client'),
        )[0]
        rtype.enabled = False
        rtype.save()

        code = 'rtypenotallowed'
        self.assertFormfieldError(
            field=RelationAddingTriggerField(model=model),
            value=self._build_value(rtype=rtype, model=model),
            messages=RelationAddingTriggerField.default_error_messages[code],
            codes=code,
        )

    def test_clean_ctype_errors(self):
        rtype = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_concerned', 'is concerned by'),
            ('creme_core-object_concerned', 'concerns'),
        )[0]
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
        rtype = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_client', 'is concerned by'),
            ('creme_core-object_client',  'concerns', [FakeActivity]),  # Not object_model
        )[0]
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

        # ---
        model2 = FakeOrganisation
        field2 = EditedEntitySourceField(model=model2)
        self.assertEqual(EditedEntitySource(model=model2), field2.clean(''))

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
        self.assertEqual(
            FixedEntitySource(entity=orga),
            field.clean(json_dump({
                'ctype': {'create': '', 'id': str(orga.entity_type_id)},
                'entity': orga.id,
            })),
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
        self.assertEqual(
            EntityFKSource(entity_source=sub_source, field_name=field_name),
            field.clean(field_name),
        )

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
        self.assertIsNone(
            field.clean(''),
        )


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

        rtype1, rtype2 = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_client', 'is a client of', [model1]),
            ('creme_core-object_client', 'has a client',    [model2]),
        )
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

        rtype2 = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_concerned', 'is concerned by'),
            ('creme_core-object_concerned', 'concerns'),
            is_internal=True,
        )[0]
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
        rtype = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_client', 'is a client of', [FakeActivity]),  # Not subject_model
            ('creme_core-object_client', 'has a client'),
        )[0]
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
        rtype = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_client', 'is a client of'),
            ('creme_core-object_client', 'has a client'),
        )[0]
        rtype.enabled = False
        rtype.save()

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
        rtype = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_concerned', 'is concerned by'),
            ('creme_core-object_concerned', 'concerns'),
        )[0]
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
        rtype = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_client', 'is concerned by'),
            ('creme_core-object_client',  'concerns', [FakeActivity]),  # Not object_model
        )[0]
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


class PropertyAddingActionFormTestCase(CremeTestCase):
    def test_fields(self):
        form = PropertyAddingActionForm(
            user=self.get_root_user(),
            instance=Workflow(
                title='My WF',
                trigger=EntityCreationTrigger(model=FakeOrganisation),
            ),
        )
        self.assertCountEqual(['source', 'ptype'], form.fields.keys())

    def test_ptype_field(self):
        user = self.get_root_user()
        model = FakeOrganisation

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Property for all CT')
        ptype2 = create_ptype(text='Property for persons').set_subject_ctypes(model, FakeContact)
        ptype3 = create_ptype(text='Property for other').set_subject_ctypes(FakeActivity)
        ptype4 = create_ptype(text='Disabled type', enabled=False)

        form = PropertyAddingActionForm(
            user=user,
            instance=Workflow(
                title='My WF', trigger=EntityCreationTrigger(model=model),
            ),
        )

        ptype_f = form.fields.get('ptype')
        self.assertIsInstance(ptype_f, ModelChoiceField)
        self.assertTrue(ptype_f.required)
        self.assertEqual(CremePropertyType, ptype_f.queryset.model)

        choices = ptype_f.choices
        self.assertInChoices(value=ptype1.id, label=ptype1.text, choices=choices)
        self.assertInChoices(value=ptype2.id, label=ptype2.text, choices=choices)
        # NB: we need the final source to know the final model for constraints
        # self.assertNotInChoices(value=ptype3.id, choices=choices)
        self.assertInChoices(value=ptype3.id, label=ptype3.text, choices=choices)
        self.assertNotInChoices(value=ptype4.id, choices=choices)

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

        rtype = RelationType.objects.smart_update_or_create(
            ('creme_core-subject_client', 'is concerned by'),
            ('creme_core-object_client',  'concerns'),
        )[0]

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
            user=user,
            instance=wf,
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

        form = PropertyAddingActionForm(
            user=user,
            instance=Workflow(
                title='My WF', trigger=EntityCreationTrigger(model=model),
            ),
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
            ['subject_source', 'rtype', 'object_source'],
            form.fields.keys(),
        )

    def test_rtype_field(self):
        user = self.get_root_user()
        model = FakeOrganisation

        create_rtype = RelationType.objects.smart_update_or_create
        rtype1, rtype2 = create_rtype(
            ('test-subject_employee', 'is employed by'),
            ('test-object_employee', 'has employee'),
        )
        rtype3 = create_rtype(
            ('test-subject_concerns', 'concerns'),
            ('test-object_concerns', 'is concerned by'),
        )[0]
        rtype3.enabled = False
        rtype3.save()

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
        self.fail('TODO')
        # user = self.get_root_user()
        # model = FakeOrganisation
        # trigger = EntityCreationTrigger(model=model)
        # form = PropertyAddingActionForm(
        #     user=user, instance=Workflow(title='My WF', trigger=trigger),
        # )
        #
        # source_f = form.fields.get('source')
        # self.assertIsInstance(source_f, SourceField)
        # self.assertEqual(user,    source_f.user)
        # self.assertEqual(trigger, source_f.trigger)

    # def test_clean__one_action(self):
    #     user = self.get_root_user()
    #     ptype = CremePropertyType.objects.create(text='Is cool')
    #     model = FakeOrganisation
    #     wf = Workflow(
    #         title='My WF', trigger=EntityCreationTrigger(model=model),
    #     )
    #     data = {
    #         'ptype': ptype.id,
    #
    #         'source': 'created_entity',
    #         'source_created_entity': '',
    #     }
    #     form1 = PropertyAddingActionForm(user=user, instance=wf, data=data)
    #     self.assertTrue(form1.is_valid())
    #     expected_action_dicts = [
    #         PropertyAddingAction(
    #             entity_source=CreatedEntitySource(model=model), ptype=ptype,
    #         ).to_dict(),
    #     ]
    #     self.assertListEqual(expected_action_dicts, wf.json_actions)
    #
    #     # Avoid duplicate ---
    #     form2 = PropertyAddingActionForm(user=user, instance=wf, data=data)
    #     self.assertTrue(form2.is_valid())
    #     self.assertListEqual(expected_action_dicts, wf.json_actions)
    #
    # def test_clean__two_actions(self):
    #     user = self.get_root_user()
    #
    #     subject_model = FakeOrganisation
    #     object_model = FakeContact
    #
    #     create_ptype = CremePropertyType.objects.create
    #     ptype1 = create_ptype(text='Is cool')
    #     ptype2 = create_ptype(text='Is prosperous').set_subject_ctypes(
    #         subject_model, object_model,
    #     )
    #
    #     rtype = RelationType.objects.smart_update_or_create(
    #         ('creme_core-subject_client', 'is concerned by'),
    #         ('creme_core-object_client',  'concerns'),
    #     )[0]
    #
    #     wf = Workflow(
    #         title='My WF',
    #         trigger=RelationAddingTrigger(
    #             subject_model=subject_model,
    #             rtype=rtype,
    #             object_model=object_model,
    #         ),
    #         actions=[
    #             PropertyAddingAction(
    #                 entity_source=SubjectEntitySource(model=subject_model),
    #                 ptype=ptype1,
    #             ),
    #         ],
    #     )
    #     form = PropertyAddingActionForm(
    #         user=user,
    #         instance=wf,
    #         data={
    #             'ptype': ptype2.id,
    #
    #             'source': 'object_entity',
    #             'source_object_entity': '',
    #         },
    #     )
    #     self.assertTrue(form.is_valid())
    #     self.assertListEqual(
    #         [
    #             PropertyAddingAction(
    #                 entity_source=SubjectEntitySource(model=subject_model), ptype=ptype1,
    #             ).to_dict(),
    #             PropertyAddingAction(
    #                 entity_source=ObjectEntitySource(model=object_model), ptype=ptype2,
    #             ).to_dict(),
    #         ],
    #         wf.json_actions,
    #     )
    #
    # def test_ptype_error(self):
    #     user = self.get_root_user()
    #     model = FakeOrganisation
    #
    #     ptype = CremePropertyType.objects.create(
    #         text='Property for other',
    #     ).set_subject_ctypes(FakeActivity)
    #
    #     form = PropertyAddingActionForm(
    #         user=user,
    #         instance=Workflow(
    #             title='My WF', trigger=EntityCreationTrigger(model=model),
    #         ),
    #         data={
    #             'ptype': ptype.id,
    #
    #             'source': 'created_entity',
    #             'source_created_entity': '',
    #         },
    #     )
    #     self.assertFormInstanceErrors(
    #         form,
    #         (
    #             'ptype',
    #             _('This property type is not compatible with the chosen type of entity.'),
    #         ),
    #     )
