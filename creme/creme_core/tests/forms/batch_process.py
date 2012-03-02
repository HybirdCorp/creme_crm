# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme_core.forms.batch_process import BatchActionsField
    from creme_core.tests.forms.base import FieldTestCase

    from persons.models import Contact
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('BatchActionsFieldTestCase',)


class BatchActionsFieldTestCase(FieldTestCase):
    format_str = '[{"name": "%(name)s", "operator": "%(operator)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]'

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
        self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '"this is a string"')
        self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '"{}"')
        self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '{"foobar":{"operator": "3", "name": "first_name"}}')

    def test_clean_invalid_data(self):
        clean = BatchActionsField(model=Contact).clean
        self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '[{"operator": "upper"}]') #no name
        self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '[{"name": "first_name"}]') #no operator
        self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '[{"name": "first_name", "value": "Rei"}]') #value is not a dict
        self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '[{"name": "first_name", "value": {"foobar":"Rei"}}]') #value has no 'value' key

    def test_clean_invalid_field(self):
        clean = BatchActionsField(model=Contact).clean

        self.assertFieldValidationError(BatchActionsField, 'invalidfield', clean,
                                        self.format_str % {'name':     'boobies_size', #<---
                                                           'operator': 'upper',
                                                           'value':     '',
                                                          }
                                        )
        self.assertFieldValidationError(BatchActionsField, 'invalidfield', clean,
                                        self.format_str % {'name':     'header_filter_search_field', #not editable
                                                           'operator': 'upper',
                                                           'value':    '',
                                                          }
                                       )
        self.assertFieldValidationError(BatchActionsField, 'invalidfield', clean,
                                        self.format_str % {'name':     'civility', #type not managed
                                                           'operator': 'upper',
                                                           'value':    '',
                                                          }
                                        )

    def test_clean_invalid_operator01(self):
        clean = BatchActionsField(model=Contact).clean
        self.assertFieldValidationError(BatchActionsField, 'invalidoperator', clean,
                                        self.format_str % {'name':     'first_name',
                                                           'operator': 'unknown_op', # <--
                                                           'value':    '',
                                                          }
                                       )
        self.assertFieldValidationError(BatchActionsField, 'invalidoperator', clean,
                                        self.format_str % {'name':     'first_name',
                                                           'operator': 'add_int', #apply to int, not str
                                                           'value':    '5',
                                                          }
                                       )

    def test_value_required(self):
        clean = BatchActionsField(model=Contact).clean
        self.assertFieldValidationError(BatchActionsField, 'invalidvalue', clean,
                                        self.format_str % {'name':     'first_name',
                                                           'operator': 'suffix',
                                                           'value':    '',
                                                          },
                                        message_args=_(u"The operator '%s' need a value.") % _('Suffix'),
                                       )

    def test_value_typeerror(self):
        clean = BatchActionsField(model=Contact).clean
        self.assertFieldValidationError(BatchActionsField, 'invalidvalue', clean,
                                        self.format_str % {'name':     'first_name',
                                                           'operator': 'rm_start',
                                                           'value':    'notanint', # <===
                                                          },
                                        message_args=_('%(operator)s : %(message)s.') % {
                                                        'operator': _('Remove the start (N characters)'),
                                                        'message':  _('enter a whole number'),
                                                    }
                                       )

    def test_ok01(self):
        actions = BatchActionsField(model=Contact).clean(
                        self.format_str % {'name':     'description',
                                           'operator': 'upper',
                                           'value':    '',
                                          }
                    )
        self.assertEqual(1, len(actions))

        contact = Contact(first_name='faye', last_name='Valentine', description='yarglaaaaaaaaaaa')
        actions[0](contact)
        self.assertEqual('YARGLAAAAAAAAAAA', contact.description)

    def test_ok02(self): #several actions
        actions = BatchActionsField(model=Contact).clean(
                        '[{"name": "%(name01)s", "operator": "%(operator01)s", "value": {"type": "%(operator01)s", "value": "%(value01)s"}},'
                        ' {"name": "%(name02)s", "operator": "%(operator02)s", "value": {"type": "%(operator02)s", "value": "%(value02)s"}}]' % {
                                'name01':  'first_name', 'operator01': 'prefix', 'value01': 'My ',
                                'name02':  'last_name',  'operator02': 'upper',  'value02': '',
                            }
                    )
        self.assertEqual(2, len(actions))

        contact = Contact(first_name='Faye', last_name='Valentine')
        for action in actions:
            action(contact)

        self.assertEqual('My Faye',   contact.first_name)
        self.assertEqual('VALENTINE', contact.last_name)
