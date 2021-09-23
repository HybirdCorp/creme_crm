# -*- coding: utf-8 -*-

from django.utils.translation import gettext as _

from creme.creme_core.models import CremeEntity, CustomField, FakeContact
from creme.creme_core.tests.forms.base import FieldTestCase
from creme.crudity.core import (
    CRUDityExtractor,
    CustomFieldExtractor,
    RegularFieldExtractor,
)
from creme.crudity.forms.config import CrudityExtractorsField


class CrudityExtractorsFieldTestCase(FieldTestCase):
    def test_clean_empty_required(self):
        clean = CrudityExtractorsField(required=True).clean
        self.assertFieldValidationError(CrudityExtractorsField, 'required', clean, None)
        self.assertFieldValidationError(CrudityExtractorsField, 'required', clean, '')
        self.assertFieldValidationError(CrudityExtractorsField, 'required', clean, '[]')

    def test_clean_empty_not_required(self):
        field = CrudityExtractorsField(required=False)

        with self.assertNoException():
            value = field.clean(None)

        self.assertListEqual([], value)

    def test_clean_invalid_data_type(self):
        clean = CrudityExtractorsField().clean
        self.assertFieldValidationError(
            CrudityExtractorsField, 'invalidtype', clean, '"this is a string"'
        )
        self.assertFieldValidationError(
            CrudityExtractorsField, 'invalidtype', clean, '"{}"'
        )

    # TODO: useful?
    @staticmethod
    def build_data(*extractor_dicts):
        from json import dumps as json_dump

        return json_dump([
            # {
            #     # 'field':    {'name': condition['name']},
            #     # 'operator': {'id': str(condition['operator'])},
            #     # 'value':    condition['value'],
            # } for condition in extractor_dicts
            *extractor_dicts
        ])

    def test_basic_regularfield_extractor(self):
        field = CrudityExtractorsField(
            model=FakeContact,
            # efilter_registry=efilter_registry, TODO?
        )
        self.assertEqual(FakeContact, field.model)
        # TODO: test widget...

        field_name = 'last_name'
        extractors = field.clean(self.build_data({
            # 'cell_key': f'regular_field-{field_name}',
            'key': f'regular_field-{field_name}',
            'extractor_type': 'basic',
            # 'extractor_data': {},
        }))
        self.assertEqual(1, len(extractors))

        extractor = extractors[0]
        self.assertIsInstance(extractor, CRUDityExtractor)
        self.assertIsInstance(extractor, RegularFieldExtractor)
        self.assertEqual(FakeContact, extractor.model)  # TODO: attribute useful?
        self.assertEqual(field_name,  extractor.field_name)

    def test_basic_customfield_extractor(self):
        model = FakeContact
        cfield = CustomField.objects.create(
            content_type=model,
            field_type=CustomField.STR,
            name='Nickname',
        )

        field = CrudityExtractorsField(
            # efilter_registry=efilter_registry, TODO?
        )
        self.assertEqual(CremeEntity, field.model)

        field.model = model
        # TODO: test widget?

        extractors = field.clean(self.build_data({
            # 'cell_key': f'custom_field-{cfield.id}',
            'key': f'custom_field-{cfield.id}',
            'extractor_type': 'basic',
            # 'extractor_data': {},
        }))
        self.assertEqual(1, len(extractors))

        extractor = extractors[0]
        self.assertIsInstance(extractor, CRUDityExtractor)
        self.assertIsInstance(extractor, CustomFieldExtractor)
        self.assertEqual(FakeContact, extractor.model)
        self.assertEqual(cfield,      extractor.custom_field)

    # TODO: complete
    #  default value?
    #  other extractor (search fk, document auto-creation?)
    #  other cell types (relations? properties?)
    #  ...

    def test_invalid_regularfield_name(self):
        clean = CrudityExtractorsField(model=FakeContact).clean
        self.assertFieldValidationError(
            # CrudityExtractorsField, 'invalidcellvalue', clean,
            CrudityExtractorsField, 'invalidextractor', clean,
            self.build_data({
                # 'cell_key': 'regular_field-invalid',
                'key': 'regular_field-invalid',
                'extractor_type': 'basic',
                # 'extractor_data': {},
            }),
            message_args={
                'error': _('the field with name "{}" is invalid').format('invalid'),
            },
        )

    def test_invalid_customfield_id(self):
        cfield = CustomField.objects.order_by('-id').first()
        invalid_id = 1 if cfield is None else cfield.id + 1

        clean = CrudityExtractorsField(model=FakeContact).clean
        self.assertFieldValidationError(
            # CrudityExtractorsField, 'invalidcellvalue', clean,
            CrudityExtractorsField, 'invalidextractor', clean,
            self.build_data({
                # 'cell_key': f'custom_field-{invalid_id}',
                'key': f'custom_field-{invalid_id}',
                'extractor_type': 'basic',
                # 'extractor_data': {},
            }),
            message_args={
                'error': _('the custom-field with id="{}" does not exist').format(invalid_id),
            },
        )

    def test_invalid_cell_type(self):
        clean = CrudityExtractorsField(model=FakeContact).clean
        self.assertFieldValidationError(
            # CrudityExtractorsField, 'invalidcellkey', clean,
            CrudityExtractorsField, 'invalidextractor', clean,
            # self.build_data({'cell_key': 'invalid-whatever'}),
            self.build_data({'key': 'invalid-whatever'}),
            message_args={'error': 'the type ID "invalid" is invalid'},
        )

    def test_invalid_cell_key(self):
        clean = CrudityExtractorsField(model=FakeContact).clean
        self.assertFieldValidationError(
            # CrudityExtractorsField, 'invalidcellkey', clean,
            CrudityExtractorsField, 'invalidextractor', clean,
            # self.build_data({'cell_key': 'i_m_invalid'}),
            self.build_data({'key': 'i_m_invalid'}),
            # message_args={'error': 'the cell key "i_m_invalid" is malformed'},
            message_args={'error': 'the key "i_m_invalid" is malformed'},
        )

    def test_missing_cell_key(self):
        clean = CrudityExtractorsField(model=FakeContact).clean
        self.assertFieldValidationError(
            # CrudityExtractorsField, 'invalidcellkey', clean,
            CrudityExtractorsField, 'invalidextractor', clean,
            self.build_data({}),
            # message_args={'error': 'the cell key is missing'},
            message_args={'error': 'the key is missing'},
        )
