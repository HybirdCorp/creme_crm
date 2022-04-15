from json import dumps as json_dump
from json import loads as json_load

from django.contrib.contenttypes.models import ContentType
from django.forms import Field
from django.utils.translation import gettext as _

from creme.creme_core.constants import REL_SUB_HAS
from creme.creme_core.forms.workflows import (
    EntityCreationTriggerField,
    EntityEditionTriggerField,
    PropertyAddingActionField,
    RelationAddingTriggerField,
)
from creme.creme_core.models import (
    FakeActivity,
    FakeContact,
    FakeOrganisation,
    RelationType,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.workflows import (
    EntityCreationTrigger,
    EntityEditionTrigger,
    RelationAddingTrigger,
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
            value=self._build_value(rtype=rtype, model=model),
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
            messages=_('This content type is not allowed.'),
            codes='ctypenotallowed',
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


class PropertyAddingActionFieldTestCase(CremeTestCase):
    # @staticmethod
    # def _build_value(rtype, model):
    #     return json_dump({
    #         'rtype': rtype if isinstance(rtype, str) else rtype.id,
    #         'ctype': ContentType.objects.get_for_model(model).id,
    #     })

    def test_ok(self):
        # model1 = FakeContact
        # field1 = RelationAddingTriggerField(model=model1)
        PropertyAddingActionField()
