from functools import partial
from json import dumps as json_dump
from json import loads as json_load

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models.query import Q, QuerySet
from django.forms import Field
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth import EntityCredentials
from creme.creme_core.core.entity_filter import EF_CREDENTIALS, EF_REGULAR
from creme.creme_core.forms.fields import (
    CreatorEntityField,
    FilteredEntityTypeField,
    GenericEntityField,
    JSONField,
    MultiCreatorEntityField,
    MultiGenericEntityField,
    MultiRelationEntityField,
    RelationEntityField,
)
from creme.creme_core.gui.quick_forms import quickform_registry
from creme.creme_core.models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    EntityFilter,
    FakeContact,
    FakeImage,
    FakeOrganisation,
    Relation,
    RelationType,
)
from creme.creme_core.utils.content_type import entity_ctypes

from .. import fake_forms
from ..base import CremeTestCase


class _JSONFieldBaseTestCase(CremeTestCase):
    def login_as_basic_user(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, own='*')

        return user

    def create_contact(
            self,
            *, user,
            first_name='Eikichi',
            last_name='Onizuka',
            ptypes=(),
            **kwargs):
        contact = FakeContact.objects.create(
            user=user,
            first_name=first_name, last_name=last_name,
            **kwargs
        )

        if ptypes:
            if isinstance(ptypes, CremePropertyType):
                ptypes = (ptypes,)

            for ptype in ptypes:
                CremeProperty.objects.create(type=ptype, creme_entity=contact)

        return contact

    def create_orga(self, user, name='Onibaku', **kwargs):
        return FakeOrganisation.objects.create(user=user, name=name, **kwargs)

    @staticmethod
    def create_loves_rtype(subject_ptypes=(), object_ptypes=(), object_forbidden_ptypes=()):
        if isinstance(subject_ptypes, CremePropertyType):
            subject_ptypes = (subject_ptypes,)

        if isinstance(object_ptypes, CremePropertyType):
            object_ptypes = (object_ptypes,)

        if isinstance(object_forbidden_ptypes, CremePropertyType):
            object_forbidden_ptypes = (object_forbidden_ptypes,)

        return RelationType.objects.builder(
            id='test-subject_loves', predicate='is loving',
            properties=subject_ptypes,
        ).symmetric(
            id='test-object_loves', predicate='loved by',
            properties=object_ptypes,
            forbidden_properties=object_forbidden_ptypes,
        ).get_or_create()[0]

    @staticmethod
    def create_hates_rtype():
        return RelationType.objects.builder(
            id='test-subject_hates', predicate='is hating',
        ).symmetric(
            id='test-object_hates', predicate='hated by',
        ).get_or_create()[0]

    @staticmethod
    def create_employed_rtype():
        return RelationType.objects.builder(
            id='test-subject_employed_by', predicate='is an employee of',
            models=[FakeContact],
        ).symmetric(
            id='test-object_employed_by', predicate='employs',
            models=[FakeOrganisation],
        ).get_or_create()[0]

    @staticmethod
    def create_customer_rtype():
        return RelationType.objects.builder(
            id='test-subject_customer', predicate='is a customer of',
            models=[FakeContact, FakeOrganisation],
        ).symmetric(
            id='test-object_customer', predicate='is a supplier of',
            models=[FakeContact, FakeOrganisation],
        ).get_or_create()[0]


class JSONFieldTestCase(_JSONFieldBaseTestCase):
    def test_clean_empty_required(self):
        code = 'required'
        self.assertFormfieldError(
            field=JSONField(required=True),
            value=None,
            messages=Field.default_error_messages[code],
            codes=code,
        )

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            JSONField(required=False).clean(None)

    def test_clean_invalid_json(self):
        field = JSONField(required=True)
        code = 'invalidformat'
        msg = _('Invalid format')
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='{"unclosed_dict"',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='["unclosed_list",',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='["","unclosed_str]',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='["" "comma_error"]',
        )

    def test_clean_valid(self):
        with self.assertNoException():
            JSONField(required=True).clean('{"ctype":"12","entity":"1"}')

    def test_clean_json_with_type(self):
        clean_json = JSONField(required=True).clean_json

        with self.assertNoException():
            clean_json('{"ctype":"12","entity":"1"}', dict)
            clean_json('125', int)
            clean_json('[125, 126]', list)

    def test_clean_json_invalid_type(self):
        field = JSONField(required=True)
        code = 'invalidtype'

        with self.assertNoException():
            message = field.default_error_messages[code]
        self.assertEqual(_('Invalid type'), message)

        with self.assertRaises(ValidationError) as cm1:
            field.clean_json(value='["a", "b"]', expected_type=int)
        self.assertValidationError(cm1.exception, messages=message, codes=code)

        # ---
        with self.assertRaises(ValidationError) as cm2:
            field.clean_json(value='["a", "b"]', expected_type=dict)
        self.assertValidationError(cm2.exception, messages=message, codes=code)

        # ---
        with self.assertRaises(ValidationError) as cm3:
            field.clean_json(value='152', expected_type=list)
        self.assertValidationError(cm3.exception, messages=message, codes=code)

    def test_FMTing_to_json(self):
        self.assertEqual('', JSONField().from_python(''))

        val = 'this is a string'
        self.assertEqual(val, JSONField().from_python(val))

    def test_format_object_to_json(self):
        val = {'ctype': '12', 'entity': '1'}
        self.assertEqual(
            json_dump(val, separators=(',', ':')),
            JSONField().from_python(val),
        )

    def test_clean_entity_from_model(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        field = JSONField(required=True)

        clean_entity = field._clean_entity_from_model
        self.assertEqual(contact, clean_entity(FakeContact, contact.pk))

        # ---
        with self.assertNoException():
            message = field.default_error_messages['doesnotexist']
        self.assertEqual(_('This entity does not exist.'), message)

        with self.assertRaises(ValidationError) as cm1:
            clean_entity(FakeOrganisation, contact.pk)
        self.assertValidationError(cm1.exception, messages=message, codes='doesnotexist')

        # ---
        with self.assertRaises(ValidationError) as cm2:
            clean_entity(FakeContact, self.UNUSED_PK)
        self.assertValidationError(cm2.exception, messages=message, codes='doesnotexist')

    def test_clean_filtered_entity_from_model(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        field = JSONField(required=True, user=user)

        clean = field._clean_entity_from_model
        self.assertEqual(contact, clean(FakeContact, contact.pk, qfilter=Q(pk=contact.pk)))
        # ---
        code = 'isexcluded'

        with self.assertNoException():
            message = field.default_error_messages[code]

        self.assertEqual(message, _('«%(entity)s» violates the constraints.'))

        with self.assertRaises(ValidationError) as cm:
            clean(FakeContact, contact.pk, ~Q(pk=contact.pk))

        self.assertValidationError(
            cm.exception,
            messages=message % {'entity': str(contact)},
            codes=code,
        )

    def test_clean_deleted_entity_from_model(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user, is_deleted=True)
        field = JSONField(user=user)

        # ---
        code = 'isdeleted'

        with self.assertNoException():
            message = field.default_error_messages[code]
        self.assertEqual(message, _('«%(entity)s» is in the trash.'))

        with self.assertRaises(ValidationError) as cm:
            field._clean_entity_from_model(FakeContact, contact.pk, Q(pk=contact.pk))

        self.assertValidationError(
            cm.exception,
            messages=message % {'entity': str(contact)},
            codes=code,
        )


class GenericEntityFieldTestCase(_JSONFieldBaseTestCase):
    @staticmethod
    def build_field_data(ctype_id, entity_id, label=None):
        return json_dump(
            {
                'ctype': {
                    'create': reverse('creme_core__quick_form', args=(ctype_id,)),
                    'id': ctype_id,
                    'create_label': label or str(
                        ContentType.objects.get_for_id(ctype_id).model_class().creation_label
                    ),
                },
                'entity': entity_id,
            },
            separators=(',', ':'),
        )

    def test_models_ctypes(self):
        get_ct = ContentType.objects.get_for_model
        self.assertListEqual(
            [get_ct(FakeOrganisation), get_ct(FakeContact), get_ct(FakeImage)],
            GenericEntityField(models=[FakeOrganisation, FakeContact, FakeImage]).get_ctypes(),
        )

    def test_default_ctypes(self):
        ctypes = GenericEntityField().get_ctypes()
        self.assertEqual([*entity_ctypes()], ctypes)
        self.assertTrue(ctypes)

    def test_models_property(self):
        user = self.get_root_user()

        contact = self.create_contact(user=user)
        orga = self.create_orga(name='orga', user=user)

        ctype1 = contact.entity_type
        ctype2 = orga.entity_type

        field = GenericEntityField()
        self.assertListEqual([], field.allowed_models)
        self.assertListEqual([*entity_ctypes()], field.get_ctypes())

        field.allowed_models = [FakeContact, FakeOrganisation]
        ctypes = [*field.get_ctypes()]
        self.assertEqual(2, len(ctypes))
        self.assertIn(ctype1, ctypes)
        self.assertIn(ctype2, ctypes)

    def test_format_object(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        field = GenericEntityField(models=[FakeOrganisation, FakeContact, FakeImage])

        self.assertEqual(
            self.build_field_data(12, 1, 'Add'),
            field.from_python({
                'ctype': {
                    'create': reverse('creme_core__quick_form', args=(12,)),
                    'id': 12,
                    'create_label': 'Add',
                },
                'entity': 1,
            }),
        )

        # No user info
        ct_id = contact.entity_type_id
        self.assertEqual(
            {
                'ctype': {
                    'id': ct_id,
                    'create': '',
                    'create_label': _('Create a contact'),
                },
                'entity': contact.id,
            },
            json_load(field.from_python(contact)),
        )

        field.user = user
        expected = {
            'ctype': {
                'id': ct_id,
                'create': reverse('creme_core__quick_form', args=(ct_id,)),
                'create_label': _('Create a contact'),
            },
            'entity': contact.id,
        }
        self.assertDictEqual(expected, json_load(field.from_python(contact)))
        self.assertDictEqual(expected, json_load(field.from_python(contact.id)))

        with self.assertRaises(ValueError) as cm:
            field.from_python(self.UNUSED_PK)
        self.assertEqual(f'No such entity with id={self.UNUSED_PK}.', str(cm.exception))

    def test_format_ctype(self):
        field = GenericEntityField(models=[FakeOrganisation, FakeContact])
        ct = ContentType.objects.get_for_model(FakeOrganisation)
        self.assertDictEqual(
            {
                'ctype': {
                    'id': ct.id,
                    'create': '',
                    'create_label': _('Create an organisation'),
                },
                'entity': None,
            },
            json_load(field.from_python(ct)),
        )

    def test_clean_empty_required(self):
        field = GenericEntityField(required=True)
        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='{}')

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            value = GenericEntityField(required=False).clean(None)

        self.assertIsNone(value)

    def test_clean_invalid_json(self):
        self.assertFormfieldError(
            field=GenericEntityField(required=False),
            value='{"ctype":"12","entity":"1"',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_invalid_data_type(self):
        field = GenericEntityField(required=False)
        msg = _('Invalid type')
        code = 'invalidtype'
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"this is a string"',
        )
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='[]')

    def test_clean_invalid_data(self):
        field = GenericEntityField(required=False)
        msg = _('Invalid format')
        code = 'invalidformat'
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=json_dump({'ctype': 'notadict', 'entity': '1'}),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=json_dump({'ctype': {'id': 'notanumber', 'create': ''}, 'entity': '1'}),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=json_dump({'ctype': {'id': '12', 'create': ''}, 'entity': 'notanumber'}),
        )

    def test_clean_unknown_ctype(self):
        contact = self.create_contact(user=self.get_root_user())
        self.assertFormfieldError(
            field=GenericEntityField(models=[FakeOrganisation, FakeImage]),
            value=self.build_field_data(
                ctype_id=self.UNUSED_PK,
                entity_id=contact.id,
                label="Boo I'm a ghost ",
            ),
            messages=_('This content type does not exist.'),
            codes='ctypedoesnotexist',
        )

    def test_clean_forbidden_ctype(self):
        contact = self.create_contact(user=self.get_root_user())
        self.assertFormfieldError(
            field=GenericEntityField(models=[FakeOrganisation, FakeImage]),
            value=self.build_field_data(contact.entity_type_id, contact.id),
            messages=_('This content type is not allowed.'),
            codes='ctypenotallowed',
        )

    def test_clean_unknown_entity(self):
        contact = self.create_contact(user=self.get_root_user())
        ct_id = ContentType.objects.get_for_model(FakeImage).id  # Not Contact !!
        self.assertFormfieldError(
            field=GenericEntityField(models=[FakeOrganisation, FakeContact, FakeImage]),
            value=self.build_field_data(ct_id, contact.pk),
            messages=_('This entity does not exist.'),
            codes='doesnotexist',
        )

    def test_clean_deleted_entity(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user, is_deleted=True)

        field = GenericEntityField(models=[FakeOrganisation, FakeContact, FakeImage])
        field.user = user

        self.assertFormfieldError(
            field=field,
            value=self.build_field_data(contact.entity_type_id, contact.pk),
            messages=_('«%(entity)s» is in the trash.') % {'entity': str(contact)},
            codes='isdeleted',
        )

    def test_clean_entity(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)

        with self.assertNumQueries(0):
            field = GenericEntityField(models=[FakeOrganisation, FakeContact, FakeImage])

        field.user = user
        self.assertEqual(
            contact,
            field.clean(self.build_field_data(contact.entity_type_id, contact.pk)),
        )

    def test_clean_incomplete_not_required(self):
        user = self.get_root_user()
        field = GenericEntityField(
            models=[FakeOrganisation, FakeContact, FakeImage],
            required=False, user=user,
        )
        self.assertIsNone(field.clean(json_dump({'ctype': {'create': '', 'id': None}})))

        contact = self.create_contact(user=user)
        self.assertIsNone(field.clean(json_dump(
            {'ctype': {'create': '', 'id': str(contact.entity_type_id)}}
        )))
        self.assertIsNone(field.clean(json_dump(
            {'ctype': {'create': '', 'id': str(contact.entity_type_id)}, 'entity': None}
        )))

    def test_clean_incomplete_required(self):
        "Required -> 'friendly' errors."
        field = GenericEntityField(
            models=[FakeOrganisation, FakeContact, FakeImage],
            required=True,
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump({'ctype': {'create': '', 'id': None}}),
            messages=_('The content type is required.'),
            codes='ctyperequired',
        )

        ct_id = ContentType.objects.get_for_model(FakeContact).id
        msg = _('The entity is required.')
        code = 'entityrequired'
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=json_dump({'ctype': {'create': '', 'id': str(ct_id)}}),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value=json_dump({
                'ctype': {'create': '', 'id': str(ct_id)}, 'entity': None,
            }),
        )

    def test_autocomplete_property(self):
        field = GenericEntityField()
        self.assertTrue(field.autocomplete)

        field = GenericEntityField(autocomplete=False)
        self.assertFalse(field.autocomplete)

        field.autocomplete = True
        self.assertTrue(field.autocomplete)

    def test_clean_with_permission01(self):
        "Perm checking OK."
        user = self.login_as_basic_user()
        contact = self.create_contact(user=user)
        field = GenericEntityField(
            models=[FakeOrganisation, FakeContact, FakeImage],
            user=user,
        )
        self.assertEqual(
            contact,
            field.clean(self.build_field_data(contact.entity_type_id, contact.pk))
        )

    def test_clean_with_permission02(self):
        "Perm checking KO (LINK)."
        user = self.login_as_basic_user()
        contact = self.create_contact(user=self.get_root_user())
        self.assertFormfieldError(
            field=GenericEntityField(models=[FakeOrganisation, FakeContact], user=user),
            value=self.build_field_data(contact.entity_type_id, contact.pk),
            messages=_('You are not allowed to link this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=contact.id)
            ),
            codes='linknotallowed',
        )

    def test_clean_with_permission03(self):
        "Perm checking: VIEW."
        user = self.login_as_basic_user()
        self.add_credentials(user.role, all=['VIEW'], model=FakeContact)

        other_user = self.get_root_user()
        contact = self.create_contact(user=other_user)
        orga    = self.create_orga(user=other_user)

        field = GenericEntityField(
            models=[FakeOrganisation, FakeContact], user=user,
            credentials=EntityCredentials.VIEW,
        )
        self.assertEqual(
            contact,
            field.clean(self.build_field_data(contact.entity_type_id, contact.pk)),
        )
        self.assertFormfieldError(
            field=field,
            value=self.build_field_data(orga.entity_type_id, orga.pk),
            messages=_('You are not allowed to view this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=orga.id)
            ),
            codes='viewnotallowed',
        )

    def test_clean_with_permission04(self):
        "Perm checking: CHANGE."
        user = self.login_as_basic_user()
        self.add_credentials(user.role, all=['CHANGE'], model=FakeContact)

        other_user = self.create_user(index=1)
        contact = self.create_contact(user=other_user)
        orga    = self.create_orga(user=other_user)

        field = GenericEntityField(
            models=[FakeOrganisation, FakeContact], user=user,
            credentials=EntityCredentials.CHANGE,
        )
        self.assertEqual(
            contact,
            field.clean(self.build_field_data(contact.entity_type_id, contact.pk))
        )
        self.assertFormfieldError(
            field=field,
            value=self.build_field_data(orga.entity_type_id, orga.pk),
            messages=_('You are not allowed to edit this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=orga.id)
            ),
            codes='changenotallowed',
        )

    def test_clean_with_permission05(self):
        "Perm checking: perm combo."
        user = self.login_as_basic_user()
        other_user = self.get_root_user()
        self.add_credentials(user.role, all=['VIEW'], model=FakeContact)
        self.add_credentials(user.role, all=['LINK'], model=FakeOrganisation)

        contact = self.create_contact(user=other_user)
        orga1 = self.create_orga(user=other_user)
        orga2 = self.create_orga(user=user)

        field = GenericEntityField(
            models=[FakeOrganisation, FakeContact],
            user=user,
            credentials=EntityCredentials.VIEW | EntityCredentials.LINK,
        )
        self.assertEqual(
            orga2,
            field.clean(self.build_field_data(orga2.entity_type_id, orga2.pk))
        )

        self.assertFormfieldError(
            field=field,
            value=self.build_field_data(orga1.entity_type_id, orga1.pk),
            messages=_('You are not allowed to view this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=orga1.id)
            ),
            codes='viewnotallowed',
        )
        self.assertFormfieldError(
            field=field,
            value=self.build_field_data(contact.entity_type_id, contact.pk),
            messages=_('You are not allowed to link this entity: {}').format(contact),
            codes='linknotallowed',
        )


class MultiGenericEntityFieldTestCase(_JSONFieldBaseTestCase):
    @staticmethod
    def _build_quick_forms_url(ct_id):
        return reverse('creme_core__quick_form', args=(ct_id,))

    @classmethod
    def build_entry(cls, ctype_id, entity_id):
        return {
            'ctype': {
                'create': reverse('creme_core__quick_form', args=(ctype_id,)),
                'id': ctype_id,
                'create_label': str(
                    ContentType.objects.get_for_id(ctype_id)
                               .model_class()
                               .creation_label
                ),
            },
            'entity': entity_id,
        }

    @classmethod
    def build_data(cls, *entities):
        return json_dump([
            cls.build_entry(entity.entity_type_id, entity.id)
            for entity in entities
        ])

    def test_models_ctypes(self):
        get_ct = ContentType.objects.get_for_model
        models = [FakeOrganisation, FakeContact, FakeImage]
        self.assertListEqual(
            [get_ct(model) for model in models],
            MultiGenericEntityField(models=models).get_ctypes()
        )

    def test_default_ctypes(self):
        ctypes = MultiGenericEntityField().get_ctypes()
        self.assertListEqual([*entity_ctypes()], ctypes)
        self.assertTrue(ctypes)

    def test_format_object(self):
        user = self.get_root_user()

        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        contact_ct_id = contact.entity_type_id
        orga_ct_id    = orga.entity_type_id

        contact_label = FakeContact.creation_label
        orga_label    = FakeOrganisation.creation_label

        build_url = self._build_quick_forms_url

        def build_entry_v1(ctype_id, entity_id, label):
            return {
                'ctype': {
                    'create': reverse('creme_core__quick_form', args=(ctype_id,)),
                    'id': ctype_id,
                    'create_label': label,
                },
                'entity': entity_id,
            }

        field = MultiGenericEntityField(models=[FakeOrganisation, FakeContact, FakeImage])
        self.assertListEqual(
            [
                build_entry_v1(contact_ct_id, 1, contact_label),
                build_entry_v1(orga_ct_id, 5,    orga_label),
            ],
            json_load(field.from_python([
                {
                    'ctype': {
                        'id': contact_ct_id,
                        'create': build_url(contact_ct_id),
                        'create_label': str(contact_label),
                    },
                    'entity': 1,
                }, {
                    'ctype': {
                        'id': orga_ct_id,
                        'create': build_url(orga_ct_id),
                        'create_label': str(orga_label),
                    },
                    'entity': 5,
                }
            ]))
        )

        # No user
        def build_entry_v2(ctype_id, entity_id, label):
            return {
                'ctype': {
                    'create': '',
                    'id': ctype_id,
                    'create_label': label,
                },
                'entity': entity_id,
            }
        self.assertListEqual(
            [
                build_entry_v2(contact_ct_id, contact.id, contact_label),
                build_entry_v2(orga_ct_id,    orga.id,    orga_label),
            ],
            json_load(field.from_python([contact, orga]))
        )

        # With user
        def build_entry_v3(ctype_id, entity_id, label):
            return {
                'ctype': {
                    'create': reverse('creme_core__quick_form', args=(ctype_id,)),
                    'id': ctype_id,
                    'create_label': label,
                },
                'entity': entity_id,
            }

        field.user = user
        self.assertListEqual(
            [
                build_entry_v3(contact_ct_id, contact.id, contact_label),
                build_entry_v3(orga_ct_id,    orga.id,    orga_label),
            ],
            json_load(field.from_python([contact, orga])),
        )

    def test_clean_empty_required(self):
        field = MultiGenericEntityField(required=True)
        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='[]')

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            val = MultiGenericEntityField(required=False).clean(None)

        self.assertListEqual([], val)

    def test_clean_invalid_json(self):
        self.assertFormfieldError(
            field=MultiGenericEntityField(required=False),
            value='{"ctype":"12","entity":"1"',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_invalid_data_type(self):
        field = MultiGenericEntityField(required=False)
        code = 'invalidtype'
        msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"this is a string"',
        )
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='{}')

    def test_clean_invalid_data(self):
        field = MultiGenericEntityField(required=False)
        code = 'invalidformat'
        msg = _('Invalid format')
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value='[{"ctype":"notadict","entity":"1"}]',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value='[{"ctype":{"id": "notanumber", "create": ""},"entity":"1"}]',
        )
        self.assertFormfieldError(
            field=field,  messages=msg, codes=code,
            value='[{"ctype":{"id": "12", "create": ""},"entity":"notanumber"}]',
        )

    def test_clean_forbidden_ctype(self):
        user = self.get_root_user()
        self.assertFormfieldError(
            field=MultiGenericEntityField(models=[FakeOrganisation, FakeImage]),
            value=self.build_data(self.create_contact(user=user), self.create_orga(user=user)),
            messages=_('This content type is not allowed.'),
            codes='ctypenotallowed',
        )

    def test_clean_unknown_entity(self):
        user = self.get_root_user()
        contact1   = self.create_contact(user=user)
        contact2   = self.create_contact(user=user, first_name='Ryuji', last_name='Danma')
        ct_orga_id = ContentType.objects.get_for_model(FakeOrganisation).id
        self.assertFormfieldError(
            field=MultiGenericEntityField(
                models=[FakeOrganisation, FakeContact, FakeImage],
            ),
            value=json_dump([
                self.build_entry(contact1.entity_type_id, contact1.id),
                self.build_entry(ct_orga_id, contact2.id),
            ]),
            messages=_('This entity does not exist.'),
            codes='doesnotexist',
        )

    def test_clean_deleted_entity(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user, is_deleted=True)
        field = MultiGenericEntityField(
            models=[FakeOrganisation, FakeContact, FakeImage],
            user=user,
        )
        self.assertFormfieldError(
            field=field, value=self.build_data(contact),
            messages=_('«%(entity)s» is in the trash.') % {'entity': str(contact)},
            codes='isdeleted',
        )

    def test_clean_entities(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        with self.assertNumQueries(0):
            field = MultiGenericEntityField(models=[FakeOrganisation, FakeContact])

        field.user = user
        self.assertEqual([contact, orga], field.clean(self.build_data(contact, orga)))

    def test_clean_duplicates(self):
        "Duplicates are removed."
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        field = MultiGenericEntityField(models=[FakeOrganisation, FakeContact])
        field.user = user
        value = self.build_data(contact, orga, contact)  # 'contact' x 2

        # Contact once
        self.assertEqual([contact, orga], field.clean(value))

    def test_clean_duplicates_no_unique(self):
        "Duplicates are allowed."
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        field = MultiGenericEntityField(
            models=[FakeOrganisation, FakeContact], unique=False, user=user,
        )
        value = self.build_data(contact, orga, contact)  # 'contact' x 2

        # Contact twice
        self.assertEqual([contact, orga, contact], field.clean(value))

    def test_clean_incomplete_not_required(self):
        "Not required."
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        clean = MultiGenericEntityField(
            models=[FakeOrganisation, FakeContact], required=False, user=user,
        ).clean

        ct_id = str(contact.entity_type_id)
        self.assertListEqual(
            [], clean(json_dump([{'ctype': {'id': ct_id}}]))),
        self.assertListEqual(
            [], clean(json_dump([{'ctype': {'id': ct_id}, 'entity': None}])),
        )

        self.assertListEqual(
            [contact, orga],
            clean(json_dump([
                {'ctype': {'id': ct_id}},
                {'ctype': {'id': ct_id}, 'entity': None},
                {'ctype': {'id': ct_id}, 'entity': str(contact.id)},
                {'ctype': {'id': str(orga.entity_type_id)}, 'entity': str(orga.pk)},
            ]))
        )

    def test_clean_incomplete_required(self):
        "Required -> 'friendly' errors."
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        field = MultiGenericEntityField(
            models=[FakeOrganisation, FakeContact], required=True, user=user,
        )
        ct_id = str(contact.entity_type_id)
        self.assertFormfieldError(
            field=field,
            value=json_dump([
                {'ctype': {'id': ct_id}},
                {'ctype': {'id': ct_id}, 'entity': None},
            ]),
            messages=_('This field is required.'),
            codes='required',
        )
        self.assertListEqual(
            [contact, orga],
            field.clean(json_dump([
                {'ctype': {'id': ct_id}},
                {'ctype': {'id': ct_id}, 'entity': None},
                {'ctype': {'id': ct_id}, 'entity': str(contact.id)},
                {'ctype': {'id': str(orga.entity_type_id)}, 'entity': str(orga.pk)},
            ])),
        )

    def test_clean_with_permission01(self):
        "Perm checking OK."
        user = self.login_as_basic_user()
        contact = self.create_contact(user=user)
        orga = self.create_orga(user=user)
        field = MultiGenericEntityField(
            models=[FakeOrganisation, FakeContact],
            user=user,
        )

        self.assertListEqual(
            [contact, orga],
            field.clean(self.build_data(contact, orga))
        )

    def test_clean_with_permission02(self):
        "Perm checking KO."
        user = self.login_as_basic_user()
        contact = self.create_contact(user=user)
        orga = self.create_orga(user=self.get_root_user())
        self.assertFormfieldError(
            field=MultiGenericEntityField(
                models=[FakeOrganisation, FakeContact],
                user=user,
            ),
            value=self.build_data(contact, orga),
            messages=_('Some entities are not linkable: {}').format(
                _('Entity #{id} (not viewable)').format(id=orga.id),
            ),
            codes='linknotallowed',
        )

    def test_clean_with_permission03(self):
        "Perm checking: perm combo."
        user = self.login_as_basic_user()
        self.add_credentials(user.role, all=['VIEW'], model=FakeContact)
        self.add_credentials(user.role, all=['LINK'], model=FakeOrganisation)

        other_user = self.get_root_user()
        contact = self.create_contact(user=other_user)
        orga1 = self.create_orga(user=other_user)
        orga2 = self.create_orga(user=user)

        field = MultiGenericEntityField(
            models=[FakeOrganisation, FakeContact],
            user=user,
            credentials=EntityCredentials.VIEW | EntityCredentials.LINK,
        )

        self.assertEqual([orga2], field.clean(self.build_data(orga2)))

        self.assertFormfieldError(
            field=field,
            value=self.build_data(orga1),
            messages=_('Some entities are not viewable: {}').format(
                _('Entity #{id} (not viewable)').format(id=orga1.id)
            ),
            codes='viewnotallowed',
        )
        self.assertFormfieldError(
            field=field,
            value=self.build_data(contact),
            messages=_('Some entities are not linkable: {}').format(contact),
            codes='linknotallowed',
        )

    def test_autocomplete_property(self):
        with self.assertNumQueries(0):
            field = MultiGenericEntityField()

        self.assertFalse(field.autocomplete)

        field = MultiGenericEntityField(autocomplete=True)
        self.assertTrue(field.autocomplete)

        field.autocomplete = False
        self.assertFalse(field.autocomplete)


class RelationEntityFieldTestCase(_JSONFieldBaseTestCase):
    @staticmethod
    def _build_data(rtype_id, entity):
        return json_dump({
            'rtype':  rtype_id,
            'ctype':  str(entity.entity_type_id),
            'entity': str(entity.id),
        })

    def test_rtypes(self):
        rtype1 = self.create_loves_rtype()
        rtype2 = self.create_hates_rtype()

        with self.assertNumQueries(0):
            field = RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id])

        self.assertCountEqual([rtype1, rtype2], [*field.allowed_rtypes.all()])

    def test_rtypes_queryset(self):
        rtype1 = self.create_loves_rtype()
        rtype2 = self.create_hates_rtype()

        with self.assertNumQueries(0):
            field = RelationEntityField(
                allowed_rtypes=RelationType.objects.filter(pk__in=[rtype1.id, rtype2.id]),
            )

        self.assertCountEqual([rtype1, rtype2], [*field.allowed_rtypes.all()])

    def test_rtypes_queryset_changes(self):
        rtype2 = self.create_hates_rtype()

        field = RelationEntityField(
            allowed_rtypes=RelationType.objects.filter(
                pk__in=['test-subject_loves', rtype2.id],
            ),
        )
        self.assertListEqual([rtype2], [*field.allowed_rtypes.all()])

        rtype1 = self.create_loves_rtype()
        self.assertCountEqual([rtype1, rtype2], [*field.allowed_rtypes.all()])

        rtype2.delete()
        self.assertListEqual([rtype1], [*field.allowed_rtypes.all()])

    def test_default_rtypes(self):
        self.assertFalse(RelationEntityField().allowed_rtypes.all())

    def test_rtypes_property(self):
        rtype1 = self.create_loves_rtype()
        rtype2 = self.create_hates_rtype()

        field = RelationEntityField()
        self.assertTrue(isinstance(field.allowed_rtypes, QuerySet))
        self.assertFalse(field.allowed_rtypes)

        field.allowed_rtypes = [rtype1.id, rtype2.id]  # <===
        self.assertCountEqual([rtype1, rtype2], [*field.allowed_rtypes.all()])

    def test_clean_empty_required(self):
        field = RelationEntityField(required=True)
        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes='required', value=None)
        self.assertFormfieldError(field=field, messages=msg, codes='required', value='{}')

    def test_clean_empty_not_required(self):
        self.assertIsNone(RelationEntityField(required=False).clean(None))

    def test_clean_invalid_json(self):
        self.assertFormfieldError(
            field=RelationEntityField(required=False),
            value='{"rtype":"10", "ctype":"12","entity":"1"',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_invalid_data_type(self):
        field = RelationEntityField(required=False)
        code = 'invalidtype'
        msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"this is a string"',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"[]"',
        )

    def test_clean_invalid_data(self):
        field = RelationEntityField(required=False)
        code = 'invalidformat'
        msg = _('Invalid format')
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value='{"rtype":"notanumber", ctype":"12","entity":"1"}',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value='{"rtype":"10", ctype":"notanumber","entity":"1"}',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value='{"rtype":"10", "ctype":"12","entity":"notanumber"}',
        )

    def test_clean_unknown_rtype(self):
        contact = self.create_contact(user=self.get_root_user())

        rtype_id1 = 'test-i_do_not_exist'
        rtype_id2 = 'test-neither_do_i'

        # Message changes cause unknown rtype is ignored in allowed list
        self.assertFormfieldError(
            field=RelationEntityField(allowed_rtypes=[rtype_id1, rtype_id2]),
            value=self._build_data(rtype_id1, contact),
            messages=_(
                'This type of relationship causes a constraint error (id="%(rtype_id)s").'
            ) % {'rtype_id': rtype_id1},
            codes='rtypenotallowed',
        )

    def test_clean_not_allowed_rtype(self):
        contact = self.create_contact(user=self.get_root_user())

        rtype1 = self.create_loves_rtype()
        rtype2 = self.create_hates_rtype()
        rtype3 = RelationType.objects.builder(
            id='test-subject_friend', predicate='is friend of',
        ).symmetric(id='test-object_friend', predicate='has friend').get_or_create()[0]

        self.assertFormfieldError(
            field=RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]),
            value=self._build_data(rtype3.id, contact),
            messages=_(
                'This type of relationship causes a constraint error (id="%(rtype_id)s").'
            ) % {'rtype_id': rtype3.id},
            codes='rtypenotallowed',
        )

    def test_clean_not_allowed_rtype_queryset(self):
        contact = self.create_contact(user=self.get_root_user())

        rtype1 = self.create_loves_rtype()
        rtype2 = self.create_hates_rtype()
        rtype3 = RelationType.objects.builder(
            id='test-subject_friend', predicate='is friend of',
        ).symmetric(
            id='test-object_friend', predicate='has friend',
        ).get_or_create()[0]

        self.assertFormfieldError(
            field=RelationEntityField(
                allowed_rtypes=RelationType.objects.filter(pk__in=[rtype1.id, rtype2.id]),
            ),
            value=self._build_data(rtype3.id, contact),
            messages=_(
                'This type of relationship causes a constraint error (id="%(rtype_id)s").'
            ) % {'rtype_id': rtype3.id},
            codes='rtypenotallowed',
        )

    def test_clean_ctype_constraint_error(self):
        user = self.get_root_user()
        orga = self.create_orga(user=user)

        rtype1 = self.create_employed_rtype().symmetric_type
        rtype2 = self.create_customer_rtype().symmetric_type

        self.assertFormfieldError(
            field=RelationEntityField(user=user, allowed_rtypes=[rtype1.id, rtype2.id]),
            value=self._build_data(rtype1.id, orga),  # <= needs a Contact
            messages=_(
                'The entity «%(entity)s» is a «%(model)s» which is not '
                'allowed by the relationship «%(predicate)s».'
            ) % {
                'entity': orga,
                'model': orga.entity_type,
                'predicate': rtype1.symmetric_type.predicate,
            },
        )

    def test_clean_unknown_entity(self):
        orga = self.create_orga(user=self.get_root_user())

        rtype1 = self.create_employed_rtype().symmetric_type
        rtype2 = self.create_customer_rtype().symmetric_type
        ct_contact_id = ContentType.objects.get_for_model(FakeContact).id
        self.assertFormfieldError(
            field=RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]),
            value=json_dump({
                'rtype':  rtype1.id,
                'ctype':  str(ct_contact_id),
                'entity': str(orga.id),
            }),
            messages=_('This entity does not exist.'),
            codes='doesnotexist',
        )

    def test_clean_deleted_entity(self):
        user = self.get_root_user()
        orga = self.create_orga(user=user, is_deleted=True)
        rtype1 = self.create_employed_rtype()
        rtype2 = self.create_customer_rtype()

        field = RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id])
        field.user = user

        self.assertFormfieldError(
            field=field,
            value=self._build_data(rtype1.id, orga),
            messages=_('«%(entity)s» is in the trash.') % {'entity': str(orga)},
            codes='isdeleted',
        )

    def test_clean_relation(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        rtype1 = self.create_employed_rtype().symmetric_type
        rtype2 = self.create_customer_rtype().symmetric_type

        with self.assertNumQueries(0):
            field = RelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id])
            field.user = user

        with self.assertNumQueries(5):
            cleaned = field.clean(self._build_data(rtype1.id, contact))

        self.assertTupleEqual((rtype1, contact), cleaned)

    def test_clean_ctype_without_constraint(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        rtype = self.create_loves_rtype()

        field = RelationEntityField(allowed_rtypes=[rtype.id], user=user)
        self.assertTupleEqual(
            (rtype, contact),
            field.clean(self._build_data(rtype.id, contact)),
        )

    def test_clean_properties_constraint_error(self):
        user = self.get_root_user()

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is strong')
        ptype2 = create_ptype(text='Is cute')
        ptype3 = create_ptype(text='Is smart')

        rtype = self.create_loves_rtype(object_ptypes=(ptype1, ptype2))

        # Does not have the property 'ptype2'
        contact = self.create_contact(user=user, ptypes=(ptype1, ptype3))

        self.assertFormfieldError(
            field=RelationEntityField(allowed_rtypes=[rtype.pk], user=user),
            value=self._build_data(rtype.id, contact),
            messages=_(
                'The entity «%(entity)s» has no property «%(property)s» '
                'which is required by the relationship «%(predicate)s».'
            ) % {
                'entity': contact,
                'property': ptype2.text,
                'predicate': rtype.symmetric_type.predicate,
            },
        )

    def test_clean_properties_constraint(self):
        user = self.get_root_user()

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is strong')
        ptype2 = create_ptype(text='Is cute')
        ptype3 = create_ptype(text='Is smart')

        rtype = self.create_loves_rtype(object_ptypes=(ptype1, ptype2))

        # Has all the properties
        contact = self.create_contact(user=user, ptypes=(ptype1, ptype2, ptype3))

        field = RelationEntityField(allowed_rtypes=[rtype.id], user=user)
        self.assertTupleEqual(
            (rtype, contact),
            field.clean(self._build_data(rtype.id, contact)),
        )

    def test_clean_forbidden_properties_constraint_error(self):
        user = self.get_root_user()
        ptype = CremePropertyType.objects.create(text='Is not kind')
        rtype = self.create_loves_rtype(object_forbidden_ptypes=ptype)
        contact = self.create_contact(user=user, ptypes=ptype)
        self.assertFormfieldError(
            field=RelationEntityField(allowed_rtypes=[rtype.pk], user=user),
            value=self._build_data(rtype.id, contact),
            messages=_(
                'The entity «%(entity)s» has the property «%(property)s» '
                'which is forbidden by the relationship «%(predicate)s».'
            ) % {
                'entity': contact,
                'property': ptype.text,
                'predicate': rtype.symmetric_type.predicate,
            },
        )

    def test_clean_forbidden_properties_constraint(self):
        user = self.get_root_user()

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is not kind')
        ptype2 = create_ptype(text='Is cute')

        rtype = self.create_loves_rtype(object_forbidden_ptypes=ptype1)

        # Has no forbidden property
        contact = self.create_contact(user=user, ptypes=ptype2)

        field = RelationEntityField(allowed_rtypes=[rtype.id], user=user)
        self.assertTupleEqual(
            (rtype, contact),
            field.clean(self._build_data(rtype.id, contact)),
        )

    def test_clean_with_permission01(self):
        "Perm checking OK."
        user = self.login_as_basic_user()
        contact = self.create_contact(user=user)
        rtype = self.create_loves_rtype()

        field = RelationEntityField(allowed_rtypes=[rtype.id], user=user)
        self.assertTupleEqual(
            (rtype, contact),
            field.clean(self._build_data(rtype.id, contact)),
        )

    def test_clean_with_permission02(self):
        "Perm checking KO."
        user = self.login_as_basic_user()
        contact = self.create_contact(user=self.get_root_user())
        rtype = self.create_loves_rtype()
        self.assertFormfieldError(
            field=RelationEntityField(allowed_rtypes=[rtype.id], user=user),
            value=self._build_data(rtype.id, contact),
            messages=_('You are not allowed to link this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=contact.id)
            ),
            codes='linknotallowed',
        )

    def test_clean_incomplete01(self):
        "Not required."
        rtype = self.create_loves_rtype()
        contact = self.create_contact(user=self.get_root_user())

        clean = RelationEntityField(required=False).clean
        self.assertIsNone(clean(json_dump({'rtype': rtype.id})))
        self.assertIsNone(clean(json_dump({
            'rtype': rtype.id, 'ctype': str(contact.entity_type_id),
        })))

    def test_clean_incomplete02(self):
        "Required -> 'friendly' errors."
        rtype = self.create_loves_rtype()
        contact = self.create_contact(user=self.get_root_user())

        field = RelationEntityField(required=True)
        self.assertFormfieldError(
            field=field, value=json_dump({'rtype': rtype.id}),
            messages=_('The content type is required.'),
            codes='ctyperequired',
        )
        self.assertFormfieldError(
            field=field,
            value=json_dump({'rtype': rtype.id, 'ctype': str(contact.entity_type_id)}),
            messages=_('The entity is required.'),
            codes='entityrequired',
        )

    def test_autocomplete_property(self):
        field = RelationEntityField()
        self.assertFalse(field.autocomplete)

        field = RelationEntityField(autocomplete=True)
        self.assertTrue(field.autocomplete)

        field.autocomplete = False
        self.assertFalse(field.autocomplete)


class MultiRelationEntityFieldTestCase(_JSONFieldBaseTestCase):
    # TODO: factorise
    @classmethod
    def _build_entry(cls, rtype_id, ctype_id, entity_id):
        return {
            'rtype':  rtype_id,
            'ctype':  str(ctype_id),
            'entity': str(entity_id),
        }

    @classmethod
    def _build_data(cls, *relations):
        return json_dump([
            cls._build_entry(rtype_id, entity.entity_type_id, entity.id)
            for rtype_id, entity in relations
        ])

    def test_rtypes(self):
        rtype1 = self.create_loves_rtype()
        rtype2 = self.create_hates_rtype()

        with self.assertNumQueries(0):
            field = MultiRelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id])

        self.assertCountEqual([rtype1, rtype2], [*field.allowed_rtypes.all()])

    def test_rtypes_queryset(self):
        rtype1 = self.create_loves_rtype()
        rtype2 = self.create_hates_rtype()

        with self.assertNumQueries(0):
            field = MultiRelationEntityField(
                allowed_rtypes=RelationType.objects.filter(
                    pk__in=[rtype1.id, rtype2.id],
                ),
            )

        self.assertCountEqual([rtype1, rtype2], [*field.allowed_rtypes.all()])

    def test_rtypes_queryset_changes(self):
        rtype2 = self.create_hates_rtype()

        field = MultiRelationEntityField(
            allowed_rtypes=RelationType.objects.filter(
                pk__in=['test-subject_loves', rtype2.id],
            ),
        )
        self.assertListEqual([rtype2], [*field.allowed_rtypes.all()])

        rtype1 = self.create_loves_rtype()
        self.assertCountEqual([rtype1, rtype2], [*field.allowed_rtypes.all()])

        rtype2.delete()
        self.assertListEqual([rtype1], [*field.allowed_rtypes.all()])

    def test_default_rtypes(self):
        self.assertFalse(MultiRelationEntityField().allowed_rtypes)

    def test_clean_empty_required(self):
        field = MultiRelationEntityField(required=True)
        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='[]')

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            MultiRelationEntityField(required=False).clean(None)

    def test_clean_invalid_json(self):
        self.assertFormfieldError(
            field=MultiRelationEntityField(required=False),
            value='{"rtype":"10", "ctype":"12","entity":"1"',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_invalid_data_type(self):
        field = MultiRelationEntityField(required=False)
        code = 'invalidtype'
        msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"this is a string"',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code, value='"{}"',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value='{"rtype":"10", "ctype":"12","entity":"1"}',
        )

    def test_clean_invalid_data(self):
        field = MultiRelationEntityField(required=False)
        code = 'invalidformat'
        msg = _('Invalid format')
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value='[{"rtype":"notanumber", ctype":"12","entity":"1"}]',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value='[{"rtype":"10", ctype":"notanumber","entity":"1"}]',
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes=code,
            value='[{"rtype":"10", "ctype":"12","entity":"notanumber"}]',
        )

    def test_clean_unknown_rtype(self):
        contact = self.create_contact(user=self.get_root_user())

        rtype_id1 = 'test-i_do_not_exist'
        rtype_id2 = 'test-neither_do_i'

        self.assertFormfieldError(
            field=MultiRelationEntityField(allowed_rtypes=[rtype_id1, rtype_id2]),
            value=self._build_data([rtype_id1, contact]),
            messages=_(
                'This type of relationship causes a constraint error (id="%(rtype_id)s").'
            ) % {'rtype_id': rtype_id1},
            codes='rtypenotallowed',
        )

    def test_clean_not_allowed_rtype(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        rtype1 = self.create_loves_rtype()
        rtype2 = self.create_hates_rtype()
        rtype3 = RelationType.objects.builder(
            id='test-subject_friend', predicate='is friend of',
        ).symmetric(id='test-object_friend', predicate='has friend').get_or_create()[0]

        self.assertFormfieldError(
            field=MultiRelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]),
            value=self._build_data(
                (rtype3.id, contact),
                (rtype3.id, orga),
            ),
            messages=_(
                'This type of relationship causes a constraint error (id="%(rtype_id)s").'
            ) % {'rtype_id': rtype3.id},
            codes='rtypenotallowed',
        )

    def test_clean_not_allowed_rtype_queryset(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        rtype1 = self.create_loves_rtype()
        rtype2 = self.create_hates_rtype()
        rtype3 = RelationType.objects.builder(
            id='test-subject_friend', predicate='is friend of',
        ).symmetric(
            id='test-object_friend', predicate='has friend',
        ).get_or_create()[0]

        self.assertFormfieldError(
            field=MultiRelationEntityField(
                allowed_rtypes=RelationType.objects.filter(pk__in=[rtype1.id, rtype2.id]),
            ),
            value=self._build_data(
                (rtype3.id, contact),
                (rtype3.id, orga),
            ),
            messages=_(
                'This type of relationship causes a constraint error (id="%(rtype_id)s").'
            ) % {'rtype_id': rtype3.id},
            codes='rtypenotallowed',
        )

    def test_clean_ctype_constraint_error(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        rtype1 = self.create_employed_rtype().symmetric_type
        rtype2 = self.create_customer_rtype().symmetric_type

        self.assertFormfieldError(
            field=MultiRelationEntityField(user=user, allowed_rtypes=[rtype2.id, rtype1.id]),
            value=self._build_data(
                (rtype1.id, orga),  # <= not a Contact
                (rtype2.id, contact),
            ),
            messages=Relation.error_messages['forbidden_subject_ctype'] % {
                'entity': orga,
                'model': orga.entity_type,
                'predicate': rtype1.symmetric_type.predicate,
            }
        )

    def test_clean_unknown_entity(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        rtype1 = self.create_employed_rtype().symmetric_type
        rtype2 = self.create_customer_rtype().symmetric_type

        self.assertFormfieldError(
            field=MultiRelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id]),
            value=json_dump([
                self._build_entry(rtype1.id, contact.entity_type_id, orga.id),  # <=== bad ctype !
                self._build_entry(rtype2.id, contact.entity_type_id, contact.id),
            ]),
            messages=_('This entity does not exist.'),
            codes='doesnotexist',
        )

    def test_clean_deleted_entity(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user, is_deleted=True)

        rtype1 = self.create_employed_rtype().symmetric_type
        rtype2 = self.create_customer_rtype().symmetric_type

        field = MultiRelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id])
        field.user = user

        self.assertFormfieldError(
            field=field,
            value=self._build_data([rtype1.id, contact]),
            messages=_('«%(entity)s» is in the trash.') % {'entity': str(contact)},
            codes='isdeleted',
        )

    def test_clean_relations(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        rtype_employed = self.create_employed_rtype()
        rtype_employs = rtype_employed.symmetric_type
        rtype_supplier = self.create_customer_rtype().symmetric_type

        with self.assertNumQueries(0):
            field = MultiRelationEntityField(
                allowed_rtypes=[
                    rtype_supplier.id,
                    rtype_employs.id,
                    rtype_employed.id,
                ],
            )
            field.user = user

        # Queries:
        #  - the RelationTypes (with symmetric parts)
        #  - the FakeContact
        #  - the FakeOrganisation
        #  - the ContentTypes (constraints)
        #  - the CremePropertyTypes (constraints)
        #  - the forbidden CremePropertyTypes (constraints)
        #  - the CremeProperties of the FakeContact/FakeOrganisation
        with self.assertNumQueries(7):
            cleaned = field.clean(self._build_data(
                (rtype_employs.id, contact),
                (rtype_supplier.id, contact),
                (rtype_employed.id, orga),
            ))

        self.assertListEqual(
            [
                (rtype_employs, contact),
                (rtype_supplier, contact),
                (rtype_employed, orga),
            ],
            cleaned,
        )

    def test_clean_relations_queryset(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        rtype_employed = self.create_employed_rtype()
        rtype_employs = rtype_employed.symmetric_type
        rtype_supplier = self.create_customer_rtype().symmetric_type

        field = MultiRelationEntityField(
            allowed_rtypes=RelationType.objects.filter(
                pk__in=[rtype_supplier.id, rtype_employs.id, rtype_employed.id],
            ),
            user=user,
        )
        self.assertListEqual(
            [
                (rtype_employs, contact),
                (rtype_supplier, contact),
                (rtype_employed, orga),
            ],
            field.clean(self._build_data(
                (rtype_employs.id,  contact),
                (rtype_supplier.id, contact),
                (rtype_employed.id, orga),
            ))
        )

    def test_clean_ctype_without_constraint(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        rtype = self.create_loves_rtype()

        field = MultiRelationEntityField(allowed_rtypes=[rtype.id], user=user)
        self.assertListEqual(
            [(rtype, contact)],
            field.clean(self._build_data([rtype.id, contact]))
        )

    def test_clean_properties_constraint_error(self):
        user = self.get_root_user()

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is strong')
        ptype2 = create_ptype(text='Is cute')
        ptype3 = create_ptype(text='Is smart')

        rtype_constr    = self.create_loves_rtype(object_ptypes=(ptype1, ptype2))
        rtype_no_constr = self.create_hates_rtype()

        # Does not have the property 'ptype2'
        contact = self.create_contact(user=user, ptypes=(ptype1, ptype3))

        orga = self.create_orga(user=user)

        self.assertFormfieldError(
            field=MultiRelationEntityField(
                allowed_rtypes=[rtype_constr.pk, rtype_no_constr.pk], user=user,
            ),
            value=self._build_data(
                (rtype_constr.id,    contact),
                (rtype_no_constr.id, orga),
            ),
            messages=Relation.error_messages['missing_subject_property'] % {
                'entity': contact,
                'property': ptype2.text,
                'predicate': rtype_constr.symmetric_type.predicate,
            },
        )

    def test_clean_properties_constraint(self):
        user = self.get_root_user()

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is strong')
        ptype2 = create_ptype(text='Is cute')
        ptype3 = create_ptype(text='Is smart')

        rtype_constr    = self.create_loves_rtype(object_ptypes=(ptype1, ptype2))
        rtype_no_constr = self.create_hates_rtype()

        # Has all the properties
        contact = self.create_contact(user=user, ptypes=(ptype1, ptype3, ptype2))

        orga = self.create_orga(user=user)

        field = MultiRelationEntityField(allowed_rtypes=[rtype_constr.pk, rtype_no_constr.pk])
        field.user = user
        self.assertListEqual(
            [(rtype_constr, contact), (rtype_no_constr, orga)],
            field.clean(self._build_data(
                (rtype_constr.pk,    contact),
                (rtype_no_constr.pk, orga),
            )),
        )

    def test_clean_forbidden_properties_constraint_error(self):
        user = self.get_root_user()
        ptype = CremePropertyType.objects.create(text='Is not kind')

        rtype_constr    = self.create_loves_rtype(object_forbidden_ptypes=[ptype])
        rtype_no_constr = self.create_hates_rtype()

        contact = self.create_contact(user=user, ptypes=ptype)
        orga = self.create_orga(user=user)
        self.assertFormfieldError(
            field=MultiRelationEntityField(
                allowed_rtypes=[rtype_constr.pk, rtype_no_constr.pk], user=user,
            ),
            value=self._build_data(
                (rtype_constr.id,    contact),
                (rtype_no_constr.id, orga),
            ),
            messages=Relation.error_messages['refused_subject_property'] % {
                'entity': contact,
                'property': ptype.text,
                'predicate': rtype_constr.symmetric_type.predicate,
            },
        )

    def test_clean_forbidden_properties_constraint(self):
        user = self.get_root_user()

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is not kind')
        ptype2 = create_ptype(text='Is cute')

        rtype_constr    = self.create_loves_rtype(object_forbidden_ptypes=ptype1)
        rtype_no_constr = self.create_hates_rtype()

        # Has no forbidden properties
        contact = self.create_contact(user=user, ptypes=ptype2)

        orga = self.create_orga(user=user)

        field = MultiRelationEntityField(allowed_rtypes=[rtype_constr.pk, rtype_no_constr.pk])
        field.user = user
        self.assertListEqual(
            [(rtype_constr, contact), (rtype_no_constr, orga)],
            field.clean(self._build_data(
                (rtype_constr.pk,    contact),
                (rtype_no_constr.pk, orga),
            )),
        )

    def test_clean_incomplete01(self):
        "Not required."
        user = self.get_root_user()
        rtype = self.create_loves_rtype()
        contact = self.create_contact(user=user)

        clean = MultiRelationEntityField(
            required=False, allowed_rtypes=[rtype.id], user=user,
        ).clean
        self.assertListEqual([], clean(json_dump([{'rtype': rtype.id}])))

        ct_id = str(contact.entity_type_id)
        self.assertListEqual(
            [], clean(json_dump([{'rtype': rtype.id, 'ctype': ct_id}])),
        )
        self.assertListEqual(
            [(rtype, contact)],
            clean(json_dump([
                {'rtype': rtype.id, 'ctype': ct_id},
                {'rtype': rtype.id, 'ctype': ct_id, 'entity': str(contact.id)},
                {'rtype': rtype.id},
            ])),
        )

    def test_clean_incomplete02(self):
        "Required -> 'friendly' errors."
        user = self.get_root_user()
        rtype = self.create_loves_rtype()
        contact = self.create_contact(user=user)

        field = MultiRelationEntityField(
            required=True, allowed_rtypes=[rtype.id], user=user,
        )
        ct_id = str(contact.entity_type_id)
        self.assertFormfieldError(
            field=field,
            value=json_dump([
                {'rtype': rtype.id, 'ctype': ct_id},
                {'rtype': rtype.id},
            ]),
            messages=_('This field is required.'),
            codes='required',
        )
        self.assertListEqual(
            [(rtype, contact)],
            field.clean(json_dump([
                {'rtype': rtype.id, 'ctype': ct_id},
                {'rtype': rtype.id, 'ctype': ct_id, 'entity': str(contact.id)},
                {'rtype': rtype.id},
            ])),
        )

    def test_clean_with_permission01(self):
        "Perm checking OK."
        user = self.login_as_basic_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)

        rtype1 = self.create_loves_rtype()
        rtype2 = self.create_hates_rtype()

        field = MultiRelationEntityField(
            required=True, allowed_rtypes=[rtype1.id, rtype2.id],
        )
        field.user = user
        self.assertListEqual(
            [(rtype1, contact), (rtype2, orga)],
            field.clean(self._build_data(
                (rtype1.pk, contact),
                (rtype2.pk, orga),
            )),
        )

    def test_clean_with_permission02(self):
        "Perm checking KO"
        user = self.login_as_basic_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=self.get_root_user())

        rtype1 = self.create_loves_rtype()
        rtype2 = self.create_hates_rtype()

        field = MultiRelationEntityField(required=True, allowed_rtypes=[rtype1.id, rtype2.id])
        field.user = user

        self.assertFormfieldError(
            field=field,
            value=self._build_data(
                (rtype1.id, contact),
                (rtype2.id, orga),
            ),
            messages=_('Some entities are not linkable: {}').format(
                _('Entity #{id} (not viewable)').format(id=orga.id),
            ),
            codes='linknotallowed',
        )

    def test_format_object(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga    = self.create_orga(user=user)
        rtype1 = self.create_loves_rtype()
        rtype2 = self.create_hates_rtype()

        field = MultiRelationEntityField(allowed_rtypes=[rtype1.id, rtype2.id])

        # TODO: assertJSONEqual ?
        with self.assertNoException():
            json_data = json_load(field.from_python([(rtype1, contact), (rtype2, orga)]))

        self.assertListEqual(
            [
                {'entity': contact.id, 'ctype': contact.entity_type_id, 'rtype': rtype1.id},
                {'entity': orga.id,    'ctype': orga.entity_type_id,    'rtype': rtype2.id},
            ],
            json_data,
        )

    def test_autocomplete_property(self):
        field = MultiRelationEntityField()
        self.assertFalse(field.autocomplete)

        field = MultiRelationEntityField(autocomplete=True)
        self.assertTrue(field.autocomplete)

        field.autocomplete = False
        self.assertFalse(field.autocomplete)


class CreatorEntityFieldTestCase(_JSONFieldBaseTestCase):
    def test_void01(self):
        "Model is None."
        with self.assertNumQueries(0):
            field = CreatorEntityField(required=False)

        self.assertIsNone(field.model)
        self.assertIsNone(field.widget.model)
        self.assertIsNone(field.clean('1'))

    def test_void02(self):
        "Model is None; required."
        with self.assertNumQueries(0):
            field = CreatorEntityField()

        self.assertFormfieldError(
            field=field, messages=_('This field is required.'), codes='required', value='1',
        )

    def test_format_object(self):
        contact = self.create_contact(user=self.get_root_user())
        from_python = CreatorEntityField(model=FakeContact).from_python
        jsonified = str(contact.pk)
        self.assertEqual(jsonified, from_python(jsonified))
        self.assertEqual(jsonified, from_python(contact))
        self.assertEqual(jsonified, from_python(contact.pk))

    def test_model(self):
        field = CreatorEntityField(model=FakeContact)
        self.assertEqual(FakeContact, field.model)
        self.assertEqual(FakeContact, field.widget.model)

        field = CreatorEntityField()
        field.model = FakeContact
        self.assertEqual(FakeContact, field.model)
        self.assertEqual(FakeContact, field.widget.model)

    def test_qfilter01(self):
        "Dict."
        contact = self.create_contact(user=self.get_root_user())
        qfilter = {'pk': contact.pk}
        action_url = f'/persons/quickforms/from_widget/{contact.entity_type_id}/'

        field = CreatorEntityField(model=FakeContact)
        self.assertIsNone(field.q_filter)
        self.assertIsNone(field.q_filter_query)
        self.assertNotEqual(field.create_action_url, action_url)

        # Set q_filter
        field.q_filter = qfilter
        self.assertEqual(field.q_filter, qfilter)
        self.assertIsNotNone(field.q_filter_query)
        self.assertNotEqual(field.create_action_url, action_url)

        # Set creation url
        field.create_action_url = action_url
        self.assertEqual(field.q_filter, qfilter)
        self.assertIsNotNone(field.q_filter_query)
        self.assertEqual(field.create_action_url, action_url)

        # Set both q_filter and creation url in constructor
        field = CreatorEntityField(
            model=FakeContact, q_filter=qfilter, create_action_url=action_url,
        )
        self.assertEqual(field.q_filter, qfilter)
        self.assertIsNotNone(field.q_filter_query)
        self.assertEqual(field.create_action_url, action_url)

    def test_qfilter02(self):
        "Dict."
        orga = self.create_orga(user=self.get_root_user())
        qfilter = ~Q(id=orga.id)

        field = CreatorEntityField(model=FakeOrganisation)
        self.assertIsNone(field.q_filter)
        self.assertIsNone(field.q_filter_query)

        # Set q_filter
        field.q_filter = qfilter
        self.assertEqual(field.q_filter, qfilter)
        # self.assertIsNotNone(field.q_filter_query)  # TODO

        # Set both q_filter in constructor
        field = CreatorEntityField(model=FakeContact, q_filter=qfilter)
        self.assertEqual(field.q_filter, qfilter)

    def test_format_object_from_other_model(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga = self.create_orga(user=user)
        field = CreatorEntityField(model=FakeContact)

        jsonified = str(contact.pk)
        self.assertEqual(jsonified, field.from_python(jsonified))
        self.assertEqual(jsonified, field.from_python(contact))

        with self.assertRaises(ValueError) as error:
            field.from_python(orga.pk)

        self.assertEqual(
            str(error.exception), f'No such entity with id={orga.id}.',
        )

    def test_invalid_qfilter(self):
        contact = self.create_contact(user=self.get_root_user())
        action_url = f'/persons/quickforms/from_widget/{contact.entity_type_id}/'

        field = CreatorEntityField(model=FakeContact)

        # Set q_filter property
        field.q_filter = ['pk', contact.pk]

        with self.assertRaises(ValueError) as error:
            field.q_filter_query()

        qfilter_error = f"Invalid type for q_filter (needs dict or Q): ['pk', {contact.id}]"
        self.assertEqual(str(error.exception), qfilter_error)

        # Set q_filter in constructor
        field = CreatorEntityField(
            model=FakeContact, q_filter=['pk', contact.pk],
            create_action_url=action_url,
        )

        with self.assertRaises(ValueError) as error:
            field.q_filter_query()

        self.assertEqual(str(error.exception), qfilter_error)

    def test_action_buttons_no_custom_quickform(self):
        self.assertIsNotNone(quickform_registry.get_form_class(FakeContact))

        user = self.get_root_user()
        self.assertTrue(user.has_perm_to_create(FakeContact))

        field = CreatorEntityField(model=FakeContact, required=False)
        field.user = user

        url = field.create_action_url
        self.assertTrue(url)
        self.assertEqual(url, field.widget.creation_url)

        contact = self.create_contact(user=user)
        q_filter = ~Q(pk=contact.pk)
        field.q_filter = q_filter
        self.assertEqual(q_filter, field.q_filter)
        self.assertEqual(q_filter, field.widget.q_filter)
        self.assertFalse(field.force_creation)
        self.assertEqual('', field.widget.creation_url)

        field.force_creation = True
        self.assertTrue(field.widget.creation_url)

        field = CreatorEntityField(
            model=FakeContact, q_filter=~Q(pk=contact.pk), required=False,
        )
        field.user = user
        self.assertEqual('', field.widget.creation_url)

    def test_action_buttons_no_user(self):
        field = CreatorEntityField(model=FakeContact, required=False)
        self.assertIsNone(field.user)

        widget = field.widget
        self.assertEqual('', widget.creation_url)
        self.assertFalse(widget.creation_allowed)

    def test_action_buttons_required(self):
        field = CreatorEntityField(model=FakeContact)

        self.assertIsNone(field.user)
        self.assertTrue(field.required)
        self.assertListEqual([], field.widget.actions)

    def test_action_buttons_no_quickform(self):
        user = self.get_root_user()

        field = CreatorEntityField(model=CremeEntity, required=False)
        field.user = user

        self.assertTrue(field.user.has_perm_to_create(CremeEntity))
        self.assertIsNone(quickform_registry.get_form_class(CremeEntity))
        self.assertFalse(field.widget.creation_url)

    def test_action_buttons_not_allowed(self):
        user = self.login_as_standard()

        field = CreatorEntityField(model=FakeContact, required=False)
        field.user = user

        self.assertFalse(field.user.has_perm_to_create(FakeContact))
        self.assertIsNotNone(quickform_registry.get_form_class(FakeContact))

        widget = field.widget
        self.assertTrue(widget.creation_url)
        self.assertFalse(widget.creation_allowed)

    def test_action_buttons_allowed(self):
        self.assertIsNotNone(quickform_registry.get_form_class(FakeContact))

        user = self.get_root_user()
        self.assertTrue(user.has_perm_to_create(FakeContact))

        field = CreatorEntityField(model=FakeContact, required=False)
        self.assertEqual('', field.widget.creation_url)

        field.user = user

        widget = field.widget
        self.assertEqual(widget.creation_url, field.create_action_url)
        self.assertTrue(widget.creation_allowed)

    def test_create_action_url(self):
        field = CreatorEntityField(model=FakeContact)
        self.assertEqual(
            reverse(
                'creme_core__quick_form',
                args=(ContentType.objects.get_for_model(FakeContact).pk,)
            ),
            field.create_action_url
        )

        self.assertIsNone(field.create_action_label)
        self.assertIsNone(field.widget.creation_label)

        field.create_action_url = url = '/persons/quickforms/from_widget/contact/add/'
        self.assertEqual(url, field.create_action_url)

    def test_create_action_label(self):
        label = 'Create an agent'
        field = CreatorEntityField(model=FakeContact, create_action_label=label)
        self.assertEqual(label, field.create_action_label)
        self.assertEqual(label, field.widget.creation_label)

    def test_clean_empty_required(self):
        field = CreatorEntityField(model=FakeContact, required=True)
        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='')

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            value = CreatorEntityField(model=FakeContact, required=False).clean(None)

        self.assertIsNone(value)

    def test_clean_invalid_json(self):
        self.assertFormfieldError(
            field=CreatorEntityField(model=FakeContact, required=False),
            value='{12',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_invalid_data_type(self):
        field = CreatorEntityField(model=FakeContact, required=False)
        msg = _('Invalid type')
        self.assertFormfieldError(field=field, messages=msg, codes='invalidtype', value='[]')
        self.assertFormfieldError(field=field, messages=msg, codes='invalidtype', value='{}')

    def test_clean_unknown_entity(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga = self.create_orga(user=user)

        msg = _('This entity does not exist.')
        self.assertFormfieldError(
            field=CreatorEntityField(model=FakeContact),
            value=str(orga.pk),
            messages=msg, codes='doesnotexist',
        )
        self.assertFormfieldError(
            field=CreatorEntityField(model=FakeOrganisation),
            value=str(contact.pk),
            messages=msg, codes='doesnotexist',
        )

    def test_clean_with_permission01(self):
        "Perm checking OK."
        user = self.login_as_basic_user()

        orga = self.create_orga(user=user)

        field = CreatorEntityField(model=FakeOrganisation)
        field.user = user
        self.assertEqual(orga, field.clean(str(orga.pk)))

    def test_clean_with_permission02(self):
        "Perm checking KO."
        user = self.login_as_basic_user()

        orga = self.create_orga(user=self.get_root_user())

        field = CreatorEntityField(model=FakeOrganisation)
        field.user = user

        self.assertFormfieldError(
            field=field,
            value=str(orga.pk),
            messages=_('You are not allowed to link this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=orga.id),
            ),
            codes='linknotallowed',
        )

    def test_clean_deleted_entity(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user, is_deleted=True)
        self.assertFormfieldError(
            field=CreatorEntityField(model=FakeContact, user=user),
            value=str(contact.pk),
            messages=_('«%(entity)s» is in the trash.') % {'entity': str(contact)},
            codes='isdeleted',
        )

    def test_clean_filtered_entity01(self):
        "q_filter is a dict."
        user = self.get_root_user()
        contact1 = self.create_contact(user=user)

        with self.assertNumQueries(0):
            field = CreatorEntityField(model=FakeContact)

        field.user = user
        field.q_filter = {'pk': contact1.pk}
        self.assertEqual(contact1, field.clean(str(contact1.pk)))

        contact2 = self.create_contact(user=user)
        self.assertFormfieldError(
            field=field,
            value=str(contact2.pk),
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(contact2)},
            codes='isexcluded',
        )

    def test_clean_filtered_entity02(self):
        "q_filter is a Q."
        user = self.get_root_user()
        orga = self.create_orga(user=user)

        with self.assertNumQueries(0):
            field = CreatorEntityField(model=FakeOrganisation)

        field.user = user
        field.q_filter = ~Q(name__startswith=orga.name)
        self.assertFormfieldError(
            field=field,
            value=str(orga.pk),
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(orga)},
            codes='isexcluded',
        )

        field.q_filter = Q(name__startswith=orga.name)
        self.assertEqual(orga, field.clean(str(orga.pk)))

    def test_clean_filtered_entity03(self):
        "Several objects returned with the same pk (not distinct)."
        user = self.get_root_user()
        onibaku = self.create_orga(user=user)
        teachers = self.create_orga(user=user, name='teachers')

        create_contact = partial(FakeContact.objects.create, user=user)
        onizuka = create_contact(first_name='Eikichi', last_name='Onizuka')
        ryuji   = create_contact(first_name='Ryuji',   last_name='Danma')
        azusa   = create_contact(first_name='Azusa',   last_name='Fuyutsuki')

        rtype = self.create_employed_rtype()

        create_rel = partial(
            Relation.objects.create, user=user, type=rtype
        )
        create_rel(subject_entity=onizuka, object_entity=onibaku)
        create_rel(subject_entity=ryuji,   object_entity=onibaku)
        create_rel(subject_entity=onizuka, object_entity=teachers)
        create_rel(subject_entity=azusa,   object_entity=teachers)

        field = CreatorEntityField(
            model=FakeContact,
            q_filter=Q(
                relations__type_id=rtype,
                relations__object_entity_id__in=[onibaku.id, teachers.id],
            ),
            user=user,
        )

        # Beware onizuka is linked twice
        self.assertEqual(onizuka, field.clean(str(onizuka.pk)))

    def test_hook(self):
        user = self.get_root_user()

        form = fake_forms.FakeContactForm(user=user)

        with self.assertNoException():
            image_f = form.fields['image']

        self.assertIsInstance(image_f, CreatorEntityField)
        self.assertEqual(_('Photograph'), image_f.label)
        self.assertFalse(image_f.required)
        self.assertFalse(image_f.q_filter)

        # -----
        form = fake_forms.FakeOrganisationForm(user=user)

        with self.assertNoException():
            image_f = form.fields['image']

        self.assertIsInstance(image_f, CreatorEntityField)
        self.assertEqual(_('Logo'), image_f.label)
        self.assertTrue(callable(image_f.q_filter))
        self.assertQEqual(Q(user__is_staff=False), image_f.q_filter_query)


class MultiCreatorEntityFieldTestCase(_JSONFieldBaseTestCase):
    def test_void01(self):
        "Model is None."
        user = self.get_root_user()

        with self.assertNumQueries(0):
            field = MultiCreatorEntityField(required=False, user=user)

        self.assertListEqual([], field.clean('[1]'))

    def test_void02(self):
        "Model is None; required."
        with self.assertNumQueries(0):
            field = MultiCreatorEntityField()

        self.assertFormfieldError(
            field=field, value='[1]',
            messages=_('This field is required.'), codes='required',
        )

    def test_format_object(self):
        contact = self.create_contact(user=self.get_root_user())

        field = MultiCreatorEntityField(model=FakeContact)
        self.assertEqual(field.value_type, list)

        from_python = field.from_python
        jsonified = f'[{contact.id}]'
        self.assertEqual(jsonified, from_python(jsonified))
        self.assertEqual(jsonified, from_python([contact]))
        self.assertEqual(jsonified, from_python([contact.pk]))
        self.assertEqual('', from_python([]))

    def test_format_object_list(self):
        user = self.get_root_user()

        contact1 = self.create_contact(user=user)
        contact2 = self.create_contact(user=user)
        contact3 = self.create_contact(user=user)

        field = MultiCreatorEntityField(model=FakeContact)
        self.assertEqual(field.value_type, list)

        from_python = field.from_python
        jsonified = json_dump(
            [contact1.id, contact2.id, contact3.id], separators=(',', ':'),
        )
        self.assertEqual(jsonified, from_python(jsonified))
        self.assertEqual(jsonified, from_python([contact1, contact2, contact3]))
        self.assertEqual(jsonified, from_python([contact1.pk, contact2.pk, contact3.pk]))

    def test_qfilter(self):
        contact = self.create_contact(user=self.get_root_user())
        qfilter = {'pk': contact.pk}
        action_url = f'/persons/quickforms/from_widget/{contact.entity_type_id}/'

        field = MultiCreatorEntityField(model=FakeContact)
        self.assertIsNone(field.q_filter)

        field.q_filter = qfilter
        self.assertIsNotNone(field.q_filter)

        field = MultiCreatorEntityField(
            model=FakeContact, q_filter=qfilter, create_action_url=action_url,
        )
        self.assertIsNotNone(field.q_filter)
        self.assertEqual(field.create_action_url, action_url)

    def test_format_object_with_qfilter(self):
        user = self.get_root_user()

        contact1 = self.create_contact(user=user)
        contact2 = self.create_contact(user=user)
        contact3 = self.create_contact(user=user)

        field = MultiCreatorEntityField(model=FakeContact, q_filter=~Q(pk=contact1.id))

        jsonified = json_dump(
            [contact1.id, contact2.id, contact3.id], separators=(',', ':'),
        )
        self.assertEqual(jsonified, field.from_python(jsonified))
        self.assertEqual(jsonified, field.from_python([contact1, contact2, contact3]))
        self.assertEqual(
            f'[{contact2.id},{contact3.id}]',
            field.from_python([contact2.pk, contact3.pk])
        )

        with self.assertRaises(ValueError) as error:
            field.from_python([contact1.pk, contact2.pk, contact3.pk])

        ids = [str(e.id) for e in (contact1, contact2, contact3)]
        self.assertEqual(
            str(error.exception),
            "The entities with ids [{}] don't exist.".format(', '.join(ids)),
        )

    def test_format_object_from_other_model(self):
        user = self.get_root_user()

        contact1 = self.create_contact(user=user)
        contact2 = self.create_contact(user=user)
        orga = self.create_orga(user=user)

        field = MultiCreatorEntityField(model=FakeContact)

        jsonified = json_dump(
            [orga.id, contact1.id, contact2.id], separators=(',', ':'),
        )

        self.assertEqual(jsonified, field.from_python(jsonified))
        self.assertEqual(jsonified, field.from_python([orga, contact1, contact2]))

        with self.assertRaises(ValueError) as error:
            field.from_python([orga.pk, contact1.pk, contact2.pk])

        self.assertEqual(
            str(error.exception),
            "The entities with ids [{}] don't exist.".format(
                ', '.join(str(e.id) for e in (orga, contact1, contact2)),
            ),
        )

    def test_invalid_qfilter(self):
        contact = self.create_contact(user=self.get_root_user())
        action_url = f'/persons/quickforms/from_widget/{contact.entity_type_id}/'

        field = MultiCreatorEntityField(model=FakeContact)
        field.q_filter = ['pk', contact.pk]

        with self.assertRaises(ValueError) as error:
            field.q_filter_query  # NOQA

        qfilter_error = f"Invalid type for q_filter (needs dict or Q): ['pk', {contact.id}]"
        self.assertEqual(str(error.exception), qfilter_error)

        field = MultiCreatorEntityField(
            model=FakeContact, q_filter=['pk', contact.pk],
            create_action_url=action_url,
        )

        with self.assertRaises(ValueError) as error:
            field.q_filter_query  # NOQA

        self.assertEqual(str(error.exception), qfilter_error)

    def test_create_action_url(self):
        field = MultiCreatorEntityField(model=FakeContact)
        self.assertEqual(
            reverse(
                'creme_core__quick_form',
                args=(ContentType.objects.get_for_model(FakeContact).pk,),
            ),
            field.create_action_url
        )

        field.create_action_url = url = '/persons/quickforms/from_widget/contact/add/'
        self.assertEqual(url, field.create_action_url)

    def test_clean_empty_required(self):
        field = MultiCreatorEntityField(model=FakeContact, required=True)
        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='')
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='[]')

    def test_clean_empty_not_required(self):
        with self.assertNoException():
            value = MultiCreatorEntityField(model=FakeContact, required=False).clean(None)

        self.assertListEqual([], value)

        with self.assertNoException():
            value = MultiCreatorEntityField(model=FakeContact, required=False).clean("[]")

        self.assertListEqual([], value)

    def test_clean_invalid_json(self):
        field = MultiCreatorEntityField(model=FakeContact, required=False)
        code = 'invalidformat'
        msg = _('Invalid format')
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='{12')
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='[12')

    def test_clean_invalid_data_type(self):
        user = self.get_root_user()
        field = MultiCreatorEntityField(
            model=FakeContact, required=False, user=user,
        )
        code = 'invalidtype'
        msg = _('Invalid type')
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='""')
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='{}')
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='[{}]')

    def test_clean_unknown_entity(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)
        orga = self.create_orga(user=user)

        code = 'doesnotexist'
        msg = _('This entity does not exist.')
        self.assertFormfieldError(
            field=MultiCreatorEntityField(model=FakeContact),
            value=f'[{orga.id}]', messages=msg, codes=code,
        )
        self.assertFormfieldError(
            field=MultiCreatorEntityField(model=FakeOrganisation),
            value=f'[{contact.id}]', messages=msg, codes=code,
        )

    def test_clean_deleted_entity(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user, is_deleted=True)

        field = MultiCreatorEntityField(model=FakeContact)
        field.user = user

        self.assertFormfieldError(
            field=field, value=f'[{contact.id}]',
            messages=_('«%(entity)s» is in the trash.') % {'entity': str(contact)},
            codes='isdeleted',
        )

    def test_clean_entities(self):
        user = self.get_root_user()
        contact1 = self.create_contact(user=user)
        contact2 = self.create_contact(user=user)

        field = MultiCreatorEntityField(model=FakeContact)
        field.user = user
        self.assertListEqual(
            [contact1, contact2],
            field.clean(json_dump([contact1.id, contact2.id])),
        )

    def test_clean_filtered_entities(self):
        user = self.get_root_user()
        contact = self.create_contact(user=user)

        with self.assertNumQueries(0):
            field = MultiCreatorEntityField(model=FakeContact)
            field.q_filter = ~Q(pk=contact.pk)

        field.user = user
        self.assertFormfieldError(
            field=field, value=f'[{contact.id}]',
            messages=_('«%(entity)s» violates the constraints.') % {'entity': str(contact)},
            codes='isexcluded',
        )

        field.q_filter = {'pk': contact.pk}
        self.assertEqual([contact], field.clean(f'[{contact.id}]'))

    def test_clean_with_permission01(self):
        "Perm checking OK."
        user = self.login_as_basic_user()

        orga1 = self.create_orga(user=user, name='Orga #1')
        orga2 = self.create_orga(user=user, name='Orga #2')

        field = MultiCreatorEntityField(model=FakeOrganisation)
        field.user = user
        self.assertListEqual(
            [orga1, orga2],
            field.clean(json_dump([orga1.id, orga2.id])),
        )

    def test_clean_with_permission02(self):
        "Perm checking KO."
        user = self.login_as_basic_user()

        orga1 = self.create_orga(name='Orga #1', user=user)
        orga2 = self.create_orga(name='Orga #2', user=self.get_root_user())

        self.assertFormfieldError(
            field=MultiCreatorEntityField(model=FakeOrganisation, user=user),
            value=f'[{orga1.id}, {orga2.id}]',
            messages=_('Some entities are not linkable: {}').format(
                _('Entity #{id} (not viewable)').format(id=orga2.id),
            ),
            codes='linknotallowed',
        )

    def test_hook(self):
        user = self.get_root_user()

        form = fake_forms.FakeEmailCampaignForm(user=user)

        with self.assertNoException():
            mlists_f = form.fields['mailing_lists']

        self.assertIsInstance(mlists_f, MultiCreatorEntityField)
        self.assertEqual(_('Related mailing lists'), mlists_f.label)
        self.assertFalse(mlists_f.required)
        self.assertFalse(mlists_f.q_filter)

        # -----
        form = fake_forms.FakeProductForm(user=user)

        with self.assertNoException():
            images_f = form.fields['images']

        self.assertIsInstance(images_f, CreatorEntityField)
        self.assertEqual(_('Images'), images_f.label)
        self.assertDictEqual({'user__is_active': True}, images_f.q_filter)


class FilteredEntityTypeFieldTestCase(_JSONFieldBaseTestCase):
    @staticmethod
    def build_value(ctype_id, efilter_id):
        return json_dump({'ctype': str(ctype_id), 'efilter': efilter_id})

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        get_ct = ContentType.objects.get_for_model
        cls.ct_contact = get_ct(FakeContact)
        cls.ct_orga    = get_ct(FakeOrganisation)

        cls.user = cls.get_root_user()

    def test_clean_empty_required(self):
        field = FilteredEntityTypeField(required=True)
        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='')

    def test_clean_invalid_json(self):
        self.assertFormfieldError(
            field=FilteredEntityTypeField(required=False),
            value='{"ctype":"10", "efilter":"creme_core-testfilter"',
            messages=_('Invalid format'),
            codes='invalidformat',
        )

    def test_clean_invalid_data_type(self):
        field = FilteredEntityTypeField(required=False)
        type_msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, value='"this is a string"', messages=type_msg, codes='invalidtype',
        )
        self.assertFormfieldError(
            field=field, value='"{}"', messages=type_msg, codes='invalidtype',
        )
        self.assertFormfieldError(
            field=field,
            value='{"ctype":"not_an_int", "efilter":"creme_core-testfilter"}',
            messages=_('Invalid format'), codes='invalidformat',
        )

    def test_clean_required_ctype(self):
        self.assertFormfieldError(
            field=FilteredEntityTypeField(required=True),
            value=self.build_value('', ''),
            messages=_('The content type is required.'),
            codes='ctyperequired',
        )

    def test_clean_unknown_ctype(self):
        self.assertFormfieldError(
            field=FilteredEntityTypeField(),
            value=self.build_value(self.UNUSED_PK, ''),
            messages=_('This content type is not allowed.'),
            codes='ctypenotallowed',
        )

    def test_clean_forbidden_ctype01(self):
        "Allowed ContentTypes given as a list of ContentType instances."
        ctypes = [self.ct_contact]
        value = self.build_value(self.ct_orga.id, '')

        field1 = FilteredEntityTypeField(ctypes=ctypes)
        self.assertEqual(ctypes, field1.ctypes)
        msg = _('This content type is not allowed.')
        code = 'ctypenotallowed'
        self.assertFormfieldError(field=field1, messages=msg, codes=code, value=value)

        # Use setter ---
        field2 = FilteredEntityTypeField()
        field2.ctypes = ctypes
        self.assertFormfieldError(field=field2, messages=msg, codes=code, value=value)

    def test_clean_forbidden_ctype02(self):
        "Allowed ContentTypes given as a list of ID."
        ctypes = [self.ct_contact.id]
        value = self.build_value(str(self.ct_orga.id), '')
        msg = _('This content type is not allowed.')
        code = 'ctypenotallowed'
        self.assertFormfieldError(
            field=FilteredEntityTypeField(ctypes=ctypes),
            value=value, messages=msg, codes=code,
        )

        # Use setter ---
        field = FilteredEntityTypeField()
        field.ctypes = ctypes
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=value)

    def test_clean_forbidden_ctype03(self):
        "Allowed ContentTypes given as a list of ID & instances."
        ctypes = [self.ct_contact.id, self.ct_orga]
        self.assertFormfieldError(
            field=FilteredEntityTypeField(ctypes=ctypes),
            value=self.build_value(ContentType.objects.get_for_model(FakeImage).id, ''),
            messages=_('This content type is not allowed.'),
            codes='ctypenotallowed',
        )

    def test_clean_unknown_efilter01(self):
        "EntityFilter does not exist."
        self.assertFormfieldError(
            field=FilteredEntityTypeField(user=self.user),
            value=self.build_value(self.ct_contact.id, 'idonotexist'),
            messages=_('This filter is invalid.'),
            codes='invalidefilter',
        )

    def test_clean_unknown_efilter02(self):
        "Content type does not correspond to EntityFilter."
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Acme', FakeOrganisation, is_custom=True,
        )
        self.assertFormfieldError(
            field=FilteredEntityTypeField(user=self.user),
            value=self.build_value(self.ct_contact.id, efilter.id),
            messages=_('This filter is invalid.'),
            codes='invalidefilter',
        )

    def test_clean_private_filter(self):
        "Private invisible filter -> no user."
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'John', FakeContact, is_custom=True,
            user=self.user, is_private=True,
        )

        field = FilteredEntityTypeField()
        field.user = self.create_user()
        self.assertFormfieldError(
            field=field,
            value=self.build_value(self.ct_contact.id, efilter.id),
            messages=_('This filter is invalid.'),
            codes='invalidefilter',
        )

    def test_clean_filter_with_excluded_type(self):
        "EF_CREDENTIALS excluded by default."
        efilter = EntityFilter.objects.create(
            id='creme_core-test_filtered_entity_field',
            name='John',
            entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )

        field = FilteredEntityTypeField(user=self.create_user())
        self.assertFormfieldError(
            field=field,
            value=self.build_value(self.ct_contact.id, efilter.id),
            messages=_('This filter is invalid.'),
            codes='invalidefilter',
        )

    def test_clean_void(self):
        field = FilteredEntityTypeField(required=False)
        field.user = self.user

        self.assertTupleEqual(
            (None, None),
            field.clean(self.build_value('', '')),
        )
        self.assertTupleEqual(
            (None, None),
            field.clean('{"ctype": "0", "efilter": null}'),
        )

    def test_clean_only_ctype01(self):
        "All element of this ContentType are allowed."
        field = FilteredEntityTypeField()
        field.user = self.user

        self.assertTupleEqual(
            (self.ct_contact, None),
            field.clean(self.build_value(self.ct_contact.id, '')),
        )

    def test_clean_only_ctype02(self):
        "Allowed ContentTypes given as a sequence of instance/id."
        ct_contact = self.ct_contact
        ct_orga    = self.ct_orga

        field = FilteredEntityTypeField(ctypes=[ct_contact, ct_orga.id])
        field.user = self.user

        self.assertTupleEqual(
            (ct_contact, None),
            field.clean(self.build_value(ct_contact.id, '')),
        )
        self.assertTupleEqual(
            (ct_orga, None),
            field.clean(self.build_value(ct_orga.id, '')),
        )

    def test_clean_with_filter01(self):
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'John', FakeContact, is_custom=True,
        )

        field = FilteredEntityTypeField()
        field.user = self.user
        self.assertCountEqual([EF_REGULAR], field.filter_types)
        self.assertCountEqual([EF_REGULAR], field.widget.efilter_types)

        ct = self.ct_contact
        self.assertTupleEqual(
            (ct, efilter),
            field.clean(self.build_value(ct.id, efilter.id)),
        )

    def test_clean_with_filter02(self):
        "Private visible filter."
        user = self.user
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'John', FakeContact, is_custom=True,
            user=user, is_private=True,
        )
        field = FilteredEntityTypeField()
        field.user = user
        ct = self.ct_contact
        self.assertTupleEqual(
            (ct, efilter),
            field.clean(self.build_value(ct.id, efilter.id)),
        )

    def test_clean_with_filter__credentials(self):
        efilter = EntityFilter.objects.create(
            id='test-filter01', name='John', entity_type=FakeContact,
            filter_type=EF_CREDENTIALS,
        )

        field = FilteredEntityTypeField(user=self.user, filter_types=[EF_CREDENTIALS])
        self.assertCountEqual([EF_CREDENTIALS], field.filter_types)
        self.assertCountEqual([EF_CREDENTIALS], field.widget.efilter_types)

        ct = self.ct_contact
        self.assertTupleEqual(
            (ct, efilter), field.clean(self.build_value(ct.id, efilter.id)),
        )

    def test_filter_types_property(self):
        filter_types = [EF_CREDENTIALS, EF_REGULAR]
        field = FilteredEntityTypeField(user=self.user)

        field.filter_types = filter_types
        self.assertCountEqual(filter_types, field.filter_types)
        self.assertCountEqual(filter_types, field.widget.efilter_types)
