# -*- coding: utf-8 -*-

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from creme.creme_core.tests.base import CremeTestCase
from creme.emails.core.validators import TemplateVariablesValidator


class ValidatorsTestCase(CremeTestCase):
    def test_template_variables01(self):
        v = TemplateVariablesValidator(['first_name', 'last_name'])

        with self.assertNoException():
            v('Hello {{first_name}}')

        with self.assertNoException():
            v('Hello {{last_name}}')

        with self.assertNoException():
            v('Hello {{first_name}} {{last_name}}')

        with self.assertRaises(ValidationError) as cm:
            v('Hello {{name}} {{invalid}}')

        exception = cm.exception
        self.assertListEqual(
            [
                _('The following variables are invalid: %(vars)s') % {
                    'vars': 'name, invalid',
                },
            ],
            exception.messages,
        )
        self.assertEqual('invalid_vars', exception.code)

        self.assertEqual(
            _('You can use variables: {}').format('{{first_name}} {{last_name}}'),
            v.help_text,
        )

    def test_template_variables02(self):
        "Other variables, Property <allowed_variables>"
        v = TemplateVariablesValidator()
        v.allowed_variables = ['name', 'nick_name']

        with self.assertNoException():
            v('Hi {{name}} {{nick_name}}')

        with self.assertRaises(ValidationError) as cm:
            v('Hello {{unknown}}')

        exception = cm.exception
        self.assertListEqual(
            [
                _('The following variables are invalid: %(vars)s') % {
                    'vars': 'unknown',
                },
            ],
            exception.messages,
        )

        self.assertEqual(
            _('You can use variables: {}').format('{{name}} {{nick_name}}'),
            v.help_text,
        )
