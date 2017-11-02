# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from .base import FieldTestCase
    from ..fake_models import FakeContact
    from creme.creme_core.forms.batch_process import BatchActionsField
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class BatchActionsFieldTestCase(FieldTestCase):
    format_str = '[{"name": "%(name)s", "operator": "%(operator)s", "value": "%(value)s"}]'

    # @classmethod
    # def setUpClass(cls):
    #     FieldTestCase.setUpClass()

    def test_clean_empty_required(self):
        clean = BatchActionsField(required=True).clean
        self.assertFieldValidationError(BatchActionsField, 'required', clean, None)
        self.assertFieldValidationError(BatchActionsField, 'required', clean, "")
        self.assertFieldValidationError(BatchActionsField, 'required', clean, "[]")

    def test_clean_empty_not_required(self):
        field = BatchActionsField(required=False)
        self.assertNoException(field.clean, None)

    def test_clean_invalid_data_type(self):
        clean = BatchActionsField().clean
        self.assertFieldValidationError(BatchActionsField, 'invalidtype', clean, '"this is a string"')
        self.assertFieldValidationError(BatchActionsField, 'invalidtype', clean, '"{}"')
        self.assertFieldValidationError(BatchActionsField, 'invalidtype', clean, '{"foobar":{"operator": "3", "name": "first_name"}}')
        self.assertFieldValidationError(BatchActionsField, 'invalidtype', clean, '1')  # Not iterable

    def test_clean_incomplete_data_required(self):
        clean = BatchActionsField(model=FakeContact).clean

        # No name
        self.assertFieldValidationError(BatchActionsField, 'required', clean, '[{"operator": "upper"}]')

        # No operator
        self.assertFieldValidationError(BatchActionsField, 'required', clean, '[{"name": "first_name"}]')

         # Value has no 'value' key
        self.assertFieldValidationError(BatchActionsField, 'required', clean, '[{"operator": "upper", "name": "first_name"}]')

    def test_clean_invalid_field(self):
        clean = BatchActionsField(model=FakeContact).clean

        self.assertFieldValidationError(BatchActionsField, 'invalidfield', clean,
                                        self.format_str % {'name':     'boobies_size',  # <---
                                                           'operator': 'upper',
                                                           'value':     '',
                                                          }
                                        )
        self.assertFieldValidationError(BatchActionsField, 'invalidfield', clean,
                                        self.format_str % {'name':     'header_filter_search_field',  # Not editable
                                                           'operator': 'upper',
                                                           'value':    '',
                                                          }
                                       )
        self.assertFieldValidationError(BatchActionsField, 'invalidfield', clean,
                                        self.format_str % {'name':     'civility',  # Type not managed
                                                           'operator': 'upper',
                                                           'value':    '',
                                                          }
                                        )

    def test_clean_invalid_operator01(self):
        clean = BatchActionsField(model=FakeContact).clean
        self.assertFieldValidationError(BatchActionsField, 'invalidoperator', clean,
                                        self.format_str % {'name':     'first_name',
                                                           'operator': 'unknown_op',  # <--
                                                           'value':    '',
                                                          }
                                       )
        self.assertFieldValidationError(BatchActionsField, 'invalidoperator', clean,
                                        self.format_str % {'name':     'first_name',
                                                           'operator': 'add_int',  # Apply to int, not str
                                                           'value':    '5',
                                                          }
                                       )

    def test_value_required(self):
        clean = BatchActionsField(model=FakeContact).clean
        self.assertFieldValidationError(BatchActionsField, 'invalidvalue', clean,
                                        self.format_str % {'name':     'first_name',
                                                           'operator': 'suffix',
                                                           'value':    '',
                                                          },
                                        message_args={'error': _(u"The operator '%s' need a value.") % _('Suffix')},
                                       )

    def test_value_typeerror(self):
        clean = BatchActionsField(model=FakeContact).clean
        self.assertFieldValidationError(BatchActionsField, 'invalidvalue', clean,
                                        self.format_str % {'name':     'first_name',
                                                           'operator': 'rm_start',
                                                           'value':    'notanint',  # <===
                                                          },
                                        message_args={'error': _('%(operator)s : %(message)s.') % {
                                                                    'operator': _('Remove the start (N characters)'),
                                                                    'message':  _('enter a whole number'),
                                                                }
                                                     },
                                       )

    def test_ok01(self):
        with self.assertNumQueries(0):
            field = BatchActionsField(model=FakeContact)

        actions = field.clean(self.format_str % {'name':     'description',
                                                 'operator': 'upper',
                                                 'value':    '',
                                                }
                             )
        self.assertEqual(1, len(actions))

        contact = FakeContact(first_name='faye', last_name='Valentine', description='yarglaaaaaaaaaaa')
        actions[0](contact)
        self.assertEqual('YARGLAAAAAAAAAAA', contact.description)

    def test_ok02(self):
        "Several actions"
        with self.assertNumQueries(0):
            field = BatchActionsField()
            field.model = FakeContact

        actions = field.clean(
                        '[{"name": "%(name01)s", "operator": "%(operator01)s", "value": "%(value01)s"},'
                        ' {"name": "%(name02)s", "operator": "%(operator02)s", "value": "%(value02)s"}]' % {
                                'name01':  'first_name', 'operator01': 'prefix', 'value01': 'My ',
                                'name02':  'last_name',  'operator02': 'upper',  'value02': '',
                            }
                    )
        self.assertEqual(2, len(actions))

        contact = FakeContact(first_name='Faye', last_name='Valentine')
        for action in actions:
            action(contact)

        self.assertEqual('My Faye',   contact.first_name)
        self.assertEqual('VALENTINE', contact.last_name)
