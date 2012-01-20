# -*- coding: utf-8 -*-

try:
    from creme_core.forms.batch_process import BatchActionsField
    from creme_core.tests.forms.base import FieldTestCase

    from persons.models import Contact
except Exception as e:
    print 'Error:', e


__all__ = ('BatchActionsFieldTestCase',)


class BatchActionsFieldTestCase(FieldTestCase):
    def test_clean_empty_required(self):
        clean = BatchActionsField(required=True).clean
        self.assertFieldValidationError(BatchActionsField, 'required', clean, None)
        self.assertFieldValidationError(BatchActionsField, 'required', clean, "")
        self.assertFieldValidationError(BatchActionsField, 'required', clean, "[]")

    def test_clean_empty_not_required(self):
        field = BatchActionsField(required=False)

        try:
            field.clean(None)
        except Exception as e:
            self.fail(str(e))

    def test_clean_invalid_data_type(self):
        clean = BatchActionsField().clean
        self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '"this is a string"')
        self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '"{}"')
        self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '{"foobar":{"operator": "3", "name": "first_name"}}') #,"value":"Rei"

    def test_clean_invalid_data(self):
        clean = BatchActionsField(model=Contact).clean
        self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '[{"operator": "upper"}]') #no name
        self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '[{"name": "first_name"}]') #no operator
        #self.assertFieldValidationError(BatchActionsField, 'invalidformat', clean, '[{"name": "first_name", "value": "Rei"}]')

    def test_clean_invalid_field(self):
        clean = BatchActionsField(model=Contact).clean
        #format_str = '[{"name": "%(name)s", "operator": "%(operator)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]'
        format_str = '[{"name": "%(name)s", "operator": "%(operator)s"}]' #, "value": {"type": "%(operator)s", "value": "%(value)s"}

        self.assertFieldValidationError(BatchActionsField, 'invalidfield', clean,
                                        format_str % {'name':     'boobies_size', #<---
                                                      'operator': 'upper',
                                                      #'value':     '90',
                                                     }
                                        )
        self.assertFieldValidationError(BatchActionsField, 'invalidfield', clean,
                                        format_str % {'name':     'header_filter_search_field', #not editable
                                                      'operator': 'upper',
                                                      #'value':    'Faye',
                                                     }
                                       )
        self.assertFieldValidationError(BatchActionsField, 'invalidfield', clean,
                                        format_str % {'name':     'civility', #type not managed
                                                      'operator': 'upper',
                                                      #'value':    '2011-5-12',
                                                     }
                                        )

    def test_clean_invalid_operator(self):
        clean = BatchActionsField(model=Contact).clean
        self.assertFieldValidationError(BatchActionsField, 'invalidoperator', clean,
                                        #'[{"name": "%(name)s", "operator": "%(operator)s", "value": {"type": "%(operator)s", "value": "%(value)s"}}]' % {
                                        '[{"name": "%(name)s", "operator": "%(operator)s"}]' % { #, "value": {"type": "%(operator)s", "value": "%(value)s"}
                                                'name':     'first_name',
                                                'operator': 'unknown_op', # <--
                                                #'value':    'Nana',
                                            }
                                       )

    def test_ok01(self):
        actions = BatchActionsField(model=Contact).clean(
                        '[{"name": "%(name)s", "operator": "%(operator)s"}]' % { #, "value": {"type": "%(operator)s", "value": "%(value)s"}
                                'name':     'description',
                                'operator': 'upper',
                                #'value':    value,
                            }
                    )
        self.assertEqual(1, len(actions))

        contact = Contact(first_name='faye', last_name='Valentine', description='yarglaaaaaaaaaaa')
        actions[0](contact)
        self.assertEqual('YARGLAAAAAAAAAAA', contact.description)

    def test_ok02(self): #several actions
        actions = BatchActionsField(model=Contact).clean(
                        '[{"name": "%(name01)s", "operator": "%(operator01)s"},'
                        ' {"name": "%(name02)s", "operator": "%(operator02)s"}]' % {
                                'name01': 'first_name', 'operator01': 'lower',
                                'name02': 'last_name',  'operator02': 'upper',
                                #'value':    value,
                            }
                    )
        self.assertEqual(2, len(actions))

        contact = Contact(first_name='faye', last_name='Valentine')
        for action in actions:
            action(contact)

        self.assertEqual('faye',      contact.first_name)
        self.assertEqual('VALENTINE', contact.last_name)
