################################################################################
#
# Copyright (c) 2020-2023 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
################################################################################

from django.core.exceptions import ValidationError
from django.template.base import Template, VariableNode
from django.utils.deconstruct import deconstructible
from django.utils.functional import lazy
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.utils.collections import OrderedSet


@deconstructible
class TemplateVariablesValidator:
    message = _('The following variables are invalid: %(vars)s')
    code = 'invalid_vars'

    def __init__(self, allowed_variables=(), message=None, code=None):
        self.allowed_variables = OrderedSet(allowed_variables)

        if message is not None:
            self.message = message

        if code is not None:
            self.code = code

        self._help_text = lazy(
            (lambda: gettext('You can use variables: {}').format(
                ' '.join('{{%s}}' % var for var in self._allowed_variables),
            )),
            str
        )()

    def __call__(self, value):
        """
        Validate that the input contains only valid variables.
        """
        allowed = self._allowed_variables
        invalid_vars = [
            var_name
            for var_node in Template(value).nodelist.get_nodes_by_type(VariableNode)
            if (var_name := var_node.filter_expression.var.var) not in allowed
        ]

        if invalid_vars:
            raise ValidationError(
                self.message,
                params={'vars': ', '.join(invalid_vars)},
                code=self.code,
            )

    def __eq__(self, other):
        return (
            isinstance(other, TemplateVariablesValidator)
            and self._allowed_variables == other._allowed_variables
        )

    @property
    def allowed_variables(self):
        yield from self._allowed_variables

    @allowed_variables.setter
    def allowed_variables(self, variables):
        self._allowed_variables = OrderedSet(variables)

    @property
    def help_text(self):
        return self._help_text
