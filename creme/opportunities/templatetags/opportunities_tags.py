# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import logging
from re import compile as compile_re

from django.template import Library, TemplateSyntaxError, Node as TemplateNode
from django.template.defaulttags import TemplateLiteral

logger = logging.getLogger(__name__)
register = Library()

@register.tag(name="is_in")
def is_in(parser, token):
    try:
        # Splitting by None == splitting by spaces.
        tag_name, args = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    match = compile_re(r'(\w+) (.*?) as (\w+)').search(args)

    if not match:
        raise TemplateSyntaxError, "%r tag had invalid arguments: %r" % (tag_name, args)

    value, list_value, var_name = match.groups()

    return IsInNode(TemplateLiteral(parser.compile_filter(value), value),
                    TemplateLiteral(parser.compile_filter(list_value), list_value),
                    var_name)

class IsInNode(TemplateNode):
    def __init__(self, value, list_var, var_name):
        self.value = value
        self.list_var = list_var
        self.var_name = var_name

    def __repr__(self):
        return "<IsIn node>"

    def render(self, context): #can raise template.VariableDoesNotExist...
        context[self.var_name] = self.value.eval(context).pk in self.list_var.eval(context)
        return ''
