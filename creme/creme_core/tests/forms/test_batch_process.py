# -*- coding: utf-8 -*-

from json import dumps as json_dump

from django.utils.translation import gettext as _

from creme.creme_core.forms.batch_process import BatchActionsField

from ..fake_models import FakeContact
from .base import FieldTestCase


class BatchActionsFieldTestCase(FieldTestCase):
    @staticmethod
    def build_data(name, operator, value):
        return json_dump([{'name': name, 'operator': operator, 'value': value}])

    def test_clean_empty_required(self):
        clean = BatchActionsField(required=True).clean
        self.assertFieldValidationError(BatchActionsField, 'required', clean, None)
        self.assertFieldValidationError(BatchActionsField, 'required', clean, '')
        self.assertFieldValidationError(BatchActionsField, 'required', clean, '[]')

    def test_clean_empty_not_required(self):
        field = BatchActionsField(required=False)
        self.assertNoException(field.clean, None)

    def test_clean_invalid_data_type(self):
        clean = BatchActionsField().clean
        self.assertFieldValidationError(
            BatchActionsField, 'invalidtype', clean, '"this is a string"',
        )
        self.assertFieldValidationError(
            BatchActionsField, 'invalidtype', clean, '"{}"',
        )
        self.assertFieldValidationError(
            BatchActionsField, 'invalidtype', clean,
            '{"foobar":{"operator": "3", "name": "first_name"}}',
        )
        self.assertFieldValidationError(
            BatchActionsField, 'invalidtype', clean, '1',
        )  # Not iterable

    def test_clean_incomplete_data_required(self):
        clean = BatchActionsField(model=FakeContact).clean

        # No name
        self.assertFieldValidationError(
            BatchActionsField, 'required', clean, '[{"operator": "upper"}]',
        )

        # No operator
        self.assertFieldValidationError(
            BatchActionsField, 'required', clean, '[{"name": "first_name"}]',
        )

        # Value has no 'value' key
        self.assertFieldValidationError(
            BatchActionsField, 'required', clean,
            '[{"operator": "upper", "name": "first_name"}]',
        )

    def test_clean_invalid_field(self):
        clean = BatchActionsField(model=FakeContact).clean

        self.assertFieldValidationError(
            BatchActionsField, 'invalidfield', clean,
            self.build_data(
                name='boobies_size',  # <---
                operator='upper',
                value='',
            ),
        )
        self.assertFieldValidationError(
            BatchActionsField, 'invalidfield', clean,
            self.build_data(
                name='header_filter_search_field',  # Not editable
                operator='upper',
                value='',
            ),
        )
        self.assertFieldValidationError(
            BatchActionsField, 'invalidfield', clean,
            self.build_data(
                name='civility',  # Type not managed
                operator='upper',
                value='',
            ),
        )

    def test_clean_invalid_operator01(self):
        clean = BatchActionsField(model=FakeContact).clean
        self.assertFieldValidationError(
            BatchActionsField, 'invalidoperator', clean,
            self.build_data(
                name='first_name',
                operator='unknown_op',  # <--
                value='',
            ),
        )
        self.assertFieldValidationError(
            BatchActionsField, 'invalidoperator', clean,
            self.build_data(
                name='first_name',
                operator='add_int',  # Apply to int, not str
                value='5',
            ),
        )

    def test_value_required(self):
        clean = BatchActionsField(model=FakeContact).clean
        self.assertFieldValidationError(
            BatchActionsField, 'invalidvalue', clean,
            self.build_data(
                name='first_name',
                operator='suffix',
                value='',
            ),
            message_args={
                'error': _("The operator '{}' needs a value.").format(_('Suffix')),
            },
        )

    def test_value_typeerror(self):
        clean = BatchActionsField(model=FakeContact).clean
        self.assertFieldValidationError(
            BatchActionsField, 'invalidvalue', clean,
            self.build_data(
                name='first_name',
                operator='rm_start',
                value='notanint',  # <===
            ),
            message_args={
                'error': _('{operator} : {message}.').format(
                    operator=_('Remove the start (N characters)'),
                    message=_('enter a whole number'),
                ),
            },
        )

    def test_ok01(self):
        with self.assertNumQueries(0):
            field = BatchActionsField(model=FakeContact)

        actions = field.clean(
            self.build_data(name='description', operator='upper', value='')
        )
        self.assertEqual(1, len(actions))

        contact = FakeContact(
            first_name='faye', last_name='Valentine', description='yarglaaaaaaaaaaa',
        )
        actions[0](contact)
        self.assertEqual('YARGLAAAAAAAAAAA', contact.description)

    def test_ok02(self):
        "Several actions."
        with self.assertNumQueries(0):
            field = BatchActionsField()
            field.model = FakeContact

        actions = field.clean(json_dump([
            {'name': 'first_name', 'operator': 'prefix', 'value': 'My '},
            {'name': 'last_name',  'operator': 'upper',  'value': ''},
        ]))
        self.assertEqual(2, len(actions))

        contact = FakeContact(first_name='Faye', last_name='Valentine')
        for action in actions:
            action(contact)

        self.assertEqual('My Faye',   contact.first_name)
        self.assertEqual('VALENTINE', contact.last_name)
